import asyncio
import json

import src.market_simulator as simulator
from src.latency import LatencyTracker
from src.latency_monitor import LatencyMonitor
from src.order_book import OrderBook
from src.order_message import encode_order
from src.order_message_bus import OrderMessageBus
from src.orders import Order


def test_whale_event_reports_touched_and_cleared_levels(
    tmp_path, monkeypatch
):
    market_state_file = tmp_path / "market_state.json"
    latency_file = tmp_path / "latency_samples.jsonl"

    monkeypatch.setattr(
        simulator, "MARKET_STATE_PATH", market_state_file
    )
    monkeypatch.setattr(
        simulator, "SAMPLE_PATH", latency_file
    )

    order_book = OrderBook()

    # Three sell price levels in the order book.
    order_book.add_order(
        Order(1, "ABC", "SELL", 100.00, 2, 1)
    )
    order_book.add_order(
        Order(2, "ABC", "SELL", 101.00, 3, 2)
    )
    order_book.add_order(
        Order(3, "ABC", "SELL", 102.00, 4, 3)
    )

    # One incoming buy order consumes all of level 1 and 2,
    # then partially consumes level 3.
    incoming_order = Order(
        4, "ABC", "BUY", 102.00, 8, 4
    )

    bus = OrderMessageBus(capacity=1)

    try:
        bus.write(encode_order(incoming_order))

        producer_done = asyncio.Event()
        producer_done.set()

        data_available = asyncio.Event()
        data_available.set()

        space_available = asyncio.Event()
        trade_queue = asyncio.Queue(maxsize=32)

        asyncio.run(
            simulator.consume_orders(
                bus,
                order_book,
                LatencyTracker(),
                LatencyMonitor(),
                producer_done,
                trade_queue,
                data_available,
                space_available,
            )
        )
    finally:
        bus.close()

    assert market_state_file.exists()

    state = json.loads(
        market_state_file.read_text(encoding="utf-8")
    )

    event = state["whale_event"]

    assert event is not None
    assert event["order_id"] == 4
    assert event["symbol"] == "ABC"
    assert event["side"] == "BUY"
    assert event["quantity"] == 8
    assert event["traded_quantity"] == 8
    assert event["levels_touched"] == 3
    assert event["levels_cleared"] == 2
    assert event["execution_prices"] == [
        100.00, 101.00, 102.00
    ]

    # The third level must still have one unit remaining.
    remaining_ask = order_book.get_best_ask("ABC")
    assert remaining_ask is not None
    assert remaining_ask.price == 102.00
    assert remaining_ask.quantity == 1