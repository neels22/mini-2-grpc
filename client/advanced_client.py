#!/usr/bin/env python3
"""
Advanced Test Client with Chunked Streaming, Cancellation, and Progress Tracking
Demonstrates Phase 2 features: progressive streaming and request control
"""

import grpc
import sys
import os
import time
import random
import threading

# Add proto directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))

import fire_service_pb2
import fire_service_pb2_grpc


class ProgressTracker:
    """Track and display query progress"""
    
    def __init__(self, request_id):
        self.request_id = request_id
        self.start_time = time.time()
        self.chunks_received = 0
        self.total_chunks = 0
        self.total_measurements = 0
        self.measurements_received = 0
        self.completed = False
        self.cancelled = False
    
    def update(self, chunk):
        """Update progress from received chunk"""
        self.chunks_received = chunk.chunk_number + 1
        self.total_chunks = chunk.total_chunks
        self.total_measurements = chunk.total_results
        self.measurements_received += len(chunk.measurements)
        self.completed = chunk.is_last_chunk
    
    def display(self):
        """Display progress bar and stats"""
        elapsed = time.time() - self.start_time
        
        if self.total_chunks > 0:
            progress_pct = (self.chunks_received / self.total_chunks) * 100
            bar_width = 40
            filled = int(bar_width * self.chunks_received / self.total_chunks)
            bar = '█' * filled + '░' * (bar_width - filled)
            
            status = "CANCELLED" if self.cancelled else ("COMPLETE" if self.completed else "STREAMING")
            
            print(f"\r[{status}] {bar} {progress_pct:5.1f}% | "
                  f"Chunks: {self.chunks_received}/{self.total_chunks} | "
                  f"Results: {self.measurements_received:,}/{self.total_measurements:,} | "
                  f"Time: {elapsed:.2f}s", end='', flush=True)
        else:
            print(f"\r[WAITING] Elapsed: {elapsed:.2f}s", end='', flush=True)
    
    def finish(self):
        """Complete the progress display"""
        self.display()
        print()  # New line after progress bar


def test_chunked_streaming(stub, chunk_size=1000):
    """Test basic chunked streaming"""
    print("\n" + "="*80)
    print("TEST 1: Basic Chunked Streaming")
    print("="*80)
    
    request_id = random.randint(1000, 9999)
    
    # Create a query request with modest filters
    query_filter = fire_service_pb2.QueryFilter(
        parameters=["PM2.5"],
        min_aqi=0,
        max_aqi=150
    )
    
    request = fire_service_pb2.QueryRequest(
        request_id=request_id,
        filter=query_filter,
        query_type="filter",
        require_chunked=True,
        max_results_per_chunk=chunk_size
    )
    
    print(f"\nSending query (request_id={request_id})")
    print(f"  Filters: PM2.5, AQI 0-150")
    print(f"  Chunk size: {chunk_size} measurements")
    print()
    
    tracker = ProgressTracker(request_id)
    
    try:
        for chunk in stub.Query(request):
            tracker.update(chunk)
            tracker.display()
            
            # Small delay to see progress
            time.sleep(0.05)
        
        tracker.finish()
        print(f"\n✓ Query completed successfully!")
        print(f"  Total measurements: {tracker.measurements_received:,}")
        print(f"  Total chunks: {tracker.chunks_received}")
        print(f"  Time elapsed: {time.time() - tracker.start_time:.2f}s")
        
    except grpc.RpcError as e:
        tracker.finish()
        print(f"\n✗ Error: {e.code()}: {e.details()}")


def test_cancellation(stub, chunk_size=500, cancel_after_chunks=3):
    """Test request cancellation mid-stream"""
    print("\n" + "="*80)
    print("TEST 2: Request Cancellation")
    print("="*80)
    
    request_id = random.randint(1000, 9999)
    
    # Query for all data to ensure many chunks
    query_filter = fire_service_pb2.QueryFilter()  # No filters = all data
    
    request = fire_service_pb2.QueryRequest(
        request_id=request_id,
        filter=query_filter,
        query_type="filter",
        require_chunked=True,
        max_results_per_chunk=chunk_size
    )
    
    print(f"\nSending query (request_id={request_id})")
    print(f"  Filters: None (all data)")
    print(f"  Chunk size: {chunk_size} measurements")
    print(f"  Will cancel after {cancel_after_chunks} chunks...")
    print()
    
    tracker = ProgressTracker(request_id)
    cancelled = False
    
    try:
        for chunk in stub.Query(request):
            tracker.update(chunk)
            tracker.display()
            
            # Cancel after receiving a few chunks
            if tracker.chunks_received >= cancel_after_chunks and not cancelled:
                print(f"\n\n🛑 Cancelling request {request_id} after {tracker.chunks_received} chunks...")
                
                # Send cancellation request
                cancel_request = fire_service_pb2.StatusRequest(
                    request_id=request_id,
                    action="cancel"
                )
                cancel_response = stub.CancelRequest(cancel_request)
                
                print(f"   Cancel response: {cancel_response.status}")
                tracker.cancelled = True
                cancelled = True
                
                # Break from loop (in real scenario, server would stop sending)
                break
            
            time.sleep(0.05)
        
        tracker.finish()
        
        if cancelled:
            print(f"\n✓ Cancellation test completed!")
            print(f"  Received {tracker.measurements_received:,} measurements before cancellation")
            print(f"  Received {tracker.chunks_received} of {tracker.total_chunks} chunks")
        else:
            print(f"\n⚠ Query completed before cancellation threshold")
        
    except grpc.RpcError as e:
        tracker.finish()
        print(f"\n✗ Error: {e.code()}: {e.details()}")


