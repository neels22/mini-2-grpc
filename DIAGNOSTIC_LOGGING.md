# Enhanced Diagnostic Logging for Circuit Breaker Testing

## Overview

Enhanced logging has been added to help diagnose why Gateway A's circuit to Team Leader E opens when only Server C fails (even though E is not connected to C).

## Changes Made

### 1. Enhanced Circuit Breaker Logging (`common/circuit_breaker.py`)

- **State Transitions**: Added emoji indicators and detailed messages
  - 🔴 When circuit opens: Shows failure count and recovery timeout
  - 🟢 When circuit closes: Confirms normal operation resumed

### 2. Enhanced Gateway Logging (`gateway/server.py`)

- **Call Timing**: Logs how long each call takes
  - `✅ Received X measurements from Y in Z.XXs`
- **Error Details**: Enhanced error logging with:
  - Error code (DEADLINE_EXCEEDED, UNAVAILABLE, etc.)
  - Failure count tracking (X/3)
  - Special warnings for timeouts that may cause cascading failures
- **Circuit State**: Shows time since circuit opened when skipping calls

### 3. Enhanced Team Leader Logging (`team_pink/server_e.py`, `team_green/server_b.py`)

- **E's Response Times**: Tracks how long E takes to:
  - Query local data
  - Forward to workers
  - Total query time
- **Worker Call Failures**: Detailed logging when workers fail
  - Error codes
  - Failure counts
  - Timeout warnings

## New Diagnostic Test Script

Created `test_circuit_breaker_diagnostic.sh` that:
1. Runs baseline test (all servers healthy)
2. Kills only Server C
3. Runs 3 queries to trigger circuit breaker
4. **Diagnoses circuit breaker states** for all connections:
   - Gateway A → B
   - Gateway A → E
   - Team Leader B → C
   - Team Leader E → D
   - Team Leader E → F
5. Shows E's response times
6. Shows Gateway A's call durations

## How to Use

### Run the Diagnostic Test

```bash
cd mini-2-grpc
./test_circuit_breaker_diagnostic.sh
```

### What to Look For

1. **If A→E circuit opens:**
   - Check E's response times - are they slow?
   - Check if E's calls to D or F timeout
   - Check Gateway A's call duration to E

2. **Expected Behavior:**
   - B→C circuit should OPEN (C is down)
   - A→B circuit should stay CLOSED (B still responds)
   - A→E circuit should stay CLOSED (E not connected to C)
   - E→D and E→F circuits should stay CLOSED

3. **If Cascading Failure Occurs:**
   - Look for TIMEOUT warnings in logs
   - Check E's total query time
   - Check if D or F are slow to respond

## Log File Locations

All logs are written to `/tmp/server_*.log`:
- `/tmp/server_a.log` - Gateway A
- `/tmp/server_b.log` - Team Leader B
- `/tmp/server_c.log` - Worker C
- `/tmp/server_d.log` - Worker D
- `/tmp/server_e.log` - Team Leader E
- `/tmp/server_f.log` - Worker F

## Example Log Output

### Normal Operation
```
[A] 📤 Forwarding query to Team Leader B at localhost:50052
[A] ✅ Received 134000 measurements from B in 0.45s
[A] 📤 Forwarding query to Team Leader E at localhost:50055
[E] 📥 Internal query from A
[E] Found 245000 local measurements (took 0.12s)
[E] Aggregated 789000 measurements from workers (forward took 0.23s, total 0.35s)
[A] ✅ Received 789000 measurements from E in 0.38s
```

### Circuit Breaker Opening
```
[B] ❌ Error contacting C: StatusCode.UNAVAILABLE (failure count: 1/3)
[B] ❌ Error contacting C: StatusCode.UNAVAILABLE (failure count: 2/3)
[B] ❌ Error contacting C: StatusCode.UNAVAILABLE (failure count: 3/3)
[CircuitBreaker-B->C] 🔴 State transition: closed -> open (failure_count=3)
[CircuitBreaker-B->C] ⚠️ Circuit OPENED - will block calls for 30.0s
```

### Cascading Failure (if it occurs)
```
[E] ❌ Error contacting D: StatusCode.DEADLINE_EXCEEDED (failure count: 1/3)
[E] ⚠️ TIMEOUT for D - this may cause E to be slow responding to Gateway A
[A] ❌ Error contacting E: StatusCode.DEADLINE_EXCEEDED (failure count: 1/3)
[A] ⚠️ TIMEOUT detected for E - this may cause cascading failure
```

## Next Steps

1. Run the diagnostic test
2. Check the logs to see exactly what happens
3. If A→E circuit opens, identify the root cause:
   - Is E slow to respond?
   - Do E's workers timeout?
   - Is there network congestion?
4. Use the findings to explain to your professor:
   - What the intended behavior was
   - What actually happened
   - Why it happened (root cause from logs)
   - How to fix it (if needed)

