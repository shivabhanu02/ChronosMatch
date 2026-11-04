
"""Asyncio-based ChronosMatch simulator with event-driven coordination
and background trade persistence.
"""

import asyncio
import json
import random
import time
from pathlib import Path

from src.orders import Order
from src.order_message import encode_order, decode_order
from src.order_message_bus import OrderMessageBus
from src.order_book import OrderBook
from src.latency import LatencyTracker
from src.latency_monitor import LatencyMonitor
from src.trade_ledger import TradeLedger


SAMPLE_PATH = Path("data/latency_samples.jsonl")
MARKET_STATE_PATH = Path("data/market_state.json")

TRADE_BATCH_SIZE = 500
MARKET_UPDATE_INTERVAL = 100


def generate_sample_orders():
    """Generate the original four sample orders."""
    current_time = time.perf_counter_ns()

    return [
        Order(1, "ABC", "SELL", 100.00, 5, current_time),
        Order(2, "ABC", "BUY", 101.00, 3, current_time + 1),
        Order(3, "XYZ", "BUY", 25.75, 20, current_time + 2),
        Order(4, "ABC", "BUY", 99.00, 4, current_time + 3),
    ]


def generate_orders(count, seed=42):
    """Generate a reproducible stream of mock market orders."""
    if count <= 0:
        raise ValueError("Order count must be positive")

    rng = random.Random(seed)
    symbols = ("ABC", "XYZ", "INFY", "TCS")
    current_time = time.perf_counter_ns()

    for order_id in range(1, count + 1):
        yield Order(
            order_id=order_id,
            symbol=rng.choice(symbols),
            side=rng.choice(("BUY", "SELL")),
            price=rng.randint(9900, 10100) / 100,
            quantity=rng.randint(1, 100),
            timestamp_ns=current_time + order_id,
        )


def publish_latency_samples(latencies):
    """Write latency measurements in one batch."""
    if not latencies:
        return

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with SAMPLE_PATH.open("a", encoding="utf-8") as sample_file:
        for latency_ns in latencies:
            sample_file.write(
                json.dumps({"latency_ns": int(latency_ns)}) + "\n"
            )


def publish_market_state(order_book, processed_count, whale_event=None):
    """Publish actual order-book prices and the latest whale event."""
    symbols = sorted(
        set(order_book.buy_orders) | set(order_book.sell_orders)
    )

    market_state = {
        "updated_at_ns": time.time_ns(),
        "processed_orders": processed_count,
        "symbols": {},
        "whale_event": whale_event,
    }

    for symbol in symbols:
        bid = order_book.get_best_bid(symbol)
        ask = order_book.get_best_ask(symbol)

        bid_price = bid.price if bid else None
        ask_price = ask.price if ask else None

        spread = (
            round(ask_price - bid_price, 8)
            if bid_price is not None and ask_price is not None
            else None
        )

        market_state["symbols"][symbol] = {
            "best_bid": bid_price,
            "best_ask": ask_price,
            "spread": spread,
        }

    MARKET_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Direct writing avoids Windows rename conflicts with dashboard readers.
    MARKET_STATE_PATH.write_text(
        json.dumps(market_state),
        encoding="utf-8",
    )


def save_trade_batch(trades):
    """Save a trade batch using a thread-local SQLite connection."""
    with TradeLedger() as ledger:
        return ledger.save_trades(trades)


async def persist_trades(trade_queue, batch_size=TRADE_BATCH_SIZE):
    """Persist trades in batches using a background worker."""
    saved_count = 0
    batch = []

    while True:
        item = await trade_queue.get()

        try:
            if item is None:
                if batch:
                    saved_count += await asyncio.to_thread(
                        save_trade_batch, batch
                    )
                break

            batch.extend(item)

            if len(batch) >= batch_size:
                current_batch = batch
                batch = []

                saved_count += await asyncio.to_thread(
                    save_trade_batch, current_batch
                )

        finally:
            trade_queue.task_done()

    return saved_count


