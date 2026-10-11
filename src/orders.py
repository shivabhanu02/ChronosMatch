
from dataclasses import dataclass
from typing import Literal


@dataclass
class Order:
    order_id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    timestamp_ns: int
