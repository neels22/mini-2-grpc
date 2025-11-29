#!/bin/bash
# Full Circuit Breaker Test with localhost client

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Circuit Breaker Full Test"
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
echo "TEST 1: Normal Operation"
echo "========================================="
echo "Checking circuit breaker initialization..."
echo ""
echo "Gateway A:"
grep -i "circuit breakers initialized" /tmp/server_a.log
echo ""
echo "Team Leader B:"
grep -i "circuit breakers initialized" /tmp/server_b.log
echo ""
echo "Team Leader E:"
grep -i "circuit breakers initialized" /tmp/server_e.log
echo ""

echo "Running test query..."
python3 -c "
import grpc
import sys
import os
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)

query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=1, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)

total = 0
for chunk in stub.Query(request):
    total += len(chunk.measurements)
print(f'  Received {total:,} measurements')
channel.close()
"
echo ""

echo "========================================="
echo "TEST 2: Failure Detection"
echo "========================================="
echo "Killing Server C..."
kill $PID_C
sleep 2

echo "Running 3 queries to trigger circuit breaker..."
for i in {1..3}; do
    echo "  Query $i/3..."
    python3 -c "
import grpc
import sys
import os
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=$i, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)
try:
    total = 0
    for chunk in stub.Query(request):
        total += len(chunk.measurements)
    print(f'    Received {total:,} measurements')
except Exception as e:
    print(f'    Error: {e}')
channel.close()
" 2>&1
    sleep 2
done

echo ""
echo "Checking circuit breaker state transitions in Team Leader B:"
grep -E "State transition|Circuit breaker.*OPEN" /tmp/server_b.log | tail -10
echo ""

echo "========================================="
echo "TEST 3: Fail-Fast Behavior"
echo "========================================="
echo "Running query with Server C still down (circuit should be OPEN)..."
START_TIME=$(date +%s)
python3 -c "
import grpc
import sys
import os
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=4, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)
try:
    total = 0
    for chunk in stub.Query(request):
        total += len(chunk.measurements)
    print(f'  Received {total:,} measurements (partial results)')
except Exception as e:
    print(f'  Error: {e}')
channel.close()
" 2>&1
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "  Query completed in ${ELAPSED} seconds (should be fast due to fail-fast)"
echo ""

echo "Checking fail-fast messages:"
grep -E "Circuit breaker OPEN|fail-fast|skipping call" /tmp/server_b.log | tail -5
echo ""

echo "========================================="
echo "TEST 4: Recovery Detection"
echo "========================================="
echo "Restarting Server C..."
./venv/bin/python3 team_green/server_c.py configs/process_c.json > /tmp/server_c.log 2>&1 &
PID_C=$!
sleep 3

echo "Waiting 35 seconds for circuit breaker timeout (30s) + probe..."
for i in {35..1}; do
    echo -ne "\r  Waiting... $i seconds remaining"
    sleep 1
done
echo ""

echo "Running query to test recovery..."
python3 -c "
import grpc
import sys
import os
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=5, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)
try:
    total = 0
    for chunk in stub.Query(request):
        total += len(chunk.measurements)
    print(f'  Received {total:,} measurements (full results after recovery)')
except Exception as e:
    print(f'  Error: {e}')
channel.close()
" 2>&1
echo ""

echo "Checking recovery state transitions:"
grep -E "State transition.*half_open|State transition.*closed" /tmp/server_b.log | tail -5
echo ""

echo "========================================="
echo "TEST 5: Partial Results"
echo "========================================="
echo "Killing Server F..."
kill $PID_F
sleep 2

echo "Running 3 queries to open circuit for F..."
for i in {1..3}; do
    python3 -c "
import grpc
import sys
import os
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=$((6+i)), filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)
try:
    total = 0
    for chunk in stub.Query(request):
        total += len(chunk.measurements)
except:
    pass
channel.close()
" > /dev/null 2>&1
    sleep 2
done

echo "Running query - should return partial results..."
python3 -c "
import grpc
import sys
import os
sys.path.insert(0, 'proto')
import fire_service_pb2
import fire_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
query_filter = fire_service_pb2.QueryFilter(parameters=['PM2.5'], min_aqi=0, max_aqi=100)
request = fire_service_pb2.QueryRequest(request_id=10, filter=query_filter, query_type='filter', require_chunked=True, max_results_per_chunk=1000)
try:
    total = 0
    for chunk in stub.Query(request):
        total += len(chunk.measurements)
    print(f'  Received {total:,} measurements (partial - missing F)')
except Exception as e:
    print(f'  Error: {e}')
channel.close()
" 2>&1
echo ""

echo "Checking Team Leader E logs (should skip F):"
grep -E "Circuit breaker OPEN.*F|skipping.*F" /tmp/server_e.log | tail -3
echo ""

echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Circuit breaker activity:"
echo "  Gateway A circuit breaker messages:"
grep -c "Circuit breaker\|State transition" /tmp/server_a.log 2>/dev/null || echo "    0"
echo "  Team Leader B circuit breaker messages:"
grep -c "Circuit breaker\|State transition" /tmp/server_b.log 2>/dev/null || echo "    0"
echo "  Team Leader E circuit breaker messages:"
grep -c "Circuit breaker\|State transition" /tmp/server_e.log 2>/dev/null || echo "    0"
echo ""
echo "All tests completed!"
echo ""

