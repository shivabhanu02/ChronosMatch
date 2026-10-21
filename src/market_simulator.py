
"""Asyncio-based ChronosMatch market simulator."""

import asyncio
import time

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus
from src.order_book import OrderBook
from src.latency import LatencyTracker


def generate_sample_orders():
    """Generate sample orders for multiple symbols."""
    current_time = time.perf_counter_ns()

    return [
        Order(
            order_id=1,
            symbol="ABC",
            side="SELL",
            price=100.00,
            quantity=5,
            timestamp_ns=current_time,
        ),
        Order(
            order_id=2,
            symbol="ABC",
            side="BUY",
            price=101.00,
            quantity=3,
            timestamp_ns=current_time + 1,
        ),
        Order(
            order_id=3,
            symbol="XYZ",
            side="BUY",
            price=25.75,
            quantity=20,
            timestamp_ns=current_time + 2,
        ),
        Order(
            order_id=4,
            symbol="ABC",
            side="BUY",
            price=99.00,
            quantity=4,
            timestamp_ns=current_time + 3,
        ),
    ]


async def produce_orders(bus, orders, producer_done):
    """Produce binary order messages asynchronously."""
    try:
        for order in orders:
            while bus.is_full():
                await asyncio.sleep(0)

            bus.write(encode_order(order))
            print(f"Produced order {order.order_id}")

            # Yield control to the consumer.
            await asyncio.sleep(0)
    finally:
        producer_done.set()


async def consume_orders(bus, order_book, latency_tracker, producer_done):
    """Consume orders and execute trades asynchronously."""
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
    """Run asynchronous order production and consumption."""
    orders = generate_sample_orders()

    bus = OrderMessageBus(capacity=len(orders))
    order_book = OrderBook()
    latency_tracker = LatencyTracker()
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

        print(f"\nTotal orders processed: {len(processed_orders)}")
        print(f"Total trades executed: {len(all_trades)}")
        print("\nMatching-engine latency statistics:")
        print(f"Minimum: {stats['min_ns']} ns")
        print(f"Average: {stats['avg_ns']:.2f} ns")
        print(f"Maximum: {stats['max_ns']} ns")

        return processed_orders, all_trades

    finally:
        bus.close()


def run_simulation():
    """Run the simulator with a synchronous interface for existing callers."""
    return asyncio.run(_run_simulation_async())


if __name__ == "__main__":
    run_simulation()
