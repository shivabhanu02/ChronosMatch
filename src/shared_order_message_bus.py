
"""File-backed mmap order bus with cross-process locking and batch operations."""

import errno
import mmap
import os
import struct
import time
from contextlib import contextmanager

from src.order_message import ORDER_SIZE

_HEADER = struct.Struct("<8sQQQQ")
_MAGIC = b"CHRONOS1"
_HEADER_SIZE = _HEADER.size


class SharedOrderMessageBus:
    """Fixed-capacity FIFO for binary orders shared between processes."""

    def __init__(self, path, capacity):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero")

        self.path = os.path.abspath(path)
        self.lock_path = self.path + ".lock"
        self.capacity = capacity
        self.slot_size = ORDER_SIZE
        self.total_size = _HEADER_SIZE + capacity * ORDER_SIZE
        self.closed = False

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._data_file = open(self.path, "a+b")
        self._lock_file = open(self.lock_path, "a+b")

        try:
            with self._file_lock():
                self._lock_file.seek(0, os.SEEK_END)
                if self._lock_file.tell() == 0:
                    self._lock_file.write(b"\0")
                    self._lock_file.flush()

                self._data_file.seek(0, os.SEEK_END)
                current_size = self._data_file.tell()

                if current_size == 0:
                    self._data_file.truncate(self.total_size)
                    self._data_file.flush()
                    self.memory = mmap.mmap(
                        self._data_file.fileno(),
                        self.total_size,
                        access=mmap.ACCESS_WRITE,
                    )
                    self._write_header(0, 0, 0)
                else:
                    if current_size != self.total_size:
                        raise ValueError(
                            "Existing shared bus has a different capacity "
                            "or incompatible file size"
                        )
                    self.memory = mmap.mmap(
                        self._data_file.fileno(),
                        self.total_size,
                        access=mmap.ACCESS_WRITE,
                    )
                    magic, stored_capacity, _, _, _ = self._read_header()
                    if magic != _MAGIC or stored_capacity != capacity:
                        raise ValueError(
                            "Existing file is not a compatible shared bus"
                        )
                    self._validate_header()
        except Exception:
            if hasattr(self, "memory"):
                self.memory.close()
            self._lock_file.close()
            self._data_file.close()
            raise

    @contextmanager
    def _file_lock(self):
        """Acquire a cross-process lock without Windows' one-second retries."""
        self._lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(
                        self._lock_file.fileno(), msvcrt.LK_NBLCK, 1
                    )
                    break
                except OSError as exc:
                    if exc.errno not in (
                        errno.EACCES,
                        errno.EDEADLK,
                        errno.EAGAIN,
                        errno.EPERM,
                    ):
                        raise
                    time.sleep(0.0001)

            try:
                yield
            finally:
                self._lock_file.seek(0)
                msvcrt.locking(
                    self._lock_file.fileno(), msvcrt.LK_UNLCK, 1
                )
        else:
            import fcntl

            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)

    def _read_header(self):
        return _HEADER.unpack_from(self.memory, 0)

    def _write_header(self, write_index, read_index, size):
        _HEADER.pack_into(
            self.memory,
            0,
            _MAGIC,
            self.capacity,
            write_index,
            read_index,
            size,
        )

    def _validate_header(self):
        magic, capacity, write_index, read_index, size = self._read_header()
        if (
            magic != _MAGIC
            or capacity != self.capacity
            or not 0 <= write_index < self.capacity
            or not 0 <= read_index < self.capacity
            or not 0 <= size <= self.capacity
        ):
            raise ValueError("Shared bus metadata is invalid")

    def is_empty(self):
        self._ensure_open()
        with self._file_lock():
            self._validate_header()
            return self._read_header()[4] == 0

    def is_full(self):
        self._ensure_open()
        with self._file_lock():
            self._validate_header()
            return self._read_header()[4] == self.capacity

    def write_many(self, messages):
        """Write as many messages as fit; return the number written."""
        self._ensure_open()
        messages = list(messages)

        for message in messages:
            if len(message) != self.slot_size:
                raise ValueError(
                    f"Each message must be exactly {self.slot_size} bytes"
                )

        if not messages:
            return 0

        with self._file_lock():
            self._validate_header()
            _, _, write_index, read_index, size = self._read_header()
            available = self.capacity - size
            count = min(len(messages), available)

            for i in range(count):
                offset = _HEADER_SIZE + write_index * self.slot_size
                self.memory[offset:offset + self.slot_size] = messages[i]
                write_index = (write_index + 1) % self.capacity

            if count:
                self._write_header(write_index, read_index, size + count)
            return count

    def read_many(self, max_items):
        """Read up to max_items messages in FIFO order."""
        self._ensure_open()
        if max_items <= 0:
            raise ValueError("max_items must be greater than zero")

        with self._file_lock():
            self._validate_header()
            _, _, write_index, read_index, size = self._read_header()
            count = min(max_items, size)
            messages = []

            for _ in range(count):
                offset = _HEADER_SIZE + read_index * self.slot_size
                messages.append(
                    self.memory[offset:offset + self.slot_size]
                )
                read_index = (read_index + 1) % self.capacity

            if count:
                self._write_header(write_index, read_index, size - count)
            return messages

    def write(self, message):
        """Write one message or raise BufferError if the bus is full."""
        if len(message) != self.slot_size:
            raise ValueError(
                f"Message must be exactly {self.slot_size} bytes"
            )
        if self.write_many([message]) == 0:
            raise BufferError("Shared order bus is full")

    def read(self):
        """Read one message or raise BufferError if the bus is empty."""
        messages = self.read_many(1)
        if not messages:
            raise BufferError("Shared order bus is empty")
        return messages[0]

    def _ensure_open(self):
        if self.closed:
            raise ValueError("Shared order bus is closed")

    def close(self):
        if not self.closed:
            self.memory.close()
            self._lock_file.close()
            self._data_file.close()
            self.closed = True
