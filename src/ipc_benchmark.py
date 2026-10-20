
"""Repeatable benchmark runner for ChronosMatch cross-process IPC."""

import argparse
import statistics
import time

from src.ipc_audit import run_audit


def main():
    parser = argparse.ArgumentParser(
        description="Run repeated ChronosMatch IPC performance audits."
    )
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--capacity", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    if args.trials <= 0:
        parser.error("--trials must be greater than zero")

    throughputs = []

    print(
        f"Running {args.trials} IPC trials "
        f"with {args.count:,} orders per trial."
    )

    for trial in range(1, args.trials + 1):
        print(f"\n========== TRIAL {trial}/{args.trials} ==========")
        start = time.perf_counter()
        throughput = run_audit(
            count=args.count,
            capacity=args.capacity,
            timeout_seconds=args.timeout,
        )
        elapsed = time.perf_counter() - start
        throughputs.append(throughput)
        print(f"Trial wall time: {elapsed:.3f} seconds")

    ordered = sorted(throughputs)
    median = statistics.median(throughputs)
    target = 100_000
    reached = sum(rate >= target for rate in throughputs)

    print("\nChronosMatch IPC Benchmark Summary")
    print("=" * 42)
    print(f"Orders per trial : {args.count:,}")
    print(f"Trials completed : {len(throughputs)}")
    print(f"Minimum          : {min(throughputs):,.0f} orders/sec")
    print(f"Median           : {median:,.0f} orders/sec")
    print(f"Maximum          : {max(throughputs):,.0f} orders/sec")
    print(f"Target reached   : {reached}/{len(throughputs)} trials")
    print(f"Target           : {target:,} orders/second")


if __name__ == "__main__":
    main()
