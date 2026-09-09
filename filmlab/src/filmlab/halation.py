"""Halation: light passing through the emulsion, reflecting off the film base,
and re-exposing the layers from behind. It reads as a coloured glow hugging
bright edges, and it is why Cinestill 800T looks the way it does."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .colorspace import luminance
from .stocks import Stock


def apply_halation(img: np.ndarray, stock: Stock, strength: float = 1.0) -> np.ndarray:
    """Screen a blurred, tinted highlight mask back over the image."""
    x = np.asarray(img, dtype=np.float32)
    amount = float(stock.halation["strength"]) * float(strength)
    if amount <= 0.0:
        return x.copy()

    threshold = float(stock.halation["threshold"])
    tint = np.array(stock.halation["tint"], dtype=np.float32)
    sigma = max(float(stock.halation["radius_frac"]) * x.shape[1], 0.5)

    lum = luminance(x)
    headroom = max(1.0 - threshold, 1e-6)
    # Squared response: the effect should stay off until highlights are genuinely
    # bright, then climb quickly.
    mask = np.clip((lum - threshold) / headroom, 0.0, 1.0) ** 2
    glow = gaussian_filter(mask, sigma=sigma, mode="nearest")
    glow = np.clip(glow[..., None] * tint * amount, 0.0, 1.0)

    out = 1.0 - (1.0 - x) * (1.0 - glow)  # screen blend
    return np.clip(out, 0.0, 1.0).astype(np.float32)
