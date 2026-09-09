"""Lens character: vignette, lateral chromatic aberration, and slight defocus.

The OV2640's plastic lens already contributes some of this; the point here is to
make it consistent and deliberate rather than leaving it to a $3 optic.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from .stocks import Stock


def apply_vignette(img: np.ndarray, stock: Stock, strength: float = 1.0) -> np.ndarray:
    """Darken toward the corners with a smooth radial falloff."""
    x = np.asarray(img, dtype=np.float32)
    amount = float(stock.optics["vignette"]) * float(strength)
    if amount <= 0.0:
        return x.copy()

    height, width = x.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cy, cx = (height - 1) / 2.0, (width - 1) / 2.0
    # Normalise so the corners sit at radius 1.0 regardless of aspect ratio.
    norm = np.hypot(cy, cx)
    radius = np.hypot(yy - cy, xx - cx) / max(norm, 1e-6)
    falloff = (1.0 - amount * radius**2).astype(np.float32)

    return np.clip(x * falloff[..., None], 0.0, 1.0).astype(np.float32)


def apply_chromatic_aberration(
    img: np.ndarray, stock: Stock, strength: float = 1.0
) -> np.ndarray:
    """Scale red slightly out and blue slightly in about the frame centre."""
    x = np.asarray(img, dtype=np.float32)
    amount = float(stock.optics["ca"]) * float(strength)
    if amount <= 0.0:
        return x.copy()

    height, width = x.shape[:2]
    # A pixel of separation at the frame edge per unit of `amount`.
    k = amount / max(width, 1)

    def _scaled(channel: np.ndarray, factor: float) -> np.ndarray:
        matrix = np.array(
            [
                [factor, 0.0, (1.0 - factor) * (width - 1) / 2.0],
                [0.0, factor, (1.0 - factor) * (height - 1) / 2.0],
            ],
            dtype=np.float32,
        )
        return cv2.warpAffine(
            channel,
            matrix,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

    out = x.copy()
    out[..., 0] = _scaled(x[..., 0], 1.0 + k)
    out[..., 2] = _scaled(x[..., 2], 1.0 - k)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def apply_defocus(img: np.ndarray, stock: Stock, strength: float = 1.0) -> np.ndarray:
    """Take the digital edge off with a sub-pixel-scale blur."""
    x = np.asarray(img, dtype=np.float32)
    amount = float(stock.optics["defocus"]) * float(strength)
    if amount <= 0.0:
        return x.copy()
    return np.clip(
        gaussian_filter(x, sigma=(amount, amount, 0.0), mode="nearest"), 0.0, 1.0
    ).astype(np.float32)


def apply_optics(
    img: np.ndarray,
    stock: Stock,
    vignette: float = 1.0,
    ca: float = 1.0,
    defocus: float = 1.0,
) -> np.ndarray:
    """Run defocus, chromatic aberration and vignette in lens order."""
    out = apply_defocus(img, stock, strength=defocus)
    out = apply_chromatic_aberration(out, stock, strength=ca)
    return apply_vignette(out, stock, strength=vignette)
