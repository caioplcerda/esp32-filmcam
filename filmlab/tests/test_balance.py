import numpy as np

from filmlab.balance import apply_cast, neutralize, to_monochrome
from filmlab.io_jpeg import Metadata
from filmlab.stocks import load_stock


def test_neutralize_removes_a_colour_cast():
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 0] = 0.6  # heavy red cast
    img[..., 1] = 0.4
    img[..., 2] = 0.3
    out = neutralize(img, Metadata.default())
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