async def produce_orders(
    bus,
    orders,
    producer_done,
    data_available,
    space_available,
):
    """Produce orders using event-driven buffer coordination."""
    produced = 0

    try:
        for order in orders:
            while bus.is_full():
                # Clear the event and recheck before waiting. This avoids
                # missing a notification if the consumer has just read.
                space_available.clear()

                if bus.is_full():
                    await space_available.wait()

            bus.write(encode_order(order))
            produced += 1

            # Notify the consumer that an order is available.
            data_available.set()

    finally:
        producer_done.set()

        # Wake the consumer so it can finish after the final order.
        data_available.set()

    return produced


async def consume_orders(
    bus,
    order_book,
    latency_tracker,
    latency_monitor,
    producer_done,
    trade_queue,
    data_available,
    space_available,
):
    """Consume orders, execute matches, and publish market state."""
    processed_orders = []
    all_trades = []
    latency_samples = []
    latest_whale_event = None

    while True:
        if bus.is_empty():
            # Clear and recheck before waiting to avoid a lost notification.
            data_available.clear()

            if bus.is_empty():
                if producer_done.is_set():
                    break

                await data_available.wait()

            continue

        message = bus.read()

        # Notify producer that a buffer slot is now free.
        space_available.set()

        order = decode_order(message)

        # Preserve original details before matching changes remaining quantity.
        original_quantity = order.quantity
        original_order_id = order.order_id
        original_side = order.side
        original_symbol = order.symbol

        start_time = latency_tracker.start()
        trades = order_book.match_order(order)
        elapsed_ns = latency_tracker.stop(start_time)

        latency_monitor.record(elapsed_ns)
        latency_samples.append(elapsed_ns)
        processed_orders.append(order)

        for trade in trades:
            trade.setdefault("executed_at_ns", time.time_ns())

        if trades:
            all_trades.extend(trades)

            # Queue trade persistence without blocking on SQLite disk writes.
            await trade_queue.put(trades)

            # Find the distinct execution prices.
            execution_prices = {trade["price"] for trade in trades}

            # Detect an order that executes across multiple price levels.
            if len(execution_prices) > 1:

                # A BUY consumes resting SELL orders.
                # A SELL consumes resting BUY orders.
                resting_side = (
                    order_book.sell_orders
                    if original_side == "BUY"
                    else order_book.buy_orders
                )

                symbol_levels = resting_side.get(original_symbol, {})

                # Count levels that are now completely empty.
                levels_cleared = sum(
                    1
                    for price in execution_prices
                    if not symbol_levels.get(price)
                )

                latest_whale_event = {
                    "order_id": original_order_id,
                    "symbol": original_symbol,
                    "side": original_side,
                    "quantity": original_quantity,

                    # Number of distinct levels the order executed against.
                    "levels_touched": len(execution_prices),

                    # Number of those levels completely consumed.
                    "levels_cleared": levels_cleared,

                    "traded_quantity": sum(
                        trade["quantity"] for trade in trades
                    ),
                    "execution_prices": sorted(execution_prices),
                    "timestamp_ns": time.time_ns(),
                }

        processed_count = len(processed_orders)

        # Publish dashboard data at a fixed interval instead of writing
        # to disk for every multi-level execution.
        if processed_count % MARKET_UPDATE_INTERVAL == 0:
            publish_market_state(
                order_book,
                processed_count,
                latest_whale_event,
            )

            # Keep the most recent whale event available for the final snapshot.
            # Do not clear it after a periodic dashboard update.

    # Write latency measurements in one batch.
    publish_latency_samples(latency_samples)

    # Always publish the final order-book state.
    publish_market_state(
        order_book,
        len(processed_orders),
        latest_whale_event,
    )

    return processed_orders, all_trades


