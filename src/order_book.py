
from collections import defaultdict, deque

from src.orders import Order

try:
    from src.matching_engine import compare_prices

    CYTHON_ENABLED = True
except ImportError:
    CYTHON_ENABLED = False

    def compare_prices(
        incoming_price: float,
        resting_price: float,
        is_buy: bool,
    ) -> int:
        """Python fallback for order price-crossing checks."""
        if is_buy:
            return int(incoming_price >= resting_price)
        return int(incoming_price <= resting_price)


class OrderBook:
    """Limit order book with price-time priority per symbol."""

    def __init__(self):
        # Structure: symbol -> price -> FIFO queue of orders
        self.buy_orders = defaultdict(lambda: defaultdict(deque))
        self.sell_orders = defaultdict(lambda: defaultdict(deque))

    def add_order(self, order: Order):
        """Add a valid order to the appropriate book."""
        if order.side not in ("BUY", "SELL"):
            raise ValueError("Order side must be BUY or SELL")

        if order.price <= 0:
            raise ValueError("Order price must be positive")

        if order.quantity <= 0:
            raise ValueError("Order quantity must be positive")

        if not order.symbol:
            raise ValueError("Order symbol must not be empty")

        if order.side == "BUY":
            book = self.buy_orders
        else:
            book = self.sell_orders

        book[order.symbol][order.price].append(order)

    def get_best_bid(self, symbol=None):
        """Return the highest-priced pending buy order."""
        symbols = [symbol] if symbol is not None else sorted(self.buy_orders)

        for current_symbol in symbols:
            price_levels = self.buy_orders.get(current_symbol, {})

            for price in sorted(price_levels, reverse=True):
                queue = price_levels[price]
                if queue:
                    return queue[0]

        return None

    def get_best_ask(self, symbol=None):
        """Return the lowest-priced pending sell order."""
        symbols = [symbol] if symbol is not None else sorted(self.sell_orders)

        for current_symbol in symbols:
            price_levels = self.sell_orders.get(current_symbol, {})

            for price in sorted(price_levels):
                queue = price_levels[price]
                if queue:
                    return queue[0]

        return None

    def match_order(self, incoming_order: Order):
        """Match an incoming order using price-time priority."""
        if incoming_order.side not in ("BUY", "SELL"):
            raise ValueError("Order side must be BUY or SELL")

        if incoming_order.price <= 0:
            raise ValueError("Order price must be positive")

        if incoming_order.quantity <= 0:
            raise ValueError("Order quantity must be positive")

        if not incoming_order.symbol:
            raise ValueError("Order symbol must not be empty")

        is_buy = incoming_order.side == "BUY"

        if is_buy:
            opposite_book = self.sell_orders
        else:
            opposite_book = self.buy_orders

        symbol_levels = opposite_book.get(incoming_order.symbol, {})
        trades = []

        while incoming_order.quantity > 0:
            available_prices = [
                price
                for price, queue in symbol_levels.items()
                if queue
            ]

            if not available_prices:
                break

            if is_buy:
                best_price = min(available_prices)
            else:
                best_price = max(available_prices)

            # Use Cython when available; otherwise use the Python fallback.
            if not compare_prices(
                incoming_order.price,
                best_price,
                is_buy,
            ):
                break

            resting_queue = symbol_levels[best_price]
            resting_order = resting_queue[0]

            trade_quantity = min(
                incoming_order.quantity,
                resting_order.quantity,
            )

            trades.append(
                {
                    "symbol": incoming_order.symbol,
                    "price": resting_order.price,
                    "quantity": trade_quantity,
                    "buy_order_id": (
                        incoming_order.order_id
                        if is_buy
                        else resting_order.order_id
                    ),
                    "sell_order_id": (
                        resting_order.order_id
                        if is_buy
                        else incoming_order.order_id
                    ),
                }
            )

            incoming_order.quantity -= trade_quantity
            resting_order.quantity -= trade_quantity

            if resting_order.quantity == 0:
                resting_queue.popleft()

                if not resting_queue:
                    del symbol_levels[best_price]

        if not symbol_levels:
            opposite_book.pop(incoming_order.symbol, None)

        if incoming_order.quantity > 0:
            self.add_order(incoming_order)

        return trades
