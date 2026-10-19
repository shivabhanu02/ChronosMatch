
import multiprocessing
import os
import tempfile

import pytest

from src.order_message import encode_order, decode_order
from src.orders import Order
from src.shared_order_message_bus import SharedOrderMessageBus


def make_message(order_id):
    return encode_order(
        Order(
            order_id=order_id,
            symbol="ABC",
            side="BUY",
            price=100.50,
            quantity=10,
            timestamp_ns=order_id + 100,
        )
    )


def producer(path, capacity, count):
    bus = SharedOrderMessageBus(path, capacity)
    try:
        for order_id in range(1, count + 1):
            while True:
                try:
                    bus.write(make_message(order_id))
                    break
                except BufferError:
                    import time
                    time.sleep(0.0001)
    finally:
        bus.close()


def consumer(path, capacity, count, results):
    bus = SharedOrderMessageBus(path, capacity)
    received = []
    try:
        while len(received) < count:
            try:
                received.append(decode_order(bus.read()).order_id)
            except BufferError:
                import time
                time.sleep(0.0001)
        results.put(received)
    finally:
        bus.close()


def test_shared_bus_fifo_and_wraparound():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "orders.mmap")
        bus = SharedOrderMessageBus(path, capacity=2)
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


def test_shared_bus_rejects_wrong_message_size():
    with tempfile.TemporaryDirectory() as directory:
        bus = SharedOrderMessageBus(
            os.path.join(directory, "orders.mmap"), 2
        )
        try:
            with pytest.raises(ValueError):
                bus.write(b"short")
        finally:
            bus.close()


def test_separate_processes_exchange_orders():
    count = 100
    capacity = 16

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "orders.mmap")
        SharedOrderMessageBus(path, capacity).close()

        context = multiprocessing.get_context("spawn")
        results = context.Queue()

        consumer_process = context.Process(
            target=consumer,
            args=(path, capacity, count, results),
        )
        producer_process = context.Process(
            target=producer,
            args=(path, capacity, count),
        )

        consumer_process.start()
        producer_process.start()

        producer_process.join(timeout=15)
        consumer_process.join(timeout=15)

        if producer_process.is_alive():
            producer_process.terminate()
            producer_process.join()
            pytest.fail("Producer process timed out")

        if consumer_process.is_alive():
            consumer_process.terminate()
            consumer_process.join()
            pytest.fail("Consumer process timed out")

        assert producer_process.exitcode == 0
        assert consumer_process.exitcode == 0
        assert results.get(timeout=2) == list(range(1, count + 1))
