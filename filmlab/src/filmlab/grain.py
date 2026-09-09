"""Film grain.

Grain size is specified in micrometres on a 36x24 mm frame and resolved against
the actual pixel width, so a downscaled export does not end up with finer grain
than its master. Amplitude is luminance-weighted: silver grain is most visible
in the midtones, and falls away in deep shadow and blown highlight.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .colorspace import luminance
from .io_jpeg import Metadata
from .stocks import Stock

_FRAME_WIDTH_UM = 36000.0  # 36 mm, the long edge of a 35 mm frame
_MAX_GAIN = 30.0  # OV2640 AGC range used to scale grain for pushed frames


def _noise(shape: tuple[int, int], sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Unit-variance blurred white noise."""
    raw = rng.standard_normal(shape).astype(np.float32)
    if sigma > 0.35:
        raw = gaussian_filter(raw, sigma=sigma, mode="wrap")
    std = float(raw.std())
    if std < 1e-6:
        return raw
    return (raw / std).astype(np.float32)


def apply_grain(
    img: np.ndarray,
    stock: Stock,
    meta: Metadata,
    strength: float = 1.0,
    seed: int | None = None,
) -> np.ndarray:
    """Add luminance-weighted monochrome and chroma grain."""
    x = np.asarray(img, dtype=np.float32)
    amplitude = float(stock.grain["amplitude"]) * float(strength)
    if amplitude <= 0.0:
        return x.copy()

    height, width = x.shape[:2]
    # Grain diameter in pixels; sigma is half that.
    grain_px = float(stock.grain["size_um"]) * width / _FRAME_WIDTH_UM
    sigma = max(grain_px * 0.5, 0.0)

    # A pushed (high-gain) frame earns coarser grain, as it would on film.
    gain_boost = 1.0 + min(float(meta.gain), _MAX_GAIN) / _MAX_GAIN
    if seed is None:
        seed = 0x5EED ^ int(meta.frame)
    rng = np.random.default_rng(seed)

    lum = np.clip(luminance(x), 0.0, 1.0)
    weight = (4.0 * lum * (1.0 - lum)).astype(np.float32)  # peaks at midtone

    mono = _noise((height, width), sigma, rng)[..., None]
    out = x + mono * (amplitude * gain_boost) * weight[..., None]

    chroma_amp = float(stock.grain.get("chroma_amplitude", 0.0)) * float(strength)
    if chroma_amp > 0.0:
        chroma = np.stack(
            [_noise((height, width), sigma, rng) for _ in range(3)], axis=-1
        )
        out = out + chroma * (chroma_amp * gain_boost) * weight[..., None]

    return np.clip(out, 0.0, 1.0).astype(np.float32)
