
import pytest

from src.orders import Order
from src.order_book import OrderBook


def make_order(order_id, symbol, side, price, quantity, timestamp_ns):
    return Order(
        order_id=order_id,
        symbol=symbol,
        side=side,
        price=price,
        quantity=quantity,
        timestamp_ns=timestamp_ns,
    )


def test_add_buy_order():
    book = OrderBook()
    order = make_order(1, "ABC", "BUY", 100.0, 10, 1)

    book.add_order(order)

    assert book.get_best_bid("ABC") is order


def test_add_sell_order():
    book = OrderBook()
    order = make_order(1, "ABC", "SELL", 101.0, 10, 1)

    book.add_order(order)

    assert book.get_best_ask("ABC") is order


def test_buy_matches_sell_at_compatible_price():
    book = OrderBook()
    sell = make_order(1, "ABC", "SELL", 100.0, 5, 1)
    buy = make_order(2, "ABC", "BUY", 101.0, 10, 2)

    book.add_order(sell)
    trades = book.match_order(buy)

    assert len(trades) == 1
    assert trades[0]["price"] == 100.0
    assert trades[0]["quantity"] == 5
    assert trades[0]["buy_order_id"] == 2
    assert trades[0]["sell_order_id"] == 1
    assert buy.quantity == 5


def test_no_match_when_prices_are_not_compatible():
    book = OrderBook()
    sell = make_order(1, "ABC", "SELL", 105.0, 5, 1)
    buy = make_order(2, "ABC", "BUY", 100.0, 10, 2)

    book.add_order(sell)
    trades = book.match_order(buy)

    assert trades == []
    assert book.get_best_bid("ABC") is buy
    assert book.get_best_ask("ABC") is sell


def test_partial_fill_leaves_remaining_order_in_book():
    book = OrderBook()
    sell = make_order(1, "ABC", "SELL", 100.0, 10, 1)
    buy = make_order(2, "ABC", "BUY", 100.0, 4, 2)

    book.add_order(sell)
    trades = book.match_order(buy)

    assert len(trades) == 1
    assert trades[0]["quantity"] == 4
    assert sell.quantity == 6
    assert book.get_best_ask("ABC") is sell


def test_price_priority_uses_best_sell_price():
    book = OrderBook()
    expensive_sell = make_order(1, "ABC", "SELL", 102.0, 5, 1)
    cheap_sell = make_order(2, "ABC", "SELL", 100.0, 5, 2)
    buy = make_order(3, "ABC", "BUY", 105.0, 5, 3)

    book.add_order(expensive_sell)
    book.add_order(cheap_sell)

    trades = book.match_order(buy)

    assert len(trades) == 1
    assert trades[0]["sell_order_id"] == 2
    assert trades[0]["price"] == 100.0


def test_fifo_priority_for_same_price():
    book = OrderBook()
    first_sell = make_order(1, "ABC", "SELL", 100.0, 3, 1)
    second_sell = make_order(2, "ABC", "SELL", 100.0, 3, 2)
    buy = make_order(3, "ABC", "BUY", 100.0, 4, 3)

    book.add_order(first_sell)
    book.add_order(second_sell)

    trades = book.match_order(buy)

    assert len(trades) == 2
    assert trades[0]["sell_order_id"] == 1
    assert trades[0]["quantity"] == 3
    assert trades[1]["sell_order_id"] == 2
    assert trades[1]["quantity"] == 1


def test_different_symbols_do_not_match():
    book = OrderBook()
    xyz_sell = make_order(1, "XYZ", "SELL", 100.0, 5, 1)
    abc_buy = make_order(2, "ABC", "BUY", 100.0, 5, 2)

    book.add_order(xyz_sell)
    trades = book.match_order(abc_buy)

    assert trades == []
    assert book.get_best_ask("XYZ") is xyz_sell
    assert book.get_best_bid("ABC") is abc_buy


