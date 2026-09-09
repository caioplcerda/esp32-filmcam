import numpy as np
import pytest

from filmlab.io_jpeg import Metadata
from filmlab.pipeline import DevelopOptions, develop
from filmlab.stocks import available_stocks, load_stock


def _scene(size=64):
    rng = np.random.default_rng(4)
    img = rng.random((size, size, 3)).astype(np.float32) * 0.4 + 0.2
    img[10:20, 10:20] = 1.0  # a highlight for halation to work on
    return img


@pytest.mark.parametrize("stock_id", available_stocks())
def test_develop_preserves_shape_dtype_and_range(stock_id):
    out = develop(_scene(), load_stock(stock_id), Metadata.default())
    assert out.shape == (64, 64, 3)
    assert out.dtype == np.float32
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_develop_does_not_mutate_input():
    img = _scene()
    original = img.copy()
    develop(img, load_stock("portra400"), Metadata.default())
    assert np.array_equal(img, original)


def test_develop_changes_the_image():
    img = _scene()
    out = develop(img, load_stock("cinestill800t"), Metadata.default())
    assert not np.allclose(out, img, atol=1e-3)


def test_hp5_output_is_greyscale_apart_from_chroma_free_grain():
    out = develop(_scene(), load_stock("hp5"), Metadata.default())
    assert np.allclose(out[..., 0], out[..., 1], atol=1e-3)
    assert np.allclose(out[..., 1], out[..., 2], atol=1e-3)


def test_develop_is_deterministic_for_a_fixed_seed():
    stock = load_stock("portra400")
    opts = DevelopOptions(seed=11)
    a = develop(_scene(), stock, Metadata.default(), opts)
    b = develop(_scene(), stock, Metadata.default(), opts)
    assert np.array_equal(a, b)


def test_camera_gains_none_differs_from_default():
    img = _scene()
    stock = load_stock("portra400")
    default_out = develop(img, stock, Metadata.default())
    no_gains_out = develop(img, stock, Metadata.default(), DevelopOptions(camera_gains=None))
    assert not np.allclose(default_out, no_gains_out, atol=1e-4)


def test_all_effects_disabled_still_returns_a_valid_image():
    opts = DevelopOptions(grain=0.0, halation=0.0, bloom=0.0, vignette=0.0, ca=0.0, defocus=0.0)
    out = develop(_scene(), load_stock("portra400"), Metadata.default(), opts)
    assert out.min() >= 0.0 and out.max() <= 1.0
