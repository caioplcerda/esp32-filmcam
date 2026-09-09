"""Optional Adobe .cube 3D LUT support.

The shipped stocks are analytic, so no third-party LUT is required. This exists
for anyone who owns a scanned profile and would rather use it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates


def load_cube(path: Path) -> np.ndarray:
    """Parse a .cube file into a (N, N, N, 3) float32 array indexed [b, g, r]."""
    size: int | None = None
    values: list[tuple[float, float, float]] = []

    for line in Path(path).read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.upper().startswith("LUT_3D_SIZE"):
            size = int(stripped.split()[-1])
            continue
        parts = stripped.split()
        if len(parts) == 3:
            try:
                values.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                continue  # a title or keyword line, not data

    if size is None:
        raise ValueError(f"{path}: no LUT_3D_SIZE declared")
    if len(values) != size**3:
        raise ValueError(
            f"{path}: expected {size**3} entries for size {size}, found {len(values)}"
        )
    # .cube data varies red fastest, so reshaping in (b, g, r) order is correct.
    return np.array(values, dtype=np.float32).reshape(size, size, size, 3)


def apply_lut(img: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Trilinearly interpolate an image through a 3D LUT."""
    x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    size = lut.shape[0]
    scale = size - 1
    coords = np.stack(
        [x[..., 2] * scale, x[..., 1] * scale, x[..., 0] * scale], axis=0
    )
    out = np.stack(
        [
            map_coordinates(lut[..., c], coords, order=1, mode="nearest")
            for c in range(3)
        ],
        axis=-1,
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)
