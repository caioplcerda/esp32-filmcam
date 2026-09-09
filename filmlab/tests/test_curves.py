import numpy as np
import pytest

from filmlab.curves import apply_curves
from filmlab.stocks import available_stocks, load_stock


@pytest.mark.parametrize("stock_id", available_stocks())
def test_curve_is_monotonic(stock_id):
    stock = load_stock(stock_id)
    ramp = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    img = np.stack([ramp, ramp, ramp], axis=-1)[None, :, :]
    out = apply_curves(img, stock)
    for c in range(3):
        assert np.all(np.diff(out[0, :, c]) >= -1e-6)


@pytest.mark.parametrize("stock_id", available_stocks())
def test_output_stays_in_range(stock_id):
    stock = load_stock(stock_id)
    rng = np.random.default_rng(1)
    img = rng.random((16, 16, 3), dtype=np.float32)
    out = apply_curves(img, stock)
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_shadows_are_lifted():
    # Negative film has a lifted toe: pure black never stays pure black.
    stock = load_stock("portra400")
    img = np.zeros((2, 2, 3), dtype=np.float32)
    assert apply_curves(img, stock).min() > 0.0


def test_input_is_not_mutated():
    stock = load_stock("portra400")
    img = np.full((4, 4, 3), 0.5, dtype=np.float32)
    original = img.copy()
    apply_curves(img, stock)
    assert np.array_equal(img, original)


def test_output_is_float32_and_same_shape():
    stock = load_stock("hp5")
    img = np.full((5, 7, 3), 0.3, dtype=np.float32)
    out = apply_curves(img, stock)
    assert out.dtype == np.float32
    assert out.shape == (5, 7, 3)
