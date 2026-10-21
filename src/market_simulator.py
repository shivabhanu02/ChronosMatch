
"""Asyncio-based ChronosMatch market simulator with latency monitoring."""

import asyncio
import time

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus
from src.order_book import OrderBook
from src.latency import LatencyTracker
from src.latency_monitor import LatencyMonitor


def generate_sample_orders():
    """Generate sample orders for multiple symbols."""
    current_time = time.perf_counter_ns()

    return [
        Order(1, "ABC", "SELL", 100.00, 5, current_time),
        Order(2, "ABC", "BUY", 101.00, 3, current_time + 1),
        Order(3, "XYZ", "BUY", 25.75, 20, current_time + 2),
        Order(4, "ABC", "BUY", 99.00, 4, current_time + 3),
    ]


async def produce_orders(bus, orders, producer_done):
    """Encode and enqueue orders asynchronously."""
    try:
        for order in orders:
            while bus.is_full():
                await asyncio.sleep(0)

            bus.write(encode_order(order))
            print(f"Produced order {order.order_id}")
            await asyncio.sleep(0)
    finally:
        producer_done.set()


async def consume_orders(
    bus, order_book, latency_tracker, latency_monitor, producer_done
):
    """Consume orders, execute matches, and record latency."""
    processed_orders = []
    all_trades = []

    while True:
        if bus.is_empty():
            if producer_done.is_set():
                break

            await asyncio.sleep(0)
            continue

        message = bus.read()
        order = decode_order(message)
        original_quantity = order.quantity

        start_time = latency_tracker.start()
        trades = order_book.match_order(order)
        elapsed_ns = latency_tracker.stop(start_time)

        # Feed real matching-engine measurements into the monitor.
        latency_monitor.record(elapsed_ns)

        processed_orders.append(order)
        all_trades.extend(trades)

        print(
            f"Order {order.order_id}: {order.side} "
            f"{original_quantity} {order.symbol} "
            f"at ₹{order.price:.2f} "
            f"| Message size: {len(message)} bytes "
            f"| Matching latency: {elapsed_ns} ns"
        )

        for trade in trades:
            print(
                f"TRADE: {trade['symbol']} | "
                f"Price: ₹{trade['price']:.2f} | "
                f"Quantity: {trade['quantity']} | "
                f"Buy order: {trade['buy_order_id']} | "
                f"Sell order: {trade['sell_order_id']}"
            )

        await asyncio.sleep(0)

    return processed_orders, all_trades


async def _run_simulation_async():
    """Run asynchronous order production and matching."""
    orders = generate_sample_orders()
    bus = OrderMessageBus(capacity=len(orders))
    order_book = OrderBook()
    latency_tracker = LatencyTracker()
    latency_monitor = LatencyMonitor()
    producer_done = asyncio.Event()

    try:
        print(f"Starting async simulation with {len(orders)} orders")

        producer_task = asyncio.create_task(
            produce_orders(bus, orders, producer_done)
        )
        consumer_task = asyncio.create_task(
            consume_orders(
                bus,
                order_book,
                latency_tracker,
                latency_monitor,
                producer_done,
            )
        )

        try:
            await asyncio.gather(producer_task, consumer_task)
        except Exception:
            producer_task.cancel()
            consumer_task.cancel()
            await asyncio.gather(
                producer_task,
                consumer_task,
                return_exceptions=True,
            )
            raise

        processed_orders, all_trades = consumer_task.result()
        stats = latency_tracker.get_statistics()
        monitor_stats = latency_monitor.statistics()

        print(f"\nTotal orders processed: {len(processed_orders)}")
        print(f"Total trades executed: {len(all_trades)}")
        print("\nMatching-engine latency statistics (LatencyTracker):")
        print(f"Minimum: {stats['min_ns']} ns")
        print(f"Average: {stats['avg_ns']:.2f} ns")
        print(f"Maximum: {stats['max_ns']} ns")

        print("\nLatency monitor statistics (real samples):")
        print(f"Samples: {monitor_stats['count']}")
        print(f"Average: {monitor_stats['average_us']:.2f} µs")
        print(f"P50: {monitor_stats['p50_us']:.2f} µs")
        print(f"P95: {monitor_stats['p95_us']:.2f} µs")
        print(f"P99: {monitor_stats['p99_us']:.2f} µs")

        return processed_orders, all_trades

    finally:
        bus.close()


def run_simulation():
    """Preserve the synchronous interface used by existing tests."""
    return asyncio.run(_run_simulation_async())


if __name__ == "__main__":
    run_simulation()
