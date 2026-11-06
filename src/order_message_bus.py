
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
        self.write_many([message])

    def write_many(self, messages):
        if self.closed:
            raise ValueError("Message bus is closed")

        messages = list(messages)

        if not messages:
            return 0

        for message in messages:
            if len(message) != self.slot_size:
                raise ValueError(
                    f"Message must be exactly {self.slot_size} bytes"
                )

        if len(messages) > self.capacity - self.size:
            raise BufferError("Message bus does not have enough free space")

        first_count = min(len(messages), self.capacity - self.write_index)

        first_data = b"".join(messages[:first_count])
        first_offset = self.write_index * self.slot_size
        self.memory[first_offset:first_offset + len(first_data)] = first_data

        remaining = messages[first_count:]

        if remaining:
            second_data = b"".join(remaining)
            self.memory[:len(second_data)] = second_data

        self.write_index = (self.write_index + len(messages)) % self.capacity
        self.size += len(messages)

        return len(messages)

    def read(self):
        messages = self.read_many(1)
        return messages[0]

    def read_many(self, max_items):
        if self.closed:
            raise ValueError("Message bus is closed")

        if not isinstance(max_items, int) or isinstance(max_items, bool):
            raise TypeError("max_items must be an integer")

        if max_items <= 0:
            raise ValueError("max_items must be greater than zero")

        if self.is_empty():
            raise BufferError("Message bus is empty")

        count = min(max_items, self.size)
        first_count = min(count, self.capacity - self.read_index)

        first_offset = self.read_index * self.slot_size
        first_end = first_offset + first_count * self.slot_size

        result = [
            self.memory[
                first_offset + i * self.slot_size:
                first_offset + (i + 1) * self.slot_size
            ]
            for i in range(first_count)
        ]

        remaining = count - first_count

        if remaining:
            result.extend(
                self.memory[
                    i * self.slot_size:(i + 1) * self.slot_size
                ]
                for i in range(remaining)
            )

        self.read_index = (self.read_index + count) % self.capacity
        self.size -= count

        return result

    def close(self):
        if not self.closed:
            self.memory.close()
            self.closed = True
