# How to Run the Mini-2 gRPC System

## Quick Start

### 1. Build C++ Servers (if not already built)
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
make clean
make servers
```

This builds:
- `build/server_c` (Team Green Worker)
- `build/server_d` (Team Pink Worker)
- `build/server_f` (Team Pink Worker)

### 2. Start All Servers (in separate terminals)

**Terminal 1 - Server C (Team Green Worker)**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./build/server_c configs/process_c.json
```
Expected output:
```
[C] Initialized as worker for Team green
[C] Loading partitioned data from 9 subdirectories...
[FireColumnModel] Processing 108 CSV files from 9 partitioned subdirectories...
[FireColumnModel] Loaded 243313 measurements from 1347 sites
[C] Data model initialized with 243313 measurements
[C] Server started on localhost:50053
```

**Terminal 2 - Server D (Team Pink Worker)**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./build/server_d configs/process_d.json
```
Expected output:
```
[D] Initialized as worker for Team pink
[D] Loading partitioned data from 9 subdirectories...
[FireColumnModel] Processing 108 CSV files from 9 partitioned subdirectories...
[FireColumnModel] Loaded 244375 measurements from 1354 sites
[D] Data model initialized with 244375 measurements
[D] Server started on localhost:50054
```

**Terminal 3 - Server F (Team Pink Worker)**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./build/server_f configs/process_f.json
```
Expected output:
```
[F] Initialized as worker for Team pink
[F] Loading partitioned data from 11 subdirectories...
[FireColumnModel] Processing 132 CSV files from 11 partitioned subdirectories...
[FireColumnModel] Loaded 300494 measurements from 1375 sites
[F] Data model initialized with 300494 measurements
[F] Server started on localhost:50056
```

**Terminal 4 - Server B (Team Green Leader)**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./venv/bin/python3 team_green/server_b.py configs/process_b.json
```
Expected output:
```
[B] Initialized as team_leader for Team green
[B] Neighbors: ['C']
[B] Loading partitioned data from: ['20200810', '20200814', '20200815', '20200816', '20200817']
[FireColumnModel] Processing 60 CSV files from 5 subdirectories...
[FireColumnModel] Loaded 134004 measurements from 1312 sites
[B] Data model initialized with 134004 measurements
[B] Server started on localhost:50052
```

**Terminal 5 - Server E (Team Pink Leader)**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./venv/bin/python3 team_pink/server_e.py configs/process_e.json
```
Expected output:
```
[E] Initialized as team_leader for Team pink
[E] Neighbors: ['F', 'D']
[E] Loading partitioned data from: ['20200905', '20200906', ..., '20200913']
[FireColumnModel] Processing 108 CSV files from 9 subdirectories...
[FireColumnModel] Loaded 245339 measurements from 1357 sites
[E] Data model initialized with 245339 measurements
[E] Server started on localhost:50055
```

**Terminal 6 - Gateway A**
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./venv/bin/python3 gateway/server.py configs/process_a.json
```
Expected output:
```
[A] Initialized as gateway for Team N/A
[A] Neighbors: ['B', 'E']
[A] Server started on localhost:50051
```

## Port Assignments

| Server | Process | Port |
|--------|---------|------|
| Gateway A | gateway/server.py | 50051 |
| Server B | team_green/server_b.py | 50052 |
| Server C | build/server_c | 50053 |
| Server D | build/server_d | 50054 |
| Server E | team_pink/server_e.py | 50055 |
| Server F | build/server_f | 50056 |

## System Architecture

```
                    Client
                      |
                      v
              Gateway A (50051)
                 /        \
                /          \
               v            v
         Server B        Server E
      (Green Leader)  (Pink Leader)
         (50052)         (50055)
            |              /  \
            v             v    v
         Server C     Server D  Server F
         (50053)       (50054)  (50056)
```

## Query Flow Example

1. **Client** → sends query to **Gateway A** (50051)
2. **Gateway A** → forwards to both **Server B** (50052) and **Server E** (50055)
3. **Server B** (Green Leader):
   - Queries its local partition (Aug 10-17)
   - Forwards to **Server C** (50053)
   - Aggregates results from self + C
4. **Server E** (Pink Leader):
   - Queries its local partition (Sep 5-13)
   - Forwards to **Server D** (50054) and **Server F** (50056)
   - Aggregates results from self + D + F
5. **Gateway A** → merges results from B and E → streams to **Client**

## Data Coverage

Each server holds a unique partition:
- **Server B**: Aug 10-17 (134K measurements)
- **Server C**: Aug 18-26 (243K measurements)
- **Server D**: Aug 27-Sep 4 (244K measurements)
- **Server E**: Sep 5-13 (245K measurements)
- **Server F**: Sep 14-24 (300K measurements)
- **Total**: 1.17M measurements

## Testing

### Run Python Client
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./venv/bin/python3 client/test_client.py
```

### Expected Behavior
- Client connects to Gateway A
- Query distributed to all 5 worker servers
- Results aggregated and returned
- Total should match sum of all partitions

## Troubleshooting

### Server Won't Start
- Check if port is already in use: `lsof -i :50051`
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Verify C++ servers built: `ls -la build/server_*`

### No Data Loaded
- Verify `data/` directory exists with CSV files
- Check partition config in `configs/process_*.json`
- Look for error messages during server startup

### Connection Refused
- Ensure servers started in correct order (workers before leaders)
- Check firewall/network settings
- Verify port assignments in config files

## Stopping Servers

Press `Ctrl+C` in each terminal to gracefully stop servers.

Or kill all at once:
```bash
pkill -f "server_[bcdef]"
pkill -f "server.py"
```

## Next Steps

1. Test end-to-end queries through Gateway A
2. Verify data aggregation across all partitions
3. Implement chunked streaming response
4. Add query cancellation and status tracking

