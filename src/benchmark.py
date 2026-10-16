
import argparse
import math
import time

from src.order_book import OrderBook
from src.orders import Order


def percentile(values, percent):
    """Calculate a percentile using the nearest-rank method."""
    if not values:
        raise ValueError("Cannot calculate a percentile from empty data")

    if not 0 < percent <= 100:
        raise ValueError("Percent must be greater than 0 and at most 100")

    sorted_values = sorted(values)
    index = math.ceil((percent / 100) * len(sorted_values)) - 1
    return sorted_values[index]


def run_benchmark(num_orders=10_000):
    """Benchmark matching-engine throughput and per-order latency."""
    if isinstance(num_orders, bool) or not isinstance(num_orders, int):
        raise ValueError("Number of orders must be an integer")

    if num_orders <= 0:
        raise ValueError("Number of orders must be positive")

    # Prepare orders before timing the matching engine.
    orders = []

    for i in range(num_orders):
        if i % 2 == 0:
            side = "SELL"
            price = 100.00
        else:
            side = "BUY"
            price = 101.00

        orders.append(
            Order(
                order_id=i + 1,
                symbol="ABC",
                side=side,
                price=price,
                quantity=1,
                timestamp_ns=i + 1,
            )
        )

    order_book = OrderBook()
    latencies_ns = []
    trades_executed = 0

    # Measure only matching-engine processing.
    benchmark_start = time.perf_counter_ns()

    for order in orders:
        order_start = time.perf_counter_ns()
        trades = order_book.match_order(order)
        order_end = time.perf_counter_ns()

        latencies_ns.append(order_end - order_start)
        trades_executed += len(trades)

    benchmark_end = time.perf_counter_ns()

    elapsed_ns = benchmark_end - benchmark_start
    elapsed_seconds = elapsed_ns / 1_000_000_000

    return {
        "orders_processed": len(orders),
        "trades_executed": trades_executed,
        "elapsed_seconds": elapsed_seconds,
        "throughput_orders_per_second": len(orders) / elapsed_seconds,
        "p50_latency_ns": percentile(latencies_ns, 50),
        "p99_latency_ns": percentile(latencies_ns, 99),
        "average_latency_ns": sum(latencies_ns) / len(latencies_ns),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark ChronosMatch matching-engine performance"
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=10_000,
        help="Number of orders to process (default: 10000)",
    )
    args = parser.parse_args()

    try:
        results = run_benchmark(args.orders)
    except ValueError as error:
        parser.error(str(error))

    print("\nChronosMatch Performance Benchmark")
    print("---------------------------------")
    print(f"Orders processed:       {results['orders_processed']:,}")
    print(f"Trades executed:        {results['trades_executed']:,}")
    print(f"Elapsed time:           {results['elapsed_seconds']:.6f} seconds")
    print(
        f"Throughput:             "
        f"{results['throughput_orders_per_second']:,.2f} orders/second"
    )
    print(f"Average latency:        {results['average_latency_ns']:.0f} ns")
    print(f"p50 latency:            {results['p50_latency_ns']} ns")
    print(f"p99 latency:            {results['p99_latency_ns']} ns")


if __name__ == "__main__":
    main()
