
import time

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus
from src.order_book import OrderBook
from src.latency import LatencyTracker


def generate_sample_orders():
    """Generate sample orders, including one compatible buy and sell."""
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


def run_simulation():
    """Process orders, execute trades, and measure processing latency."""
    orders = generate_sample_orders()
    processed_orders = []
    all_trades = []

    bus = OrderMessageBus(capacity=len(orders))
    order_book = OrderBook()
    latency_tracker = LatencyTracker()

    try:
        for order in orders:
            bus.write(encode_order(order))

        print(f"Orders added to message bus: {len(orders)}")

        while not bus.is_empty():
            message = bus.read()
            order = decode_order(message)
            original_quantity = order.quantity

            # Measure matching-engine processing time for this order.
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

        stats = latency_tracker.get_statistics()

        print(f"\nTotal orders processed: {len(processed_orders)}")
        print(f"Total trades executed: {len(all_trades)}")
        print("\nMatching-engine latency statistics:")
        print(f"Minimum: {stats['min_ns']} ns")
        print(f"Average: {stats['avg_ns']:.2f} ns")
        print(f"Maximum: {stats['max_ns']} ns")

    finally:
        bus.close()

    return processed_orders, all_trades


if __name__ == "__main__":
    run_simulation()
