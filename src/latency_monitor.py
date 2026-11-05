
"""ChronosMatch responsive live trading engine dashboard."""

import argparse
import curses
import json
import random
import time
from collections import deque
from pathlib import Path
from threading import Lock

SAMPLE_PATH = Path("data/latency_samples.jsonl")
MARKET_STATE_PATH = Path("data/market_state.json")


class LatencyMonitor:
    """Store latency samples and calculate useful statistics."""

    def __init__(self, history_size=200):
        if history_size <= 0:
            raise ValueError("history_size must be positive")

        self.history = deque(maxlen=history_size)
        self.total_count = 0
        self.total_latency_ns = 0
        self.minimum_ns = None
        self.maximum_ns = 0
        self.lock = Lock()

    def record(self, latency_ns):
        if latency_ns < 0:
            raise ValueError("Latency cannot be negative")

        latency_ns = int(latency_ns)

        with self.lock:
            self.history.append(latency_ns)
            self.total_count += 1
            self.total_latency_ns += latency_ns

            if self.minimum_ns is None or latency_ns < self.minimum_ns:
                self.minimum_ns = latency_ns

            self.maximum_ns = max(self.maximum_ns, latency_ns)

    def statistics(self):
        with self.lock:
            samples = list(self.history)
            count = self.total_count
            total = self.total_latency_ns
            minimum = self.minimum_ns
            maximum = self.maximum_ns

        if not samples:
            return {
                "count": count,
                "average_us": 0.0,
                "minimum_us": 0.0,
                "maximum_us": 0.0,
                "p50_us": 0.0,
                "p95_us": 0.0,
                "p99_us": 0.0,
            }

        samples.sort()

        def percentile(percent):
            index = round((len(samples) - 1) * percent / 100)
            return samples[index] / 1000

        return {
            "count": count,
            "average_us": total / count / 1000 if count else 0.0,
            "minimum_us": minimum / 1000,
            "maximum_us": maximum / 1000,
            "p50_us": percentile(50),
            "p95_us": percentile(95),
            "p99_us": percentile(99),
        }


def load_market_state():
    """Load the latest simulator market snapshot."""
    if not MARKET_STATE_PATH.exists():
        return None

    try:
        with MARKET_STATE_PATH.open("r", encoding="utf-8") as file:
            state = json.load(file)

        return state if isinstance(state, dict) else None

    except (OSError, json.JSONDecodeError):
        return None


