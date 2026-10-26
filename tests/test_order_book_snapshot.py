
"""Tests for saving and recovering ChronosMatch order books."""

import json

import pytest

from src.order_book import OrderBook
from src.order_book_snapshot import (
    load_order_book,
    save_order_book,
)
from src.orders import Order


def make_order(order_id, side, price, quantity, timestamp, symbol="ABC"):
    return Order(
        order_id=order_id,
        symbol=symbol,
        side=side,
        price=price,
        quantity=quantity,
        timestamp_ns=timestamp,
    )


def test_save_and_restore_unmatched_orders(tmp_path):
    path = tmp_path / "order_book.json"
    original = OrderBook()

    original.add_order(make_order(1, "BUY", 100, 5, 10))
    original.add_order(make_order(2, "BUY", 100, 3, 20))
    original.add_order(make_order(3, "SELL", 105, 4, 30))

    assert save_order_book(original, path) == 3

    restored = load_order_book(path)

    assert restored.get_best_bid("ABC").order_id == 1
    assert restored.get_best_ask("ABC").order_id == 3
    assert restored.buy_orders["ABC"][100][1].order_id == 2


def test_fifo_priority_survives_recovery(tmp_path):
    path = tmp_path / "order_book.json"
    original = OrderBook()

    original.add_order(make_order(1, "SELL", 100, 2, 10))
    original.add_order(make_order(2, "SELL", 100, 3, 20))

    save_order_book(original, path)
    restored = load_order_book(path)

    incoming = make_order(3, "BUY", 100, 4, 30)
    trades = restored.match_order(incoming)

    assert [trade["sell_order_id"] for trade in trades] == [1, 2]
    assert [trade["quantity"] for trade in trades] == [2, 2]
    assert restored.get_best_ask("ABC").order_id == 2
    assert restored.get_best_ask("ABC").quantity == 1


def test_empty_order_book_can_be_restored(tmp_path):
    path = tmp_path / "empty.json"

    assert save_order_book(OrderBook(), path) == 0

    restored = load_order_book(path)

    assert restored.get_best_bid() is None
    assert restored.get_best_ask() is None


def test_missing_snapshot_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_order_book(tmp_path / "missing.json")


def test_unsupported_snapshot_version_is_rejected(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps(
            {"version": 999, "order_count": 0, "orders": []}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="version"):
        load_order_book(path)


def test_incorrect_order_count_is_rejected(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps(
            {"version": 1, "order_count": 2, "orders": []}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="order count"):
        load_order_book(path)


def test_invalid_order_is_rejected(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "order_count": 1,
                "orders": [
                    {
                        "order_id": 1,
                        "symbol": "ABC",
                        "side": "INVALID",
                        "price": 100,
                        "quantity": 5,
                        "timestamp_ns": 10,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="side"):
        load_order_book(path)
def test_price_priority_survives_recovery(tmp_path):
    path = tmp_path / "order_book.json"
    original = OrderBook()

    # The lower-priced sell order must be matched first.
    original.add_order(make_order(1, "SELL", 105, 2, 10))
    original.add_order(make_order(2, "SELL", 101, 3, 20))
    original.add_order(make_order(3, "SELL", 103, 4, 30))

    save_order_book(original, path)
    restored = load_order_book(path)

    incoming = make_order(4, "BUY", 105, 5, 40)
    trades = restored.match_order(incoming)

    assert [trade["sell_order_id"] for trade in trades] == [2, 3]
    assert [trade["price"] for trade in trades] == [101, 103]
    assert [trade["quantity"] for trade in trades] == [3, 2]

    # The remaining quantity belongs to the next sell order.
    best_ask = restored.get_best_ask("ABC")
    assert best_ask.order_id == 3
    assert best_ask.quantity == 2
