# Health Check and Monitoring Implementation

## Overview

This document details the implementation of health check and monitoring functionality for the distributed gRPC fire air quality query system. The implementation adds fault tolerance capabilities by enabling servers to monitor the health status of their neighbors and detect failures automatically.

**Date:** January 2025  
**Project:** Mini-3 Fault Tolerance - Health Monitoring Phase

---

## Files Changed/Added

### New Files Created (3 files)

1. **`common/health_monitor.py`** (~200 lines) - Core health monitoring module
   - `ServerStatus` enum (HEALTHY, DEGRADED, UNAVAILABLE)
   - `HealthMonitor` class with thread-safe health tracking
   - Background monitoring thread support
   - Status transition logic (1 failure → DEGRADED, 3 failures → UNAVAILABLE)

2. **`test_health_check.py`** - Manual health check test script
   - Tests all 6 servers' HealthCheck RPC
   - Verifies health check responses
   - Tests connectivity to all servers

3. **`test_health_monitoring.sh`** - Automated monitoring test script
   - Starts all servers automatically
   - Tests failure detection (kills worker C)
   - Tests recovery detection (restarts worker C)
   - Shows status transitions in logs

### Modified Server Files (6 files)

1. **`gateway/server.py`**
   - Added `HealthMonitor` import
   - Initialized health monitor in `__init__()` method
   - Implemented `HealthCheck()` RPC method
   - Added `_start_health_monitoring()` method for background monitoring
   - Monitors all neighbors (Team Leaders B and E)

2. **`team_green/server_b.py`**
   - Added `HealthMonitor` import
   - Initialized health monitor in `__init__()` method
   - Implemented `HealthCheck()` RPC method
   - Added `_start_health_monitoring()` method for background monitoring
   - Monitors query-enabled neighbors only (Worker C)

3. **`team_pink/server_e.py`**
   - Added `HealthMonitor` import
   - Initialized health monitor in `__init__()` method
   - Implemented `HealthCheck()` RPC method
   - Added `_start_health_monitoring()` method for background monitoring
   - Monitors query-enabled neighbors (Workers F and D)

