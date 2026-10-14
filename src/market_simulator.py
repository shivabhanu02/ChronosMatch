
import time

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus


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
    """Process sample orders through the binary message bus."""
    orders = generate_sample_orders()
    processed_orders = []

    # Create a message bus with enough capacity for all sample orders.
    bus = OrderMessageBus(capacity=len(orders))

    try:
        # Encode each order and write its binary message to the bus.
        for order in orders:
            message = encode_order(order)
            bus.write(message)

        print(f"Orders added to message bus: {len(orders)}")

        # Read messages in FIFO order and reconstruct the original orders.
        while not bus.is_empty():
            message = bus.read()
            decoded_order = decode_order(message)
            processed_orders.append(decoded_order)

            print(
                f"Order {decoded_order.order_id}: "
                f"{decoded_order.side} {decoded_order.quantity} "
                f"{decoded_order.symbol} at ₹{decoded_order.price:.2f} "
                f"| Message size: {len(message)} bytes"
            )

    finally:
        # Always release the memory-mapped buffer.
        bus.close()

    print(f"\nTotal orders processed: {len(processed_orders)}")

    return processed_orders


if __name__ == "__main__":
    run_simulation()
