#!/usr/bin/env python3
"""
Health monitoring utilities for tracking neighbor server status
"""

import time
import threading
from enum import Enum
from typing import Dict, Optional, Callable


class ServerStatus(Enum):
    """Server health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"      # Some failures, but still responding
    UNAVAILABLE = "unavailable"  # Not responding


class HealthMonitor:
    """
    Tracks health status of neighbor servers
    
    Monitors neighbor health through periodic checks and updates status
    based on consecutive failures/successes.
    """
    
    def __init__(self, process_id: str, health_check_interval: float = 5.0):
        """
        Initialize health monitor
        
        Args:
            process_id: ID of this process (for logging)
            health_check_interval: Seconds between health checks (default: 5.0)
        """
        self.process_id = process_id
        self.health_check_interval = health_check_interval
        
        # Track health of each neighbor
        # neighbor_id -> {status, last_seen, consecutive_failures, last_check_time}
        self.neighbor_health: Dict[str, dict] = {}
        
        self.lock = threading.Lock()
        self.running = False
        self.health_check_thread: Optional[threading.Thread] = None
        
        print(f"[HealthMonitor-{process_id}] Initialized with interval={health_check_interval}s")
    
    def register_neighbor(self, neighbor_id: str):
        """
        Register a neighbor to monitor
        
        Args:
            neighbor_id: ID of neighbor to monitor
        """
        with self.lock:
            if neighbor_id not in self.neighbor_health:
                self.neighbor_health[neighbor_id] = {
                    'status': ServerStatus.UNAVAILABLE,
                    'last_seen': 0,
                    'consecutive_failures': 0,
                    'consecutive_successes': 0,
                    'last_check_time': 0,
                    'total_checks': 0,
                    'total_failures': 0
                }
                print(f"[HealthMonitor-{self.process_id}] Registered neighbor: {neighbor_id}")
    
    def update_health(self, neighbor_id: str, is_healthy: bool):
        """
        Update health status for a neighbor
        
        Args:
            neighbor_id: ID of neighbor
            is_healthy: True if health check succeeded, False if failed
        """
        with self.lock:
            if neighbor_id not in self.neighbor_health:
                self.register_neighbor(neighbor_id)
            
            health_info = self.neighbor_health[neighbor_id]
            health_info['last_check_time'] = time.time()
            health_info['total_checks'] += 1
            
            old_status = health_info['status']
            
            if is_healthy:
                # Success: reset failure count, update last_seen
                health_info['last_seen'] = time.time()
                health_info['consecutive_failures'] = 0
                health_info['consecutive_successes'] += 1
                
                # Transition to healthy if we have enough successes
                if health_info['consecutive_successes'] >= 1:
                    health_info['status'] = ServerStatus.HEALTHY
            else:
                # Failure: increment failure count
                health_info['consecutive_failures'] += 1
                health_info['consecutive_successes'] = 0
                health_info['total_failures'] += 1
                
                # Update status based on failure count
                if health_info['consecutive_failures'] >= 3:
                    health_info['status'] = ServerStatus.UNAVAILABLE
                elif health_info['consecutive_failures'] >= 1:
                    health_info['status'] = ServerStatus.DEGRADED
            
            # Log status changes
            new_status = health_info['status']
            if old_status != new_status:
                print(f"[HealthMonitor-{self.process_id}] {neighbor_id} status: {old_status.value} -> {new_status.value} "
                      f"(failures: {health_info['consecutive_failures']})")
    
    def get_status(self, neighbor_id: str) -> ServerStatus:
        """
        Get current status of a neighbor
        
        Args:
            neighbor_id: ID of neighbor
            
        Returns:
            ServerStatus enum value
        """
        with self.lock:
            if neighbor_id not in self.neighbor_health:
                return ServerStatus.UNAVAILABLE
            return self.neighbor_health[neighbor_id]['status']
    
    def is_healthy(self, neighbor_id: str) -> bool:
        """
        Check if neighbor is currently healthy
        
        Args:
            neighbor_id: ID of neighbor
            
        Returns:
            True if healthy, False otherwise
        """
        return self.get_status(neighbor_id) == ServerStatus.HEALTHY
    
    def get_health_info(self, neighbor_id: str) -> Optional[dict]:
        """
        Get detailed health information for a neighbor
        
        Args:
            neighbor_id: ID of neighbor
            
        Returns:
            Dictionary with health info or None if not registered
        """
        with self.lock:
            if neighbor_id not in self.neighbor_health:
                return None
            # Return a copy to avoid external modification
            info = self.neighbor_health[neighbor_id].copy()
            info['status'] = info['status'].value  # Convert enum to string
            return info
    
    def get_all_status(self) -> Dict[str, dict]:
        """
        Get status of all registered neighbors
        
        Returns:
            Dictionary mapping neighbor_id -> health_info
        """
        with self.lock:
            result = {}
            for neighbor_id, health_info in self.neighbor_health.items():
                result[neighbor_id] = {
                    'status': health_info['status'].value,
                    'last_seen': health_info['last_seen'],
                    'consecutive_failures': health_info['consecutive_failures'],
                    'consecutive_successes': health_info['consecutive_successes'],
                    'total_checks': health_info['total_checks'],
                    'total_failures': health_info['total_failures'],
                    'last_check_time': health_info['last_check_time']
                }
            return result
    
    def start_monitoring(self, check_callback: Callable):
        """
        Start background health check thread
        
        Args:
            check_callback: Function to call for health checks
                           Signature: callback(monitor: HealthMonitor)
        """
        if self.running:
            print(f"[HealthMonitor-{self.process_id}] Already monitoring")
            return
        
        self.running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            args=(check_callback,),
            daemon=True,
            name=f"HealthCheck-{self.process_id}"
        )
        self.health_check_thread.start()
        print(f"[HealthMonitor-{self.process_id}] Background monitoring started")
    
    def stop_monitoring(self):
        """Stop background health check thread"""
        if not self.running:
            return
        
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=2.0)
        print(f"[HealthMonitor-{self.process_id}] Background monitoring stopped")
    
    def _health_check_loop(self, check_callback: Callable):
        """
        Background thread that periodically checks neighbor health
        
        Args:
            check_callback: Function to call for health checks
        """
        while self.running:
            try:
                check_callback(self)
            except Exception as e:
                print(f"[HealthMonitor-{self.process_id}] Error in health check loop: {e}")
            
            # Sleep with small intervals to allow quick shutdown
            sleep_time = 0
            while sleep_time < self.health_check_interval and self.running:
                time.sleep(0.5)
                sleep_time += 0.5

