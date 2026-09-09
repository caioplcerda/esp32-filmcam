"""Reading frames off the card and writing developed masters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


@dataclass(frozen=True)
class Metadata:
    """Camera state at capture time, from the firmware's .TXT sidecar."""

    frame: int
    millis: int
    exposure: int
    gain: int
    awb_r: int
    awb_b: int
    framesize: str
    quality: int

    @classmethod
    def default(cls) -> "Metadata":
        """Used when a sidecar is missing or unreadable."""
        return cls(
            frame=0,
            millis=0,
            exposure=0,
            gain=0,
            awb_r=0,
            awb_b=0,
            framesize="UNKNOWN",
            quality=0,
        )


_INT_FIELDS = ("frame", "millis", "exposure", "gain", "awb_r", "awb_b", "quality")


def read_image(path: Path) -> np.ndarray:
    """Decode a JPEG to float32 (H, W, 3) in [0, 1], still sRGB-encoded."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no such image: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"{path.name} is empty (camera reset during the write)")
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        arr = np.asarray(rgb, dtype=np.float32) / 255.0
    return arr


def read_sidecar(path: Path) -> Metadata:
    """Parse a key=value sidecar. Missing or malformed entries fall back to defaults."""
    path = Path(path)
    defaults = Metadata.default()
    if not path.exists():
        return defaults

    values = {f.name: getattr(defaults, f.name) for f in Metadata.__dataclass_fields__.values()}
    for line in path.read_text(errors="replace").splitlines():
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        raw = raw.strip()
        if key not in values:
            continue
        if key in _INT_FIELDS:
            try:
                values[key] = int(raw)
            except ValueError:
                continue  # keep the default for this field
        else:
            if raw:
                values[key] = raw
    return Metadata(**values)


def write_tiff(path: Path, img: np.ndarray) -> None:
    """Write a 16-bit TIFF master from float32 sRGB-encoded data."""
    data = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    tifffile.imwrite(Path(path), (data * 65535.0 + 0.5).astype(np.uint16))


def write_jpeg(path: Path, img: np.ndarray, quality: int = 95) -> None:
    """Write a shareable JPEG from float32 sRGB-encoded data."""
    data = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    Image.fromarray((data * 255.0 + 0.5).astype(np.uint8)).save(
        Path(path), quality=quality, subsampling=0
    )
