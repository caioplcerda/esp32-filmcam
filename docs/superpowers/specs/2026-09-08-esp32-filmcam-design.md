# FilmCam — ESP32-CAM as a film-like still camera

**Date:** 2026-09-08
**Status:** Approved design

## 1. Purpose

Turn an AI-Thinker ESP32-CAM (OV2640) plus its CH340 MB adapter into a camera that
*behaves* like a film camera and *produces* images that look like scanned 35 mm film.

Two success criteria:

1. **Behaviour** — one physical button press produces exactly one frame. No preview,
   no app, no shutter menu. Press, wind, shoot.
2. **Look** — output is indistinguishable at a glance from a lab scan of the chosen
   stock: correct colour cast, characteristic curve, halation, and grain.

## 2. Hardware baseline

| Item | Value |
|---|---|
| Board | AI-Thinker ESP32-CAM, OV2640, 4 MB PSRAM |
| Adapter | ESP32-CAM-MB, CH340 (VID `0x1A86` / PID `0x7523`) |
| Serial port | `/dev/cu.usbserial-110` |
| Storage | microSD, present in module slot |
| Host | macOS (Darwin 25.2), Python 3.14 |

### 2.1 The GPIO0 constraint

On this board `GPIO0` is the OV2640 `XCLK` line and carries a continuous 20 MHz
clock while the sensor is initialised. The MB adapter's BOOT button shorts `GPIO0`
to ground. Therefore **the BOOT button cannot be read as a shutter input while the
camera is alive** — pressing it both shorts a push-pull output and starves the
sensor of its clock.

Three options were considered:

| Option | Verdict |
|---|---|
| External tactile button on `GPIO13`→GND | Best latency (~250 ms) but requires wiring. Rejected: user wants no added hardware. |
| BOOT button + `esp_camera_deinit()` / PWDN cycling between shots | Uses the existing button with no wiring, but `deinit` + PWDN is reported to cause spurious reboots. Rejected: reliability. |
| **RST button + deep sleep** | **Chosen.** Zero wiring, no pin conflict, fully reliable. ~1.1 s shutter lag. |

### 2.2 Chosen shutter model

The **RST button is the shutter**. Each press resets the ESP32, which boots,
initialises the sensor, settles exposure, captures one frame, writes it to SD, and
enters deep sleep. The BOOT button stays free for its real job — entering download
mode when flashing.

The ~1.1 s lag is accepted, and is consistent with the product intent: a film
camera gives no preview and rewards deliberate framing.

## 3. Architecture

```
[ESP32-CAM]  RST press -> boot -> mount SD -> init OV2640 -> AE/AWB settle
             -> capture UXGA JPEG -> write /DCIM/FILM_nnnn.JPG + .TXT sidecar
             -> deep sleep
                              |
                       (microSD card, moved by hand to the Mac)
                              v
[Mac film lab]  filmlab CLI: decode -> linearize -> white balance -> stock curve
                -> halation -> bloom -> grain -> optics -> encode
                -> 16-bit TIFF master + quality-95 JPEG
```

### 3.1 Why the work is split

The OV2640 emits JPEG only — there is no RAW path. The ESP32 has no FPU headroom
for per-pixel float work at 1600x1200; on-device emulation would take 3–5 s per
frame and could only afford a baked tone curve, not real grain or halation.

So the firmware stays deliberately dumb and fast: expose well, save the least-damaged
JPEG possible, sleep. All emulation happens on the Mac in float32, where a frame can
be processed properly.

## 4. Firmware

Location: `firmware/filmcam/filmcam.ino`. Built with `arduino-cli` against the
`esp32` core (which bundles `esp32-camera`).

### 4.1 Boot sequence

1. Configure `GPIO33` (onboard red LED) for status output.
2. Mount SD with `SD_MMC.begin("/sdcard", true)` — **1-bit mode**. This frees
   `GPIO4`, `GPIO12`, `GPIO13` and keeps the flash LED on `GPIO4` usable.
3. `esp_camera_init()` with the AI-Thinker pin map, `FRAMESIZE_UXGA` (1600x1200),
   `jpeg_quality = 4`, `fb_count = 2`, `CAMERA_FB_IN_PSRAM`, `PIXFORMAT_JPEG`.
