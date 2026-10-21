
"""Measure end-to-end order latency through the shared IPC bus."""

import argparse
import multiprocessing as mp
import os
import queue
import statistics
import tempfile
import time

from src.order_message import encode_order, decode_order
from src.orders import Order
from src.shared_order_message_bus import SharedOrderMessageBus

BATCH_SIZE = 256


def producer(path, capacity, count, errors):
    bus = None
    try:
        bus = SharedOrderMessageBus(path, capacity)
        next_id = 1

        while next_id <= count:
            end_id = min(next_id + BATCH_SIZE, count + 1)
            batch = []

            for order_id in range(next_id, end_id):
                order = Order(
                    order_id=order_id,
                    symbol="AAPL",
                    side="BUY" if order_id % 2 else "SELL",
                    price=150.00,
                    quantity=10,
                    timestamp_ns=time.perf_counter_ns(),
                )
                batch.append(encode_order(order))

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
    latencies_ns = []
    received = 0
    fifo_ok = True

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

                if order.order_id != expected_id:
                    fifo_ok = False
                    errors.put(
                        f"FIFO mismatch: expected {expected_id}, "
                        f"received {order.order_id}"
                    )
                    results.put((received, fifo_ok, []))
                    return

                latency = time.perf_counter_ns() - order.timestamp_ns
                if latency < 0:
                    raise RuntimeError("Negative latency measurement")

                latencies_ns.append(latency)
                received += 1

                if received >= count:
                    break

        results.put((received, fifo_ok, latencies_ns))

    except Exception as exc:
        errors.put(f"Consumer error: {exc!r}")
    finally:
        if bus is not None:
            bus.close()


def percentile(sorted_values, percent):
    index = round((len(sorted_values) - 1) * percent / 100)
    return sorted_values[index]


def run_benchmark(count, capacity, timeout_seconds):
    if count <= 0 or capacity <= 0 or timeout_seconds <= 0:
        raise ValueError("Count, capacity, and timeout must be positive")

    context = mp.get_context("spawn")

    with tempfile.TemporaryDirectory(prefix="chronosmatch_latency_") as folder:
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
                        f"Latency benchmark exceeded {timeout_seconds} seconds"
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
                        f"{process.name} exited with code {process.exitcode}"
                    )

            if error_messages:
                raise RuntimeError("\n".join(error_messages))

            try:
                received, fifo_ok, latencies_ns = results.get(timeout=5)
            except queue.Empty as exc:
                raise RuntimeError("No latency results received") from exc

            if received != count or not fifo_ok or len(latencies_ns) != count:
                raise RuntimeError("Latency benchmark integrity check failed")

            ordered = sorted(latencies_ns)
            average_us = statistics.fmean(ordered) / 1000
            throughput = received / elapsed

            print("\nChronosMatch IPC Latency Benchmark")
            print("-" * 42)
            print(f"Orders received : {received:,}")
            print(f"FIFO verified   : {fifo_ok}")
            print(f"Elapsed time    : {elapsed:.3f} seconds")
            print(f"Throughput      : {throughput:,.0f} orders/second")
            print(f"Average latency : {average_us:.2f} microseconds")
            print(f"P50 latency     : {percentile(ordered, 50) / 1000:.2f} microseconds")
            print(f"P95 latency     : {percentile(ordered, 95) / 1000:.2f} microseconds")
            print(f"P99 latency     : {percentile(ordered, 99) / 1000:.2f} microseconds")
            print(f"Maximum latency : {max(ordered) / 1000:.2f} microseconds")

            return throughput, average_us

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
        description="Benchmark end-to-end order latency over shared mmap IPC."
    )
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--capacity", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    run_benchmark(args.count, args.capacity, args.timeout)


if __name__ == "__main__":
    main()
