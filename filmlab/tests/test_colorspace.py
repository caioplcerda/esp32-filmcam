import numpy as np
import pytest

from filmlab.colorspace import linear_to_srgb, luminance, srgb_to_linear


def test_round_trip_is_identity():
    rng = np.random.default_rng(0)
    img = rng.random((8, 8, 3), dtype=np.float32)
    out = linear_to_srgb(srgb_to_linear(img))
    assert np.allclose(out, img, atol=1e-5)


def test_known_midpoint():
    # sRGB 0.5 is roughly 0.214 in linear light.
    img = np.full((1, 1, 3), 0.5, dtype=np.float32)
    assert srgb_to_linear(img)[0, 0, 0] == pytest.approx(0.2140, abs=1e-3)


def test_endpoints_are_preserved():
    img = np.array([[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]], dtype=np.float32)
    lin = srgb_to_linear(img)
    assert lin[0, 0, 0] == pytest.approx(0.0)
    assert lin[0, 1, 0] == pytest.approx(1.0)


def test_output_is_float32_and_input_untouched():
    img = np.full((4, 4, 3), 0.6, dtype=np.float32)
    original = img.copy()
    out = srgb_to_linear(img)
    assert out.dtype == np.float32
    assert np.array_equal(img, original)


def test_luminance_of_white_is_one():
    img = np.ones((2, 2, 3), dtype=np.float32)
    assert np.allclose(luminance(img), 1.0)


def test_luminance_weights_green_most():
    red = luminance(np.array([[[1.0, 0.0, 0.0]]], dtype=np.float32))
    green = luminance(np.array([[[0.0, 1.0, 0.0]]], dtype=np.float32))
    blue = luminance(np.array([[[0.0, 0.0, 1.0]]], dtype=np.float32))
    assert green > red > blue
