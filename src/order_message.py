
import struct

from src.orders import Order


# Binary message layout:
# order_id:  unsigned 64-bit integer
# symbol:    8 ASCII bytes
# side:      1 byte (1 = BUY, 2 = SELL)
# price:     unsigned 64-bit integer in paise
# quantity:  unsigned 32-bit integer
# timestamp: unsigned 64-bit integer in nanoseconds

ORDER_FORMAT = "!Q8sBQI Q".replace(" ", "")
ORDER_SIZE = struct.calcsize(ORDER_FORMAT)

BUY_CODE = 1
SELL_CODE = 2


def encode_order(order: Order) -> bytes:
    if order.side not in ("BUY", "SELL"):
        raise ValueError("Side must be BUY or SELL")

    if not order.symbol.isascii():
        raise ValueError("Symbol must contain ASCII characters only")

    symbol_bytes = order.symbol.encode("ascii")

    if not 1 <= len(symbol_bytes) <= 8:
        raise ValueError("Symbol must be between 1 and 8 ASCII bytes")

    if order.order_id < 0 or order.order_id > (2**64 - 1):
        raise ValueError("Order ID is outside the supported range")

    if order.price <= 0:
        raise ValueError("Price must be greater than zero")

    price_paise = round(order.price * 100)

    if not 0 <= price_paise <= (2**64 - 1):
        raise ValueError("Price is outside the supported range")

    if not 1 <= order.quantity <= (2**32 - 1):
        raise ValueError("Quantity is outside the supported range")

    if not 0 <= order.timestamp_ns <= (2**64 - 1):
        raise ValueError("Timestamp is outside the supported range")

    side_code = BUY_CODE if order.side == "BUY" else SELL_CODE

    return struct.pack(
        ORDER_FORMAT,
        order.order_id,
        symbol_bytes.ljust(8, b"\0"),
        side_code,
        price_paise,
        order.quantity,
        order.timestamp_ns,
    )


def decode_order(message: bytes) -> Order:
    if len(message) != ORDER_SIZE:
        raise ValueError(f"Message must be exactly {ORDER_SIZE} bytes")

    order_id, symbol_bytes, side_code, price_paise, quantity, timestamp_ns = (
        struct.unpack(ORDER_FORMAT, message)
    )

    if side_code not in (BUY_CODE, SELL_CODE):
        raise ValueError("Invalid side code")

    symbol = symbol_bytes.rstrip(b"\0").decode("ascii")

    if not symbol:
        raise ValueError("Symbol cannot be empty")

    side = "BUY" if side_code == BUY_CODE else "SELL"

    return Order(
        order_id=order_id,
        symbol=symbol,
        side=side,
        price=price_paise / 100,
        quantity=quantity,
        timestamp_ns=timestamp_ns,
    )
