"""Saturation: the colour intensity the flat capture profile deliberately gave up.

The firmware shoots with `set_saturation(s, -1)` on purpose — a flat, desaturated
profile that leaves headroom for the film lab to shape colour rather than fight
a camera-baked look. But headroom is only useful if something fills it back in,
and until this stage nothing did: every stage after decoding shrinks or holds
saturation (curves compress it, halation and bloom dilute it with white), none
restores it. This stage is the other half of that bargain. Each stock carries
its own colour intensity — Portra stays restrained, Superia goes punchy — so
the amount lives in stock data, not as a single global constant.
"""

from __future__ import annotations

import numpy as np

from .colorspace import luminance
from .stocks import Stock


def apply_saturation(img: np.ndarray, stock: Stock, strength: float = 1.0) -> np.ndarray:
    """Scale each pixel's distance from its own luminance by stock.saturation * strength."""
    x = np.asarray(img, dtype=np.float32)
    amount = float(stock.saturation) * float(strength)
    if amount == 1.0:
        return x.copy()

    grey = np.repeat(luminance(x)[..., None], x.shape[-1], axis=-1)
    out = grey + (x - grey) * amount
    return np.clip(out, 0.0, 1.0).astype(np.float32)
