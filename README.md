# ChronosMatch
### Zero-Copy High-Frequency Trading Engine

ChronosMatch is a Python-based high-frequency trading engine prototype developed as part of the Infotact Solutions Python Development Internship.

The project explores low-latency order processing using memory-mapped communication, binary order messages, a Cython-accelerated matching component, asynchronous market simulation, and live latency monitoring.

## 1. Project Objectives

- Process incoming buy and sell orders efficiently.
- Implement price-time priority matching.
- Use binary messages instead of JSON or Pickle for order communication.
- Support inter-process communication using memory-mapped files.
- Accelerate matching operations using Cython.
- Simulate market activity asynchronously.
- Measure execution latency and display market statistics.
- Persist executed trades in SQLite using background batch processing.

## 2. Main Features

- **Order Book:** Maintains buy and sell orders with price-time priority.
- **Cython Matching Component:** Accelerates price comparison and FIFO quantity matching.
- **Binary Order Messaging:** Encodes and decodes orders using Python's `struct` module.
- **Memory-Mapped Ring Buffers:** Supports buffered order communication.
- **Shared IPC Bus:** Enables communication between separate processes.
- **Async Market Simulator:** Generates and processes simulated market orders.
- **Trade Persistence:** Saves executed trades to SQLite in batches.
- **Latency Monitoring:** Tracks minimum, maximum, average, P50, P95, and P99 latency.
- **Live Dashboard:** Displays latency statistics, best bid/ask, spread, and whale-order events.

## 3. Project Architecture

The main processing flow is:

1. The market simulator generates incoming orders.
2. Orders are encoded into binary messages.
3. The message bus transfers orders through its buffer.
4. The order book processes incoming orders.
5. The matching component performs price and FIFO quantity matching.
6. Executed trades are sent to the background persistence queue.
7. Trade batches are saved to SQLite.
8. Latency samples and market state are made available to the monitoring dashboard.

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main application development |
| Cython | Accelerated matching operations |
| asyncio | Asynchronous market simulation |
| mmap | Memory-mapped communication |
| struct | Binary order encoding |
| SQLite | Trade persistence |
| pytest | Automated testing |
| curses | Terminal-based monitoring |
| Git and GitHub | Version control |

## 5. Project Structure

```text
ChronosMatch/
│
├── data/
│   ├── market_state.json
│   ├── latency_samples.jsonl
│   └── trade database
│
├── src/
│   ├── orders.py
│   ├── order_book.py
│   ├── matching_engine.pyx
│   ├── matching_engine.c
│   ├── ring_buffer.py
│   ├── mmap_ring_buffer.py
│   ├── order_message.py
│   ├── order_message_bus.py
│   ├── shared_order_message_bus.py
│   ├── ipc_audit.py
│   ├── ipc_benchmark.py
│   ├── ipc_latency_benchmark.py
│   ├── market_simulator.py
│   ├── trade_ledger.py
│   ├── latency.py
│   ├── latency_monitor.py
│   └── benchmark.py
│
├── tests/
│   ├── test_orders.py
│   ├── test_order_book.py
│   ├── test_matching_engine.py
│   ├── test_ring_buffer.py
│   ├── test_mmap_ring_buffer.py
│   ├── test_order_message.py
│   ├── test_order_message_bus.py
│   ├── test_shared_order_message_bus.py
│   ├── test_trade_ledger.py
│   ├── test_latency.py
│   ├── test_latency_monitor.py
│   └── test_benchmark.py
│
├── requirements.txt
├── setup.py
└── README.md
```

## 6. Installation and Setup

### Prerequisites

- Python 3.10 or later
- pip
- Git
- A C compiler supported by the installed Python and Cython toolchain

### Step 1: Clone the repository

```bash
git clone https://github.com/shivabhanu02/ChronosMatch.git
cd ChronosMatch
```

### Step 2: Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 3: Build the Cython extension

```bash
python setup.py build_ext --inplace
```

## 7. Running the Project

### Start the market simulator

```bash
python -m src.market_simulator
```

This runs the asynchronous order simulation, matching process, latency measurement, and background trade persistence.

### Start the latency dashboard

Open another terminal in the project directory and run:

```bash
python -m src.latency_monitor
```

Run the dashboard while the simulator is active to observe live market and latency information.

### Run the dashboard in demonstration mode

```bash
python -m src.latency_monitor --demo
```

## 8. Running Tests

Execute the complete test suite:

```bash
python -m pytest -q
```

**Latest recorded test result:**

```text
103 passed in 1.38s
```

All 103 tests passed in the latest recorded run.

## 9. Performance Measurements

The following are recorded results from project testing, not guaranteed production performance.

### Market simulation

| Metric | Recorded result |
|---|---:|
| Orders processed | 100,000 |
| Trades executed | 77,533 |
| Simulation time | 5.345 seconds |
| Throughput | 18,708 orders/second |
| Average matching latency | 6.32 µs |
| P50 latency | 2.70 µs |
| P95 latency | 10.70 µs |
| P99 latency | 24.30 µs |
| Maximum matching latency | 3.13 ms |

### Inter-process communication audit

A separate 1-million-order IPC audit recorded:

- Orders transferred: 1,000,000
- Throughput: approximately 334,874 orders/second
- FIFO ordering: Passed
- Data integrity: Passed

These measurements represent separate tests and should not be interpreted as the same workload.

## 10. Important Implementation Notes

- The matching component uses Cython for compiled price comparison and FIFO quantity calculations.
- The Python order book still manages order queues and trade objects.
- Memory-mapped communication is implemented, but some message operations create byte copies; the implementation should not be described as completely copy-free.
- The simulator uses asynchronous coordination and background trade persistence.
- Latency measurements are collected using high-resolution performance timestamps.

## 11. Internship Project

**Organization:** Infotact Solutions  
**Domain:** Python Development  
**Project:** ChronosMatch — Zero-Copy High-Frequency Trading Engine  
**Repository:** https://github.com/shivabhanu02/ChronosMatch

## 12. Future Improvements

- Move more order-book operations into C-level data structures.
- Reduce Python object creation in the matching path.
- Further optimize memory-mapped message handling.
- Improve sustained order throughput and tail latency.
- Expand performance testing under concurrent workloads.

---

**ChronosMatch — Efficient Order Processing, Matching, and Latency Monitoring.**