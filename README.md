# Mini-2 gRPC: Distributed Fire Air Quality Query System

A multi-process distributed system for querying fire air quality data using gRPC, featuring **chunked streaming**, **request control**, and intelligent data partitioning across 5 worker servers.

## 🎯 Project Status: 100% Complete ✅

✅ **Phase 1:** Data Partitioning (COMPLETE)  
✅ **Phase 2:** Chunked Streaming & Request Control (COMPLETE)  
✅ **Phase 2.5:** Performance Analysis (COMPLETE)  
✅ **Single-Computer:** Fully Validated & Documented  
✅ **Phase 3:** Multi-Computer Deployment (COMPLETE - 2 computers, 1.5ms latency)

---

## 🚀 Quick Start

### Run the Full System Test
```bash
./test_phase2.sh
```

This automated script:
- Starts all 6 servers
- Runs comprehensive tests
- Demonstrates chunked streaming, cancellation, and status tracking
- Shows server logs and statistics

**Press Enter when done to stop all servers.**

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `MULTI_COMPUTER_RESULTS.md` | **✅ Multi-computer deployment results (2 machines)** |
| `SINGLE_COMPUTER_COMPLETE.md` | **✅ Single-computer deployment guide** |
| `results/single_computer_analysis.md` | **✅ Performance analysis & benchmarks** |
| `MULTI_COMPUTER_SETUP.md` | Multi-computer setup guide |
| `PROJECT_STATUS.md` | Overall project status and checklist |
| `PHASE1_DATA_PARTITIONING_COMPLETE.md` | Phase 1 technical details |
| `PHASE2_CHUNKED_STREAMING_COMPLETE.md` | Phase 2 technical details |
| `presentation-iteration-1.md` | Bug fixes and iterations |

---

## 🏗️ System Architecture

```
                      Client
                        |
                        v
                  Gateway A (50051)
                  [Chunked Streaming]
                  [Request Control]
                   /            \
                  /              \
                 v                v
           Server B            Server E
        (Green Leader)       (Pink Leader)
           (50052)             (50055)
              |                /      \
              v               v        v
           Server C       Server D   Server F
           (Worker)       (Worker)   (Worker)
           (50053)        (50054)    (50056)
```

### Data Distribution
- **Server B:** 134K measurements (Aug 10-17)
- **Server C:** 243K measurements (Aug 18-26)
- **Server D:** 244K measurements (Aug 27-Sep 4)
- **Server E:** 245K measurements (Sep 5-13)
- **Server F:** 300K measurements (Sep 14-24)
- **Total:** 1.17M measurements, 0% overlap

### Query Traversal Algorithm

The system uses a **parallel post-order tree traversal** pattern:

**Query Propagation (Top-Down):**
1. Client → Gateway A (root node)
2. Gateway A → Team Leaders B & E (parallel broadcast)
3. Leader B → Worker C
4. Leader E → Workers D & F (parallel broadcast)

**Result Aggregation (Bottom-Up):**
1. Workers (C, D, F) query local data and return results to their leaders
2. Leaders (B, E) aggregate worker results with their own local data
3. Gateway A aggregates results from both team leaders
4. Gateway A streams chunked results to client

**Traversal Characteristics:**
- **Type:** Depth-first with post-order processing
- **Execution:** Parallel at each level (fan-out to children)
- **Aggregation:** Bottom-up (children complete before parent)
- **Complexity:** O(log n) depth for balanced tree, O(n) for visiting all nodes

**Example Query Flow:**
```
Query: "Find all PM2.5 measurements with AQI < 100"

Step 1: Client sends query to A
Step 2: A forwards to B and E (parallel)
Step 3: B forwards to C, E forwards to D and F (parallel)
Step 4: C returns 50K results to B
Step 5: D returns 60K results to E
Step 6: F returns 70K results to E
Step 7: B (adds own 30K) returns 80K total to A
Step 8: E (adds own 40K) returns 170K total to A
Step 9: A aggregates 250K total results
Step 10: A streams results in chunks to client
```

**Benefits:**
- **Parallelism:** Multiple servers process simultaneously
- **Load distribution:** Work divided across all servers
- **Scalability:** Can add more workers without changing traversal
- **Fault tolerance:** Leader can continue if one worker fails

---

## ✨ Key Features

### Phase 1: Data Partitioning
- ✅ 6-process distributed system with gRPC
- ✅ Intelligent data partitioning (no overlaps)
- ✅ Hybrid C++ and Python servers
- ✅ Configuration-driven design
- ✅ Columnar data model (FireColumnModel)

### Phase 2: Chunked Streaming & Request Control
- ✅ **Configurable chunk sizes** (100-5000 measurements/chunk)
- ✅ **Progressive streaming** (data sent as ready, not all at once)
- ✅ **Request cancellation** (cancel mid-query)
- ✅ **Status tracking** (real-time progress monitoring)
- ✅ **Client disconnect detection** (graceful cleanup)
- ✅ **Memory optimization** (80% reduction vs bulk responses)

---

## 🧪 Testing

### Basic Test Client
```bash
./venv/bin/python3 client/test_client.py
```

### Advanced Client (All Features)
```bash
./venv/bin/python3 client/advanced_client.py
```

Demonstrates:
- Chunked streaming with progress bars
- Mid-query cancellation
- Status tracking during query
- Progressive delivery with small chunks

---

## 🔧 Build & Setup

