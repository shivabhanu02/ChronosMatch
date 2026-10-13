
import pytest

from src.mmap_ring_buffer import MMapRingBuffer


def test_write_and_read():
    rb = MMapRingBuffer(3)
    try:
        rb.write(100)
        rb.write(200)

        assert rb.read() == 100
        assert rb.read() == 200
        assert rb.is_empty()
    finally:
        rb.close()


def test_buffer_full():
    rb = MMapRingBuffer(2)
    try:
        rb.write(10)
        rb.write(20)

        assert rb.is_full()

        with pytest.raises(BufferError):
            rb.write(30)
    finally:
        rb.close()


def test_buffer_empty():
    rb = MMapRingBuffer(2)
    try:
        with pytest.raises(BufferError):
            rb.read()
    finally:
        rb.close()


def test_wraparound():
    rb = MMapRingBuffer(2)
    try:
        rb.write(10)
        rb.write(20)

        assert rb.read() == 10

        rb.write(30)

        assert rb.read() == 20
        assert rb.read() == 30
        assert rb.is_empty()
    finally:
        rb.close()


def test_invalid_capacity():
    with pytest.raises(ValueError):
        MMapRingBuffer(0)