4. Apply the flat capture profile (§4.2).
5. Discard the first 5 frames so auto-exposure and auto-white-balance converge.
6. Capture frame 6. This is the photograph.
7. Determine the frame number (§4.3), write the JPEG and its sidecar, `f.flush()`
   and `f.close()` before doing anything else.
8. `esp_deep_sleep_start()`.

### 4.2 Flat capture profile

The sensor's defaults over-sharpen and over-saturate, which destroys the headroom the
film lab needs. Before capture, set:

- `saturation = -1`
- `contrast = -1`
- `sharpness = -2`
- `denoise = 0`
- gain ceiling `GAINCEILING_4X` (limits sensor noise, since grain is added later
  deliberately rather than inherited accidentally)
- AEC and AWB left on automatic

### 4.3 Frame numbering

RTC memory does **not** survive an external reset, so the counter cannot live there.
On boot the firmware scans `/DCIM` for the highest existing `FILM_nnnn.JPG` index and
writes `n+1`. This is O(files-in-directory) per shot, which is acceptable at the
scale of a roll and is robust to card swaps and power loss.

### 4.4 Sidecar metadata

Every `FILM_nnnn.JPG` is accompanied by `FILM_nnnn.TXT` containing key=value lines:

```
frame=1
millis=812
exposure=<AEC value>
gain=<AGC value>
awb_r=<red gain>
awb_b=<blue gain>
framesize=UXGA
quality=4
```

The film lab reads `gain` to scale grain (a high-gain frame was shot in low light and
earns coarser grain, exactly as a pushed film would).

### 4.5 Status codes

The red LED on `GPIO33` blinks before sleep:

| Blinks | Meaning |
|---|---|
| 1 | Frame written successfully |
| 2 | SD card missing or unmountable |
| 3 | Camera init or capture failed |
| 4 | SD write failed (card full or read-only) |

There is no preview and no serial dependency: the camera is fully usable on a USB
power bank with no host attached.

## 5. Film lab

Location: `filmlab/`, a Python package with a `filmlab` console entry point.
Dependencies: `numpy`, `Pillow`, `opencv-python`, `scipy`, `tifffile`.

### 5.1 Module boundaries

Each stage is one module with one public function taking and returning a float32
linear RGB array, so it can be tested in isolation:

| Module | Responsibility |
|---|---|
| `io_jpeg.py` | decode JPEG, read the sidecar, encode TIFF/JPEG |
| `colorspace.py` | sRGB <-> linear, working-space conversions |
| `balance.py` | neutralise the camera's AWB gains, then apply the stock's cast |
| `curves.py` | per-channel density curves, evaluated from stock data |
| `halation.py` | highlight mask -> gaussian -> tinted screen blend |
| `bloom.py` | soft highlight glow |
| `grain.py` | luminance-weighted monochrome + chroma grain layers |
| `optics.py` | vignette, lateral chromatic aberration, slight defocus |
| `stocks.py` | load stock definitions from `stock_data/*.toml` |
| `lut.py` | optional `.cube` LUT loading, applied in place of `curves` |
| `pipeline.py` | ordering and orchestration only — no image maths |
| `cli.py` | argument parsing, file discovery, progress output |

### 5.2 Pipeline order

1. **decode** JPEG to float32 [0,1]
2. **linearize** — undo sRGB gamma. All subsequent maths is in linear light, which
   is what makes halation and bloom behave physically rather than looking pasted on.
3. **white balance** — divide out the sidecar AWB gains to get a neutral base, then
   apply the stock's own cast.
4. **stock curve** — per-channel characteristic curves. Negative film has a long
   shoulder and a lifted toe; this is the single largest contributor to "looks like
   film" and is applied before any highlight effects so halation feeds on
   film-shaped highlights.
5. **halation** — threshold the luminance, gaussian blur the mask, tint it, screen-blend
   back. Strength and tint are per-stock. This is Cinestill 800T's signature (its
   missing anti-halation layer is literally why the stock exists).
6. **bloom** — a wider, weaker, neutral glow on top of halation.
7. **grain** — sampled noise scaled so grain size is specified in micrometres on a
   36x24 mm frame and resolved against the actual output resolution, so a downscaled
   export does not get finer grain than the master. Amplitude is luminance-weighted
   (strongest in the midtones, suppressed in deep shadow and blown highlight) and
   further scaled by the sidecar `gain`.