async def _run_simulation_async(
    order_count=4,
    bus_capacity=None,
    seed=42,
):
    """Run asynchronous order production, matching, and persistence."""
    if order_count <= 0:
        raise ValueError("Order count must be positive")

    if bus_capacity is None:
        bus_capacity = min(order_count, 4096)

    if bus_capacity <= 0:
        raise ValueError("Bus capacity must be positive")

    if order_count == 4 and seed == 42:
        orders = generate_sample_orders()
    else:
        orders = generate_orders(order_count, seed)

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_PATH.write_text("", encoding="utf-8")

    bus = OrderMessageBus(capacity=bus_capacity)
    order_book = OrderBook()
    latency_tracker = LatencyTracker()
    latency_monitor = LatencyMonitor()

    producer_done = asyncio.Event()
    data_available = asyncio.Event()
    space_available = asyncio.Event()

    trade_queue = asyncio.Queue(maxsize=32)
    persistence_task = None
    producer_task = None
    consumer_task = None

    try:
        print(f"Starting simulation: {order_count:,} orders")
        print(f"Message bus capacity: {bus_capacity:,}")

        simulation_start = time.perf_counter()

        persistence_task = asyncio.create_task(
            persist_trades(trade_queue)
        )

        producer_task = asyncio.create_task(
            produce_orders(
                bus,
                orders,
                producer_done,
                data_available,
                space_available,
            )
        )

        consumer_task = asyncio.create_task(
            consume_orders(
                bus,
                order_book,
                latency_tracker,
                latency_monitor,
                producer_done,
                trade_queue,
                data_available,
                space_available,
            )
        )

        try:
            await asyncio.gather(producer_task, consumer_task)

            # Wait until all queued trades have been persisted.
            await trade_queue.join()

            # Stop the background persistence worker.
            await trade_queue.put(None)
            newly_saved = await persistence_task

        except Exception:
            for task in (producer_task, consumer_task):
                if task is not None:
                    task.cancel()

            await asyncio.gather(
                *(
                    task
                    for task in (producer_task, consumer_task)
                    if task is not None
                ),
                return_exceptions=True,
            )

            if persistence_task is not None:
                persistence_task.cancel()
                await asyncio.gather(
                    persistence_task,
                    return_exceptions=True,
                )

            raise

        elapsed_seconds = time.perf_counter() - simulation_start

        processed_orders, all_trades = consumer_task.result()

        with TradeLedger() as ledger:
            total_saved = ledger.count_trades()

        stats = latency_tracker.get_statistics()
        monitor_stats = latency_monitor.statistics()

        throughput = (
            len(processed_orders) / elapsed_seconds
            if elapsed_seconds > 0
            else 0
        )

        print("\nSimulation results")
        print(f"Orders processed: {len(processed_orders):,}")
        print(f"Trades executed: {len(all_trades):,}")
        print(f"New trades saved: {newly_saved:,}")
        print(f"Total trades in SQLite: {total_saved:,}")
        print(f"Simulation time: {elapsed_seconds:.3f} seconds")
        print(f"Throughput: {throughput:,.0f} orders/second")

        print("\nMatching latency")
        print(f"Minimum: {stats['min_ns']} ns")
        print(f"Average: {stats['avg_ns']:.2f} ns")
        print(f"Maximum: {stats['max_ns']} ns")

        print("\nLatency percentiles")
        print(f"P50: {monitor_stats['p50_us']:.2f} us")
        print(f"P95: {monitor_stats['p95_us']:.2f} us")
        print(f"P99: {monitor_stats['p99_us']:.2f} us")

        return processed_orders, all_trades

    finally:
        bus.close()


def run_simulation(order_count=4, bus_capacity=None, seed=42):
    """Preserve the synchronous simulation interface."""
    return asyncio.run(
        _run_simulation_async(
            order_count=order_count,
            bus_capacity=bus_capacity,
            seed=seed,
        )
    )


if __name__ == "__main__":
    run_simulation()
