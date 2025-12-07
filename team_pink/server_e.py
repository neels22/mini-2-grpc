#!/usr/bin/env python3
"""
Process E - Team Pink Leader Server
Coordinates Team Pink workers (F and D)
"""

import json
import grpc
from concurrent import futures
import sys
import os
import time

# Add proto and common directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'common'))

import fire_service_pb2
import fire_service_pb2_grpc
from fire_column_model import FireColumnModel
from health_monitor import HealthMonitor, ServerStatus
from circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


class FireQueryServiceImpl(fire_service_pb2_grpc.FireQueryServiceServicer):
    """Implementation of FireQueryService for Process E (Team Pink Leader)"""
    
    def __init__(self, config):
        self.config = config
        self.process_id = config['identity']
        self.role = config['role']
        self.team = config['team']
        self.neighbors = config['neighbors']
        print(f"[{self.process_id}] Initialized as {self.role} for Team {self.team}")
        print(f"[{self.process_id}] Neighbors: {[n['process_id'] for n in self.neighbors]}")
        
        # Initialize FireColumnModel with Team Pink data
        self.data_model = FireColumnModel()
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data')
        if os.path.exists(data_path):
            # Check if partition is configured
            allowed_dirs = None
            if 'data_partition' in config and config['data_partition'].get('enabled'):
                allowed_dirs = config['data_partition'].get('directories', [])
                print(f"[{self.process_id}] Loading partitioned data from: {allowed_dirs}")
            
            self.data_model.read_from_directory(data_path, allowed_dirs)
            print(f"[{self.process_id}] Data model initialized with {self.data_model.measurement_count()} measurements")
        else:
            print(f"[{self.process_id}] Data directory not found: {data_path}")
            print(f"[{self.process_id}] Data model initialized with 0 measurements")
        
        # Initialize health monitor
        health_config = config.get('health_monitoring', {})
        health_check_interval = health_config.get('interval_seconds', 5.0)
        self.health_monitor = HealthMonitor(self.process_id, health_check_interval)
        
        # Register query-enabled neighbors for monitoring
        for neighbor in self.neighbors:
            if neighbor.get('query_enabled', True):
                self.health_monitor.register_neighbor(neighbor['process_id'])
        
        # Initialize circuit breakers for query-enabled neighbors
        self.circuit_breakers = {}
        cb_config = config.get('circuit_breakers', {})
        failure_threshold = cb_config.get('failure_threshold', 3)
        open_timeout = cb_config.get('open_timeout_seconds', 30.0)
        success_threshold = cb_config.get('success_threshold', 1)
        
        for neighbor in self.neighbors:
            if neighbor.get('query_enabled', True):
                neighbor_id = neighbor['process_id']
                self.circuit_breakers[neighbor_id] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    open_timeout=open_timeout,
                    success_threshold=success_threshold,
                    name=f"{self.process_id}->{neighbor_id}"
                )
        
        print(f"[{self.process_id}] Health monitoring initialized")
        print(f"[{self.process_id}] Circuit breakers initialized for {len(self.circuit_breakers)} query-enabled neighbors")
        
        # Start health monitoring
        self._start_health_monitoring()
    
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
        query_start = time.time()
        print(f"[{self.process_id}] 📥 Internal query from {request.requesting_process}")
        print(f"  Request ID: {request.request_id}")
        print(f"  Original request: {request.original_request_id}")
        print(f"  Query type: {request.query_type}")
        
        # Query local FireColumnModel data (E acts as worker too)
        local_start = time.time()
        local_measurements = self._query_local_data(request)
        local_time = time.time() - local_start
        print(f"[{self.process_id}] Found {len(local_measurements)} local measurements (took {local_time:.2f}s)")
        
        # Forward query to workers F and D
        forward_start = time.time()
        worker_measurements = self.forward_to_workers(request)
        forward_time = time.time() - forward_start
        all_measurements = local_measurements + worker_measurements
        
        total_time = time.time() - query_start
        print(f"[{self.process_id}] Aggregated {len(all_measurements)} measurements from workers (forward took {forward_time:.2f}s, total {total_time:.2f}s)")
        
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
    
    def _query_local_data(self, request):
        """
        Query local FireColumnModel data
        Returns list of FireMeasurement proto messages
        """
        matching_indices = []
        
        if request.HasField('filter'):
            filter_obj = request.filter
            
            # Start with parameter or site filtering (OR logic for multiple parameters)
            if len(filter_obj.parameters) > 0:
                # Handle multiple parameters (OR logic - match any parameter)
                all_param_indices = set()
                for param in filter_obj.parameters:
                    param_indices = self.data_model.get_indices_by_parameter(param)
                    all_param_indices.update(param_indices)
                matching_indices = list(all_param_indices)
            elif len(filter_obj.site_names) > 0:
                # Filter by site name
                site = filter_obj.site_names[0]
                matching_indices = self.data_model.get_indices_by_site(site)
            else:
                # No parameter/site filter - start with all measurements
                matching_indices = list(range(self.data_model.measurement_count()))
            
            # Apply AQI range filter (AND logic - must also match AQI range)
            if filter_obj.min_aqi > 0 or filter_obj.max_aqi > 0:
                filtered_indices = []
                for idx in matching_indices:
                    aqi = self.data_model.aqis[idx]
                    if ((filter_obj.min_aqi == 0 or aqi >= filter_obj.min_aqi) and
                        (filter_obj.max_aqi == 0 or aqi <= filter_obj.max_aqi)):
                        filtered_indices.append(idx)
                matching_indices = filtered_indices
        else:
            # No filter - return all measurements
            matching_indices = list(range(self.data_model.measurement_count()))
        
        # Convert to proto messages
        measurements = []
        for idx in matching_indices:
            measurement = fire_service_pb2.FireMeasurement(
                latitude=self.data_model.latitudes[idx],
                longitude=self.data_model.longitudes[idx],
                datetime=self.data_model.datetimes[idx],
                parameter=self.data_model.parameters[idx],
                concentration=self.data_model.concentrations[idx],
                unit=self.data_model.units[idx],
                raw_concentration=self.data_model.raw_concentrations[idx],
                aqi=self.data_model.aqis[idx],
                category=self.data_model.categories[idx],
                site_name=self.data_model.site_names[idx],
                agency_name=self.data_model.agency_names[idx],
                aqs_code=self.data_model.aqs_codes[idx],
                full_aqs_code=self.data_model.full_aqs_codes[idx]
            )
            measurements.append(measurement)
        
        return measurements
    
    def _make_grpc_call(self, neighbor_address, request):
        """
        Helper method to make gRPC call (used by circuit breaker)
        
        Args:
            neighbor_address: Address of the neighbor server
            request: InternalQueryRequest to send
            
        Returns:
            InternalQueryResponse from the server
        """
        # Create channel to neighbor with increased message size limits
        options = [
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
            ('grpc.max_send_message_length', 100 * 1024 * 1024),     # 100MB
        ]
        channel = grpc.insecure_channel(neighbor_address, options=options)
        try:
            stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
            # Forward the query
            response = stub.InternalQuery(request)
            return response
        finally:
            channel.close()
    
    def forward_to_workers(self, request):
        """
        Forward query to worker processes (F and D)
        Returns aggregated results from all workers
        """
        all_measurements = []
        
        for neighbor in self.neighbors:
            neighbor_id = neighbor['process_id']
            neighbor_address = f"{neighbor['hostname']}:{neighbor['port']}"
            
            print(f"[{self.process_id}] Forwarding query to {neighbor_id} at {neighbor_address}")
            
            # Check circuit breaker state before attempting call
            if neighbor_id in self.circuit_breakers:
                cb_state = self.circuit_breakers[neighbor_id].get_state()
                if cb_state.value == "open":
                    print(f"[{self.process_id}] Circuit breaker OPEN for {neighbor_id}, skipping call (fail-fast)")
                    continue
            
            try:
                # Wrap gRPC call with circuit breaker
                if neighbor_id in self.circuit_breakers:
                    response = self.circuit_breakers[neighbor_id].call(
                        lambda: self._make_grpc_call(neighbor_address, request)
                    )
                else:
                    # Fallback if circuit breaker not initialized (shouldn't happen)
                    response = self._make_grpc_call(neighbor_address, request)
                
                # Collect measurements
                all_measurements.extend(response.measurements)
                print(f"[{self.process_id}] Received {len(response.measurements)} measurements from {neighbor_id}")
                
            except CircuitBreakerOpenError:
                # Circuit is OPEN - fail fast, skip call
                print(f"[{self.process_id}] ⏭️ Circuit breaker OPEN for {neighbor_id}, skipping call (fail-fast)")
            except grpc.RpcError as e:
                # gRPC error - circuit breaker records failure automatically
                error_code = e.code()
                if neighbor_id in self.circuit_breakers:
                    stats = self.circuit_breakers[neighbor_id].get_stats()
                    fc = stats.get('failure_count', 0)
                    print(f"[{self.process_id}] ❌ Error contacting {neighbor_id}: {error_code} (failure count: {fc}/3)")
                else:
                    print(f"[{self.process_id}] ❌ Error contacting {neighbor_id}: {error_code}")
                if error_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"[{self.process_id}] ⚠️ TIMEOUT for {neighbor_id} - this may cause E to be slow responding to Gateway A")
            except Exception as e:
                # Other errors - circuit breaker records failure automatically
                print(f"[{self.process_id}] ❌ Unexpected error contacting {neighbor_id}: {type(e).__name__}: {e}")
        
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
    
    def HealthCheck(self, request, context):
        """Handle health check requests"""
        return fire_service_pb2.HealthResponse(
            healthy=True,
            status="healthy",
            timestamp=int(time.time()),
            process_id=self.process_id,
            role=self.role
        )
    
    def _start_health_monitoring(self):
        """Start background health check thread"""
        def health_check_loop(monitor):
            """Periodically check health of neighbors"""
            while monitor.running:
                for neighbor in self.neighbors:
                    # Only check query-enabled neighbors
                    if not neighbor.get('query_enabled', True):
                        continue
                    
                    neighbor_id = neighbor['process_id']
                    neighbor_address = f"{neighbor['hostname']}:{neighbor['port']}"
                    
                    try:
                        channel = grpc.insecure_channel(neighbor_address)
                        stub = fire_service_pb2_grpc.FireQueryServiceStub(channel)
                        
                        health_request = fire_service_pb2.HealthRequest(
                            requester_id=self.process_id,
                            timestamp=int(time.time())
                        )
                        
                        health_config = self.config.get('health_monitoring', {})
                        timeout = health_config.get('timeout_seconds', 2.0)
                        response = stub.HealthCheck(health_request, timeout=timeout)
                        monitor.update_health(neighbor_id, response.healthy)
                        channel.close()
                        
                    except grpc.RpcError as e:
                        monitor.update_health(neighbor_id, False)
                        status = monitor.get_status(neighbor_id)
                        if status == ServerStatus.UNAVAILABLE:
                            # UNIMPLEMENTED can occur when server is dead/unreachable
                            # UNAVAILABLE means server is down
                            # DEADLINE_EXCEEDED means timeout
                            error_msg = f"{e.code()}"
                            if e.code() == grpc.StatusCode.UNIMPLEMENTED:
                                error_msg += " (server may be down or unreachable)"
                            print(f"[{self.process_id}] Health check failed for {neighbor_id}: {error_msg}")
                    except Exception as e:
                        monitor.update_health(neighbor_id, False)
                        print(f"[{self.process_id}] Health check error for {neighbor_id}: {e}")
        
        self.health_monitor.start_monitoring(health_check_loop)
        print(f"[{self.process_id}] Background health monitoring started")
    
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
        print("Usage: python server_e.py <config_file>")
        print("Example: python server_e.py ../configs/process_e.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    serve(config_path)

