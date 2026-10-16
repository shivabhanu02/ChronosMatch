
from time import perf_counter_ns


class LatencyTracker:
    """Record operation latencies and calculate summary statistics."""

    def __init__(self):
        self.latencies_ns = []

    def start(self):
        """Return a high-resolution start timestamp."""
        return perf_counter_ns()

    def stop(self, start_time_ns):
        """Record elapsed time in nanoseconds and return it."""
        elapsed_ns = perf_counter_ns() - start_time_ns

        if elapsed_ns < 0:
            raise ValueError("Elapsed time cannot be negative")

        self.latencies_ns.append(elapsed_ns)
        return elapsed_ns

    def record(self, elapsed_ns):
        """Record a measured duration, useful for testing."""
        if elapsed_ns < 0:
            raise ValueError("Latency cannot be negative")

        self.latencies_ns.append(elapsed_ns)

    def get_statistics(self):
        """Return latency statistics in nanoseconds."""
        if not self.latencies_ns:
            return {
                "count": 0,
                "min_ns": None,
                "avg_ns": None,
                "max_ns": None,
            }

        return {
            "count": len(self.latencies_ns),
            "min_ns": min(self.latencies_ns),
            "avg_ns": sum(self.latencies_ns) / len(self.latencies_ns),
            "max_ns": max(self.latencies_ns),
        }

    def reset(self):
        """Clear all recorded latency measurements."""
        self.latencies_ns.clear()
