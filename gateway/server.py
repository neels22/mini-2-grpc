#!/usr/bin/env python3
"""
Process A - Gateway Server
Entry point for client queries, coordinates Team Green and Team Pink
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
    """Implementation of FireQueryService for Process A (Gateway)"""
    
    def __init__(self, config):
        self.config = config
        self.process_id = config['identity']
        self.role = config['role']
        self.neighbors = config['neighbors']
        print(f"[{self.process_id}] Initialized as {self.role}")
        print(f"[{self.process_id}] Neighbors: {[n['process_id'] for n in self.neighbors]}")
    
    def Query(self, request, context):
        """
        Handle client query request
        Returns a stream of QueryResponseChunk messages
        """
        print(f"[{self.process_id}] Received query request_id={request.request_id}")
        print(f"  Query type: {request.query_type}")
        print(f"  Parameters: {list(request.filter.parameters)}")
        
        # Forward query to Team Leaders (B and E) and aggregate results
        all_measurements = self.forward_to_team_leaders(request)
        
        print(f"[{self.process_id}] Aggregated {len(all_measurements)} total measurements")
        
        # Split results into chunks
        max_per_chunk = request.max_results_per_chunk if request.max_results_per_chunk > 0 else 100
        total_results = len(all_measurements)
        total_chunks = (total_results + max_per_chunk - 1) // max_per_chunk if total_results > 0 else 1
        
        if total_results == 0:
            # Return empty result
            chunk = fire_service_pb2.QueryResponseChunk(
                request_id=request.request_id,
                chunk_number=0,
                is_last_chunk=True,
                total_chunks=1,
                total_results=0
            )
            print(f"[{self.process_id}] Sending chunk 0/1 (empty result)")
            yield chunk
        else:
            # Send results in chunks
            for chunk_idx in range(total_chunks):
                start_idx = chunk_idx * max_per_chunk
                end_idx = min(start_idx + max_per_chunk, total_results)
                chunk_measurements = all_measurements[start_idx:end_idx]
                
                chunk = fire_service_pb2.QueryResponseChunk(
                    request_id=request.request_id,
                    chunk_number=chunk_idx,
                    is_last_chunk=(chunk_idx == total_chunks - 1),
                    total_chunks=total_chunks,
                    total_results=total_results
                )
                chunk.measurements.extend(chunk_measurements)
                
                print(f"[{self.process_id}] Sending chunk {chunk_idx + 1}/{total_chunks} with {len(chunk_measurements)} measurements")
                yield chunk
    
    def forward_to_team_leaders(self, request):
        """
        Forward query to Team Leaders (B and E) and aggregate results
        Returns list of all measurements from both teams
        """
        all_measurements = []
        
        # Create internal query request
        internal_request = fire_service_pb2.InternalQueryRequest(
            request_id=request.request_id,
            original_request_id=str(request.request_id),
            filter=request.filter,
            query_type=request.query_type,
            requesting_process=self.process_id
        )
        
        # Forward to each team leader
        for neighbor in self.neighbors:
            neighbor_id = neighbor['process_id']
            neighbor_address = f"{neighbor['hostname']}:{neighbor['port']}"
            
            print(f"[{self.process_id}] Forwarding query to Team Leader {neighbor_id} at {neighbor_address}")
            
            try:
                # Create channel to team leader
                channel = grpc.insecure_channel(neighbor_address)
                stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
                
                # Forward the query
                response = stub.InternalQuery(internal_request)
                
                # Collect measurements
                measurements_count = len(response.measurements)
                all_measurements.extend(response.measurements)
                print(f"[{self.process_id}] Received {measurements_count} measurements from {neighbor_id}")
                
                channel.close()
                
            except grpc.RpcError as e:
                print(f"[{self.process_id}] Error contacting {neighbor_id}: {e.code()}: {e.details()}")
        
        return all_measurements
    
    def CancelRequest(self, request, context):
        """Handle request cancellation"""
        print(f"[{self.process_id}] Cancel request_id={request.request_id}")
        
        # TODO: Cancel ongoing query and notify downstream processes
        
        return fire_service_pb2.StatusResponse(
            request_id=request.request_id,
            status="cancelled",
            chunks_delivered=0,
            total_chunks=0
        )
    
    def GetStatus(self, request, context):
        """Handle status check"""
        print(f"[{self.process_id}] Status request_id={request.request_id}")
        
        # TODO: Check actual status from request tracking
        
        return fire_service_pb2.StatusResponse(
            request_id=request.request_id,
            status="pending",
            chunks_delivered=0,
            total_chunks=0
        )
    
    def InternalQuery(self, request, context):
        """Handle internal queries from other processes"""
        print(f"[{self.process_id}] Internal query from {request.requesting_process}")
        
        # TODO: Query local FireColumnModel data
        # TODO: Return matching measurements
        
        return fire_service_pb2.InternalQueryResponse(
            request_id=request.request_id,
            original_request_id=request.original_request_id,
            is_complete=True,
            responding_process=self.process_id
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
        print("Usage: python server.py <config_file>")
        print("Example: python server.py ../configs/process_a.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    serve(config_path)

