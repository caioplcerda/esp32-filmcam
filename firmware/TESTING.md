# Firmware bench tests

The firmware has no automated test harness; it is verified by hand against the
real board. Run this list after any change to `filmcam.ino`.

| # | Action | Expected |
|---|--------|----------|
| 1 | Flash, press RST | LED blinks once; `/DCIM/FILM_0001.JPG` and `.TXT` exist |
| 2 | Press RST ten times | Ten sequentially numbered frames, no gaps, no overwrites |
| 3 | Unplug power, replug, press RST | Numbering continues from the highest file, does not reset to 1 |
| 4 | Remove the SD card, press RST | LED blinks twice; board sleeps, no reset loop |
| 5 | Cover the lens, press RST | Frame is written; sidecar `gain` is noticeably higher than a daylight frame, and `exposure` also differs — both come from the sensor's real AEC/AGC registers, not the driver's cached status |
| 6 | Point at a bright window, press RST | Highlights are not fully clipped across the whole frame |
| 7 | Time RST press to LED blink | Under 2.6 s |

If test 1 fails to upload with "Failed to connect": hold BOOT, tap RST, release
BOOT, re-run `flash.sh`.
| 8 | Shoot a backlit subject (a face under a lit ceiling, or against a window) | Subject renders brighter than with `AE_LEVEL = 0`; a bright sky in frame may clip more — that is the documented trade |
