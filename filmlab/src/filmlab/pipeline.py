"""Stage ordering. This module orchestrates; it contains no image maths.

Order matters:
  * curves run before halation so highlight effects feed on film-shaped highlights
  * grain runs after the tonal work so it is not squashed by a curve
  * optics run last, since they are properties of the lens, not the emulsion
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .balance import apply_cast, neutralize, to_monochrome
from .bloom import apply_bloom
from .colorspace import linear_to_srgb, srgb_to_linear
from .curves import apply_curves
from .grain import apply_grain
from .halation import apply_halation
from .io_jpeg import Metadata
from .lut import apply_lut
from .optics import apply_optics
from .stocks import Stock


@dataclass(frozen=True)
class DevelopOptions:
    """Per-run multipliers on the stock's values. 1.0 means "as the stock says"."""

    grain: float = 1.0
    halation: float = 1.0
    bloom: float = 1.0
    vignette: float = 1.0
    ca: float = 1.0
    defocus: float = 1.0
    lut: np.ndarray | None = field(default=None, compare=False)
    seed: int | None = None


def develop(
    img: np.ndarray,
    stock: Stock,
    meta: Metadata,
    options: DevelopOptions = DevelopOptions(),
) -> np.ndarray:
    """Develop one frame. sRGB-encoded float32 in, sRGB-encoded float32 out."""
    linear = srgb_to_linear(img)
    linear = neutralize(linear, meta)

    if options.lut is not None:
        linear = apply_lut(linear, options.lut)
    else:
        linear = apply_cast(linear, stock)
        linear = apply_curves(linear, stock)

    if stock.monochrome:
        linear = to_monochrome(linear, stock)

    linear = apply_halation(linear, stock, strength=options.halation)
    linear = apply_bloom(linear, stock, strength=options.bloom)
    linear = apply_grain(linear, stock, meta, strength=options.grain, seed=options.seed)
    linear = apply_optics(
        linear,
        stock,
        vignette=options.vignette,
        ca=options.ca,
        defocus=options.defocus,
    )
    return linear_to_srgb(linear)
