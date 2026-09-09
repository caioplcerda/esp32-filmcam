import pytest

from filmlab.stocks import Stock, available_stocks, load_stock

EXPECTED = {"portra400", "cinestill800t", "hp5", "superia400"}


def test_all_four_stocks_are_available():
    assert set(available_stocks()) == EXPECTED


def test_available_stocks_is_sorted():
    assert available_stocks() == sorted(available_stocks())


@pytest.mark.parametrize("stock_id", sorted(EXPECTED))
def test_every_stock_loads_with_complete_fields(stock_id):
    stock = load_stock(stock_id)
    assert isinstance(stock, Stock)
    assert stock.id == stock_id
    assert stock.name
    assert set(stock.curves) == {"red", "green", "blue"}
    for points in stock.curves.values():
        assert len(points) >= 4
        xs = [x for x, _ in points]
        # PchipInterpolator requires STRICTLY increasing x; a duplicate would
        # pass a plain sorted() check and then fail at curve-build time.
        assert all(b > a for a, b in zip(xs, xs[1:]))
        assert xs[0] == 0.0 and xs[-1] == 1.0
    assert stock.grain["size_um"] > 0
    assert stock.grain["amplitude"] > 0


def test_unknown_stock_raises_with_helpful_message():
    with pytest.raises(ValueError, match="unknown stock"):
        load_stock("velvia50")


def test_hp5_is_monochrome_and_others_are_not():
    assert load_stock("hp5").monochrome is True
    assert load_stock("portra400").monochrome is False


def test_cinestill_has_the_strongest_halation():
    strengths = {s: load_stock(s).halation["strength"] for s in EXPECTED}
    assert max(strengths, key=strengths.get) == "cinestill800t"
