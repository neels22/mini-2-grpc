#!/usr/bin/env python3
"""Quick circuit breaker test using venv"""

import grpc
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))
import fire_service_pb2
import fire_service_pb2_grpc


def run_query(stub, query_id):
    """Run a query and return result count"""
    query_filter = fire_service_pb2.QueryFilter(
        parameters=["PM2.5"],
        min_aqi=0,
        max_aqi=100
    )
    request = fire_service_pb2.QueryRequest(
        request_id=query_id,
        filter=query_filter,
        query_type="filter",
        require_chunked=True,
        max_results_per_chunk=1000
    )
    try:
        total = 0
        for chunk in stub.Query(request):
            total += len(chunk.measurements)
        return total, True
    except Exception as e:
        return 0, False


def main():
    print("=" * 60)
    print("Circuit Breaker Quick Test")
    print("=" * 60)
    print()
    
    channel = grpc.insecure_channel('localhost:50051')
    stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
    
    print("TEST 1: Normal operation")
    total, success = run_query(stub, 1)
    if success:
        print(f"  ✓ Received {total:,} measurements")
    else:
        print(f"  ✗ Query failed")
    print()
    
    print("TEST 2: After killing Server C, run 3 queries")
    print("  (This will trigger circuit breaker to open)")
    input("  Press Enter after killing Server C...")
    
    for i in range(2, 5):
        total, success = run_query(stub, i)
        print(f"  Query {i}: {total:,} measurements")
        time.sleep(2)
    print()
    
    print("TEST 3: Fail-fast (circuit should be OPEN)")
    start = time.time()
    total, success = run_query(stub, 5)
    elapsed = time.time() - start
    print(f"  ✓ Query completed in {elapsed:.2f}s with {total:,} measurements (partial)")
    print()
    
    print("TEST 4: Recovery (restart Server C, wait 35s)")
    input("  Press Enter after restarting Server C and waiting 35s...")
    total, success = run_query(stub, 6)
    if success:
        print(f"  ✓ Received {total:,} measurements (should be full results)")
    print()
    
    channel.close()
    print("=" * 60)
    print("Test complete! Check server logs for circuit breaker activity.")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(0)