@pytest.mark.parametrize(
    "price, quantity",
    [
        (0, 5),
        (-1, 5),
        (100, 0),
        (100, -2),
    ],
)
def test_add_order_rejects_invalid_price_or_quantity(price, quantity):
    book = OrderBook()
    order = make_order(1, "ABC", "BUY", price, quantity, 1)

    with pytest.raises(ValueError):
        book.add_order(order)


def test_match_rejects_invalid_quantity():
    book = OrderBook()
    order = make_order(1, "ABC", "BUY", 100.0, 0, 1)

    with pytest.raises(ValueError):
        book.match_order(order)

def test_same_price_orders_for_different_symbols_stay_separate():
    book = OrderBook()

    abc_sell = make_order(1, "ABC", "SELL", 100.0, 5, 1)
    xyz_sell = make_order(2, "XYZ", "SELL", 100.0, 5, 2)
    abc_buy = make_order(3, "ABC", "BUY", 100.0, 5, 3)

    book.add_order(xyz_sell)
    book.add_order(abc_sell)

    trades = book.match_order(abc_buy)

    assert len(trades) == 1
    assert trades[0]["symbol"] == "ABC"
    assert trades[0]["sell_order_id"] == 1
    assert trades[0]["quantity"] == 5

    # The XYZ order must remain untouched.
    assert book.get_best_ask("XYZ") is xyz_sell
    assert xyz_sell.quantity == 5

from src.market_simulator import run_simulation


def test_market_simulator_executes_expected_trade():
    processed_orders, trades = run_simulation()

    assert len(processed_orders) == 4
    assert len(trades) == 1

    trade = trades[0]

    assert trade["symbol"] == "ABC"
    assert trade["price"] == 100.00
    assert trade["quantity"] == 3
    assert trade["buy_order_id"] == 2
    assert trade["sell_order_id"] == 1

def test_best_bid_uses_highest_price_after_multiple_levels():
    book = OrderBook()

    low_bid = make_order(1, "ABC", "BUY", 98.0, 5, 1)
    high_bid = make_order(2, "ABC", "BUY", 103.0, 5, 2)
    middle_bid = make_order(3, "ABC", "BUY", 100.0, 5, 3)

    book.add_order(low_bid)
    book.add_order(high_bid)
    book.add_order(middle_bid)

    assert book.get_best_bid("ABC") is high_bid


def test_best_ask_uses_lowest_price_after_multiple_levels():
    book = OrderBook()

    high_ask = make_order(1, "ABC", "SELL", 105.0, 5, 1)
    low_ask = make_order(2, "ABC", "SELL", 99.0, 5, 2)
    middle_ask = make_order(3, "ABC", "SELL", 102.0, 5, 3)

    book.add_order(high_ask)
    book.add_order(low_ask)
    book.add_order(middle_ask)

    assert book.get_best_ask("ABC") is low_ask


def test_best_ask_updates_after_best_price_is_fully_consumed():
    book = OrderBook()

    first_ask = make_order(1, "ABC", "SELL", 100.0, 2, 1)
    second_ask = make_order(2, "ABC", "SELL", 101.0, 2, 2)
    buy = make_order(3, "ABC", "BUY", 101.0, 2, 3)

    book.add_order(first_ask)
    book.add_order(second_ask)

    trades = book.match_order(buy)

    assert len(trades) == 1
    assert trades[0]["sell_order_id"] == 1
    assert book.get_best_ask("ABC") is second_ask


def test_best_bid_updates_after_best_price_is_fully_consumed():
    book = OrderBook()

    first_bid = make_order(1, "ABC", "BUY", 105.0, 2, 1)
    second_bid = make_order(2, "ABC", "BUY", 104.0, 2, 2)
    sell = make_order(3, "ABC", "SELL", 104.0, 2, 3)

    book.add_order(first_bid)
    book.add_order(second_bid)

    trades = book.match_order(sell)

    assert len(trades) == 1
    assert trades[0]["buy_order_id"] == 1
    assert book.get_best_bid("ABC") is second_bid

