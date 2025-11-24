#!/bin/bash
# Test health monitoring with server failures

cd /Users/indraneelsarode/Downloads/mini-2-grpc/mini-2-grpc

echo "========================================="
echo "Health Monitoring Test"
echo "========================================="
echo ""

# Start all servers
echo "Starting all servers..."

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

# Wait for health checks to run
echo "Waiting 10 seconds for health checks to run..."
sleep 10

# Check logs for health check messages
echo ""
echo "========================================="
echo "Health Check Logs"
echo "========================================="
echo ""

echo "Gateway A health checks:"
grep -i "health" /tmp/server_a.log | tail -10

echo ""
echo "Team Leader B health checks:"
grep -i "health" /tmp/server_b.log | tail -10

echo ""
echo "Team Leader E health checks:"
grep -i "health" /tmp/server_e.log | tail -10

echo ""
echo "========================================="
echo "Test: Kill worker C and observe health monitoring"
echo "========================================="
echo ""

echo "Killing worker C..."
kill $PID_C
sleep 8  # Wait for health checks to detect failure

echo ""
echo "Gateway A logs (should show C as unavailable):"
grep -i "health\|unavailable\|degraded" /tmp/server_a.log | tail -5

echo ""
echo "Team Leader B logs (should show C as unavailable):"
grep -i "health\|unavailable\|degraded" /tmp/server_b.log | tail -5

echo ""
echo "========================================="
echo "Test: Restart worker C and observe recovery"
echo "========================================="
echo ""

echo "Restarting worker C..."
./venv/bin/python3 team_green/server_c.py configs/process_c.json > /tmp/server_c.log 2>&1 &
PID_C=$!
sleep 8  # Wait for health checks to detect recovery

echo ""
echo "Team Leader B logs (should show C as healthy):"
grep -i "health\|healthy" /tmp/server_b.log | tail -5

echo ""
echo "========================================="
echo "Test Complete"
echo "========================================="
echo ""
echo "Check logs in /tmp/server_*.log for detailed health monitoring output"

