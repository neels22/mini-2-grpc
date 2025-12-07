#!/usr/bin/env python3
"""
Circuit breaker implementation for fault tolerance
Prevents repeated calls to failing servers by opening circuit after threshold failures
"""

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, allowing calls
    OPEN = "open"          # Failing fast, blocking calls
    HALF_OPEN = "half_open"  # Testing recovery, allowing one probe call


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is OPEN and call is attempted"""
    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures
    
    State machine:
    CLOSED -> [3 failures] -> OPEN -> [30s timeout] -> HALF_OPEN -> [1 success] -> CLOSED
                                                                  -> [1 failure] -> OPEN
    """
    
    def __init__(self, failure_threshold: int = 3, open_timeout: float = 30.0, 
                 success_threshold: int = 1, name: str = "unknown"):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of consecutive failures before opening (default: 3)
            open_timeout: Seconds to stay OPEN before transitioning to HALF_OPEN (default: 30.0)
            success_threshold: Number of successes needed to close from HALF_OPEN (default: 1)
            name: Name identifier for logging (default: "unknown")
        """
        self.failure_threshold = failure_threshold
        self.open_timeout = open_timeout
        self.success_threshold = success_threshold
        self.name = name
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change_time = time.time()
        
        # Thread safety
        self.lock = threading.Lock()
        
        print(f"[CircuitBreaker-{name}] Initialized: threshold={failure_threshold}, timeout={open_timeout}s")
    
    def get_state(self) -> CircuitState:
        """
        Get current circuit state
        
        Returns:
            Current CircuitState
        """
        with self.lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self.last_failure_time is not None:
                    elapsed = time.time() - self.last_failure_time
                    if elapsed >= self.open_timeout:
                        self._transition_to_half_open()
            
            return self.state
    
    def call(self, func: Callable[[], Any]) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute (should be a callable that takes no arguments)
            
        Returns:
            Result of function execution
            
        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Any exception raised by func (after recording failure)
        """
        # Check current state (may trigger OPEN -> HALF_OPEN transition)
        current_state = self.get_state()
        
        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"Circuit breaker OPEN for {self.name}")
        
        # CLOSED or HALF_OPEN: attempt the call
        try:
            result = func()
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
    
    def _record_success(self):
        """Record a successful call"""
        with self.lock:
            old_state = self.state
            
            if self.state == CircuitState.HALF_OPEN:
                # In HALF_OPEN, we need success_threshold successes to close
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                # In CLOSED, reset failure count on success
                self.failure_count = 0
                self.success_count = 0
            
            # Log state change if it occurred
            if old_state != self.state:
                print(f"[CircuitBreaker-{self.name}] 🟢 State transition: {old_state.value} -> {self.state.value}")
                if self.state == CircuitState.CLOSED:
                    print(f"[CircuitBreaker-{self.name}] ✅ Circuit CLOSED - normal operation resumed")
    
    def _record_failure(self):
        """Record a failed call"""
        with self.lock:
            old_state = self.state
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Failure in HALF_OPEN: go back to OPEN
                self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                # Failure in CLOSED: increment count, open if threshold reached
                self.failure_count += 1
                self.success_count = 0
                if self.failure_count >= self.failure_threshold:
                    self._transition_to_open()
            
            # Log state change if it occurred
            if old_state != self.state:
                print(f"[CircuitBreaker-{self.name}] 🔴 State transition: {old_state.value} -> {self.state.value} "
                      f"(failure_count={self.failure_count})")
                if self.state == CircuitState.OPEN:
                    print(f"[CircuitBreaker-{self.name}] ⚠️ Circuit OPENED - will block calls for {self.open_timeout}s")
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        self.last_state_change_time = time.time()
        self.success_count = 0
        # Keep failure_count at threshold (don't reset)
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change_time = time.time()
        self.success_count = 0
        # Reset failure count for the probe
        self.failure_count = 0
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.last_state_change_time = time.time()
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self.lock:
            old_state = self.state
            self._transition_to_closed()
            if old_state != CircuitState.CLOSED:
                print(f"[CircuitBreaker-{self.name}] Manually reset: {old_state.value} -> CLOSED")
    
    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics
        
        Returns:
            Dictionary with state, failure_count, and timing information
        """
        with self.lock:
            stats = {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_state_change_time': self.last_state_change_time,
                'last_failure_time': self.last_failure_time,
                'time_since_last_failure': time.time() - self.last_failure_time if self.last_failure_time else None
            }
            return stats

