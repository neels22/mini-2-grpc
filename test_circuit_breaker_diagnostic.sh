#!/bin/bash
# Diagnostic Circuit Breaker Test - Isolated Server C Failure
# This test isolates Server C failure to see if it causes cascading failures

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Circuit Breaker Diagnostic Test"
echo "Testing: Isolated Server C Failure"
echo "========================================="
echo ""

# Clean up any existing servers
pkill -f "server_[a-f].py" 2>/dev/null
sleep 2

# Start all servers
echo "Starting all 6 servers..."
./venv/bin/python3 team_green/server_c.py configs/process_c.json > /tmp/server_c.log 2>&1 &
PID_C=$!
sleep 1

./venv/bin/python3 team_pink/server_d.py configs/process_d.json > /tmp/server_d.log 2>&1 &
PID_D=$!
sleep 1

./venv/bin/python3 team_pink/server_f.py configs/process_f.json > /tmp/server_f.log 2>&1 &
PID_F=$!
sleep 1

./venv/bin/python3 team_green/server_b.py configs/process_b.json > /tmp/server_b.log 2>&1 &
PID_B=$!
sleep 2

./venv/bin/python3 team_pink/server_e.py configs/process_e.json > /tmp/server_e.log 2>&1 &
PID_E=$!
sleep 2

./venv/bin/python3 gateway/server.py configs/process_a.json > /tmp/server_a.log 2>&1 &
PID_A=$!
sleep 3

echo "All servers started"
echo "  Gateway A: PID $PID_A (localhost:50051)"
echo "  Server B:  PID $PID_B (localhost:50052)"
echo "  Server C:  PID $PID_C (localhost:50053)"
echo "  Server D:  PID $PID_D (localhost:50054)"
echo "  Server E:  PID $PID_E (localhost:50055)"
echo "  Server F:  PID $PID_F (localhost:50056)"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping all servers..."
    kill $PID_A $PID_B $PID_C $PID_D $PID_E $PID_F 2>/dev/null
    wait 2>/dev/null
    echo "Done"
}
trap cleanup EXIT INT TERM

# Wait for initialization
echo "Waiting for servers to initialize..."
sleep 5

echo "========================================="
echo "BASELINE: Normal Operation"
echo "========================================="
echo "Running baseline query (all servers healthy)..."
python3 -c "
import grpc
import sys
import os
import time
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)

query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=0, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)

start = time.time()
total = 0
for chunk in stub.Query(request):
    total += len(chunk.measurements)
elapsed = time.time() - start

print(f'  ✅ Received {total:,} measurements in {elapsed:.2f}s')
channel.close()
"
echo ""

echo "Checking circuit breaker states (should all be CLOSED):"
echo "  Gateway A circuits:"
grep -E "Circuit breaker.*initialized|State transition" /tmp/server_a.log | tail -3
echo "  Team Leader B circuits:"
grep -E "Circuit breaker.*initialized|State transition" /tmp/server_b.log | tail -3
echo "  Team Leader E circuits:"
grep -E "Circuit breaker.*initialized|State transition" /tmp/server_e.log | tail -3
echo ""

echo "========================================="
echo "TEST: Kill Server C Only"
echo "========================================="
echo "Killing Server C (PID $PID_C)..."
kill $PID_C
sleep 2

echo ""
echo "Running 3 queries to trigger B→C circuit breaker..."
for i in {1..3}; do
    echo ""
    echo "  Query $i/3..."
    python3 -c "
import grpc
import sys
import os
import time
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=$i, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)
try:
    start = time.time()
    total = 0
    for chunk in stub.Query(request):
        total += len(chunk.measurements)
    elapsed = time.time() - start
    print(f'    ✅ Received {total:,} measurements in {elapsed:.2f}s')
except Exception as e:
    print(f'    ❌ Error: {e}')
channel.close()
" 2>&1
    sleep 2
done

echo ""
echo "========================================="
echo "DIAGNOSTIC: Checking Circuit Breaker States"
echo "========================================="
echo ""
echo "Gateway A → B circuit:"
grep -E "Circuit breaker.*B|State transition.*B|Error contacting B|TIMEOUT.*B" /tmp/server_a.log | tail -5
echo ""
echo "Gateway A → E circuit:"
grep -E "Circuit breaker.*E|State transition.*E|Error contacting E|TIMEOUT.*E" /tmp/server_a.log | tail -5
echo ""
echo "Team Leader B → C circuit:"
grep -E "Circuit breaker.*C|State transition.*C|Error contacting C" /tmp/server_b.log | tail -5
echo ""
echo "Team Leader E → D circuit:"
grep -E "Circuit breaker.*D|State transition.*D|Error contacting D|TIMEOUT.*D" /tmp/server_e.log | tail -5
echo ""
echo "Team Leader E → F circuit:"
grep -E "Circuit breaker.*F|State transition.*F|Error contacting F|TIMEOUT.*F" /tmp/server_e.log | tail -5
echo ""

echo "========================================="
echo "DIAGNOSTIC: E's Response Times"
echo "========================================="
echo "Checking how long E takes to respond:"
grep -E "Internal query from|took.*s|Aggregated.*measurements" /tmp/server_e.log | tail -10
echo ""

echo "========================================="
echo "DIAGNOSTIC: Gateway A's Call Times"
echo "========================================="
echo "Checking Gateway A's call durations:"
grep -E "Received.*measurements from.*in.*s|TIMEOUT|Error contacting" /tmp/server_a.log | tail -10
echo ""

echo "========================================="
echo "Summary"
echo "========================================="
echo ""
echo "Expected behavior:"
echo "  - B→C circuit should OPEN (Server C is down)"
echo "  - A→B circuit should stay CLOSED (B still responds with local data)"
echo "  - A→E circuit should stay CLOSED (E is not connected to C)"
echo "  - E→D and E→F circuits should stay CLOSED (D and F are healthy)"
echo ""
echo "If A→E circuit opened, check:"
echo "  1. Did E's calls to D or F timeout?"
echo "  2. Did Gateway A's call to E timeout?"
echo "  3. Check E's response times in the logs above"
echo ""
echo "Log files are in /tmp/server_*.log"
echo ""

