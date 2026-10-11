
from src.orders import Order


def test_create_buy_order():
    order = Order(
        order_id=1,
        symbol="ABC",
        side="BUY",
        price=100.50,
        quantity=10,
        timestamp_ns=123456789
    )

    assert order.order_id == 1
    assert order.symbol == "ABC"
    assert order.side == "BUY"
    assert order.price == 100.50
    assert order.quantity == 10
    assert order.timestamp_ns == 123456789
