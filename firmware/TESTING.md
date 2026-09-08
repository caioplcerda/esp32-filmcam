# Firmware bench tests

The firmware has no automated test harness; it is verified by hand against the
real board. Run this list after any change to `filmcam.ino`.

| # | Action | Expected |
|---|--------|----------|
| 1 | Flash, press RST | LED blinks once; `/DCIM/FILM_0001.JPG` and `.TXT` exist |
| 2 | Press RST ten times | Ten sequentially numbered frames, no gaps, no overwrites |
| 3 | Unplug power, replug, press RST | Numbering continues from the highest file, does not reset to 1 |
| 4 | Remove the SD card, press RST | LED blinks twice; board sleeps, no reset loop |
| 5 | Cover the lens, press RST | Frame is written; sidecar `gain` is noticeably higher than a daylight frame |
| 6 | Point at a bright window, press RST | Highlights are not fully clipped across the whole frame |
| 7 | Time RST press to LED blink | Under 1.5 s |

If test 1 fails to upload with "Failed to connect": hold BOOT, tap RST, release
BOOT, re-run `flash.sh`.