8. **optics** — vignette, subtle lateral chromatic aberration, slight defocus.
9. **delinearize** and encode.

### 5.3 Stocks

Four profiles ship as `stock_data/*.toml` data, not code, so they can be tuned without
touching the pipeline:

| Stock | Character |
|---|---|
| `portra400` | Warm, lifted shadows, low contrast, creamy skin tones, fine grain, soft red-orange halation |
| `cinestill800t` | Tungsten-balanced, cyan shadows, heavy red halation, coarse grain |
| `hp5` | Black & white, panchromatic channel mix, high contrast, pronounced grain, no halation tint |
| `superia400` | Green-cyan cast, punchy contrast, medium grain |

A stock file declares: channel curves (control points), colour cast matrix, halation
strength/radius/tint, bloom strength/radius, grain micrometre size and amplitude
curve, vignette amount, and CA amount.

Analytic profiles are used rather than shipping third-party scanned LUTs, to avoid a
licensing dependency. `--lut file.cube` remains available for anyone who has their own.

### 5.4 CLI

```bash
filmlab develop /Volumes/<CARD>/DCIM --stock portra400 --out ~/Pictures/FilmCam
filmlab develop shot.jpg --stock cinestill800t --grain 1.3 --halation 1.5
filmlab contact ~/Pictures/FilmCam/roll_001
filmlab stocks
```

- `develop` processes a file, a directory, or a mounted card. Outputs a 16-bit TIFF
  master plus a quality-95 JPEG per frame. Skips frames already developed unless
  `--force`.
- `--grain`, `--halation`, `--bloom`, `--vignette` are multipliers on the stock's
  values, defaulting to 1.0.
- `contact` renders a contact sheet with a 35 mm rebate border and frame numbers.
- `stocks` lists available profiles.

Errors are explicit: a missing sidecar degrades gracefully to defaults with a
warning; an unreadable JPEG fails that frame and continues the roll, and the exit
code reflects whether any frame failed.

## 6. Testing

### 6.1 Film lab — pytest, TDD, 80%+ coverage

- **Unit, per stage.** `linearize`/`delinearize` round-trip within tolerance; curves
  are monotonic across the full domain; grain has the expected mean and variance and
  is luminance-weighted as specified; halation conserves total energy within bounds
  and is zero on an image with no highlights; vignette is radially symmetric.
- **Golden images.** For each stock, render a fixed synthetic test chart and compare
  a downscaled hash against a committed reference, so a pipeline change that alters
  the look is caught deliberately rather than by eye.
- **CLI integration.** Develop a small fixture directory end-to-end; assert both
  outputs exist, TIFF is 16-bit, already-developed frames are skipped, and a corrupt
  frame does not abort the roll.
- **Sidecar parsing.** Well-formed, missing, and malformed sidecars.

### 6.2 Firmware — manual bench checklist

Documented in `firmware/TESTING.md`, executed by hand:

1. Flash, press RST, confirm one file appears on the card and the LED blinks once.
2. Press RST ten times; confirm ten sequentially numbered frames.
3. Power-cycle the board, press RST; confirm numbering continues rather than restarting.
4. Remove the card, press RST; confirm two blinks and no crash loop.
5. Cover the lens and shoot; confirm the sidecar reports a high gain value.
6. Run the frames through `filmlab develop` for each stock and inspect.

## 7. Repository layout

```
esp32-filmcam/
  README.md
  docs/superpowers/specs/2026-09-08-esp32-filmcam-design.md
  firmware/
    filmcam/filmcam.ino
    TESTING.md
    flash.sh                 # arduino-cli compile + upload to /dev/cu.usbserial-110
  filmlab/
    pyproject.toml
    src/filmlab/*.py
    src/filmlab/stock_data/*.toml
    tests/
```

## 8. Out of scope

Deliberately excluded to keep the first version buildable and honest:

- Wi-Fi, streaming, and any web UI — the camera is offline by design.
- On-device film emulation.
- Video or burst capture.
- Automatic card detection / watch-folder daemon on the Mac. `filmlab develop` is
  run explicitly.
- Light leaks, dust, and scratch overlays. These are a later addition to the optics
  stage, not a first-version requirement.
