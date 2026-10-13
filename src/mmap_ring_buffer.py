
import mmap
import struct


class MMapRingBuffer:
    """
    A basic fixed-size ring buffer backed by anonymous memory mapping.

    Each slot stores one signed 64-bit integer.
    """

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")

        self.capacity = capacity
        self.slot_size = struct.calcsize("q")
        self.total_size = self.capacity * self.slot_size

        self.memory = mmap.mmap(-1, self.total_size)
        self.write_index = 0
        self.read_index = 0
        self.size = 0

    def is_empty(self):
        return self.size == 0

    def is_full(self):
        return self.size == self.capacity

    def write(self, value):
        if self.is_full():
            raise BufferError("Ring buffer is full")

        offset = self.write_index * self.slot_size
        struct.pack_into("q", self.memory, offset, value)

        self.write_index = (self.write_index + 1) % self.capacity
        self.size += 1

    def read(self):
        if self.is_empty():
            raise BufferError("Ring buffer is empty")

        offset = self.read_index * self.slot_size
        value = struct.unpack_from("q", self.memory, offset)[0]

        self.read_index = (self.read_index + 1) % self.capacity
        self.size -= 1

        return value

    def close(self):
        self.memory.close()
