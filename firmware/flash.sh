#!/usr/bin/env bash
# Compile and upload FilmCam firmware to the ESP32-CAM.
#
# The ESP32-CAM-MB adapter auto-resets into download mode via DTR/RTS.
# If upload fails with "Failed to connect", hold BOOT, tap RST, release BOOT,
# then re-run this script.
set -euo pipefail

PORT="${FILMCAM_PORT:-/dev/cu.usbserial-110}"
FQBN="esp32:esp32:esp32cam:PartitionScheme=huge_app,PSRAM=enabled"
SKETCH="$(cd "$(dirname "$0")" && pwd)/filmcam"

if [ ! -e "$PORT" ]; then
  echo "error: serial port $PORT not found. Is the ESP32-CAM plugged in?" >&2
  echo "available ports:" >&2
  ls /dev/cu.usbserial* 2>/dev/null >&2 || echo "  (none)" >&2
  exit 1
fi

echo "==> compiling $SKETCH"
arduino-cli compile --fqbn "$FQBN" "$SKETCH"

echo "==> uploading to $PORT"
arduino-cli upload --fqbn "$FQBN" --port "$PORT" "$SKETCH"

echo "==> done. Press RST on the board to take a photo."
