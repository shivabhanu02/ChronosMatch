
import time

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus
from src.order_book import OrderBook


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
    """Process binary messages and match orders through the order book."""
    orders = generate_sample_orders()
    processed_orders = []
    all_trades = []

    bus = OrderMessageBus(capacity=len(orders))
    order_book = OrderBook()

    try:
        # Encode orders and send their messages to the bus.
        for order in orders:
            bus.write(encode_order(order))

        print(f"Orders added to message bus: {len(orders)}")

        # Read each message and process its decoded order.
        while not bus.is_empty():
            message = bus.read()
            order = decode_order(message)
            processed_orders.append(order)

            print(
                f"Order {order.order_id}: {order.side} "
                f"{order.quantity} {order.symbol} "
                f"at ₹{order.price:.2f} "
                f"| Message size: {len(message)} bytes"
            )

            trades = order_book.match_order(order)

            if trades:
                for trade in trades:
                    all_trades.append(trade)
                    print(
                        f"TRADE: {trade['symbol']} | "
                        f"Price: ₹{trade['price']:.2f} | "
                        f"Quantity: {trade['quantity']} | "
                        f"Buy order: {trade['buy_order_id']} | "
                        f"Sell order: {trade['sell_order_id']}"
                    )

        print(f"\nTotal orders processed: {len(processed_orders)}")
        print(f"Total trades executed: {len(all_trades)}")

    finally:
        bus.close()

    return processed_orders, all_trades


if __name__ == "__main__":
    run_simulation()
