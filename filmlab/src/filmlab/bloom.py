"""Bloom: a wider, weaker, neutral glow from light scattering in the lens.

Distinct from halation, which happens inside the film and carries a colour.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .colorspace import luminance
from .stocks import Stock


def apply_bloom(img: np.ndarray, stock: Stock, strength: float = 1.0) -> np.ndarray:
    """Add a soft neutral glow around highlights."""
    x = np.asarray(img, dtype=np.float32)
    amount = float(stock.bloom["strength"]) * float(strength)
    if amount <= 0.0:
        return x.copy()

    threshold = float(stock.bloom["threshold"])
    sigma = max(float(stock.bloom["radius_frac"]) * x.shape[1], 0.5)

    lum = luminance(x)
    headroom = max(1.0 - threshold, 1e-6)
    mask = np.clip((lum - threshold) / headroom, 0.0, 1.0)
    glow = gaussian_filter(mask, sigma=sigma, mode="nearest")[..., None] * amount

    out = 1.0 - (1.0 - x) * (1.0 - np.clip(glow, 0.0, 1.0))
    return np.clip(out, 0.0, 1.0).astype(np.float32)
