"""White balance and stock colour cast.

The OV2640's auto-white-balance is inconsistent frame to frame. Normalising to a
neutral base first means the stock's cast is the only colour signature left, so
the same stock looks the same across a roll.
"""

from __future__ import annotations

import numpy as np

from .io_jpeg import Metadata
from .stocks import Stock

_EPS = 1e-6


def neutralize(img: np.ndarray, meta: Metadata) -> np.ndarray:
    """Grey-world normalisation: scale each channel so the means match.

    `meta` is accepted so callers have one stable signature across stages; the
    firmware's AWB registers are indices rather than gains, so the channel means
    are the reliable signal.
    """
    x = np.asarray(img, dtype=np.float32)
    means = x.reshape(-1, 3).mean(axis=0)
    target = float(means.mean())
    if target < _EPS:
        return x.copy()
    gains = target / np.maximum(means, _EPS)
    return np.clip(x * gains.astype(np.float32), 0.0, 1.0).astype(np.float32)


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