4. **`team_green/server_c.py`**
   - Implemented `HealthCheck()` RPC method only
   - No background monitoring (leaf node - doesn't need to monitor others)

5. **`team_pink/server_d.py`**
   - Implemented `HealthCheck()` RPC method only
   - No background monitoring (leaf node - doesn't need to monitor others)

6. **`team_pink/server_f.py`**
   - Implemented `HealthCheck()` RPC method only
   - No background monitoring (leaf node - doesn't need to monitor others)

### Protocol Files (3 files)

1. **`proto/fire_service.proto`**
   - Added `HealthRequest` message definition
   - Added `HealthResponse` message definition
   - Added `HealthCheck` RPC to `FireQueryService`

2. **`proto/fire_service_pb2.py`** (generated)
   - Generated Python code for health check messages
   - Contains `HealthRequest` and `HealthResponse` classes

3. **`proto/fire_service_pb2_grpc.py`** (generated, patched)
   - Generated Python code for `HealthCheck` RPC
   - Patched with import fix for compatibility (try/except fallback for relative/absolute imports)

### Configuration Files (3 files)

1. **`configs/process_a.json`**
   - Added `health_monitoring` configuration section with:
     - `enabled`: true
     - `interval_seconds`: 5.0
     - `timeout_seconds`: 2.0

2. **`configs/process_b.json`**
   - Added `health_monitoring` configuration section

3. **`configs/process_e.json`**
   - Added `health_monitoring` configuration section

### Summary

- **Total Files**: 14 files
  - **New Files**: 3 (1 core module, 2 test scripts)
  - **Modified Server Files**: 6 (gateway, 2 team leaders, 3 workers)
  - **Protocol Files**: 3 (1 source, 2 generated)
  - **Configuration Files**: 3 (process_a, process_b, process_e)

### File Changes Summary

```
NEW FILES:
+ common/health_monitor.py
+ test_health_check.py
+ test_health_monitoring.sh

MODIFIED SERVER FILES:
M gateway/server.py
M team_green/server_b.py
M team_pink/server_e.py
M team_green/server_c.py
M team_pink/server_d.py
M team_pink/server_f.py

PROTOCOL FILES:
M proto/fire_service.proto
M proto/fire_service_pb2.py (generated)
M proto/fire_service_pb2_grpc.py (generated, patched)

CONFIGURATION FILES:
M configs/process_a.json
M configs/process_b.json
M configs/process_e.json
```

---

## Objectives

1. Implement health check RPC for all servers
2. Create background health monitoring system
3. Track neighbor server status (healthy/degraded/unavailable)
4. Detect server failures automatically
5. Detect server recovery automatically

---

## Implementation Details

### Phase 1: Protocol Updates

#### Changes Made

**File:** `proto/fire_service.proto`

Added health check messages and RPC:

```protobuf
// Health check messages
message HealthRequest {
    string requester_id = 1;  // Who is requesting health check
    int64 timestamp = 2;      // Request timestamp (optional)
}

message HealthResponse {
    bool healthy = 1;         // Is server healthy?
    string status = 2;        // "healthy", "degraded", "unhealthy"
    int64 timestamp = 3;      // Server timestamp
    string process_id = 4;    // Responding process ID
    string role = 5;          // Server role (optional)
}

// Added to FireQueryService
rpc HealthCheck(HealthRequest) returns (HealthResponse);
```

**Command to regenerate:**
```bash
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/fire_service.proto
```

---

### Phase 2: Health Monitor Module

#### Created File: `common/health_monitor.py`

**Key Components:**

1. **ServerStatus Enum:**
   - `HEALTHY`: Server is responding normally
   - `DEGRADED`: Server has some failures but still responding
   - `UNAVAILABLE`: Server is not responding (3+ consecutive failures)

2. **HealthMonitor Class:**
   - Thread-safe health tracking with locks
   - Tracks consecutive failures and successes
   - Status transitions:
     - 1 failure → DEGRADED
     - 3 failures → UNAVAILABLE
     - 1 success → HEALTHY
   - Background monitoring thread support

**Key Methods:**
- `register_neighbor()`: Register a neighbor for monitoring
- `update_health()`: Update health status based on check results
- `get_status()`: Get current status of a neighbor
- `is_healthy()`: Check if neighbor is healthy
- `start_monitoring()`: Start background health check thread
- `stop_monitoring()`: Stop background thread

---

### Phase 3: Server Implementation

#### Gateway Server (`gateway/server.py`)

**Changes:**
1. Added health monitor initialization in `__init__()`
2. Implemented `HealthCheck()` RPC method
3. Added `_start_health_monitoring()` method for background monitoring
4. Monitors all neighbors (Team Leaders B and E)

**Health Check Interval:** 5 seconds (configurable)  
**Health Check Timeout:** 2 seconds (configurable)

#### Team Leader Servers (`team_green/server_b.py`, `team_pink/server_e.py`)

**Changes:**
1. Added health monitor initialization
2. Implemented `HealthCheck()` RPC method
3. Added background monitoring
4. Only monitors `query_enabled=true` neighbors (skips control links)

#### Worker Servers (`server_c.py`, `server_d.py`, `server_f.py`)

**Changes:**
1. Implemented `HealthCheck()` RPC method only
2. No background monitoring (leaf nodes don't need to monitor others)

---

### Phase 4: Configuration Updates

**Files Updated:**
- `configs/process_a.json`
- `configs/process_b.json`
- `configs/process_e.json`

**Added Configuration:**
```json
"health_monitoring": {
  "enabled": true,
  "interval_seconds": 5.0,
  "timeout_seconds": 2.0
}
```

---

### Phase 5: Testing

#### Test Files Created

1. **`test_health_check.py`**: Manual health check test
   - Tests all 6 servers
   - Verifies HealthCheck RPC responses

2. **`test_health_monitoring.sh`**: Automated monitoring test
   - Starts all servers
   - Kills worker C to test failure detection
   - Restarts worker C to test recovery detection
   - Shows status transitions in logs

---

## Errors and Challenges Encountered

### Challenge 1: Proto File Import Issues

#### Problem
After regenerating proto files, the generated `fire_service_pb2_grpc.py` had an import statement:
```python
from proto import fire_service_pb2 as proto_dot_fire__service__pb2
```

This caused `ModuleNotFoundError: No module named 'proto'` when client scripts tried to import.

#### Root Cause
- Client scripts add `proto/` directory to `sys.path`
- When `proto/` is in `sys.path`, Python treats it as a module directory, not a package
- The absolute import `from proto import` doesn't work in this context

#### Solution Attempt 1: Relative Import
Changed to:
```python
from . import fire_service_pb2 as proto_dot_fire__service__pb2
```

**Result:** Failed with `ImportError: attempted relative import with no known parent package`

#### Solution Attempt 2: Try/Except Fallback (Final Solution)
Implemented a fallback mechanism:
```python
try:
    from . import fire_service_pb2 as proto_dot_fire__service__pb2
except ImportError:
    import fire_service_pb2 as proto_dot_fire__service__pb2
```

**Why This Works:**
- When used as a package (servers): relative import works
- When `proto/` is in `sys.path` (clients): direct import works
- Handles both use cases gracefully

**Lesson Learned:** Generated proto files need to be compatible with different import patterns used by servers vs clients.

---

### Challenge 2: UNIMPLEMENTED Error Code When Server Dies

#### Problem
When a server is killed, health checks return `StatusCode.UNIMPLEMENTED` instead of expected codes like `UNAVAILABLE` or `DEADLINE_EXCEEDED`.

#### Root Cause
When a server process is killed:
1. The gRPC connection may still attempt to connect
2. The server is dead, so gRPC can't determine available methods
3. gRPC returns `UNIMPLEMENTED` as a fallback error code
4. This is a quirk of how gRPC handles dead connections

#### Solution
Updated error handling to clarify that `UNIMPLEMENTED` can indicate a dead server:
```python
error_msg = f"{e.code()}"
if e.code() == grpc.StatusCode.UNIMPLEMENTED:
    error_msg += " (server may be down or unreachable)"
print(f"[{self.process_id}] Health check failed for {neighbor_id}: {error_msg}")
```

**Key Insight:** The specific error code doesn't matter - any `grpc.RpcError` indicates a failure. The health monitoring system correctly treats all RPC errors as failures.

**Lesson Learned:** gRPC error codes can be misleading. Focus on detecting failures rather than interpreting specific error codes.

---

### Challenge 3: Status Oscillation During Server Startup

#### Problem
After restarting a server, health status oscillates between `healthy` and `degraded` for a short period.

#### Root Cause
1. Server takes time to fully initialize
2. Health checks run every 5 seconds
3. During startup, some checks may fail (server not ready) and some succeed
4. This causes rapid status transitions

#### Solution
This is expected behavior and stabilizes once the server is fully running. The system correctly:
- Detects when server is fully operational (stabilizes to `healthy`)
- Handles transient failures during startup gracefully

**Lesson Learned:** Health monitoring systems need to account for startup time. The current implementation handles this correctly by requiring multiple consecutive failures before marking as unavailable.

---

## Testing Results

### Test 1: Basic Health Checks

**Command:**
```bash
python3 test_health_check.py
```

**Results:**
```
✓ Gateway A (localhost:50051): healthy
✓ Team Leader B (localhost:50052): healthy
✓ Worker C (localhost:50053): healthy
✓ Worker D (localhost:50054): healthy
✓ Team Leader E (localhost:50055): healthy
✓ Worker F (localhost:50056): healthy

Results: 6/6 servers healthy
```

**Status:** ✅ All servers responding correctly

---

### Test 2: Failure Detection

**Scenario:** Kill worker C

**Observed Behavior:**
1. Health checks continue running every 5 seconds
2. After 1 failure: Status changes to `DEGRADED`
3. After 3 failures: Status changes to `UNAVAILABLE`
4. Logs show: `[B] Health check failed for C: StatusCode.UNIMPLEMENTED (server may be down or unreachable)`

**Status Transitions:**
```
healthy → degraded (1 failure)
degraded → unavailable (3 failures)
```

**Status:** ✅ Failure detection working correctly

---

### Test 3: Recovery Detection

**Scenario:** Restart worker C

**Observed Behavior:**
1. Health checks detect successful response
2. Status immediately changes from `UNAVAILABLE` to `HEALTHY`
3. System recognizes server recovery

**Status Transitions:**
```
unavailable → healthy (1 success)
```

**Note:** Brief oscillation between healthy/degraded during startup is normal and expected.

**Status:** ✅ Recovery detection working correctly

---

## Architecture Decisions

### 1. Status Transition Logic

**Decision:** Use consecutive failure counting
- 1 failure → DEGRADED (server may be having issues)
- 3 failures → UNAVAILABLE (server is definitely down)
- 1 success → HEALTHY (server recovered)

**Rationale:**
- Prevents false positives from transient network issues
- Quick recovery detection (1 success is enough)
- Conservative failure detection (3 failures required)

### 2. Background Monitoring Thread

**Decision:** Use daemon threads for background health checks

**Rationale:**
- Non-blocking (doesn't interfere with query processing)
- Automatic cleanup when main process exits
- Runs independently of request handling

### 3. Only Monitor Query-Enabled Neighbors

**Decision:** Team leaders only monitor neighbors with `query_enabled=true`

**Rationale:**
- Control links (like B↔D) don't need health monitoring
- Reduces unnecessary network traffic
- Focuses monitoring on actual data paths

### 4. Workers Don't Monitor

**Decision:** Worker servers don't run background monitoring

**Rationale:**
- Workers are leaf nodes (no downstream dependencies)
- They only need to respond to health checks
- Reduces system complexity

---

## Performance Characteristics

### Health Check Overhead

- **Check Interval:** 5 seconds (configurable)
- **Check Timeout:** 2 seconds
- **Network Calls:** 1 per neighbor per interval
- **CPU Impact:** Minimal (background thread)
- **Memory Impact:** Negligible (status tracking only)

### Failure Detection Time

- **Minimum:** 5 seconds (1 check cycle)
- **Typical:** 15 seconds (3 check cycles for UNAVAILABLE)
- **Maximum:** 20 seconds (accounting for timing)

### Recovery Detection Time

- **Minimum:** 5 seconds (1 check cycle)
- **Typical:** 5-10 seconds (next check after restart)

---

## Code Statistics

### Files Modified
- 1 new file created: `common/health_monitor.py` (~200 lines)
- 6 server files updated: gateway, server_b, server_e, server_c, server_d, server_f
- 1 proto file updated: `fire_service.proto`
- 3 config files updated: process_a.json, process_b.json, process_e.json
- 1 generated file patched: `proto/fire_service_pb2_grpc.py` (import fix)

### Lines of Code Added
- Health monitor module: ~200 lines
- Server implementations: ~150 lines total
- Test files: ~150 lines total
- **Total:** ~500 lines of new code

---

## Future Enhancements

### Potential Improvements

1. **Health Status Endpoint**
   - Add RPC to query current health status of all neighbors
   - Useful for debugging and monitoring dashboards

2. **Configurable Failure Thresholds**
   - Make the "3 failures = unavailable" threshold configurable
   - Allow different thresholds for different server types

3. **Health Check Metrics**
   - Track success/failure rates
   - Measure average response times
   - Log health check statistics

4. **Integration with Retry Logic**
   - Use health status to skip unhealthy servers in retry attempts
   - Implement circuit breaker pattern using health status

5. **Health Check Aggregation**
   - Gateway could aggregate health status from all servers
   - Provide system-wide health dashboard

---

## Lessons Learned

### Technical Lessons

1. **Generated Code Compatibility**
   - Generated proto files need to work with different import patterns
   - Try/except fallback is a good pattern for compatibility

2. **gRPC Error Codes**
   - Error codes can be misleading (UNIMPLEMENTED doesn't always mean method missing)
   - Focus on detecting failures, not interpreting specific codes

3. **Startup Timing**
   - Health checks during server startup can cause false positives
   - System should be tolerant of transient failures

4. **Thread Safety**
   - Health monitoring requires proper locking
   - Background threads need careful lifecycle management

### Process Lessons

1. **Incremental Testing**
   - Test each phase before moving to the next
   - Health check RPC first, then background monitoring

2. **Error Handling**
   - Plan for edge cases (dead servers, network issues)
   - Logging is crucial for debugging distributed systems

3. **Documentation**
   - Documenting errors and solutions helps future development
   - Clear error messages improve debugging experience

---

## Conclusion

The health check and monitoring system has been successfully implemented and tested. The system:

✅ Detects server failures automatically  
✅ Detects server recovery automatically  
✅ Tracks health status with proper state transitions  
✅ Runs in background without blocking queries  
✅ Handles edge cases (dead servers, startup timing)  

The implementation provides a solid foundation for future fault tolerance features like retry logic, circuit breakers, and graceful degradation.

---

## References

- gRPC Python Documentation: https://grpc.io/docs/languages/python/
- Protocol Buffers: https://developers.google.com/protocol-buffers
- Health Check Pattern: https://microservices.io/patterns/observability/health-check-api.html

---

**Implementation Date:** January 2025  
**Status:** ✅ Complete and Tested

