
import pytest

from src.latency import LatencyTracker


def test_tracker_starts_empty():
    tracker = LatencyTracker()

    assert tracker.latencies_ns == []
    assert tracker.get_statistics() == {
        "count": 0,
        "min_ns": None,
        "avg_ns": None,
        "max_ns": None,
    }


def test_record_latency():
    tracker = LatencyTracker()

    tracker.record(150)

    assert tracker.latencies_ns == [150]


def test_calculate_latency_statistics():
    tracker = LatencyTracker()

    tracker.record(100)
    tracker.record(200)
    tracker.record(300)

    stats = tracker.get_statistics()

    assert stats["count"] == 3
    assert stats["min_ns"] == 100
    assert stats["avg_ns"] == 200
    assert stats["max_ns"] == 300


def test_record_zero_latency():
    tracker = LatencyTracker()

    tracker.record(0)

    assert tracker.get_statistics() == {
        "count": 1,
        "min_ns": 0,
        "avg_ns": 0,
        "max_ns": 0,
    }


def test_negative_latency_is_rejected():
    tracker = LatencyTracker()

    with pytest.raises(ValueError):
        tracker.record(-1)


def test_reset_clears_measurements():
    tracker = LatencyTracker()

    tracker.record(100)
    tracker.record(200)
    tracker.reset()

    assert tracker.latencies_ns == []
    assert tracker.get_statistics()["count"] == 0


def test_start_and_stop_record_elapsed_time():
    tracker = LatencyTracker()

    start_time = tracker.start()
    elapsed_ns = tracker.stop(start_time)

    assert elapsed_ns >= 0
    assert tracker.get_statistics()["count"] == 1
    assert tracker.get_statistics()["min_ns"] == elapsed_ns


def test_stop_rejects_future_start_timestamp():
    tracker = LatencyTracker()

    future_start = tracker.start() + 1_000_000_000

    with pytest.raises(ValueError):
        tracker.stop(future_start)
