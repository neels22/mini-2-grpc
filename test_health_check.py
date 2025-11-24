#!/usr/bin/env python3
"""
Manual test for health check functionality
"""

import grpc
import sys
import os

# Add proto to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))

import fire_service_pb2
import fire_service_pb2_grpc


def test_health_check(server_address: str, server_name: str):
    """Test health check for a server"""
    try:
        channel = grpc.insecure_channel(server_address)
        stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
        
        request = fire_service_pb2.HealthRequest(
            requester_id="test_client",
            timestamp=0
        )
        
        response = stub.HealthCheck(request, timeout=5.0)
        
        print(f"✓ {server_name} ({server_address}):")
        print(f"  Process ID: {response.process_id}")
        print(f"  Status: {response.status}")
        print(f"  Healthy: {response.healthy}")
        print(f"  Timestamp: {response.timestamp}")
        
        channel.close()
        return True
        
    except grpc.RpcError as e:
        print(f"✗ {server_name} ({server_address}): {e.code()}: {e.details()}")
        return False
    except Exception as e:
        print(f"✗ {server_name} ({server_address}): {e}")
        return False


def main():
    print("=" * 50)
    print("Health Check Test")
    print("=" * 50)
    print()
    
    servers = [
        ("localhost:50051", "Gateway A"),
        ("localhost:50052", "Team Leader B"),
        ("localhost:50053", "Worker C"),
        ("localhost:50054", "Worker D"),
        ("localhost:50055", "Team Leader E"),
        ("localhost:50056", "Worker F"),
    ]
    
    results = []
    for address, name in servers:
        results.append(test_health_check(address, name))
        print()
    
    print("=" * 50)
    print(f"Results: {sum(results)}/{len(servers)} servers healthy")
    print("=" * 50)


if __name__ == '__main__':
    main()