def draw_dashboard(stdscr, monitor, demo):
    """Render a responsive dashboard."""

    curses.curs_set(0)
    stdscr.nodelay(True)

    started_at = time.perf_counter()
    sample_position = 0
    next_demo_sample = started_at

    while True:
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            break

        now = time.perf_counter()

        if demo:
            if now >= next_demo_sample:
                monitor.record(random.randint(500, 5000))
                next_demo_sample = now + 0.1

        elif SAMPLE_PATH.exists():
            try:
                current_size = SAMPLE_PATH.stat().st_size

                if current_size < sample_position:
                    sample_position = 0
                    monitor = LatencyMonitor()

                with SAMPLE_PATH.open("r", encoding="utf-8") as file:
                    file.seek(sample_position)

                    for line in file:
                        if not line.strip():
                            continue

                        data = json.loads(line)
                        monitor.record(int(data["latency_ns"]))

                    sample_position = file.tell()

            except (
                OSError,
                ValueError,
                KeyError,
                json.JSONDecodeError,
            ):
                pass

        stats = monitor.statistics()
        market = load_market_state()

        height, width = stdscr.getmaxyx()
        stdscr.erase()

        def write(y, message, bold=False):
            """Safely write text within the current terminal size."""
            if 0 <= y < height and width > 1:
                try:
                    attr = curses.A_BOLD if bold else curses.A_NORMAL
                    stdscr.addnstr(y, 0, str(message), width - 1, attr)
                except curses.error:
                    pass

        def section(y, heading):
            write(y, "=" * min(width - 1, 65))
            write(y + 1, heading, True)

        # Header
        write(0, "=" * min(width - 1, 65), True)
        write(1, " CHRONOSMATCH | LIVE TRADING MONITOR", True)
        write(2, "=" * min(width - 1, 65), True)

        write(3, f"Mode: {'DEMO' if demo else 'LIVE SIMULATOR DATA'}")
        write(4, f"Elapsed: {now - started_at:.1f} seconds")
        write(5, f"Latency samples: {stats['count']:,}")

        # Latency statistics
        section(7, "LATENCY STATISTICS (microseconds)")
        write(9, f"Average: {stats['average_us']:.2f} us")
        write(10, f"Minimum: {stats['minimum_us']:.2f} us")
        write(11, f"Maximum: {stats['maximum_us']:.2f} us")
        write(12, f"P50: {stats['p50_us']:.2f} us")
        write(13, f"P95: {stats['p95_us']:.2f} us")
        write(14, f"P99: {stats['p99_us']:.2f} us")

        # Recent history
        section(16, "RECENT LATENCY HISTORY")

        with monitor.lock:
            recent = list(monitor.history)[-3:]

        for index, latency in enumerate(recent):
            write(
                18 + index,
                f"Sample {index + 1}: {latency / 1000:.2f} us",
            )

        # Market state
        section(22, "LIVE ORDER BOOK")

        if market is None:
            write(24, "Waiting for simulator market data...")
        else:
            write(
                24,
                f"Orders processed: {market.get('processed_orders', 0):,}",
            )

            symbols = market.get("symbols", {})

            if not isinstance(symbols, dict) or not symbols:
                write(25, "No open orders in the book.")
            else:
                write(25, "SYMBOL       BEST BID       BEST ASK       SPREAD", True)

                for index, (symbol, book) in enumerate(
                    sorted(symbols.items())
                ):
                    if not isinstance(book, dict):
                        continue

                    bid = book.get("best_bid")
                    ask = book.get("best_ask")
                    spread = book.get("spread")

                    bid_text = f"{bid:.2f}" if bid is not None else "-"
                    ask_text = f"{ask:.2f}" if ask is not None else "-"
                    spread_text = (
                        f"{spread:.2f}" if spread is not None else "-"
                    )

                    write(
                        26 + index,
                        f"{symbol:<12} {bid_text:<14} "
                        f"{ask_text:<14} {spread_text}",
                    )

        # Whale alert: place after the order book rows.
        symbols = market.get("symbols", {}) if market else {}
        whale_y = max(29, 27 + len(symbols))

        section(whale_y, "WHALE ORDER ALERT")

        whale = market.get("whale_event") if market else None

        if not whale:
            write(
                whale_y + 2,
                "No multi-level whale execution reported yet.",
            )
        else:
            write(
                whale_y + 2,
                f"Order #{whale.get('order_id', '-')} | "
                f"{whale.get('side', '-')} "
                f"{whale.get('symbol', '-')} | "
                f"Quantity: {whale.get('quantity', '-')}",
                True,
            )

            write(
                whale_y + 3,
                f"Traded: {whale.get('traded_quantity', '-')} | "
                f"Levels touched: {whale.get('levels_touched', '-')} | "
                f"Levels cleared: {whale.get('levels_cleared', '-')}",
            )

            prices = whale.get("execution_prices", [])

            if prices:
                write(
                    whale_y + 4,
                    "Execution prices: "
                    + ", ".join(f"{price:.2f}" for price in prices),
                )

        # Footer
        write(height - 1, "Press Q to quit", True)

        stdscr.refresh()
        time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser(
        description="ChronosMatch live monitoring dashboard"
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate illustrative latency samples",
    )

    args = parser.parse_args()

    try:
        curses.wrapper(
            draw_dashboard,
            LatencyMonitor(),
            args.demo,
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
