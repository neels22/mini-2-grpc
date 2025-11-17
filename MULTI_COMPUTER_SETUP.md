# Multi-Computer Deployment Guide

**Prerequisites:** 2-3 computers on same network, project tested on single computer

---

## Overview

This guide helps you deploy the Fire Query System across multiple physical computers to test real network performance and meet the assignment requirement for multi-computer deployment.

###  Why Multi-Computer?

**Assignment Requirement:** The project must be deployed on 2-3 physical computers.

**Testing Goals:**
- Measure real network latency
- Validate chunked streaming across network
- Compare performance with single-computer
- Test system under realistic conditions

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **2-3 physical computers** on same network
- [ ] **Network access** between all computers (same subnet preferred)
- [ ] **Firewall configured** to allow ports 50051-50056
- [ ] **Project working** on single computer (run `./test_phase2.sh` to verify)
- [ ] **IP addresses** noted for each computer
- [ ] **SSH access** (optional but helpful for remote management)
- [ ] **30-60 minutes** for setup and testing

---

## Deployment Options

### Option 1: Two Computers (Recommended)

**Best for:** Most use cases, simpler setup

| Computer | Processes | Description |
|----------|-----------|-------------|
| Computer 1 | A, B, D | Gateway + Team Green + Worker |
| Computer 2 | C, E, F | Workers + Team Pink Leader |

**Advantages:**
- Only 2 machines needed
- Balanced load distribution
- Clear separation: gateway/green vs workers/pink

### Option 2: Three Computers

**Best for:** Maximum distribution, more testing scenarios

| Computer | Processes | Description |
|----------|-----------|-------------|
| Computer 1 | A, C | Gateway + Worker |
| Computer 2 | B, D | Team Green Leader + Worker |
| Computer 3 | E, F | Team Pink Leader + Worker |

**Advantages:**
- Maximum process isolation
- Each team on separate machine
- More realistic distributed scenario

---

## Step-by-Step Setup

### Phase 1: Network Preparation (10-15 min)

#### 1.1 Get IP Addresses

On each computer, find its local IP address:

**macOS/Linux:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
# Example output: inet 192.168.1.100 netmask 0xffffff00
```

**Alternative:**
```bash
hostname -I  # Linux
ipconfig getifaddr en0  # macOS WiFi
ipconfig getifaddr en1  # macOS Ethernet
```

**Windows:**
```bash
ipconfig
# Look for IPv4 Address under your network adapter
```

**Record the IPs:**
```
Computer 1: 192.168.1.100
Computer 2: 192.168.1.101
Computer 3: 192.168.1.102 (if using 3 computers)
```

#### 1.2 Test Network Connectivity

From Computer 1, ping other computers:
```bash
ping 192.168.1.101  # Computer 2
ping 192.168.1.102  # Computer 3 (if applicable)
```

Expected: < 5ms latency on LAN, < 50ms on WiFi

#### 1.3 Configure Firewall

**macOS:**
```bash
# System Preferences → Security & Privacy → Firewall
# Allow incoming connections for Python and your C++ servers
```

**Linux (UFW):**
```bash
sudo ufw allow 50051:50056/tcp
sudo ufw status
```

**Windows:**
```bash
# Windows Defender Firewall → Advanced Settings → Inbound Rules
# New Rule → Port → TCP → Specific ports: 50051-50056
```

#### 1.4 Test Port Connectivity

From Computer 1 to Computer 2:
```bash
# Using netcat
nc -zv 192.168.1.101 50055

# Using telnet
telnet 192.168.1.101 50055

# Expected: Connection successful
```

---

### Phase 2: Project Distribution (10-15 min)

#### 2.1 Copy Project to Each Computer

**Option A: Using SCP (Recommended)**
```bash
# From your main computer, copy to Computer 2
scp -r mini-2-grpc/ user@192.168.1.101:~/

# For Computer 3
scp -r mini-2-grpc/ user@192.168.1.102:~/
```

**Option B: Using USB Drive**
1. Copy `mini-2-grpc/` folder to USB drive
2. Transfer to each computer
3. Place in home directory or accessible location

**Option C: Using Git**
```bash
# On each computer
git clone <your-repo-url>
cd mini-2-grpc
```

#### 2.2 Prepare Python Environment on Each Computer

**On each computer that will run Python servers:**
```bash
cd mini-2-grpc
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Phase 3: Configuration (15-20 min)

