# ChronosMatch: Zero-Copy High-Frequency Trading Engine

## Project Overview

ChronosMatch is a Python-based high-frequency trading engine simulation developed to explore low-latency order processing, price-time priority matching, memory-mapped inter-process communication (IPC), and persistent trade and order-book state.

The project combines Python with Cython optimization, binary order messages, ring buffers, SQLite persistence, and latency benchmarking.

## Objectives

- Implement an order book with price-time priority matching.
- Encode and decode binary order messages.
- Explore in-process and memory-mapped ring buffers.
- Implement memory-mapped IPC for communication between processes.
- Measure order-processing latency and benchmark throughput.
- Persist executed trades using SQLite.
- Save and restore order-book snapshots.
- Validate correctness using automated tests.

## Technologies

- **Language:** Python
- **Performance:** Cython
- **IPC and memory:** `mmap`, `struct`, ring buffers
- **Asynchronous processing:** `asyncio`
- **Persistence:** SQLite
- **Testing:** pytest
- **Version control:** Git and GitHub

## Project Structure

```text
ChronosMatch/
├── src/
│   ├── orders.py
│   ├── order_book.py
│   ├── order_message.py
│   ├── ring_buffer.py
│   ├── mmap_ring_buffer.py
│   ├── shared_order_message_bus.py
│   ├── trade_ledger.py
│   ├── order_book_snapshot.py
│   ├── market_simulator.py
│   ├── latency.py
│   ├── latency_monitor.py
│   ├── benchmark.py
│   ├── ipc_benchmark.py
│   ├── ipc_audit.py
│   └── matching_engine.pyx
├── tests/
├── data/
├── requirements.txt
├── setup.py
└── README.md
```

## Core Features

### 1. Order Book and Matching

Maintains buy and sell orders and supports price-time priority matching.

### 2. Binary Order Messages

Encodes and decodes order messages using Python's `struct` module.

### 3. Ring Buffers and IPC

Includes in-process ring buffers, memory-mapped buffers, and a file-backed shared order-message bus for inter-process communication.

### 4. Cython Optimization

Uses a Cython extension for price-crossing comparisons in the matching engine.

### 5. Trade Persistence

Stores executed trades in SQLite and includes integrity-checking and persistence tests.

### 6. Order-Book Snapshots

Supports saving and loading order-book snapshots, including tests for recovery behavior and save failures.

### 7. Latency Monitoring and Benchmarking

Provides latency tracking, a monitoring dashboard, IPC benchmarks, and cross-process audit utilities.

## Installation

Use Python and run these commands from the project root:

```bash
python -m pip install -r requirements.txt
python -m pip install cython
python setup.py build_ext --inplace
```

## Run Tests

```bash
python -m pytest -q
```

The latest recorded test run passed **95 tests**. Run the command above to verify the current checkout.

## Performance Testing

The repository includes benchmark and IPC audit modules under `src/`. Run a benchmark using the relevant module's supported options and record the workload, number of trials, throughput, and latency results.

Performance depends on the workload and environment. Benchmark results should be measured and reported rather than treated as guaranteed production performance.

## Project Status

The project has implemented core order-book matching, binary messaging, ring buffers, memory-mapped IPC, Cython price comparison, latency monitoring, SQLite trade persistence, and order-book snapshot functionality.

Further work includes integrating snapshot recovery into simulator startup and shutdown, validating end-to-end latency under larger workloads, and improving operational reliability.

## Disclaimer

ChronosMatch is an educational trading-engine simulation. It is not a production-ready exchange or a system intended to execute real financial trades.
