// FilmCam - ESP32-CAM as a film-like still camera.
//
// The RST button is the shutter. Each reset boots the chip, exposes one frame,
// writes it to the SD card, and returns to deep sleep. GPIO0 is the camera XCLK
// on this board and is never read as an input.

#include "esp_camera.h"
#include "esp_sleep.h"
#include "FS.h"
#include "SD_MMC.h"

// AI-Thinker ESP32-CAM pin map.
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

static const int STATUS_LED_PIN = 33;  // onboard red LED, active LOW
// Discarded so AEC/AWB converge. Measured on-board: the OV2640's AEC register
// climbs from ~624 at 2 settle frames to a ~1092 plateau by 16-20 frames (see
// firmware/TESTING.md). 18 frames at 80ms lands on that plateau while keeping
// total shutter lag near 2.4s rather than the ~3.2s that 20 frames at 100ms
// would cost.
static const int SETTLE_FRAMES = 18;
static const int JPEG_QUALITY = 0;     // esp32-camera scale is inverted (0-63); 0 is maximum quality, at the cost of larger files

// Blink codes reported before sleeping.
enum StatusCode {
  STATUS_OK = 1,
  STATUS_NO_SD = 2,
  STATUS_CAMERA_FAIL = 3,
  STATUS_WRITE_FAIL = 4,
};

static void blink(int times) {
  pinMode(STATUS_LED_PIN, OUTPUT);
  for (int i = 0; i < times; i++) {
    digitalWrite(STATUS_LED_PIN, LOW);  // active LOW
    delay(120);
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(180);
  }
}

static void sleepNow(StatusCode code) {
  blink((int)code);
  Serial.printf("filmcam: status=%d, sleeping\n", (int)code);
  Serial.flush();
  esp_deep_sleep_start();
}

static bool initCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_UXGA;
  config.jpeg_quality = JPEG_QUALITY;
  config.fb_count = 2;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  if (!psramFound()) {
    Serial.println("filmcam: PSRAM not found");
    return false;
  }
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("filmcam: esp_camera_init failed 0x%x\n", err);
    return false;
  }
  return true;
}

