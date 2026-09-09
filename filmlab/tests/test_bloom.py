import numpy as np

from filmlab.bloom import apply_bloom
from filmlab.stocks import load_stock


def _frame_with_bright_spot():
    img = np.full((64, 64, 3), 0.15, dtype=np.float32)
    img[30:34, 30:34] = 1.0
    return img


def test_bloom_brightens_around_highlights():
    stock = load_stock("portra400")
    img = _frame_with_bright_spot()
    out = apply_bloom(img, stock)
    assert out[26, 30, 1] > img[26, 30, 1]


def test_bloom_is_neutral_in_colour():
    stock = load_stock("portra400")
    out = apply_bloom(_frame_with_bright_spot(), stock)
    glow = out[26, 30]
    assert abs(float(glow[0] - glow[2])) < 1e-3


def test_zero_strength_is_a_no_op():
    stock = load_stock("portra400")
    img = _frame_with_bright_spot()
    assert np.allclose(apply_bloom(img, stock, strength=0.0), img, atol=1e-5)


def test_output_in_range_and_input_untouched():
    stock = load_stock("portra400")
    img = _frame_with_bright_spot()
    original = img.copy()
    out = apply_bloom(img, stock, strength=2.0)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.array_equal(img, original)