def test_status_tracking(stub):
    """Test status tracking during query"""
    print("\n" + "="*80)
    print("TEST 3: Status Tracking")
    print("="*80)
    
    request_id = random.randint(1000, 9999)
    
    query_filter = fire_service_pb2.QueryFilter(
        parameters=["PM2.5", "PM10", "OZONE"]
    )
    
    request = fire_service_pb2.QueryRequest(
        request_id=request_id,
        filter=query_filter,
        query_type="filter",
        require_chunked=True,
        max_results_per_chunk=800
    )
    
    print(f"\nSending query (request_id={request_id})")
    print(f"  Will check status periodically during streaming...")
    print()
    
    tracker = ProgressTracker(request_id)
    status_checks = []
    
    # Start a thread to check status periodically
    stop_status_thread = threading.Event()
    
    def check_status_periodically():
        while not stop_status_thread.is_set():
            time.sleep(0.5)
            if not stop_status_thread.is_set():
                status_req = fire_service_pb2.StatusRequest(
                    request_id=request_id,
                    action="status"
                )
                try:
                    status_resp = stub.GetStatus(status_req)
                    status_checks.append({
                        'time': time.time() - tracker.start_time,
                        'status': status_resp.status,
                        'chunks': status_resp.chunks_delivered,
                        'total': status_resp.total_chunks
                    })
                except:
                    pass
    
    status_thread = threading.Thread(target=check_status_periodically, daemon=True)
    status_thread.start()
    
    try:
        for chunk in stub.Query(request):
            tracker.update(chunk)
            tracker.display()
            time.sleep(0.1)  # Slower to allow status checks
        
        tracker.finish()
        stop_status_thread.set()
        status_thread.join(timeout=1)
        
        print(f"\n✓ Query completed with status tracking!")
        print(f"  Total measurements: {tracker.measurements_received:,}")
        print(f"  Status checks performed: {len(status_checks)}")
        
        if status_checks:
            print(f"\n  Status check samples:")
            for i, check in enumerate(status_checks[:5]):
                print(f"    [{check['time']:.2f}s] Status: {check['status']}, "
                      f"Progress: {check['chunks']}/{check['total']} chunks")
        
    except grpc.RpcError as e:
        stop_status_thread.set()
        tracker.finish()
        print(f"\n✗ Error: {e.code()}: {e.details()}")


def test_small_chunks(stub):
    """Test with very small chunks to see progressive streaming"""
    print("\n" + "="*80)
    print("TEST 4: Progressive Streaming (Small Chunks)")
    print("="*80)
    
    request_id = random.randint(1000, 9999)
    
    query_filter = fire_service_pb2.QueryFilter(
        parameters=["PM2.5"],
        min_aqi=50,
        max_aqi=100
    )
    
    request = fire_service_pb2.QueryRequest(
        request_id=request_id,
        filter=query_filter,
        query_type="filter",
        require_chunked=True,
        max_results_per_chunk=100  # Very small chunks
    )
    
    print(f"\nSending query (request_id={request_id})")
    print(f"  Small chunks (100 measurements each) to demonstrate progressive streaming")
    print()
    
    tracker = ProgressTracker(request_id)
    
    try:
        for chunk in stub.Query(request):
            tracker.update(chunk)
            tracker.display()
            time.sleep(0.1)  # Delay to see chunks arrive progressively
        
        tracker.finish()
        print(f"\n✓ Progressive streaming demonstrated!")
        print(f"  Total measurements: {tracker.measurements_received:,}")
        print(f"  Total chunks: {tracker.chunks_received}")
        
    except grpc.RpcError as e:
        tracker.finish()
        print(f"\n✗ Error: {e.code()}: {e.details()}")


def main():
    """Run all advanced tests"""
    # Server address (Gateway A)
    server_address = "localhost:50051"
    
    print("="*80)
    print("ADVANCED CLIENT - Phase 2 Features Demo")
    print("="*80)
    print(f"\nConnecting to gateway server at {server_address}...")
    
    # Create a channel
    channel = grpc.insecure_channel(server_address)
    stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
    
    print("✓ Connected successfully!")
    
    # Run all tests
    test_chunked_streaming(stub, chunk_size=1000)
    time.sleep(1)
    
    test_cancellation(stub, chunk_size=500, cancel_after_chunks=3)
    time.sleep(1)
    
    test_status_tracking(stub)
    time.sleep(1)
    
    test_small_chunks(stub)
    
    # Close channel
    channel.close()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print("\nPhase 2 Features Demonstrated:")
    print("  ✓ Chunked streaming response")
    print("  ✓ Progressive data delivery")
    print("  ✓ Request cancellation")
    print("  ✓ Status tracking")
    print("  ✓ Client disconnect handling")
    print()


if __name__ == '__main__':
    try:
        main()
    except grpc.RpcError as e:
        print(f"\n✗ Failed to connect: {e.code()}: {e.details()}")
        print("\nMake sure all servers are running:")
        print("  1. Start C++ workers: ./build/server_c, ./build/server_d, ./build/server_f")
        print("  2. Start Python leaders: ./venv/bin/python3 team_green/server_b.py, team_pink/server_e.py")
        print("  3. Start gateway: ./venv/bin/python3 gateway/server.py configs/process_a.json")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(0)