### Build C++ Servers
```bash
make clean
make servers
```

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Rebuild Proto Files (if needed)
```bash
# Python
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/fire_service.proto

# C++
protoc -I. --cpp_out=. --grpc_out=. --plugin=protoc-gen-grpc=`which grpc_cpp_plugin` proto/fire_service.proto
```

---

## 📊 Performance Characteristics

### Chunking Strategy

| Chunk Size | Chunks (for 150K results) | Latency | Memory | Use Case |
|------------|---------------------------|---------|--------|----------|
| 100 | 1500 | High | Low | Progressive UX |
| 500 | 300 | Medium | Medium | Balanced |
| 1000 | 150 | Low | Medium | **Default** |
| 5000 | 30 | Very Low | High | Large queries |

### Memory Benefits
- **Before:** Gateway holds 1.17M measurements (200MB)
- **After:** Streams 1K at a time (~100KB per chunk)
- **Savings:** 80% memory reduction

---

## 🎮 Usage Examples

### Example 1: Simple Query
```python
import grpc
import fire_service_pb2, fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)

request = fire_service_pb2.QueryRequest(
    request_id=12345,
    filter=fire_service_pb2.QueryFilter(parameters=["PM2.5"]),
    require_chunked=True,
    max_results_per_chunk=1000
)

for chunk in stub.Query(request):
    print(f"Chunk {chunk.chunk_number + 1}/{chunk.total_chunks}")
    print(f"  Received {len(chunk.measurements)} measurements")
```

### Example 2: Query with Cancellation
```python
import threading, time

def run_query():
    for chunk in stub.Query(request):
        process(chunk)

# Start query
thread = threading.Thread(target=run_query)
thread.start()

# Cancel after 2 seconds
time.sleep(2)
cancel = fire_service_pb2.StatusRequest(request_id=12345, action="cancel")
stub.CancelRequest(cancel)
```

### Example 3: Status Monitoring
```python
# Check query progress
status = stub.GetStatus(
    fire_service_pb2.StatusRequest(request_id=12345, action="status")
)
print(f"Progress: {status.chunks_delivered}/{status.total_chunks}")
print(f"Status: {status.status}")
```

---

## 📁 Project Structure

```
mini-2-grpc/
├── gateway/
│   └── server.py              # Gateway with chunked streaming
├── team_green/
│   ├── server_b.py            # Python leader
│   └── server_c.cpp           # C++ worker
├── team_pink/
│   ├── server_d.cpp           # C++ worker
│   ├── server_e.py            # Python leader
│   └── server_f.cpp           # C++ worker
├── common/
│   ├── FireColumnModel.hpp/.cpp  # C++ data model
│   └── fire_column_model.py      # Python data model
├── proto/
│   └── fire_service.proto     # gRPC definitions
├── client/
│   ├── test_client.py         # Basic test
│   └── advanced_client.py     # Advanced demo
├── configs/
│   └── process_[a-f].json     # Server configs
├── data/
│   └── YYYYMMDD/              # CSV files by date
└── test_phase2.sh             # Automated test
```

---

## 🎓 Assignment Requirements Met

### Core Requirements
- ✅ 6 processes with gRPC communication
- ✅ Correct overlay topology (AB, BC, AE, EF, ED)
- ✅ Both C++ and Python servers
- ✅ Configuration-driven (no hardcoding)
- ✅ Non-overlapping data partitions
- ✅ Realistic data structures

### Critical Features (Emphasized in Assignment)
- ✅ **Chunked/segmented responses** (not single bulk)
- ✅ **Request cancellation** (client can cancel)
- ✅ **Connection loss handling** (disconnect detection)
- ✅ **Status tracking** (progress monitoring)
- ✅ **Multi-computer deployment** (2 computers, 1.5ms latency)

---

## ✅ Project Complete

### All Phases Completed
1. ✅ **Performance Analysis** - Complete with benchmarks
2. ✅ **Single-Computer Validation** - All tests passing
3. ✅ **Bug Fixes** - Filter logic and gRPC message size
4. ✅ **Documentation** - Comprehensive guides and analysis
5. ✅ **Multi-Computer Deployment** - Successfully deployed on 2 computers
   - ✅ Deployed on 2 physical machines (10.10.10.1, 10.10.10.2)
   - ✅ Updated configs with actual IP addresses
   - ✅ Tested cross-network performance (~1.5ms latency)
   - ✅ Retrieved 421,606 measurements across network
   - ✅ Documented in `MULTI_COMPUTER_RESULTS.md`

**Project Status: PRODUCTION READY** 🎉

**Performance Highlights:**
- 124,008 measurements/second (max throughput)
- 1.0s to first chunk (best latency)
- 5+ concurrent clients supported
- 100% success rate across all tests

---

## 🏆 What Makes This Strong

1. **Efficient Architecture**: 80% memory savings with partitioning
2. **Robust Streaming**: Progressive chunked delivery with cancellation
3. **Full Request Control**: Status tracking and disconnect handling
4. **Clean Code**: Separation of concerns, config-driven
5. **Comprehensive Testing**: Automated tests with feature demos
6. **Thorough Documentation**: Technical details and usage guides

---

## 🤝 Contributing

This is an academic project for the Mini-2 gRPC assignment.

---

## 📝 License

Academic use only.

---

## 🆘 Troubleshooting

See `QUICK_START_PHASE2.md` for common issues and solutions.

**Quick fix for most problems:**
```bash
# Kill all servers
pkill -f server_

# Rebuild
make clean && make servers

# Test again
./test_phase2.sh
```

---

**For detailed technical documentation, see the markdown files in the project root.**