#### 3.1 Choose Deployment Template

Copy the appropriate template:
```bash
cd configs/multi_computer

# For 2 computers
cp two_computer_template.json deployment_config.json

# For 3 computers
cp three_computer_template.json deployment_config.json
```

#### 3.2 Update IP Addresses

Edit `deployment_config.json` and replace placeholders:

**Example for 2-computer setup:**
```json
{
  "computers": [
    {
      "hostname": "192.168.1.100",  // ← Replace COMPUTER1_IP
      "processes": ["A", "B", "D"],
      ...
    },
    {
      "hostname": "192.168.1.101",  // ← Replace COMPUTER2_IP
      "processes": ["C", "E", "F"],
      ...
    }
  ]
}
```

#### 3.3 Generate Process Configs

**Manual method:** Update each `process_X.json` file with correct IPs

**Example - `process_a.json` (on Computer 1):**
```json
{
  "identity": "A",
  "role": "leader",
  "team": "green",
  "hostname": "192.168.1.100",  // This computer's IP
  "port": 50051,
  "neighbors": [
    {
      "process_id": "B",
      "hostname": "192.168.1.100",  // B is also on Computer 1
      "port": 50052
    },
    {
      "process_id": "E",
      "hostname": "192.168.1.101",  // E is on Computer 2
      "port": 50055
    }
  ]
}
```

**Key Point:** Update `hostname` fields to match actual computer IPs where each process runs.

#### 3.4 Distribute Configs

Copy the updated configs to each computer:

**Computer 1 needs:** `process_a.json`, `process_b.json`, `process_d.json`
**Computer 2 needs:** `process_c.json`, `process_e.json`, `process_f.json`

```bash
# From your main computer
scp configs/process_a.json user@192.168.1.100:~/mini-2-grpc/configs/
scp configs/process_c.json user@192.168.1.101:~/mini-2-grpc/configs/
# etc...
```

---

### Phase 4: Deployment (10-15 min)

#### 4.1 Start Servers in Order

**Important:** Start in this order to avoid connection errors:
1. Workers first (C, D, F)
2. Then Leaders (B, E)
3. Finally Gateway (A)

**On Computer 2 (Workers C, F):**
```bash
cd mini-2-grpc
source venv/bin/activate

# Terminal 1 - Worker C
python3 team_green/server_c.py configs/process_c.json

# Terminal 2 - Worker F
python3 team_pink/server_f.py configs/process_f.json
```

**On Computer 1:**
```bash
cd mini-2-grpc
source venv/bin/activate

# Terminal 1 - Server D (shared worker)
python3 team_pink/server_d.py configs/process_d.json

# Terminal 2 - Server B (Team Green leader)
python3 team_green/server_b.py configs/process_b.json

# Wait for B to start, then Terminal 3 - Gateway A
python3 gateway/server.py configs/process_a.json
```

**On Computer 2 (Team Pink leader):**
```bash
# Terminal 3 - Server E
python3 team_pink/server_e.py configs/process_e.json
```

#### 4.2 Verify Server Startup

Check logs on each server. You should see:
```
[X] Data model initialized with NNNN measurements
[X] Server started on HOSTNAME:PORT
```

---

### Phase 5: Testing (15-20 min)

#### 5.1 Run Basic Client Test

From Computer 1 (or any computer):
```bash
cd mini-2-grpc
source venv/bin/activate
python3 client/test_client.py
```

**Expected:** Query returns results (not 0)

#### 5.2 Run Performance Tests

```bash
python3 scripts/performance_test.py --output results/multi_computer.json
```

**This will take 30-60 minutes** - same tests as single-computer.

#### 5.3 Compare Results

Compare `results/multi_computer.json` with `results/single_computer.json`:

**Expected differences:**
- 10-20% slower total time (network latency)
- Similar throughput (network not saturated)
- +100-500ms to first chunk (cross-machine aggregation)

---

## Troubleshooting

### Problem: "Connection refused" error

