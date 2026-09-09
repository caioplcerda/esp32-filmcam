import numpy as np

from filmlab.halation import apply_halation
from filmlab.stocks import load_stock


def _frame_with_bright_spot():
    img = np.full((64, 64, 3), 0.15, dtype=np.float32)
    img[30:34, 30:34] = 1.0
    return img


def test_no_highlights_means_no_change():
    stock = load_stock("cinestill800t")
    dark = np.full((32, 32, 3), 0.05, dtype=np.float32)
    assert np.allclose(apply_halation(dark, stock), dark, atol=1e-5)


def test_halation_spreads_beyond_the_highlight():
    stock = load_stock("cinestill800t")
    img = _frame_with_bright_spot()
    out = apply_halation(img, stock)
    # Sigma is radius_frac * WIDTH: on this 64px frame Cinestill gives sigma ~1.15px,
    # not the ~29px it gives on a real 1600px frame. Sample 2px above the square
    # (~1.7 sigma), where the glow is ~0.08 — beyond ~3 sigma it is numerically zero.
    assert out[28, 32, 0] > img[28, 32, 0]


def test_cinestill_halation_is_red_tinted():
    stock = load_stock("cinestill800t")
    out = apply_halation(_frame_with_bright_spot(), stock)
    glow = out[28, 32]
    assert glow[0] > glow[1] > glow[2]


def test_strength_multiplier_scales_the_effect():
    stock = load_stock("cinestill800t")
    img = _frame_with_bright_spot()
    weak = apply_halation(img, stock, strength=0.5)
    strong = apply_halation(img, stock, strength=2.0)
    assert strong[28, 32, 0] > weak[28, 32, 0]


def test_zero_strength_is_a_no_op():
    stock = load_stock("cinestill800t")
    img = _frame_with_bright_spot()
    assert np.allclose(apply_halation(img, stock, strength=0.0), img, atol=1e-5)


def test_output_stays_in_range_and_input_is_untouched():
    stock = load_stock("cinestill800t")
    img = _frame_with_bright_spot()
    original = img.copy()
    out = apply_halation(img, stock, strength=3.0)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.array_equal(img, original)
