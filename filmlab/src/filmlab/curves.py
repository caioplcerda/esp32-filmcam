"""Per-channel characteristic curves.

This is the single largest contributor to a film look. It runs before halation
so the highlight effects feed on film-shaped highlights rather than sensor ones.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator

from .stocks import Stock

_LUT_SIZE = 1024
_CHANNELS = ("red", "green", "blue")


def _channel_lut(points: list[tuple[float, float]]) -> np.ndarray:
    """Build a 1-D lookup table from control points.

    PchipInterpolator is shape-preserving, so monotonic control points yield a
    monotonic curve with no overshoot between them.
    """
    xs = np.array([p[0] for p in points], dtype=np.float64)
    ys = np.array([p[1] for p in points], dtype=np.float64)
    interp = PchipInterpolator(xs, ys)
    grid = np.linspace(0.0, 1.0, _LUT_SIZE)
    return np.clip(interp(grid), 0.0, 1.0).astype(np.float32)


def apply_curves(img: np.ndarray, stock: Stock) -> np.ndarray:
    """Apply the stock's per-channel curves to a linear-light image."""
    x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    out = np.empty_like(x)
    idx = np.rint(x * (_LUT_SIZE - 1)).astype(np.int32)
    for c, channel in enumerate(_CHANNELS):
        lut = _channel_lut(stock.curves[channel])
        out[..., c] = lut[idx[..., c]]
    return out
