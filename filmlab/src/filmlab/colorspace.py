"""sRGB <-> linear light conversion.

Every stage after decoding works in linear light. Halation, bloom and grain are
all energy-like operations: doing them on gamma-encoded values makes highlights
bloom too weakly and grain read as plastic.
"""

import numpy as np

# ITU-R BT.709 luma coefficients, matching the sRGB primaries.
_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def srgb_to_linear(img: np.ndarray) -> np.ndarray:
    """Undo the sRGB transfer function. Input and output are float32 in [0, 1]."""
    x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(
        np.float32
    )


def linear_to_srgb(img: np.ndarray) -> np.ndarray:
    """Apply the sRGB transfer function. Input and output are float32 in [0, 1]."""
    x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055).astype(
        np.float32
    )


def luminance(img: np.ndarray) -> np.ndarray:
    """Relative luminance of a linear RGB image, shaped (H, W)."""
    return (np.asarray(img, dtype=np.float32) @ _LUMA).astype(np.float32)
