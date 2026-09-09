"""Film stock profiles, loaded from TOML data files.

Stocks are data, not code: a look can be retuned without touching the pipeline.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_STOCK_DIR_NAME = "stock_data"

_DEFAULT_OPTICS = {"vignette": 0.20, "ca": 0.35, "defocus": 0.25}
_DEFAULT_BLOOM = {"strength": 0.10, "threshold": 0.85, "radius_frac": 0.030}


@dataclass(frozen=True)
class Stock:
    id: str
    name: str
    monochrome: bool
    mono_mix: tuple[float, float, float]
    cast: tuple[float, float, float]
    saturation: float
    curves: dict[str, list[tuple[float, float]]]
    halation: dict
    bloom: dict
    grain: dict
    optics: dict


def _stock_dir() -> Path:
    return Path(__file__).parent / _STOCK_DIR_NAME


def available_stocks() -> list[str]:
    """Sorted ids of every stock profile shipped with the package."""
    return sorted(p.stem for p in _stock_dir().glob("*.toml"))


def load_stock(stock_id: str) -> Stock:
    """Load a stock by id. Raises ValueError for an unknown id."""
    path = _stock_dir() / f"{stock_id}.toml"
    if not path.exists():
        raise ValueError(
            f"unknown stock {stock_id!r}; available: {', '.join(available_stocks())}"
        )
    raw = tomllib.loads(path.read_text())
    curves = {
        channel: [(float(x), float(y)) for x, y in raw["curves"][channel]]
        for channel in ("red", "green", "blue")
    }
    return Stock(
        id=raw["id"],
        name=raw["name"],
        monochrome=bool(raw.get("monochrome", False)),
        mono_mix=tuple(float(v) for v in raw.get("mono_mix", (0.299, 0.587, 0.114))),
        cast=tuple(float(v) for v in raw.get("cast", (1.0, 1.0, 1.0))),
        saturation=float(raw.get("saturation", 1.0)),
        curves=curves,
        halation=dict(raw["halation"]),
        bloom={**_DEFAULT_BLOOM, **raw.get("bloom", {})},
        grain=dict(raw["grain"]),
        optics={**_DEFAULT_OPTICS, **raw.get("optics", {})},
    )
