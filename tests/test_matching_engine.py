
from array import array

import pytest

from src.matching_engine import compare_prices, match_fifo_quantities


def test_buy_price_crosses_when_incoming_price_is_higher():
    assert compare_prices(105.0, 100.0, True) == 1


def test_sell_price_crosses_when_incoming_price_is_lower():
    assert compare_prices(95.0, 100.0, False) == 1


def test_equal_prices_cross():
    assert compare_prices(100.0, 100.0, True) == 1
    assert compare_prices(100.0, 100.0, False) == 1


def test_fifo_quantity_matching():
    quantities = array("q", [3, 4, 5])

    fills, remaining = match_fifo_quantities(5, quantities)

    assert fills == [3, 2, 0]
    assert remaining == 0
    assert list(quantities) == [0, 2, 5]


def test_partial_matching_leaves_incoming_quantity():
    quantities = array("q", [2, 3])

    fills, remaining = match_fifo_quantities(8, quantities)

    assert fills == [2, 3]
    assert remaining == 3
    assert list(quantities) == [0, 0]


def test_zero_or_negative_incoming_quantity_is_rejected():
    quantities = array("q", [2, 3])

    with pytest.raises(ValueError):
        match_fifo_quantities(0, quantities)

    with pytest.raises(ValueError):
        match_fifo_quantities(-1, quantities)


def test_non_positive_resting_quantity_is_rejected():
    quantities = array("q", [2, 0])

    with pytest.raises(ValueError):
        match_fifo_quantities(3, quantities)
