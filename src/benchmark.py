
import argparse
import math
import statistics
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
    """Run one matching-engine benchmark trial."""
    if isinstance(num_orders, bool) or not isinstance(num_orders, int):
        raise ValueError("Number of orders must be an integer")

    if num_orders <= 0:
        raise ValueError("Number of orders must be positive")

    # Prepare the workload before starting the timer.
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

    # Every BUY should match one preceding SELL in this workload.
    expected_trades = num_orders // 2

    if trades_executed != expected_trades:
        raise RuntimeError(
            f"Expected {expected_trades} trades, "
            f"but got {trades_executed}"
        )

    return {
        "orders_processed": len(orders),
        "trades_executed": trades_executed,
        "elapsed_seconds": elapsed_seconds,
        "throughput_orders_per_second": len(orders) / elapsed_seconds,
        "average_latency_ns": sum(latencies_ns) / len(latencies_ns),
        "p50_latency_ns": percentile(latencies_ns, 50),
        "p99_latency_ns": percentile(latencies_ns, 99),
    }


def run_repeated_benchmarks(num_orders=10_000, trials=5):
    """Run multiple trials and calculate median performance metrics."""
    if isinstance(trials, bool) or not isinstance(trials, int):
        raise ValueError("Number of trials must be an integer")

    if trials <= 0:
        raise ValueError("Number of trials must be positive")

    results = [
        run_benchmark(num_orders)
        for _ in range(trials)
    ]

    return {
        "orders_per_trial": num_orders,
        "trials_completed": len(results),
        "trials": results,
        "median_throughput_orders_per_second": statistics.median(
            result["throughput_orders_per_second"]
            for result in results
        ),
        "median_average_latency_ns": statistics.median(
            result["average_latency_ns"]
            for result in results
        ),
        "median_p50_latency_ns": statistics.median(
            result["p50_latency_ns"]
            for result in results
        ),
        "median_p99_latency_ns": statistics.median(
            result["p99_latency_ns"]
            for result in results
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark ChronosMatch matching-engine performance"
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=10_000,
        help="Number of orders per trial (default: 10000)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of benchmark trials (default: 5)",
    )

    args = parser.parse_args()

    try:
        summary = run_repeated_benchmarks(args.orders, args.trials)
    except ValueError as error:
        parser.error(str(error))

    print("\nChronosMatch Repeated Performance Benchmark")
    print("-------------------------------------------")
    print(f"Orders per trial: {summary['orders_per_trial']:,}")
    print(f"Trials completed: {summary['trials_completed']}")

    for index, result in enumerate(summary["trials"], start=1):
        print(
            f"Trial {index}: "
            f"{result['throughput_orders_per_second']:,.2f} orders/sec | "
            f"p50 {result['p50_latency_ns']} ns | "
            f"p99 {result['p99_latency_ns']} ns | "
            f"{result['trades_executed']:,} trades"
        )

    print("\nMedian results across trials")
    print("----------------------------")
    print(
        f"Throughput: "
        f"{summary['median_throughput_orders_per_second']:,.2f} orders/sec"
    )
    print(
        f"Average latency: "
        f"{summary['median_average_latency_ns']:.0f} ns"
    )
    print(f"p50 latency: {summary['median_p50_latency_ns']:.0f} ns")
    print(f"p99 latency: {summary['median_p99_latency_ns']:.0f} ns")


if __name__ == "__main__":
    main()
