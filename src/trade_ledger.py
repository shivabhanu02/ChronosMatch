
"""SQLite persistence for executed ChronosMatch trades."""

import sqlite3
from pathlib import Path


DEFAULT_DATABASE = Path("data/chronosmatch_trades.db")


class TradeLedger:
    """Persist executed trades and recover them after application restarts."""

    def __init__(self, database_path=DEFAULT_DATABASE):
        self.database_path = str(database_path)

        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(
                parents=True, exist_ok=True
            )

        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        """Create the trade table if it does not already exist."""
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL CHECK (price > 0),
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    buy_order_id INTEGER NOT NULL,
                    sell_order_id INTEGER NOT NULL,
                    executed_at_ns INTEGER NOT NULL,
                    UNIQUE (
                        symbol,
                        price,
                        quantity,
                        buy_order_id,
                        sell_order_id
                    )
                )
                """
            )

    def save_trade(self, trade):
        """Save one trade; return True if it was newly inserted."""
        required = {
            "symbol",
            "price",
            "quantity",
            "buy_order_id",
            "sell_order_id",
        }
        missing = required.difference(trade)

        if missing:
            raise ValueError(
                f"Trade is missing required fields: {sorted(missing)}"
            )

        symbol = str(trade["symbol"])
        price = float(trade["price"])
        quantity = int(trade["quantity"])
        buy_order_id = int(trade["buy_order_id"])
        sell_order_id = int(trade["sell_order_id"])

        if not symbol.strip():
            raise ValueError("Trade symbol cannot be empty")
        if price <= 0:
            raise ValueError("Trade price must be positive")
        if quantity <= 0:
            raise ValueError("Trade quantity must be positive")

        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO trades (
                    symbol,
                    price,
                    quantity,
                    buy_order_id,
                    sell_order_id,
                    executed_at_ns
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    price,
                    quantity,
                    buy_order_id,
                    sell_order_id,
                    int(trade.get("executed_at_ns", 0)),
                ),
            )

        return cursor.rowcount == 1

    def save_trades(self, trades):
        """Save a collection of trades and return the number inserted."""
        inserted = 0

        with self.connection:
            for trade in trades:
                required = {
                    "symbol",
                    "price",
                    "quantity",
                    "buy_order_id",
                    "sell_order_id",
                }
                missing = required.difference(trade)

                if missing:
                    raise ValueError(
                        f"Trade is missing required fields: "
                        f"{sorted(missing)}"
                    )

                symbol = str(trade["symbol"])
                price = float(trade["price"])
                quantity = int(trade["quantity"])
                buy_order_id = int(trade["buy_order_id"])
                sell_order_id = int(trade["sell_order_id"])

                if not symbol.strip():
                    raise ValueError("Trade symbol cannot be empty")
                if price <= 0:
                    raise ValueError("Trade price must be positive")
                if quantity <= 0:
                    raise ValueError("Trade quantity must be positive")

                cursor = self.connection.execute(
                    """
                    INSERT OR IGNORE INTO trades (
                        symbol,
                        price,
                        quantity,
                        buy_order_id,
                        sell_order_id,
                        executed_at_ns
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        price,
                        quantity,
                        buy_order_id,
                        sell_order_id,
                        int(trade.get("executed_at_ns", 0)),
                    ),
                )
                inserted += cursor.rowcount

        return inserted

    def get_all_trades(self):
        """Return persisted trades in insertion order."""
        rows = self.connection.execute(
            """
            SELECT id, symbol, price, quantity,
                   buy_order_id, sell_order_id, executed_at_ns
            FROM trades
            ORDER BY id
            """
        ).fetchall()

        return [dict(row) for row in rows]

    def count_trades(self):
        """Return the number of trades in the ledger."""
        row = self.connection.execute(
            "SELECT COUNT(*) AS total FROM trades"
        ).fetchone()
        return row["total"]

    def close(self):
        """Close the database connection."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
