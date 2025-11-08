#!/bin/bash
# Test script to verify the network overlay is working
# This script assumes all 6 servers are running

echo "Testing mini-2-grpc Network Overlay"
echo "===================================="
echo ""
echo "Make sure all 6 servers are running:"
echo "  Terminal 1: cd gateway && python server.py ../configs/process_a.json"
echo "  Terminal 2: cd team_green && python server_b.py ../configs/process_b.json"
echo "  Terminal 3: cd team_green && python server_c.py ../configs/process_c.json"
echo "  Terminal 4: cd team_pink && python server_d.py ../configs/process_d.json"
echo "  Terminal 5: cd team_pink && python server_e.py ../configs/process_e.json"
echo "  Terminal 6: cd team_pink && python server_f.py ../configs/process_f.json"
echo ""
echo "Press Enter to run the test client..."
read

cd "$(dirname "$0")/.." || exit
source venv/bin/activate
cd client || exit
python test_client.py

