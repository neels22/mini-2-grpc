# Testing the Network Overlay

## Query Forwarding Implementation

The network now supports query forwarding through the overlay:

```
Client → A (Gateway)
         ├─→ B (Team Green Leader) ──→ C, D (Workers)
         └─→ E (Team Pink Leader) ──→ F, D (Workers)
```

## How to Test

### 1. Start All 6 Servers

Open 6 separate terminals and run each server:

**Terminal 1 - Process A (Gateway):**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/gateway
source ../venv/bin/activate
python server.py ../configs/process_a.json
```

**Terminal 2 - Process B (Team Green Leader):**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/team_green
source ../venv/bin/activate
python server_b.py ../configs/process_b.json
```

**Terminal 3 - Process C (Team Green Worker):**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/team_green
source ../venv/bin/activate
python server_c.py ../configs/process_c.json
```

**Terminal 4 - Process D (Team Pink Worker):**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/team_pink
source ../venv/bin/activate
python server_d.py ../configs/process_d.json
```

**Terminal 5 - Process E (Team Pink Leader):**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/team_pink
source ../venv/bin/activate
python server_e.py ../configs/process_e.json
```

**Terminal 6 - Process F (Team Pink Worker):**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/team_pink
source ../venv/bin/activate
python server_f.py ../configs/process_f.json
```

### 2. Run the Test Client

In a 7th terminal:

```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/client
source ../venv/bin/activate
python test_client.py
```

### 3. What to Observe

When you run the test client, watch the server terminals. You should see:

**Process A output:**
```
[A] Received query request_id=12345
[A] Forwarding query to Team Leader B at localhost:50052
[A] Forwarding query to Team Leader E at localhost:50055
[A] Received 0 measurements from B
[A] Received 0 measurements from E
[A] Aggregated 0 total measurements
```

**Process B output:**
```
[B] Internal query from A
[B] Forwarding query to C at localhost:50053
[B] Forwarding query to D at localhost:50054
[B] Received 0 measurements from C
[B] Received 0 measurements from D
[B] Returning response with 0 measurements
```

**Process E output:**
```
[E] Internal query from A
[E] Forwarding query to F at localhost:50056
[E] Forwarding query to D at localhost:50054
[E] Received 0 measurements from F
[E] Received 0 measurements from D
[E] Returning response with 0 measurements
```

**Processes C, D, F output:**
```
[C] Internal query from B
[C] Returning response with 0 measurements
```

### 4. Verify the Network

✅ **Success indicators:**
- All 6 servers start without errors
- Client connects to Process A
- Process A forwards to B and E
- Process B forwards to C
- Process B maintains control link to D (no data forwarding)
- Process E forwards to D and F
- All responses propagate back to client
- No connection errors

❌ **If you see errors:**
- Check all servers are running
- Check port numbers match configs
- Check no firewall blocking localhost connections

## What's Working

✅ gRPC communication setup  
✅ Configuration system  
✅ Network overlay topology  
✅ Query forwarding A→B→C  
✅ Query forwarding A→E→D,F  
✅ Control signaling A→B↔D  
✅ Result aggregation  
✅ Chunked responses  

## What's Next

The network skeleton is complete. Next steps:

1. Load FireColumnModel data in each process
2. Implement actual query filtering
3. Add real measurement data to responses
4. Implement request tracking and cancellation
5. Add caching mechanisms
6. Implement C++ client (required)
7. Add C++ servers (at least one required)

