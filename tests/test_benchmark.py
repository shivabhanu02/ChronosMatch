
import pytest

from src.benchmark import percentile, run_benchmark


def test_percentile_calculates_median():
    assert percentile([10, 30, 20], 50) == 20


def test_percentile_calculates_p99():
    values = list(range(1, 101))
    assert percentile(values, 99) == 99


def test_percentile_handles_unsorted_values():
    assert percentile([50, 10, 40, 20, 30], 100) == 50


def test_percentile_rejects_empty_values():
    with pytest.raises(ValueError):
        percentile([], 50)


@pytest.mark.parametrize("percent", [0, -1, 101])
def test_percentile_rejects_invalid_percent(percent):
    with pytest.raises(ValueError):
        percentile([10, 20, 30], percent)


def test_benchmark_processes_orders_and_executes_trades():
    results = run_benchmark(20)

    assert results["orders_processed"] == 20
    assert results["trades_executed"] == 10
    assert results["elapsed_seconds"] > 0
    assert results["throughput_orders_per_second"] > 0
    assert results["average_latency_ns"] >= 0
    assert results["p50_latency_ns"] >= 0
    assert results["p99_latency_ns"] >= 0


def test_benchmark_rejects_zero_orders():
    with pytest.raises(ValueError):
        run_benchmark(0)


def test_benchmark_rejects_negative_orders():
    with pytest.raises(ValueError):
        run_benchmark(-10)


def test_benchmark_rejects_non_integer_orders():
    with pytest.raises(ValueError):
        run_benchmark(10.5)
