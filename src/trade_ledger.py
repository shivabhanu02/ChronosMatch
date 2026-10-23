
"""Durable SQLite persistence for ChronosMatch executed trades."""

import sqlite3
from pathlib import Path


DEFAULT_DATABASE = Path("data/chronosmatch_trades.db")


class TradeLedger:
    """Persist trades with SQLite durability and integrity checks."""

    def __init__(self, database_path=DEFAULT_DATABASE):
        self.database_path = str(database_path)

        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(
                parents=True, exist_ok=True
            )

        self.connection = sqlite3.connect(
            self.database_path,
            timeout=10.0,
        )
        self.connection.row_factory = sqlite3.Row

        if self.database_path != ":memory:":
            self.connection.execute("PRAGMA journal_mode=WAL")

        self.connection.execute("PRAGMA synchronous=FULL")
        self._create_schema()

    def _create_schema(self):
        """Create the trade table and indexes if they do not exist."""
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

            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trades_symbol
                ON trades(symbol)
                """
            )

    @staticmethod
    def _validate_trade(trade):
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

        symbol = str(trade["symbol"]).strip()
        price = float(trade["price"])
        quantity = int(trade["quantity"])
        buy_order_id = int(trade["buy_order_id"])
        sell_order_id = int(trade["sell_order_id"])
        executed_at_ns = int(trade.get("executed_at_ns", 0))

        if not symbol:
            raise ValueError("Trade symbol cannot be empty")
        if price <= 0:
            raise ValueError("Trade price must be positive")
        if quantity <= 0:
            raise ValueError("Trade quantity must be positive")
        if buy_order_id < 0 or sell_order_id < 0:
            raise ValueError("Order IDs cannot be negative")
        if executed_at_ns < 0:
            raise ValueError("Execution timestamp cannot be negative")

        return (
            symbol,
            price,
            quantity,
            buy_order_id,
            sell_order_id,
            executed_at_ns,
        )

    def save_trade(self, trade):
        """Save one trade; return True only when newly inserted."""
        values = self._validate_trade(trade)

        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO trades (
                    symbol, price, quantity,
                    buy_order_id, sell_order_id, executed_at_ns
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                values,
            )

        return cursor.rowcount == 1

    def save_trades(self, trades):
        """Save trades atomically; roll back the entire batch on failure."""
        values = [self._validate_trade(trade) for trade in trades]

        with self.connection:
            inserted = 0

            for trade_values in values:
                cursor = self.connection.execute(
                    """
                    INSERT OR IGNORE INTO trades (
                        symbol, price, quantity,
                        buy_order_id, sell_order_id, executed_at_ns
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    trade_values,
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

    def verify_integrity(self):
        """Return SQLite's database integrity-check messages."""
        rows = self.connection.execute(
            "PRAGMA integrity_check"
        ).fetchall()
        return [row[0] for row in rows]

    def checkpoint(self):
        """Checkpoint the WAL for a file-backed database."""
        if self.database_path == ":memory:":
            return None

        return tuple(
            self.connection.execute(
                "PRAGMA wal_checkpoint(PASSIVE)"
            ).fetchone()
        )

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
