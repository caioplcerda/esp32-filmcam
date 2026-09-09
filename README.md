# FilmCam

An AI-Thinker ESP32-CAM turned into a film-like still camera. The RST button is
the shutter. Frames land on the microSD card. A Python "film lab" on the Mac
develops them into images that look like scanned 35 mm.

## How it works

Press RST. The ESP32 boots, brings up the OV2640, lets auto-exposure settle,
captures one 1600x1200 JPEG, writes it plus a metadata sidecar to the card, and
goes back to deep sleep. There is no preview and no app — that is the point.

`GPIO0` on this board is the camera's clock line, so the BOOT button cannot be
read as a shutter. RST can, and costs roughly 2.4 s of lag while auto-exposure
settles.

## Setup

```bash
brew install arduino-cli
arduino-cli config init --overwrite
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32

cd filmlab
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Flashing

```bash
./firmware/flash.sh
```

Override the port with `FILMCAM_PORT=/dev/cu.usbserial-XXX ./firmware/flash.sh`.
Override the upload baud rate with `FILMCAM_BAUD=115200 ./firmware/flash.sh` (default is 115200; use a higher rate like 460800 only if your adapter supports it).
If it reports "Failed to connect": hold BOOT, tap RST, release BOOT, re-run.

## Shooting

Press RST. Watch the red LED:

| Blinks | Meaning |
|--------|---------|
| 1 | Frame written |
| 2 | No SD card |
| 3 | Camera failed |
| 4 | SD write failed |

The board runs from any USB power source. No computer required to shoot.

## Developing

Move the card to the Mac, then:

```bash
cd filmlab
.venv/bin/filmlab stocks
.venv/bin/filmlab develop /Volumes/<CARD>/DCIM --stock portra400 --out ~/Pictures/FilmCam
.venv/bin/filmlab develop ~/Pictures/raw/FILM_0007.JPG --stock cinestill800t --grain 1.3 --halation 1.5 --out ~/Pictures/FilmCam
```

Each frame produces a 16-bit TIFF master and a quality-95 JPEG. Already-developed
frames are skipped unless you pass `--force`.

### Stocks

| Id | Look |
|----|------|
| `portra400` | Warm, creamy skin tones, low contrast, fine grain |
| `cinestill800t` | Tungsten, cyan shadows, heavy red halation |
| `hp5` | High-contrast black and white, pronounced grain |
| `superia400` | Green-cyan cast, punchy consumer-film contrast |

Every effect takes a multiplier: `--grain`, `--halation`, `--bloom`,
`--vignette`, `--ca`, `--defocus`. `1.0` is the stock's own value. Pass
`--lut yours.cube` to use a scanned profile instead of the built-in curves.

`--rotate {0,90,180,270}` rotates each frame clockwise before developing —
it exists because the camera may be mounted rotated in its housing.

The firmware pins the OV2640 to a fixed white-balance preset (rather than
leaving it automatic — see `applyFlatProfile()`), and filmlab applies a fixed
per-camera calibration (`--no-camera-gains` disables it) that corrects that
preset's measured residual cast before anything else runs. `--neutralize`
(default `0.15`) then applies a light residual per-frame correction on top:
`0` applies none, `1` is full grey-world normalisation. The default is low
because the sensor is now calibrated at the source, so per-frame correction
should mostly be lifting small remaining drift, not doing the whole job.
It stays a partial correction rather than `1.0` because real film has a fixed
colour balance — a daylight stock under tungsten light is *supposed* to go
warm, that's the look; fully neutralising every frame would erase the scene's
own light along with the camera's drift.

## Tuning a look

Stocks are data. Edit `filmlab/src/filmlab/stock_data/<id>.toml` — curves, cast,
halation, grain and optics are all there, and nothing in the pipeline needs to
change. After editing, regenerate the golden renders and review the diff:

```bash
cd filmlab && FILMLAB_UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_golden.py
```

## Tests

```bash
cd filmlab && .venv/bin/pytest --cov=filmlab
```

Firmware has no automated harness; see `firmware/TESTING.md` for the bench list.

## Layout

```
firmware/filmcam/filmcam.ino   the camera
firmware/flash.sh              compile + upload
filmlab/src/filmlab/           one module per pipeline stage
filmlab/src/filmlab/stock_data/    stock profiles as TOML data
docs/superpowers/specs/        design
docs/superpowers/plans/        implementation plan
```
