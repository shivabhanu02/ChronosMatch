
import pytest

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus


def make_message(order_id):
    order = Order(
        order_id=order_id,
        symbol="ABC",
        side="BUY",
        price=100.50,
        quantity=10,
        timestamp_ns=order_id + 100,
    )
    return encode_order(order)


def test_write_and_read_message():
    bus = OrderMessageBus(2)
    try:
        message = make_message(1)
        bus.write(message)

        assert decode_order(bus.read()).order_id == 1
        assert bus.is_empty()
    finally:
        bus.close()


def test_bus_full():
    bus = OrderMessageBus(1)
    try:
        bus.write(make_message(1))

        with pytest.raises(BufferError):
            bus.write(make_message(2))
    finally:
        bus.close()


def test_bus_empty():
    bus = OrderMessageBus(2)
    try:
        with pytest.raises(BufferError):
            bus.read()
    finally:
        bus.close()


def test_fifo_order_and_wraparound():
    bus = OrderMessageBus(2)
    try:
        bus.write(make_message(1))
        bus.write(make_message(2))

        assert decode_order(bus.read()).order_id == 1

        bus.write(make_message(3))

        assert decode_order(bus.read()).order_id == 2
        assert decode_order(bus.read()).order_id == 3
        assert bus.is_empty()
    finally:
        bus.close()


def test_reject_wrong_message_size():
    bus = OrderMessageBus(2)
    try:
        with pytest.raises(ValueError):
            bus.write(b"short")
    finally:
        bus.close()


def test_operations_after_close():
    bus = OrderMessageBus(1)
    bus.close()

    with pytest.raises(ValueError):
        bus.read()

    with pytest.raises(ValueError):
        bus.write(make_message(1))
