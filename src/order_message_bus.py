
import mmap

from src.order_message import ORDER_SIZE


class OrderMessageBus:
    """Fixed-size FIFO buffer for binary order messages."""

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")

        self.capacity = capacity
        self.slot_size = ORDER_SIZE
        self.total_size = capacity * self.slot_size

        self.memory = mmap.mmap(-1, self.total_size)
        self.write_index = 0
        self.read_index = 0
        self.size = 0
        self.closed = False

    def is_empty(self):
        return self.size == 0

    def is_full(self):
        return self.size == self.capacity

    def write(self, message):
        if self.closed:
            raise ValueError("Message bus is closed")

        if len(message) != self.slot_size:
            raise ValueError(
                f"Message must be exactly {self.slot_size} bytes"
            )

        if self.is_full():
            raise BufferError("Message bus is full")

        offset = self.write_index * self.slot_size
        self.memory[offset:offset + self.slot_size] = message

        self.write_index = (self.write_index + 1) % self.capacity
        self.size += 1

    def read(self):
        if self.closed:
            raise ValueError("Message bus is closed")

        if self.is_empty():
            raise BufferError("Message bus is empty")

        offset = self.read_index * self.slot_size
        message = self.memory[offset:offset + self.slot_size]

        self.read_index = (self.read_index + 1) % self.capacity
        self.size -= 1

        return message

    def close(self):
        if not self.closed:
            self.memory.close()
            self.closed = True
