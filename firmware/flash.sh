#!/usr/bin/env bash
# Compile and upload FilmCam firmware to the ESP32-CAM.
#
# This script uses esptool.py directly instead of arduino-cli upload because
# the ESP32-CAM board profile sets a hardcoded upload speed of 460800 baud,
# which this CH340 adapter cannot sustain. esptool is invoked at a slower,
# configurable speed (default 115200) to work around the adapter's limitation.
# The ESP32-CAM-MB adapter auto-resets into download mode via DTR/RTS.
# If upload fails with "Failed to connect", hold BOOT, tap RST, release BOOT,
# then re-run this script.
set -euo pipefail

PORT="${FILMCAM_PORT:-/dev/cu.usbserial-110}"
BAUD="${FILMCAM_BAUD:-115200}"
FQBN="esp32:esp32:esp32cam:PartitionScheme=huge_app"
SKETCH="$(cd "$(dirname "$0")" && pwd)/filmcam"
BUILD_DIR="/tmp/filmcam-build-$$"

if [ ! -e "$PORT" ]; then
  echo "error: serial port $PORT not found. Is the ESP32-CAM plugged in?" >&2
  echo "available ports:" >&2
  ls /dev/cu.usbserial* 2>/dev/null >&2 || echo "  (none)" >&2
  exit 1
fi

# Resolve esptool path dynamically to avoid hardcoding versions.
ESPTOOL_DIR="$HOME/Library/Arduino15/packages/esp32/tools/esptool_py"
if [ ! -d "$ESPTOOL_DIR" ]; then
  echo "error: esptool_py not found at $ESPTOOL_DIR" >&2
  echo "Run: arduino-cli core install esp32:esp32" >&2
  exit 1
fi
ESPTOOL=$(find "$ESPTOOL_DIR" -name "esptool" -type f 2>/dev/null | head -1)
if [ -z "$ESPTOOL" ]; then
  echo "error: esptool binary not found in $ESPTOOL_DIR" >&2
  echo "Run: arduino-cli core install esp32:esp32" >&2
  exit 1
fi

# Resolve ESP32 core path dynamically to find boot_app0.bin.
CORE_DIR="$HOME/Library/Arduino15/packages/esp32/hardware/esp32"
if [ ! -d "$CORE_DIR" ]; then
  echo "error: esp32 core not found at $CORE_DIR" >&2
  echo "Run: arduino-cli core install esp32:esp32" >&2
  exit 1
fi
CORE_VERSION=$(find "$CORE_DIR" -maxdepth 1 -type d | sort -V | tail -1)
if [ ! -d "$CORE_VERSION" ]; then
  echo "error: no ESP32 core version found in $CORE_DIR" >&2
  echo "Run: arduino-cli core install esp32:esp32" >&2
  exit 1
fi
BOOT_APP0="$CORE_VERSION/tools/partitions/boot_app0.bin"
if [ ! -f "$BOOT_APP0" ]; then
  echo "error: boot_app0.bin not found at $BOOT_APP0" >&2
  exit 1
fi

echo "==> compiling $SKETCH"
mkdir -p "$BUILD_DIR"
arduino-cli compile --fqbn "$FQBN" --output-dir "$BUILD_DIR" "$SKETCH"

echo "==> uploading to $PORT at $BAUD baud"
"$ESPTOOL" --chip esp32 --port "$PORT" --baud "$BAUD" --before default-reset --after hard-reset \
  write-flash -z --flash-mode dio --flash-freq 80m --flash-size 4MB \
  0x1000 "$BUILD_DIR/filmcam.ino.bootloader.bin" \
  0x8000 "$BUILD_DIR/filmcam.ino.partitions.bin" \
  0xe000 "$BOOT_APP0" \
  0x10000 "$BUILD_DIR/filmcam.ino.bin"

rm -rf "$BUILD_DIR"

echo "==> done. Press RST on the board to take a photo."
