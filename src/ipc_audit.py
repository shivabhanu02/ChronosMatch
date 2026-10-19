
"""Cross-process IPC audit for the ChronosMatch shared mmap bus."""

import argparse
import multiprocessing as mp
import os
import queue
import tempfile
import time

from src.order_message import encode_order, decode_order
from src.orders import Order
from src.shared_order_message_bus import SharedOrderMessageBus

BATCH_SIZE = 256


def make_message(order_id):
    return encode_order(
        Order(
            order_id=order_id,
            symbol="AAPL",
            side="BUY" if order_id % 2 else "SELL",
            price=150.00,
            quantity=10,
            timestamp_ns=time.perf_counter_ns(),
        )
    )


def producer(path, capacity, count, errors):
    bus = None
    try:
        bus = SharedOrderMessageBus(path, capacity)
        next_id = 1

        while next_id <= count:
            end_id = min(next_id + BATCH_SIZE, count + 1)
            batch = [make_message(order_id) for order_id in range(next_id, end_id)]
            written = bus.write_many(batch)

            if written:
                next_id += written
            else:
                time.sleep(0.0001)
    except Exception as exc:
        errors.put(f"Producer error: {exc!r}")
    finally:
        if bus is not None:
            bus.close()


def consumer(path, capacity, count, results, errors):
    bus = None
    received = 0
    sequence_ok = True

    try:
        bus = SharedOrderMessageBus(path, capacity)

        while received < count:
            messages = bus.read_many(BATCH_SIZE)
            if not messages:
                time.sleep(0.0001)
                continue

            for message in messages:
                order = decode_order(message)
                expected_id = received + 1
                received += 1

                if order.order_id != expected_id:
                    sequence_ok = False
                    errors.put(
                        f"FIFO mismatch: expected {expected_id}, "
                        f"received {order.order_id}"
                    )
                    results.put((received, sequence_ok))
                    return

                if received >= count:
                    break

        results.put((received, sequence_ok))
    except Exception as exc:
        errors.put(f"Consumer error: {exc!r}")
    finally:
        if bus is not None:
            bus.close()


def run_audit(count, capacity, timeout_seconds=120):
    if count <= 0 or capacity <= 0:
        raise ValueError("Count and capacity must be positive")

    context = mp.get_context("spawn")

    with tempfile.TemporaryDirectory(prefix="chronosmatch_audit_") as folder:
        path = os.path.join(folder, "orders.mmap")

        initial_bus = SharedOrderMessageBus(path, capacity)
        initial_bus.close()

        results = context.Queue()
        errors = context.Queue()

        consumer_process = context.Process(
            target=consumer,
            args=(path, capacity, count, results, errors),
        )
        producer_process = context.Process(
            target=producer,
            args=(path, capacity, count, errors),
        )
        processes = [consumer_process, producer_process]
        start = time.perf_counter()

        try:
            for process in processes:
                process.start()

            deadline = time.monotonic() + timeout_seconds
            while any(process.is_alive() for process in processes):
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"IPC audit exceeded {timeout_seconds} seconds"
                    )

                for process in processes:
                    process.join(timeout=0.05)

            elapsed = time.perf_counter() - start

            error_messages = []
            while True:
                try:
                    error_messages.append(errors.get_nowait())
                except queue.Empty:
                    break

            for process in processes:
                if process.exitcode != 0:
                    error_messages.append(
                        f"Process {process.name} exited with code "
                        f"{process.exitcode}"
                    )

            if error_messages:
                raise RuntimeError("\n".join(error_messages))

            try:
                received, sequence_ok = results.get(timeout=2)
            except queue.Empty as exc:
                raise RuntimeError("Consumer did not return audit results") from exc

            throughput = received / elapsed if elapsed else 0

            print("\nChronosMatch Cross-Process IPC Audit")
            print("-" * 42)
            print(f"Requested orders : {count:,}")
            print(f"Received orders  : {received:,}")
            print(f"FIFO verified    : {sequence_ok}")
            print(f"Elapsed time     : {elapsed:.3f} seconds")
            print(f"Throughput       : {throughput:,.0f} orders/second")
            print(f"Integrity passed : {received == count and sequence_ok}")
            print(f"100k/sec target  : {'REACHED' if throughput >= 100_000 else 'NOT REACHED'}")

            if received != count or not sequence_ok:
                raise RuntimeError("IPC audit failed: data integrity mismatch")

            return throughput
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
            for process in processes:
                if process.pid is not None:
                    process.join(timeout=5)

            results.close()
            errors.close()
            results.join_thread()
            errors.join_thread()


def main():
    parser = argparse.ArgumentParser(
        description="Verify shared-memory IPC between separate processes."
    )
    parser.add_argument("--count", type=int, default=1_000_000)
    parser.add_argument("--capacity", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    run_audit(args.count, args.capacity, args.timeout)


if __name__ == "__main__":
    main()
