"""Golden-image regression tests.

A change to any stage will change these renders. That is the point: the test
failing means "the look changed", and the reviewer decides whether that was
intended. Regenerate with:

    FILMLAB_UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_golden.py
"""

import os
from pathlib import Path

import numpy as np
import pytest

from filmlab.io_jpeg import Metadata
from filmlab.pipeline import DevelopOptions, develop
from filmlab.stocks import available_stocks, load_stock

GOLDEN_DIR = Path(__file__).parent / "goldens"
TOLERANCE = 1e-4


def _test_chart(size: int = 96) -> np.ndarray:
    """A fixed synthetic chart: greyscale ramp, colour patches, and a highlight."""
    chart = np.zeros((size, size, 3), dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, size, dtype=np.float32)
    chart[: size // 3] = ramp[None, :, None]
    third = size // 3
    for i, colour in enumerate(
        [(0.8, 0.1, 0.1), (0.1, 0.8, 0.1), (0.1, 0.1, 0.8), (0.8, 0.7, 0.6)]
    ):
        x0 = i * (size // 4)
        chart[third : 2 * third, x0 : x0 + size // 4] = colour
    chart[2 * third :] = 0.35
    chart[size - 20 : size - 8, size - 20 : size - 8] = 1.0  # highlight
    return chart


@pytest.mark.parametrize("stock_id", available_stocks())
def test_render_matches_golden(stock_id):
    rendered = develop(
        _test_chart(),
        load_stock(stock_id),
        Metadata.default(),
        DevelopOptions(seed=1234),
    )
    golden_path = GOLDEN_DIR / f"{stock_id}.npy"

    if os.environ.get("FILMLAB_UPDATE_GOLDEN"):
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        np.save(golden_path, rendered)
        pytest.skip(f"regenerated golden for {stock_id}")

    assert golden_path.exists(), (
        f"missing golden for {stock_id}; "
        "regenerate with FILMLAB_UPDATE_GOLDEN=1"
    )
    expected = np.load(golden_path)
    assert np.allclose(rendered, expected, atol=TOLERANCE), (
        f"{stock_id} render drifted from its golden; "
        "if this was intended, regenerate with FILMLAB_UPDATE_GOLDEN=1"
    )


def test_stocks_render_differently_from_each_other():
    chart = _test_chart()
    renders = {
        stock_id: develop(
            chart, load_stock(stock_id), Metadata.default(), DevelopOptions(seed=1234)
        )
        for stock_id in available_stocks()
    }
    ids = sorted(renders)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            assert not np.allclose(renders[a], renders[b], atol=1e-3), (
                f"{a} and {b} render identically"
            )
