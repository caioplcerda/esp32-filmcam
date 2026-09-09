import numpy as np

from filmlab.grain import apply_grain
from filmlab.io_jpeg import Metadata
from filmlab.stocks import load_stock


def _flat(value, size=96):
    return np.full((size, size, 3), value, dtype=np.float32)


def test_grain_adds_variance_to_a_flat_frame():
    stock = load_stock("hp5")
    img = _flat(0.5)
    out = apply_grain(img, stock, Metadata.default(), seed=1)
    assert out.std() > img.std()


def test_grain_preserves_mean_brightness():
    stock = load_stock("hp5")
    img = _flat(0.5)
    out = apply_grain(img, stock, Metadata.default(), seed=1)
    assert abs(float(out.mean() - img.mean())) < 0.01


def test_grain_is_strongest_in_the_midtones():
    stock = load_stock("hp5")
    meta = Metadata.default()
    mid = apply_grain(_flat(0.5), stock, meta, seed=2).std()
    shadow = apply_grain(_flat(0.02), stock, meta, seed=2).std()
    highlight = apply_grain(_flat(0.98), stock, meta, seed=2).std()
    assert mid > shadow
    assert mid > highlight


def test_higher_camera_gain_gives_coarser_grain():
    stock = load_stock("portra400")
    low = apply_grain(_flat(0.5), stock, Metadata.default(), seed=3).std()
    pushed = Metadata.default().__class__(
        frame=1, millis=0, exposure=0, gain=30, awb_r=0, awb_b=0,
        framesize="UXGA", quality=4,
    )
    high = apply_grain(_flat(0.5), stock, pushed, seed=3).std()
    assert high > low


def test_same_seed_is_reproducible():
    stock = load_stock("portra400")
    meta = Metadata.default()
    a = apply_grain(_flat(0.5), stock, meta, seed=7)
    b = apply_grain(_flat(0.5), stock, meta, seed=7)
    assert np.array_equal(a, b)


def test_frame_number_seeds_grain_when_seed_is_omitted():
    stock = load_stock("portra400")
    m1 = Metadata.default().__class__(
        frame=1, millis=0, exposure=0, gain=0, awb_r=0, awb_b=0,
        framesize="UXGA", quality=4,
    )
    m2 = Metadata.default().__class__(
        frame=2, millis=0, exposure=0, gain=0, awb_r=0, awb_b=0,
        framesize="UXGA", quality=4,
    )
    assert not np.array_equal(
        apply_grain(_flat(0.5), stock, m1), apply_grain(_flat(0.5), stock, m2)
    )


def test_zero_strength_is_a_no_op():
    stock = load_stock("portra400")
    img = _flat(0.5)
    assert np.allclose(apply_grain(img, stock, Metadata.default(), strength=0.0), img)


def test_output_in_range_and_input_untouched():
    stock = load_stock("hp5")
    img = _flat(0.5)
    original = img.copy()
    out = apply_grain(img, stock, Metadata.default(), strength=4.0, seed=5)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.array_equal(img, original)


def _lag1_correlation(width, stock_id, seed=1):
    """Horizontal lag-1 autocorrelation of the extracted grain, red channel.

    Blurred grain is spatially correlated; independent per-pixel noise is not.
    This is what distinguishes real grain-size behaviour from white noise.
    """
    img = np.full((64, width, 3), 0.5, dtype=np.float32)
    out = apply_grain(img, load_stock(stock_id), Metadata.default(), seed=seed)
    noise = (out - img)[..., 0]
    a, b = noise[:, :-1].ravel(), noise[:, 1:].ravel()
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).mean() / (a.std() * b.std()))


def test_grain_is_spatially_correlated_at_real_frame_width():
    # sigma = size_um * width / 36000 * 0.5, and the blur is skipped below 0.35.
    # At 96px Portra gives sigma 0.033 (no blur, corr ~0.00); at 1600px it gives
    # 0.556 (blurred, corr ~0.36). This pins the resolution-correct grain-size
    # mechanism, which no other test reaches.
    assert abs(_lag1_correlation(96, "portra400")) < 0.05
    assert _lag1_correlation(1600, "portra400") > 0.25


def test_coarser_stock_has_larger_grain_at_the_same_width():
    # HP5's 45um against Portra's 25um at the same frame width: coarser grain
    # means a wider blur and so stronger spatial correlation (~0.77 vs ~0.36).
    assert _lag1_correlation(1600, "hp5") > _lag1_correlation(1600, "portra400")
