
import pytest

from src.latency_monitor import LatencyMonitor


def test_empty_monitor_statistics():
    monitor = LatencyMonitor()

    stats = monitor.statistics()

    assert stats["count"] == 0
    assert stats["average_us"] == 0.0
    assert stats["p50_us"] == 0.0


def test_latency_statistics():
    monitor = LatencyMonitor()

    for latency in [1000, 2000, 3000, 4000, 5000]:
        monitor.record(latency)

    stats = monitor.statistics()

    assert stats["count"] == 5
    assert stats["average_us"] == 3.0
    assert stats["minimum_us"] == 1.0
    assert stats["maximum_us"] == 5.0
    assert stats["p50_us"] == 3.0


def test_history_is_limited_but_count_is_lifetime_total():
    monitor = LatencyMonitor(history_size=3)

    for latency in [1000, 2000, 3000, 4000, 5000]:
        monitor.record(latency)

    stats = monitor.statistics()

    assert stats["count"] == 5
    assert list(monitor.history) == [3000, 4000, 5000]


def test_negative_latency_is_rejected():
    monitor = LatencyMonitor()

    with pytest.raises(ValueError):
        monitor.record(-1)


def test_history_size_must_be_positive():
    with pytest.raises(ValueError):
        LatencyMonitor(history_size=0)
