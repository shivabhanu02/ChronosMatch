
"""Save and restore an order book using atomic JSON snapshots."""

import json
import math
import os
import tempfile
from pathlib import Path

from src.order_book import OrderBook
from src.orders import Order

DEFAULT_SNAPSHOT_PATH = Path("data/order_book_snapshot.json")
SNAPSHOT_VERSION = 1


def save_order_book(order_book, path=DEFAULT_SNAPSHOT_PATH):
    """Save resting orders and return the number saved."""
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    orders = []

    for side, books in (
        ("BUY", order_book.buy_orders),
        ("SELL", order_book.sell_orders),
    ):
        for symbol in sorted(books):
            levels = books[symbol]

            for price in sorted(levels, reverse=(side == "BUY")):
                for order in levels[price]:
                    orders.append({
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "price": order.price,
                        "quantity": order.quantity,
                        "timestamp_ns": order.timestamp_ns,
                    })

    payload = {
        "version": SNAPSHOT_VERSION,
        "order_count": len(orders),
        "orders": orders,
    }

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=snapshot_path.parent,
            prefix=f".{snapshot_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, separators=(",", ":"))
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, snapshot_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    return len(orders)


def load_order_book(path=DEFAULT_SNAPSHOT_PATH):
    """Load a snapshot and return a restored OrderBook."""
    with Path(path).open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Snapshot must contain a JSON object.")

    if payload.get("version") != SNAPSHOT_VERSION:
        raise ValueError("Unsupported order-book snapshot version.")

    orders = payload.get("orders")
    if not isinstance(orders, list):
        raise ValueError("Snapshot orders must be a list.")

    if payload.get("order_count") != len(orders):
        raise ValueError("Snapshot order count does not match.")

    restored = OrderBook()

    for item in orders:
        if not isinstance(item, dict):
            raise ValueError("Each snapshot order must be an object.")

        if item.get("side") not in ("BUY", "SELL"):
            raise ValueError("Invalid order side in snapshot.")

        try:
            order = Order(
                order_id=int(item["order_id"]),
                symbol=str(item["symbol"]),
                side=item["side"],
                price=float(item["price"]),
                quantity=int(item["quantity"]),
                timestamp_ns=int(item["timestamp_ns"]),
            )
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Invalid order fields in snapshot.") from exc

        if (
            order.order_id < 0
            or order.timestamp_ns < 0
            or not order.symbol.strip()
            or not math.isfinite(order.price)
            or order.price <= 0
            or order.quantity <= 0
        ):
            raise ValueError("Invalid order values in snapshot.")

        restored.add_order(order)

    return restored

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
