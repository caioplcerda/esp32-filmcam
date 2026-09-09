import colorsys

import numpy as np

from filmlab.colorspace import luminance
from filmlab.saturation import apply_saturation
from filmlab.stocks import load_stock


def _grey_image():
    return np.full((32, 32, 3), 0.5, dtype=np.float32)


def _colourful_image():
    # Kept away from 0/1 extremes so boosting saturation does not clip and
    # distort luminance -- real frames rarely sit at the very edges either.
    rng = np.random.default_rng(7)
    img = rng.random((32, 32, 3)).astype(np.float32) * 0.4 + 0.3
    return img


def _mean_hsv_saturation(img: np.ndarray) -> float:
    sats = [
        colorsys.rgb_to_hsv(float(r), float(g), float(b))[1]
        for r, g, b in img.reshape(-1, 3)
    ]
    return float(np.mean(sats))


def test_grey_image_is_unchanged_at_any_amount():
    stock = load_stock("superia400")
    img = _grey_image()
    out = apply_saturation(img, stock, strength=1.0)
    assert np.allclose(out, img, atol=1e-5)


def test_superia_gains_more_saturation_than_portra():
    img = _colourful_image()
    superia = load_stock("superia400")
    portra = load_stock("portra400")

    out_superia = apply_saturation(img, superia)
    out_portra = apply_saturation(img, portra)

    sat_superia = _mean_hsv_saturation(out_superia)
    sat_portra = _mean_hsv_saturation(out_portra)

    assert sat_superia > sat_portra


def test_zero_strength_fully_desaturates():
    stock = load_stock("superia400")
    img = _colourful_image()
    out = apply_saturation(img, stock, strength=0.0)
    assert np.allclose(out[..., 0], out[..., 1], atol=1e-5)
    assert np.allclose(out[..., 1], out[..., 2], atol=1e-5)


def test_luminance_is_preserved():
    stock = load_stock("superia400")
    img = _colourful_image()
    out = apply_saturation(img, stock)
    assert np.allclose(luminance(out), luminance(img), atol=1e-3)


def test_input_not_mutated():
    stock = load_stock("superia400")
    img = _colourful_image()
    original = img.copy()
    apply_saturation(img, stock, strength=2.0)
    assert np.array_equal(img, original)


def test_output_dtype_and_range():
    stock = load_stock("superia400")
    img = _colourful_image()
    out = apply_saturation(img, stock, strength=2.0)
    assert out.dtype == np.float32
    assert out.min() >= 0.0 and out.max() <= 1.0
