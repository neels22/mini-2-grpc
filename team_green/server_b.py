#!/usr/bin/env python3
"""
Process B - Team Green Leader Server
Coordinates Team Green workers (C and D)
"""

import json
import grpc
from concurrent import futures
import sys
import os

# Add proto directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))

import fire_service_pb2
import fire_service_pb2_grpc


class FireQueryServiceImpl(fire_service_pb2_grpc.FireQueryServiceServicer):
    """Implementation of FireQueryService for Process B (Team Green Leader)"""
    
    def __init__(self, config):
        self.config = config
        self.process_id = config['identity']
        self.role = config['role']
        self.team = config['team']
        self.neighbors = config['neighbors']
        print(f"[{self.process_id}] Initialized as {self.role} for Team {self.team}")
        print(f"[{self.process_id}] Neighbors: {[n['process_id'] for n in self.neighbors]}")
        
        # TODO: Initialize FireColumnModel for Team Green data
    
    def Query(self, request, context):
        """
        Handle client query request (if called directly)
        Team leaders typically receive InternalQuery instead
        """
        print(f"[{self.process_id}] Received direct query request_id={request.request_id}")
        
        # Team leaders don't typically receive direct client queries
        # but can act as workers too
        chunk = fire_service_pb2.QueryResponseChunk(
            request_id=request.request_id,
            chunk_number=0,
            is_last_chunk=True,
            total_chunks=1,
            total_results=0
        )
        yield chunk
    
    def InternalQuery(self, request, context):
        """
        Handle internal queries from other processes (mainly from A)
        This is the main method for team leaders
        """
        print(f"[{self.process_id}] Internal query from {request.requesting_process}")
        print(f"  Request ID: {request.request_id}")
        print(f"  Original request: {request.original_request_id}")
        print(f"  Query type: {request.query_type}")
        
        # TODO: Query local FireColumnModel data (B can also act as worker)
        
        # Forward query to workers C and D
        all_measurements = self.forward_to_workers(request)
        
        print(f"[{self.process_id}] Aggregated {len(all_measurements)} measurements from workers")
        
        # Return response with aggregated results
        response = fire_service_pb2.InternalQueryResponse(
            request_id=request.request_id,
            original_request_id=request.original_request_id,
            is_complete=True,
            responding_process=self.process_id
        )
        response.measurements.extend(all_measurements)
        
        print(f"[{self.process_id}] Returning response with {len(response.measurements)} measurements")
        return response
    
    def forward_to_workers(self, request):
        """
        Forward query to worker processes (C and D)
        Returns aggregated results from all workers
        """
        all_measurements = []
        
        for neighbor in self.neighbors:
            neighbor_id = neighbor['process_id']
            neighbor_address = f"{neighbor['hostname']}:{neighbor['port']}"
            
            print(f"[{self.process_id}] Forwarding query to {neighbor_id} at {neighbor_address}")
            
            try:
                # Create channel to neighbor
                channel = grpc.insecure_channel(neighbor_address)
                stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
                
                # Forward the query
                response = stub.InternalQuery(request)
                
                # Collect measurements
                all_measurements.extend(response.measurements)
                print(f"[{self.process_id}] Received {len(response.measurements)} measurements from {neighbor_id}")
                
                channel.close()
                
            except grpc.RpcError as e:
                print(f"[{self.process_id}] Error contacting {neighbor_id}: {e.code()}")
        
        return all_measurements
    
    def CancelRequest(self, request, context):
        """Handle request cancellation"""
        print(f"[{self.process_id}] Cancel request_id={request.request_id}")
        
        # TODO: Cancel ongoing query and notify workers
        
        return fire_service_pb2.StatusResponse(
            request_id=request.request_id,
            status="cancelled",
            chunks_delivered=0,
            total_chunks=0
        )
    
    def GetStatus(self, request, context):
        """Handle status check"""
        print(f"[{self.process_id}] Status request_id={request.request_id}")
        
        return fire_service_pb2.StatusResponse(
            request_id=request.request_id,
            status="pending",
            chunks_delivered=0,
            total_chunks=0
        )
    
    def Notify(self, request, context):
        """Handle notifications from other processes"""
        print(f"[{self.process_id}] Notification from {request.requesting_process}")
        
        return fire_service_pb2.StatusResponse(
            request_id=request.request_id,
            status="acknowledged"
        )


def load_config(config_path):
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)


def serve(config_path):
    """Start the gRPC server"""
    # Load configuration
    config = load_config(config_path)
    process_id = config['identity']
    hostname = config['hostname']
    port = config['port']
    
    # Create server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add service implementation
    service_impl = FireQueryServiceImpl(config)
    fire_service_pb2_grpc.add_FireQueryServiceServicer_to_server(service_impl, server)
    
    # Bind to address
    server_address = f"{hostname}:{port}"
    server.add_insecure_port(server_address)
    
    # Start server
    server.start()
    print(f"[{process_id}] Server started on {server_address}")
    print(f"[{process_id}] Press Ctrl+C to stop")
    
    # Keep server running
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print(f"\n[{process_id}] Shutting down...")
        server.stop(0)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python server_b.py <config_file>")
        print("Example: python server_b.py ../configs/process_b.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    serve(config_path)

