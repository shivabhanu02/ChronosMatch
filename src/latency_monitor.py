
"""ChronosMatch terminal latency dashboard with live simulator data."""

import argparse
import curses
import json
import time
from collections import deque
from pathlib import Path
from threading import Lock


SAMPLE_PATH = Path("data/latency_samples.jsonl")


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
        """Record a latency measurement in nanoseconds."""
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
        """Return lifetime totals and rolling-window percentiles."""
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


def draw_dashboard(stdscr, monitor, demo):
    """Refresh the dashboard until Q is pressed."""
    import random

    curses.curs_set(0)
    stdscr.nodelay(True)

    started_at = time.perf_counter()
    next_demo_sample = started_at
    file_position = 0

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

                # Handle the simulator starting a new run.
                if current_size < file_position:
                    file_position = 0
                    monitor = LatencyMonitor()

                with SAMPLE_PATH.open("r", encoding="utf-8") as sample_file:
                    sample_file.seek(file_position)

                    for line in sample_file:
                        if not line.strip():
                            continue

                        data = json.loads(line)
                        monitor.record(int(data["latency_ns"]))

                    file_position = sample_file.tell()

            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                # Retry on the next refresh if a file write is in progress.
                pass

        stats = monitor.statistics()
        height, width = stdscr.getmaxyx()
        stdscr.erase()

        def write_line(y, message, attr=0):
            if 0 <= y < height and width > 1:
                stdscr.addnstr(y, 0, message, width - 1, attr)

        write_line(0, "=" * min(width - 1, 60), curses.A_BOLD)
        write_line(1, " CHRONOSMATCH | LATENCY MONITOR", curses.A_BOLD)
        write_line(2, "=" * min(width - 1, 60), curses.A_BOLD)

        mode = "DEMO DATA" if demo else "LIVE SIMULATOR DATA"
        write_line(4, f"Mode: {mode}")
        write_line(5, f"Elapsed: {now - started_at:.1f} seconds")
        write_line(6, f"Total samples: {stats['count']:,}")

        write_line(8, "LATENCY STATISTICS (microseconds)", curses.A_BOLD)
        write_line(9, f"Average: {stats['average_us']:.2f} us")
        write_line(10, f"Minimum: {stats['minimum_us']:.2f} us")
        write_line(11, f"Maximum: {stats['maximum_us']:.2f} us")
        write_line(12, f"P50:     {stats['p50_us']:.2f} us")
        write_line(13, f"P95:     {stats['p95_us']:.2f} us")
        write_line(14, f"P99:     {stats['p99_us']:.2f} us")

        write_line(16, "RECENT LATENCY HISTORY", curses.A_BOLD)

        with monitor.lock:
            recent = list(monitor.history)[-max(0, min(10, height - 19)):]

        if recent:
            scale = max(recent) or 1
            graph_width = max(1, min(width - 15, 40))

            for index, latency in enumerate(recent):
                bar_length = max(1, int(latency / scale * graph_width))
                write_line(
                    17 + index,
                    f"{latency / 1000:8.2f} us | {'#' * bar_length}",
                )

        write_line(height - 2, "Press Q to quit")
        stdscr.refresh()
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(
        description="ChronosMatch latency monitoring dashboard"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate illustrative latency samples",
    )
    args = parser.parse_args()

    monitor = LatencyMonitor()

    try:
        curses.wrapper(draw_dashboard, monitor, args.demo)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
