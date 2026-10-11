
class RingBuffer:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")

        self.capacity = capacity
        self.buffer = [None] * capacity
        self.write_index = 0
        self.read_index = 0
        self.size = 0

    def is_empty(self):
        return self.size == 0

    def is_full(self):
        return self.size == self.capacity

    def write(self, item):
        if self.is_full():
            raise BufferError("Ring buffer is full")

        self.buffer[self.write_index] = item
        self.write_index = (self.write_index + 1) % self.capacity
        self.size += 1

    def read(self):
        if self.is_empty():
            raise BufferError("Ring buffer is empty")

        item = self.buffer[self.read_index]
        self.buffer[self.read_index] = None
        self.read_index = (self.read_index + 1) % self.capacity
        self.size -= 1

        return item
