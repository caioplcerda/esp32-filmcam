import numpy as np

from filmlab.optics import (
    apply_chromatic_aberration,
    apply_defocus,
    apply_optics,
    apply_vignette,
)
from filmlab.stocks import load_stock


def test_vignette_darkens_corners_more_than_centre():
    stock = load_stock("portra400")
    img = np.full((64, 64, 3), 0.8, dtype=np.float32)
    out = apply_vignette(img, stock)
    assert out[0, 0, 0] < out[32, 32, 0]


def test_vignette_is_radially_symmetric():
    stock = load_stock("portra400")
    img = np.full((64, 64, 3), 0.8, dtype=np.float32)
    out = apply_vignette(img, stock)
    corners = [out[0, 0, 0], out[0, 63, 0], out[63, 0, 0], out[63, 63, 0]]
    assert max(corners) - min(corners) < 1e-5


def test_vignette_zero_strength_is_a_no_op():
    stock = load_stock("portra400")
    img = np.full((16, 16, 3), 0.8, dtype=np.float32)
    assert np.allclose(apply_vignette(img, stock, strength=0.0), img)


def test_chromatic_aberration_shifts_channels_apart():
    stock = load_stock("cinestill800t")
    img = np.zeros((64, 64, 3), dtype=np.float32)
    img[:, 8:12, :] = 1.0  # a vertical edge well off centre
    out = apply_chromatic_aberration(img, stock, strength=4.0)
    assert not np.allclose(out[..., 0], out[..., 2], atol=1e-4)


def test_chromatic_aberration_is_a_no_op_for_monochrome_stocks():
    stock = load_stock("hp5")  # ca = 0.0
    img = np.random.default_rng(0).random((32, 32, 3)).astype(np.float32)
    assert np.allclose(apply_chromatic_aberration(img, stock), img)


def test_defocus_reduces_high_frequency_detail():
    stock = load_stock("portra400")
    img = np.zeros((64, 64, 3), dtype=np.float32)
    img[::2, :, :] = 1.0  # one-pixel stripes
    out = apply_defocus(img, stock)
    assert out.std() < img.std()


def test_apply_optics_runs_all_three_and_stays_in_range():
    stock = load_stock("superia400")
    img = np.full((32, 32, 3), 0.6, dtype=np.float32)
    original = img.copy()
    out = apply_optics(img, stock)
    assert out.shape == img.shape
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.array_equal(img, original)
