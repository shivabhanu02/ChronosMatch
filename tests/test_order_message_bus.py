
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
        bus.write(make_message(1))

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


def test_write_many_and_read_many():
    bus = OrderMessageBus(4)
    try:
        messages = [make_message(i) for i in range(1, 4)]

        bus.write_many(messages)
        received = bus.read_many(3)

        order_ids = [decode_order(msg).order_id for msg in received]

        assert order_ids == [1, 2, 3]
        assert bus.is_empty()
    finally:
        bus.close()


def test_batch_fifo_order_across_wraparound():
    bus = OrderMessageBus(4)
    try:
        bus.write_many([make_message(i) for i in range(1, 4)])

        first_batch = bus.read_many(2)
        assert [decode_order(msg).order_id for msg in first_batch] == [1, 2]

        bus.write_many([make_message(4), make_message(5), make_message(6)])

        remaining = bus.read_many(4)
        assert [decode_order(msg).order_id for msg in remaining] == [3, 4, 5, 6]
        assert bus.is_empty()
    finally:
        bus.close()


def test_write_many_rejects_batch_when_full():
    bus = OrderMessageBus(3)
    try:
        bus.write_many([make_message(1), make_message(2)])

        with pytest.raises(BufferError):
            bus.write_many([make_message(3), make_message(4)])

        # Failed batch must not partially enter the buffer.
        received = bus.read_many(3)
        assert [decode_order(msg).order_id for msg in received] == [1, 2]
    finally:
        bus.close()


def test_write_many_rejects_invalid_message_size():
    bus = OrderMessageBus(3)
    try:
        with pytest.raises(ValueError):
            bus.write_many([make_message(1), b"short"])

        assert bus.is_empty()
    finally:
        bus.close()


def test_read_many_rejects_empty_buffer():
    bus = OrderMessageBus(2)
    try:
        with pytest.raises(BufferError):
            bus.read_many(1)
    finally:
        bus.close()