// Flat capture profile: the sensor's defaults over-sharpen and over-saturate,
// which destroys the headroom the film lab needs.
static void applyFlatProfile() {
  sensor_t *s = esp_camera_sensor_get();
  if (s == nullptr) return;
  s->set_saturation(s, -1);
  s->set_contrast(s, -1);
  s->set_sharpness(s, -2);
  s->set_denoise(s, 0);
  s->set_gainceiling(s, GAINCEILING_4X);
  // Real film has a FIXED colour balance -- that is what gives a stock its
  // identity. The OV2640's auto white balance drifts frame to frame (measured
  // R/G 0.91-1.29, B/G 0.66-1.15 across similar scenes), which is both
  // un-film-like and impossible to correct afterwards. Preset 4 measured
  // closest to neutral on a white wall, and the residual is corrected in
  // filmlab with the camera calibration gains.
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_wb_mode(s, 4);
  s->set_exposure_ctrl(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_lenc(s, 1);
  s->set_bpc(s, 1);
  s->set_wpc(s, 1);
}

// RTC memory does not survive an external reset, so the counter is derived
// from the card: find the highest FILM_nnnn.JPG in /DCIM and add one.
//
// A reset landing mid-write leaves a 0-byte FILM_nnnn.JPG behind -- the
// capture never completed, so there is no frame there, just litter that
// later fails development. Sweep those out while we're already scanning.
// Deleting has to wait until the directory iteration is done: removing an
// entry while openNextFile() is still walking it is not safe.
static int nextFrameNumber() {
  File dir = SD_MMC.open("/DCIM");
  if (!dir || !dir.isDirectory()) return 1;
  int highest = 0;
  static const int MAX_STALE = 32;
  String stale[MAX_STALE];
  int staleCount = 0;
  for (File f = dir.openNextFile(); f; f = dir.openNextFile()) {
    String name = String(f.name());
    int slash = name.lastIndexOf('/');
    if (slash >= 0) name = name.substring(slash + 1);
    bool empty = f.size() == 0;
    if (name.startsWith("FILM_") && name.endsWith(".JPG")) {
      if (empty) {
        if (staleCount < MAX_STALE) stale[staleCount++] = name;
      } else {
        int n = name.substring(5, name.length() - 4).toInt();
        if (n > highest) highest = n;
      }
    }
    f.close();
  }
  dir.close();

  for (int i = 0; i < staleCount; i++) {
    String path = "/DCIM/" + stale[i];
    if (SD_MMC.remove(path)) {
      Serial.printf("removed empty frame %s (reset during write)\n", stale[i].c_str());
    }
  }

  return highest + 1;
}

// The OV2640's real AEC value is split across three registers in the SENSOR
// bank. sensor_t::status holds driver-side cached values that are never
// refreshed, so reading the registers is the only way to record what the
// sensor actually did.
static uint16_t readAec(sensor_t *s) {
  s->set_reg(s, 0xFF, 0xFF, 0x01);           // select SENSOR bank
  uint16_t hi = s->get_reg(s, 0x45, 0x3F);   // AEC[15:10]
  uint16_t mid = s->get_reg(s, 0x10, 0xFF);  // AEC[9:2]
  uint16_t lo = s->get_reg(s, 0x04, 0x03);   // AEC[1:0]
  return (hi << 10) | (mid << 2) | lo;
}

static uint8_t readGain(sensor_t *s) {
  s->set_reg(s, 0xFF, 0xFF, 0x01);
  return (uint8_t)s->get_reg(s, 0x00, 0xFF);
}

static bool writeSidecar(const char *path, int frame, uint32_t elapsedMs) {
  sensor_t *s = esp_camera_sensor_get();
  File f = SD_MMC.open(path, FILE_WRITE);
  if (!f) return false;
  f.printf("frame=%d\n", frame);
  f.printf("millis=%lu\n", (unsigned long)elapsedMs);
  f.printf("exposure=%d\n", s ? readAec(s) : 0);
  f.printf("gain=%d\n", s ? readGain(s) : 0);
  f.printf("awb_r=%d\n", s ? s->status.wb_mode : 0);
  f.printf("awb_b=%d\n", s ? s->status.awb_gain : 0);
  f.printf("framesize=UXGA\n");
  f.printf("quality=%d\n", JPEG_QUALITY);
  f.flush();
  f.close();
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(50);
  Serial.println("\nfilmcam: shutter");

  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, HIGH);  // LED off

  // 1-bit mode keeps GPIO4/12/13 free and the flash LED usable.
  if (!SD_MMC.begin("/sdcard", true)) {
    sleepNow(STATUS_NO_SD);
  }
  if (SD_MMC.cardType() == CARD_NONE) {
    sleepNow(STATUS_NO_SD);
  }
  if (!SD_MMC.exists("/DCIM")) {
    SD_MMC.mkdir("/DCIM");
  }

  if (!initCamera()) {
    sleepNow(STATUS_CAMERA_FAIL);
  }
  applyFlatProfile();

  // Discard frames while auto-exposure and auto-white-balance converge.
  for (int i = 0; i < SETTLE_FRAMES; i++) {
    camera_fb_t *warm = esp_camera_fb_get();
    if (warm) esp_camera_fb_return(warm);
    delay(80);
  }

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb || fb->len == 0) {
    if (fb) esp_camera_fb_return(fb);
    sleepNow(STATUS_CAMERA_FAIL);
  }

  int frame = nextFrameNumber();
  char jpgPath[32];
  char txtPath[32];
  snprintf(jpgPath, sizeof(jpgPath), "/DCIM/FILM_%04d.JPG", frame);
  snprintf(txtPath, sizeof(txtPath), "/DCIM/FILM_%04d.TXT", frame);

  File out = SD_MMC.open(jpgPath, FILE_WRITE);
  if (!out) {
    esp_camera_fb_return(fb);
    sleepNow(STATUS_WRITE_FAIL);
  }
  size_t written = out.write(fb->buf, fb->len);
  out.flush();
  out.close();
  size_t expected = fb->len;
  esp_camera_fb_return(fb);

  if (written != expected) {
    SD_MMC.remove(jpgPath);
    sleepNow(STATUS_WRITE_FAIL);
  }
  if (!writeSidecar(txtPath, frame, millis())) {
    sleepNow(STATUS_WRITE_FAIL);
  }

  Serial.printf("filmcam: wrote %s (%u bytes)\n", jpgPath, (unsigned)written);
  sleepNow(STATUS_OK);
}

void loop() {
  // Never reached: setup() always ends in deep sleep.
}
