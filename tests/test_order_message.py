
import pytest

from src.orders import Order
from src.order_message import (
    ORDER_SIZE,
    decode_order,
    encode_order,
)


def test_encode_decode_order():
    original = Order(
        order_id=123,
        symbol="ABC",
        side="BUY",
        price=100.50,
        quantity=10,
        timestamp_ns=123456789,
    )

    message = encode_order(original)
    decoded = decode_order(message)

    assert len(message) == ORDER_SIZE
    assert decoded.order_id == original.order_id
    assert decoded.symbol == original.symbol
    assert decoded.side == original.side
    assert decoded.price == original.price
    assert decoded.quantity == original.quantity
    assert decoded.timestamp_ns == original.timestamp_ns


def test_sell_order():
    original = Order(
        order_id=2,
        symbol="XYZ",
        side="SELL",
        price=25.75,
        quantity=5,
        timestamp_ns=987654321,
    )

    assert decode_order(encode_order(original)) == original


def test_invalid_symbol():
    order = Order(1, "TOO-LONG-SYMBOL", "BUY", 10, 1, 100)

    with pytest.raises(ValueError):
        encode_order(order)


def test_invalid_side():
    order = Order(1, "ABC", "HOLD", 10, 1, 100)

    with pytest.raises(ValueError):
        encode_order(order)


def test_invalid_message_length():
    with pytest.raises(ValueError):
        decode_order(b"short")
