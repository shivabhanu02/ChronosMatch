import heapq
from array import array
from collections import defaultdict, deque
from itertools import count

from src.orders import Order

try:
    from src.matching_engine import compare_prices, match_fifo_quantities

    CYTHON_ENABLED = True

except ImportError:
    CYTHON_ENABLED = False

    def compare_prices(incoming_price, resting_price, is_buy):
        if is_buy:
            return int(incoming_price >= resting_price)
        return int(incoming_price <= resting_price)

    def match_fifo_quantities(incoming_quantity, resting_quantities):
        if incoming_quantity <= 0:
            raise ValueError("Incoming quantity must be positive")

        fills = []

        for i in range(len(resting_quantities)):
            available = resting_quantities[i]

            if available <= 0:
                raise ValueError("Resting quantities must be positive")

            fill = min(incoming_quantity, available)
            resting_quantities[i] -= fill
            incoming_quantity -= fill
            fills.append(fill)

        return fills, incoming_quantity


class OrderBook:
    """Limit order book with price-time priority per symbol."""

    def __init__(self):
        self.buy_orders = defaultdict(lambda: defaultdict(deque))
        self.sell_orders = defaultdict(lambda: defaultdict(deque))

        self._price_heaps = {
            "BUY": defaultdict(list),
            "SELL": defaultdict(list),
        }

        self._price_tokens = {
            "BUY": defaultdict(dict),
            "SELL": defaultdict(dict),
        }

        self._token_counter = count()

    def _best_price(self, symbol, side):
        """Return the best active price using lazy heap cleanup."""
        book = self.buy_orders if side == "BUY" else self.sell_orders

        levels = book.get(symbol, {})
        heap = self._price_heaps[side].get(symbol, [])
        tokens = self._price_tokens[side].get(symbol, {})

        while heap:
            priority, token, price = heap[0]

            if (
                tokens.get(price) != token
                or price not in levels
                or not levels[price]
            ):
                heapq.heappop(heap)
                continue

            return price

        return None

    def add_order(self, order: Order):
        """Add a valid order and register its price level."""
        if order.side not in ("BUY", "SELL"):
            raise ValueError("Order side must be BUY or SELL")

        if order.price <= 0:
            raise ValueError("Order price must be positive")

        if order.quantity <= 0:
            raise ValueError("Order quantity must be positive")

        if not order.symbol:
            raise ValueError("Order symbol must not be empty")

        book = self.buy_orders if order.side == "BUY" else self.sell_orders
        levels = book[order.symbol]

        if order.price not in levels:
            token = next(self._token_counter)

            levels[order.price] = deque()
            self._price_tokens[order.side][order.symbol][order.price] = token

            priority = -order.price if order.side == "BUY" else order.price

            heapq.heappush(
                self._price_heaps[order.side][order.symbol],
                (priority, token, order.price),
            )

        levels[order.price].append(order)

    def get_best_bid(self, symbol=None):
        """Return the highest-priced pending buy order."""
        symbols = [symbol] if symbol is not None else sorted(self.buy_orders)

        for current_symbol in symbols:
            best_price = self._best_price(current_symbol, "BUY")

            if best_price is not None:
                return self.buy_orders[current_symbol][best_price][0]

        return None

    def get_best_ask(self, symbol=None):
        """Return the lowest-priced pending sell order."""
        symbols = [symbol] if symbol is not None else sorted(self.sell_orders)

        for current_symbol in symbols:
            best_price = self._best_price(current_symbol, "SELL")

            if best_price is not None:
                return self.sell_orders[current_symbol][best_price][0]

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

        resting_side = "SELL" if is_buy else "BUY"
        opposite_book = self.sell_orders if is_buy else self.buy_orders

        symbol_levels = opposite_book.get(incoming_order.symbol, {})
        trades = []

        while incoming_order.quantity > 0:
            best_price = self._best_price(
                incoming_order.symbol,
                resting_side,
            )

            if best_price is None:
                break

            if not compare_prices(
                incoming_order.price,
                best_price,
                is_buy,
            ):
                break

            resting_queue = symbol_levels[best_price]

            quantities = array(
                "q",
                (order.quantity for order in resting_queue),
            )

            fills, remaining_quantity = match_fifo_quantities(
                incoming_order.quantity,
                quantities,
            )

            for resting_order, fill, remaining in zip(
                resting_queue,
                fills,
                quantities,
            ):
                resting_order.quantity = remaining

                if fill == 0:
                    continue

                trades.append(
                    {
                        "symbol": incoming_order.symbol,
                        "price": resting_order.price,
                        "quantity": fill,
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

            incoming_order.quantity = remaining_quantity

            while resting_queue and resting_queue[0].quantity == 0:
                resting_queue.popleft()

            if not resting_queue:
                del symbol_levels[best_price]

                self._price_tokens[resting_side][
                    incoming_order.symbol
                ].pop(best_price, None)

        if not symbol_levels:
            opposite_book.pop(incoming_order.symbol, None)

        if incoming_order.quantity > 0:
            self.add_order(incoming_order)

        return trades