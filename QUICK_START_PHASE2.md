# Quick Start: Phase 2 - Chunked Streaming

## Run Full System Test (Automated)

The easiest way to see Phase 2 in action:

```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./test_phase2.sh
```

This script will:
1. Start all 6 servers automatically
2. Run both test clients
3. Show server logs and statistics
4. Clean up on exit

**Press Enter when done to stop all servers.**

---

## Manual Testing (Step-by-Step)

### 1. Start All Servers

Open 6 terminals and run:

**Terminal 1 - Server C:**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./build/server_c configs/process_c.json
```

**Terminal 2 - Server D:**
```bash
./build/server_d configs/process_d.json
```

**Terminal 3 - Server F:**
```bash
./build/server_f configs/process_f.json
```

**Terminal 4 - Server B:**
```bash
./venv/bin/python3 team_green/server_b.py configs/process_b.json
```

**Terminal 5 - Server E:**
```bash
./venv/bin/python3 team_pink/server_e.py configs/process_e.json
```

**Terminal 6 - Gateway A:**
```bash
./venv/bin/python3 gateway/server.py configs/process_a.json
```

Wait for all servers to show "Server started" messages.

### 2. Run Basic Test Client

**Terminal 7:**
```bash
./venv/bin/python3 client/test_client.py
```

Expected output:
```
=== Testing Query RPC ===
  Progress: [██████████████] 100.0% | Chunk 156/156 | Results: 155,847/155,847
✓ Query completed!
```

### 3. Run Advanced Client (Full Demo)

```bash
./venv/bin/python3 client/advanced_client.py
```

This demonstrates:
- Basic chunked streaming (1000 per chunk)
- Request cancellation (cancels after 3 chunks)
- Status tracking (checks progress periodically)
- Small chunks (100 per chunk for progressive streaming)

---

## Quick Tests

### Test 1: Simple Query with Progress
```bash
./venv/bin/python3 client/test_client.py
```

### Test 2: All Phase 2 Features
```bash
./venv/bin/python3 client/advanced_client.py
```

### Test 3: Custom Query (Python REPL)
```python
import grpc
import sys
sys.path.insert(0, 'proto')
import fire_service_pb2, fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)

# Query with custom filters
request = fire_service_pb2.QueryRequest(
    request_id=99999,
    filter=fire_service_pb2.QueryFilter(
        parameters=["PM2.5"],
        min_aqi=50,
        max_aqi=100
    ),
    query_type="filter",
    require_chunked=True,
    max_results_per_chunk=500
)

# Stream results
for chunk in stub.Query(request):
    print(f"Chunk {chunk.chunk_number + 1}: {len(chunk.measurements)} measurements")
```

---

## Verify Features

### ✅ Chunked Streaming
Watch the progress bar fill incrementally as chunks arrive.

### ✅ Cancellation
Advanced client cancels queries mid-stream. Watch for "🛑 Cancelling request..." message.

### ✅ Status Tracking
Advanced client checks status while query runs. See periodic status updates.

### ✅ Progressive Delivery
Small chunks (100 measurements) show data arriving incrementally.

---

## Troubleshooting

### Servers Won't Start
```bash
# Check if ports are in use
lsof -i :50051
lsof -i :50052
# ... etc

# Kill existing processes
pkill -f server_
```

### Client Can't Connect
```bash
# Verify gateway is running
curl -v http://localhost:50051  # Should get "Connection refused" but confirms port is open

# Check gateway logs
grep "Server started" /tmp/server_a.log
```

### No Data Returned
```bash
# Verify workers loaded data
grep "Data model initialized" /tmp/server_*.log

# Should show:
# Server B: 134,004 measurements
# Server C: 243,313 measurements
# Server D: 244,375 measurements
# Server E: 245,339 measurements
# Server F: 300,494 measurements
```

---

## Performance Tips

### Optimal Chunk Sizes

- **100-200**: Best for showing progressive streaming, more overhead
- **500-1000**: Balanced (default)
- **2000-5000**: Best for large queries, fewer chunks

### Test Different Sizes
```python
# Small chunks - more frequent updates
max_results_per_chunk=100

# Medium chunks - balanced
max_results_per_chunk=1000

# Large chunks - fewer updates
max_results_per_chunk=5000
```

---

## What Phase 2 Demonstrates

1. **Chunked Response**: Results split into configurable segments
2. **Progressive Delivery**: Chunks sent as ready (not all at once)
3. **Memory Optimization**: Gateway doesn't hold all results
4. **Request Control**: Cancel queries mid-stream
5. **Status Tracking**: Monitor progress in real-time
6. **Client Disconnect**: Detected and handled gracefully
7. **Multi-Server**: Data aggregated from 5 distributed servers

---

## Next Steps

After Phase 2, you need:

1. **Multi-Machine Deployment** - Run on 2-3 computers
2. **Performance Benchmarks** - Measure latency, throughput
3. **Documentation** - Final project writeup
4. **Demo Preparation** - Show all features working

Current progress: **~70% complete!**

