
import time

from src.orders import Order
from src.order_message import encode_order, decode_order


def generate_sample_orders():
    """Generate a small set of sample market orders."""
    current_time = time.perf_counter_ns()

    return [
        Order(
            order_id=1,
            symbol="ABC",
            side="BUY",
            price=100.50,
            quantity=10,
            timestamp_ns=current_time,
        ),
        Order(
            order_id=2,
            symbol="ABC",
            side="SELL",
            price=101.00,
            quantity=5,
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
    ]


def run_simulation():
    """Generate orders and verify binary encoding and decoding."""
    orders = generate_sample_orders()
    processed_orders = []

    for order in orders:
        message = encode_order(order)
        decoded_order = decode_order(message)
        processed_orders.append(decoded_order)

        print(
            f"Order {decoded_order.order_id}: "
            f"{decoded_order.side} {decoded_order.quantity} "
            f"{decoded_order.symbol} at ₹{decoded_order.price:.2f} "
            f"| Message size: {len(message)} bytes"
        )

    return processed_orders


if __name__ == "__main__":
    run_simulation()
