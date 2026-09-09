"""White balance and stock colour cast.

The OV2640's auto-white-balance is inconsistent frame to frame. Normalising to a
neutral base first means the stock's cast is the only colour signature left, so
the same stock looks the same across a roll.
"""

from __future__ import annotations

import numpy as np

from .colorspace import luminance
from .io_jpeg import Metadata
from .stocks import Stock

_EPS = 1e-6


def neutralize(img: np.ndarray, meta: Metadata, strength: float = 0.35) -> np.ndarray:
    """Partial, luminance-preserving grey-world correction.

    `meta` is accepted so callers have one stable signature across stages; the
    firmware's AWB registers are indices rather than gains, so the channel means
    are the reliable signal.

    Full grey-world normalisation (forcing the three channel means equal) corrects
    the scene's own light along with the camera's drift — a daylight-balanced stock
    under tungsten is *supposed* to go warm, that's the look. What actually needs
    fixing is the OV2640's frame-to-frame AWB drift, not the light itself. `strength`
    raises the grey-world gains to a power: 0.0 leaves the image untouched, 1.0 is
    full grey-world, and the default of 0.35 only partially corrects the cast.

    The result is rescaled to match the input's mean luminance, since ungained,
    unequal gains would otherwise darken or brighten the frame as a side effect of
    colour correction.
    """
    x = np.asarray(img, dtype=np.float32)
    means = x.reshape(-1, 3).mean(axis=0)
    target = float(means.mean())
    if target < _EPS:
        return x.copy()
    gains = (target / np.maximum(means, _EPS)).astype(np.float32)
    gains = gains ** np.float32(strength)
    out = x * gains
    before = float(luminance(x).mean())
    after = float(luminance(out).mean())
    if after > _EPS:
        out = out * np.float32(before / after)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def apply_cast(img: np.ndarray, stock: Stock) -> np.ndarray:
    """Apply the stock's per-channel colour cast."""
    x = np.asarray(img, dtype=np.float32)
    cast = np.array(stock.cast, dtype=np.float32)
    return np.clip(x * cast, 0.0, 1.0).astype(np.float32)


def to_monochrome(img: np.ndarray, stock: Stock) -> np.ndarray:
    """Collapse to the stock's panchromatic mix, returned as three equal channels."""
    x = np.asarray(img, dtype=np.float32)
    mix = np.array(stock.mono_mix, dtype=np.float32)
    mix = mix / max(float(mix.sum()), _EPS)
    grey = x @ mix
    return np.repeat(grey[..., None], 3, axis=-1).astype(np.float32)
