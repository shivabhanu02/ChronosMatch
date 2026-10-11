
import pytest

from src.ring_buffer import RingBuffer


def test_write_and_read():
    rb = RingBuffer(3)

    rb.write("A")
    rb.write("B")

    assert rb.read() == "A"
    assert rb.read() == "B"
    assert rb.is_empty()


def test_buffer_becomes_full():
    rb = RingBuffer(2)

    rb.write("A")
    rb.write("B")

    assert rb.is_full()

    with pytest.raises(BufferError):
        rb.write("C")


def test_buffer_becomes_empty():
    rb = RingBuffer(2)

    with pytest.raises(BufferError):
        rb.read()


def test_index_wraps_around():
    rb = RingBuffer(2)

    rb.write("A")
    rb.write("B")
    assert rb.read() == "A"

    rb.write("C")

    assert rb.read() == "B"
    assert rb.read() == "C"
    assert rb.is_empty()


def test_invalid_capacity():
    with pytest.raises(ValueError):
        RingBuffer(0)
