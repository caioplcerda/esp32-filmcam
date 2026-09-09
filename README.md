# FilmCam

An AI-Thinker ESP32-CAM turned into a film camera.

Press the reset button and it takes one photograph. There is no preview, no
app, no Wi-Fi. Frames land on a microSD card. A Python "film lab" then develops
them into images that look like scanned 35 mm — real characteristic curves,
halation, grain sized in micrometres, lens character.

The camera is deliberately dumb: expose well, save the least-damaged JPEG it
can, sleep. Everything that makes a photograph look like film happens later, in
float, on a computer that can afford it.

## Hardware

| | |
|---|---|
| Board | AI-Thinker ESP32-CAM (OV2640, 4 MB PSRAM) |
| Programmer | ESP32-CAM-MB adapter (CH340) |
| Storage | any microSD card |
| Host | macOS or Linux with Python 3.12+ |

Nothing to solder. The reset button on the board is the shutter.

### Why RST and not BOOT

On this board `GPIO0` carries the camera's 20 MHz clock, and the BOOT button
shorts `GPIO0` to ground — so BOOT cannot be read as an input while the sensor
is alive. RST can: each press boots the chip, which takes one frame and sleeps
again. It costs about 2.4 s of shutter lag, most of it waiting for
auto-exposure to settle.

## Setup

```bash
# firmware toolchain
brew install arduino-cli
arduino-cli config init --overwrite
arduino-cli config add board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32

# film lab
cd filmlab
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Flashing

```bash
./firmware/flash.sh
```

Override the port with `FILMCAM_PORT=/dev/cu.usbserial-XXX` and the baud rate
with `FILMCAM_BAUD`. If it reports "Failed to connect", hold BOOT, tap RST,
release BOOT, and run it again.

The script compiles with `arduino-cli` but uploads with `esptool` at 115200,
because `arduino-cli` hard-codes 460800 for this board with no way to override
it, and the CH340 adapter cannot sustain that rate.

## Shooting

Press RST. Watch the red LED:

| Blinks | Meaning |
|--------|---------|
| 1 | Frame written |
| 2 | No SD card |
| 3 | Camera failed |
| 4 | SD write failed |

The board runs from any USB power source — no computer needed to shoot.

Each frame is saved as `/DCIM/FILM_nnnn.JPG` at 1600x1200, alongside a
`FILM_nnnn.TXT` sidecar recording the sensor's real exposure and gain. The film
lab reads that gain to give low-light frames coarser grain, exactly as a pushed
film would. Frame numbers are derived by scanning the card, so they survive
power cycles and never overwrite an existing photograph.

## Developing

```bash
cd filmlab
.venv/bin/filmlab stocks
.venv/bin/filmlab develop /Volumes/<CARD>/DCIM --stock portra400 --out ~/Pictures/FilmCam
```

Each frame produces a 16-bit TIFF master and a quality-95 JPEG. Frames already
developed are skipped unless you pass `--force`, so re-running on a card is
cheap. One corrupt frame fails that frame and the rest of the roll still
develops.

### Film stocks

| Id | Look |
|----|------|
| `portra400` | Warm, natural skin tones, restrained contrast |
| `gold200` | Golden, vivid yellows — the classic warm consumer film |
| `natura1600` | Fast night film: warm, open shadows, coarse grain |
| `cinestill800t` | Tungsten balance, cyan shadows, heavy red halation |
| `superia400` | Punchy, green-leaning contrast |
| `hp5` | High-contrast black and white with pronounced grain |

### Adjusting a photograph

Every effect takes a multiplier where `1.0` means "as the stock specifies":

```bash
--grain 0.7        # calmer grain
--saturation 1.3   # more colour
--halation 1.5     # stronger highlight bleed
--bloom  --vignette  --ca  --defocus
--rotate 180       # if the camera is mounted upside down
--neutralize 0.5   # stronger white-balance correction on this frame
```

`--lut yours.cube` uses a scanned film profile instead of the built-in curves.

## How the film look is built

`pipeline.py` orchestrates and contains no image maths of its own. The order is
the design argument:

1. **linearize** — halation, bloom and grain are energy-like and only behave
   physically in linear light
2. **camera calibration** — a fixed per-camera correction for the sensor's own
   colour bias
3. **white balance** — a light residual correction, not a full neutralisation
4. **characteristic curves** — the film's density response; the single largest
   contributor to an image reading as film
5. **saturation** — the camera shoots deliberately flat, so each stock restores
   its own colour intensity
6. **halation** — light reflecting off the film base and re-exposing the
   emulsion from behind; this is why Cinestill 800T looks the way it does
7. **bloom** — a wider, weaker, neutral lens glow
8. **grain** — sized in micrometres on a 36x24 mm frame and resolved against
   the output width, so a downscaled export does not get finer grain than its
   master; weighted by luminance and by the camera's own gain
9. **optics** — defocus, chromatic aberration, vignette: properties of the
   lens, not the emulsion
10. **delinearize**

Every stage is a pure function on `float32 (H, W, 3)` arrays in `[0, 1]`.
Stocks are data (`filmlab/src/filmlab/stock_data/*.toml`), never code.

### Colour calibration, and why interiors look warm

The OV2640's auto white balance drifts badly between frames — measured on this
unit, a white wall read R/G 0.908 on one frame and 1.022 on the next, and an
outdoor scene rendered with a magenta sky. So the firmware pins the sensor to a
fixed preset, and the film lab corrects the residual with a constant measured
from neutral surfaces **in daylight**.

That is deliberate. Real film carries a fixed colour balance; a daylight stock
shot under tungsten goes warm, and that is the look, not a defect. If you want
a given interior frame neutralised anyway, `--neutralize 1.0` forces full
grey-world correction on it.

The calibration constant lives in `filmlab/src/filmlab/balance.py`. It is
specific to the camera it was measured on — recalibrate if you build your own.

## Tuning a look

Stocks are plain TOML. Edit curves, cast, saturation, halation, grain or optics
and nothing in the pipeline needs to change. Golden-image tests then tell you
exactly what moved:

```bash
cd filmlab && .venv/bin/pytest tests/test_golden.py
```

A failure means the rendered output changed. If that was intended, regenerate
and review the diff as part of the change:

```bash
FILMLAB_UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_golden.py
```

Never regenerate to make a red test green without understanding why it moved —
that is the one way this safety net gets defeated.

## Tests

```bash
cd filmlab && .venv/bin/pytest
```

129 tests, 96% coverage. The firmware has no automated harness — it is verified
against real hardware using the checklist in `firmware/TESTING.md`.

## Known limitations

- **Dynamic range.** The sensor holds maybe eight stops. A bright sky with an
  interior in frame will clip; measured up to 70% of highlights on some frames.
- **Metering.** The meter averages the whole frame, so a backlit subject is
  metered dark. `AE_LEVEL` in the firmware biases exposure about a third of a
  stop; `+2` gives nearly a full stop at the cost of more clipping.
- **`jpeg_quality` must not be lowered below 4.** 0 is nominally the sensor's
  best but hangs the encoder at 1600x1200 — capture never completes.
- **Fixed-focus plastic lens.** Softness and edge falloff are physical.

## Layout

```
firmware/filmcam/filmcam.ino   the camera
firmware/flash.sh              compile + upload
firmware/TESTING.md            hardware bench checklist
filmlab/src/filmlab/           one module per pipeline stage
filmlab/src/filmlab/stock_data/  film stocks as TOML data
filmlab/tests/                 unit + golden-image tests
docs/superpowers/              design spec and implementation plan
```

## License

MIT — see [LICENSE](LICENSE).
