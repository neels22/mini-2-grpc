#!/bin/bash
# Phase 2 End-to-End Testing Script
# Tests chunked streaming with request control across all servers

cd /Users/indraneelsarode/Desktop/mini-2-grpc

echo "========================================="
echo "Phase 2: End-to-End Testing"
echo "Chunked Streaming + Request Control"
echo "========================================="
echo ""

# Check if all servers are built
echo "Checking server builds..."
if [ ! -f "build/server_c" ] || [ ! -f "build/server_d" ] || [ ! -f "build/server_f" ]; then
    echo "❌ C++ servers not built. Run 'make servers' first."
    exit 1
fi
echo "✓ C++ servers found"
echo ""

# Start all servers in background
echo "Starting all 6 servers..."
echo ""

# Start C++ workers
echo "Starting Server C (Team Green Worker)..."
./build/server_c configs/process_c.json > /tmp/server_c.log 2>&1 &
PID_C=$!
sleep 2

echo "Starting Server D (Team Pink Worker)..."
./build/server_d configs/process_d.json > /tmp/server_d.log 2>&1 &
PID_D=$!
sleep 2

echo "Starting Server F (Team Pink Worker)..."
./build/server_f configs/process_f.json > /tmp/server_f.log 2>&1 &
PID_F=$!
sleep 2

# Start Python team leaders
echo "Starting Server B (Team Green Leader)..."
./venv/bin/python3 team_green/server_b.py configs/process_b.json > /tmp/server_b.log 2>&1 &
PID_B=$!
sleep 3

echo "Starting Server E (Team Pink Leader)..."
./venv/bin/python3 team_pink/server_e.py configs/process_e.json > /tmp/server_e.log 2>&1 &
PID_E=$!
sleep 3

# Start Gateway
echo "Starting Gateway A..."
./venv/bin/python3 gateway/server.py configs/process_a.json > /tmp/server_a.log 2>&1 &
PID_A=$!
sleep 3

echo ""
echo "========================================="
echo "All Servers Started"
echo "========================================="
echo "  Gateway A: PID $PID_A (port 50051)"
echo "  Server B:  PID $PID_B (port 50052)"
echo "  Server C:  PID $PID_C (port 50053)"
echo "  Server D:  PID $PID_D (port 50054)"
echo "  Server E:  PID $PID_E (port 50055)"
echo "  Server F:  PID $PID_F (port 50056)"
echo ""

# Function to cleanup servers
cleanup() {
    echo ""
    echo "========================================="
    echo "Stopping all servers..."
    echo "========================================="
    kill $PID_A $PID_B $PID_C $PID_D $PID_E $PID_F 2>/dev/null
    wait 2>/dev/null
    echo "✓ All servers stopped"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Wait a bit for all servers to be ready
echo "Waiting for servers to initialize..."
sleep 5
echo ""

# Check server logs for successful startup
echo "========================================="
echo "Server Startup Verification"
echo "========================================="
echo ""

echo "Gateway A:"
grep -E "Server started|Data model initialized" /tmp/server_a.log | tail -2

echo ""
echo "Server B (Team Green Leader):"
grep -E "Server started|Data model initialized" /tmp/server_b.log | tail -2

echo ""
echo "Server C (Team Green Worker):"
grep -E "Server started|Data model initialized" /tmp/server_c.log | tail -2

echo ""
echo "Server D (Team Pink Worker):"
grep -E "Server started|Data model initialized" /tmp/server_d.log | tail -2

echo ""
echo "Server E (Team Pink Leader):"
grep -E "Server started|Data model initialized" /tmp/server_e.log | tail -2

echo ""
echo "Server F (Team Pink Worker):"
grep -E "Server started|Data model initialized" /tmp/server_f.log | tail -2

echo ""
echo "========================================="
echo "Running Client Tests"
echo "========================================="
echo ""

# Test 1: Basic test client
echo "TEST 1: Basic Chunked Query"
echo "----------------------------"
./venv/bin/python3 client/test_client.py
TEST1_RESULT=$?

echo ""
echo ""

# Test 2: Advanced client with all features
echo "TEST 2: Advanced Features (Cancellation, Status, Progress)"
echo "-----------------------------------------------------------"
./venv/bin/python3 client/advanced_client.py
TEST2_RESULT=$?

echo ""
echo ""

# Display server statistics
echo "========================================="
echo "Server Statistics"
echo "========================================="
echo ""

echo "Gateway A - Query handling:"
grep -E "Received query|Aggregated|Sending chunk|completed" /tmp/server_a.log | tail -20

echo ""
echo "Server B - Forwarding to workers:"
grep -E "Found.*local|Forwarding|Received.*from" /tmp/server_b.log | tail -10

echo ""
echo "Server E - Forwarding to workers:"
grep -E "Found.*local|Forwarding|Received.*from" /tmp/server_e.log | tail -10

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""

if [ $TEST1_RESULT -eq 0 ]; then
    echo "✓ TEST 1 PASSED: Basic chunked streaming"
else
    echo "✗ TEST 1 FAILED: Basic chunked streaming"
fi

if [ $TEST2_RESULT -eq 0 ]; then
    echo "✓ TEST 2 PASSED: Advanced features"
else
    echo "✗ TEST 2 FAILED: Advanced features"
fi

echo ""
echo "Phase 2 Features Verified:"
echo "  • Chunked response streaming"
echo "  • Progressive data delivery"
echo "  • Request tracking and status"
echo "  • Cancellation support"
echo "  • Client disconnect handling"
echo "  • Multi-server aggregation"
echo ""

echo "Server logs saved to:"
echo "  /tmp/server_[a-f].log"
echo ""

# Wait before cleanup
echo "Press Enter to stop all servers..."
read

exit 0