**Possible causes:**
1. Server not started on target computer
2. Wrong IP address in config
3. Firewall blocking connection
4. Wrong port number

**Solution:**
```bash
# On target computer, verify server is running
ps aux | grep server_

# Check if port is listening
lsof -i :50055  # Example for server E

# Test connection
telnet TARGET_IP TARGET_PORT
```

### Problem: Query returns 0 results

**Possible causes:**
1. Not all servers running
2. Data not loaded
3. Network connectivity issues

**Solution:**
```bash
# Check server logs
tail -f /tmp/server_*.log

# Verify all 6 servers are running
# On Computer 1: ps aux | grep server_
# On Computer 2: ps aux | grep server_
```

### Problem: Slow performance (>2x single-computer)

**Possible causes:**
1. WiFi instead of wired network
2. Network congestion
3. Computers on different subnets

**Solution:**
1. Use wired Ethernet connections
2. Ensure computers on same subnet
3. Ping to check latency (should be < 5ms LAN, < 50ms WiFi)

### Problem: Firewall blocks connections

**macOS:**
```bash
# Temporarily disable firewall for testing
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

# Re-enable after testing
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
```

**Linux:**
```bash
# Check UFW status
sudo ufw status

# Allow ports
sudo ufw allow 50051:50056/tcp
```

---

## Performance Comparison

### Expected Results

| Metric | Single Computer | Multi-Computer (Est.) |
|--------|----------------|---------------------|
| Time to first chunk | 2.2s | 2.4-2.8s (+9-27%) |
| Total query time | 8.3s | 9.1-10.0s (+10-20%) |
| Throughput | 51K/s | 42-46K/s (-10-18%) |
| Concurrent (5 clients) | 12.9s | 14.2-15.5s (+10-20%) |

### Network Overhead Sources

1. **LAN latency:** ~1-5ms per hop (3 hops = 3-15ms)
2. **Serialization:** ~10-50ms per large message
3. **TCP handshake:** ~1-3ms per connection
4. **Total overhead:** ~50-200ms per query

### When Multi-Computer is Faster

- Multiple CPU cores utilized across machines
- Parallel processing of independent tasks
- Less resource contention

### When Single-Computer is Faster

- No network overhead
- Shared memory possible
- Lower latency communication

---

## Documentation

### After Testing, Document:

1. **Network Topology**
   - Which processes on which computers
   - IP addresses used
   - Network type (wired/wireless)

2. **Performance Comparison**
   - Single vs multi-computer results
   - Network latency measurements
   - Bottlenecks identified

3. **Issues Encountered**
   - Problems faced
   - Solutions applied
   - Lessons learned

4. **Create:** `MULTI_COMPUTER_RESULTS.md`

---

## Quick Reference

### Start All Servers (2-Computer Setup)

**Computer 1:**
```bash
cd mini-2-grpc
./build/server_d configs/process_d.json &
source venv/bin/activate
python3 team_green/server_b.py configs/process_b.json &
python3 gateway/server.py configs/process_a.json &
```

**Computer 2:**
```bash
cd mini-2-grpc
./build/server_c configs/process_c.json &
./build/server_f configs/process_f.json &
source venv/bin/activate
python3 team_pink/server_e.py configs/process_e.json &
```

### Stop All Servers

**On each computer:**
```bash
pkill -f server_
pkill -f "python3 gateway"
pkill -f "python3 team_"
```

### View Logs

```bash
tail -f /tmp/server_a.log
tail -f /tmp/server_b.log
# etc...
```

---

## Success Criteria

✅ **Multi-Computer Deployment Complete When:**

- [ ] All 6 servers running across 2-3 computers
- [ ] Client can query from any computer
- [ ] Performance tests complete
- [ ] Results documented and compared
- [ ] Network latency measured
- [ ] System demonstrates cross-network chunked streaming

---

## Next Steps After Multi-Computer

1. **Compare performance** with single-computer
2. **Document findings** in `MULTI_COMPUTER_RESULTS.md`
3. **Update PROJECT_STATUS.md** to 100% complete
4. **Prepare final presentation** showing both deployments
5. **Submit project** with all documentation

**Estimated time:** 3-4 hours for complete multi-computer deployment and testing.

