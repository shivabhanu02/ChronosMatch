
"""Tests for the ChronosMatch SQLite trade ledger."""

import pytest

from src.trade_ledger import TradeLedger


@pytest.fixture
def ledger(tmp_path):
    database = tmp_path / "test_trades.db"

    with TradeLedger(database) as trade_ledger:
        yield trade_ledger


@pytest.fixture
def sample_trade():
    return {
        "symbol": "ABC",
        "price": 100.0,
        "quantity": 3,
        "buy_order_id": 2,
        "sell_order_id": 1,
        "executed_at_ns": 123456789,
    }


def test_new_ledger_has_no_trades(ledger):
    assert ledger.count_trades() == 0
    assert ledger.get_all_trades() == []


def test_save_and_retrieve_trade(ledger, sample_trade):
    assert ledger.save_trade(sample_trade) is True

    trades = ledger.get_all_trades()

    assert len(trades) == 1
    assert trades[0]["symbol"] == "ABC"
    assert trades[0]["price"] == 100.0
    assert trades[0]["quantity"] == 3
    assert trades[0]["buy_order_id"] == 2
    assert trades[0]["sell_order_id"] == 1
    assert trades[0]["executed_at_ns"] == 123456789


def test_duplicate_trade_is_not_inserted(ledger, sample_trade):
    assert ledger.save_trade(sample_trade) is True
    assert ledger.save_trade(sample_trade) is False
    assert ledger.count_trades() == 1


def test_save_multiple_trades(ledger, sample_trade):
    second_trade = {
        **sample_trade,
        "symbol": "XYZ",
        "price": 25.75,
        "quantity": 10,
        "buy_order_id": 4,
        "sell_order_id": 3,
    }

    inserted = ledger.save_trades([sample_trade, second_trade])

    assert inserted == 2
    assert ledger.count_trades() == 2


def test_trade_survives_database_reopen(tmp_path, sample_trade):
    database = tmp_path / "persistent_trades.db"

    with TradeLedger(database) as first:
        first.save_trade(sample_trade)

    with TradeLedger(database) as reopened:
        trades = reopened.get_all_trades()

    assert len(trades) == 1
    assert trades[0]["symbol"] == "ABC"
    assert trades[0]["quantity"] == 3


def test_missing_fields_are_rejected(ledger):
    with pytest.raises(ValueError, match="missing required fields"):
        ledger.save_trade({"symbol": "ABC"})


@pytest.mark.parametrize(
    "field,value",
    [
        ("price", 0),
        ("price", -10),
        ("quantity", 0),
        ("quantity", -1),
    ],
)
def test_invalid_trade_values_are_rejected(
    ledger, sample_trade, field, value
):
    invalid_trade = {**sample_trade, field: value}

    with pytest.raises(ValueError):
        ledger.save_trade(invalid_trade)


def test_batch_save_rolls_back_on_invalid_trade(ledger, sample_trade):
    invalid_trade = {"symbol": "ABC"}

    with pytest.raises(ValueError):
        ledger.save_trades([sample_trade, invalid_trade])

    assert ledger.count_trades() == 0
