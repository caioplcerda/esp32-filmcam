import numpy as np
import pytest

from filmlab.balance import apply_cast, neutralize, to_monochrome
from filmlab.colorspace import luminance
from filmlab.io_jpeg import Metadata
from filmlab.stocks import load_stock


def test_neutralize_removes_a_colour_cast():
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 0] = 0.6  # heavy red cast
    img[..., 1] = 0.4
    img[..., 2] = 0.3
    out = neutralize(img, Metadata.default(), strength=1.0)
    means = out.reshape(-1, 3).mean(axis=0)
    assert np.allclose(means, means[0], atol=1e-3)


def test_neutralize_leaves_a_neutral_image_alone():
    img = np.full((8, 8, 3), 0.5, dtype=np.float32)
    assert np.allclose(neutralize(img, Metadata.default()), img, atol=1e-4)


def test_neutralize_handles_pure_black_without_dividing_by_zero():
    img = np.zeros((4, 4, 3), dtype=np.float32)
    out = neutralize(img, Metadata.default())
    assert np.all(np.isfinite(out))


def test_cinestill_cast_is_cool_and_portra_cast_is_warm():
    grey = np.full((2, 2, 3), 0.5, dtype=np.float32)
    cine = apply_cast(grey, load_stock("cinestill800t"))
    portra = apply_cast(grey, load_stock("portra400"))
    assert cine[0, 0, 2] > cine[0, 0, 0]  # blue over red
    assert portra[0, 0, 0] > portra[0, 0, 2]  # red over blue


def test_monochrome_output_has_equal_channels():
    img = np.array([[[0.8, 0.2, 0.4]]], dtype=np.float32)
    out = to_monochrome(img, load_stock("hp5"))
    assert out[0, 0, 0] == out[0, 0, 1] == out[0, 0, 2]


def test_balance_does_not_mutate_input():
    img = np.full((4, 4, 3), 0.4, dtype=np.float32)
    original = img.copy()
    neutralize(img, Metadata.default())
    apply_cast(img, load_stock("portra400"))
    to_monochrome(img, load_stock("hp5"))
    assert np.array_equal(img, original)


def test_neutralize_does_not_fully_equalise_a_clipping_frame():
    """Pins a known limitation: clipping after normalisation leaves residual cast.

    On strongly-cast bright frames, grey-world normalisation may require gains > 1.0
    to match the target mean. When scaling saturates highlights, clipping becomes
    non-commutative: post-clip channel means no longer equal the target. We accept
    this residual cast to preserve exposure (normalising all gains down to guarantee
    equal means would darken the frame by ~1 stop, a poor trade on a small sensor).
    See neutralize() docstring and comments for the full reasoning.
    """
    # Strongly-cast image with a bright highlight that will saturate when its
    # weak channels are scaled up. Three dark pixels (red-cast) and one bright.
    img = np.zeros((2, 2, 3), dtype=np.float32)
    img[0, 0] = img[0, 1] = img[1, 0] = [0.7, 0.3, 0.3]  # dark, red-cast
    img[1, 1] = [0.7, 0.95, 0.95]  # bright, weak in G/B channels

    out = neutralize(img, Metadata.default(), strength=1.0)

    # Output is finite and within valid range [0, 1]
    assert np.all(np.isfinite(out))
    assert np.all((out >= 0.0) & (out <= 1.0))

    # Channel means are NOT equal due to saturation clipping of the bright pixel
    means = out.reshape(-1, 3).mean(axis=0)
    assert not np.allclose(means, means[0], atol=1e-3)


def test_neutralize_preserves_luminance():
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 0] = 0.6  # heavy red cast
    img[..., 1] = 0.4
    img[..., 2] = 0.1
    out = neutralize(img, Metadata.default(), strength=0.35)
    before = luminance(img).mean()
    after = luminance(out).mean()
    assert after == pytest.approx(before, rel=1e-3)


def test_neutralize_strength_scales_the_correction():
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 0] = 0.6  # heavy red cast
    img[..., 1] = 0.4
    img[..., 2] = 0.1

    none = neutralize(img, Metadata.default(), strength=0.0)
    assert np.allclose(none, img, atol=1e-4)

    full = neutralize(img, Metadata.default(), strength=1.0)
    full_means = full.reshape(-1, 3).mean(axis=0)
    assert np.allclose(full_means, full_means[0], atol=1e-3)

    default = neutralize(img, Metadata.default(), strength=0.35)
    default_means = default.reshape(-1, 3).mean(axis=0)
    default_spread = default_means.max() - default_means.min()
    none_spread = img.reshape(-1, 3).mean(axis=0).max() - img.reshape(-1, 3).mean(axis=0).min()
    full_spread = full_means.max() - full_means.min()
    assert full_spread < default_spread < none_spread
