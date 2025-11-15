# Multi-Computer Configuration Templates

This directory contains templates for deploying the Fire Query System across multiple computers.

## Templates Available

### 1. Two-Computer Deployment (`two_computer_template.json`)
**Recommended for most cases**

- **Computer 1:** Gateway A + Team Green Leader B + Worker D
- **Computer 2:** Worker C + Team Pink Leader E + Worker F

**Advantages:**
- Simple setup (only 2 machines needed)
- Balanced load distribution
- Gateway on separate machine from most workers

### 2. Three-Computer Deployment (`three_computer_template.json`)
**For maximum distribution**

- **Computer 1:** Gateway A + Worker C
- **Computer 2:** Team Green Leader B + Worker D
- **Computer 3:** Team Pink Leader E + Worker F

**Advantages:**
- Maximum separation of concerns
- Each team on separate machine
- Better isolation for testing

## How to Use

### Step 1: Choose Deployment Type
Select either 2-computer or 3-computer based on available resources.

### Step 2: Get IP Addresses
On each computer, find its IP address:

**macOS/Linux:**
```bash
ifconfig | grep "inet "
# Or
ip addr show
```

**Windows:**
```bash
ipconfig
```

Look for the IP address on your local network (usually 192.168.x.x or 10.x.x.x).

### Step 3: Update Template
1. Copy the template file
2. Replace placeholders with actual IP addresses:
   - `REPLACE_WITH_COMPUTER1_IP` → actual IP (e.g., `192.168.1.100`)
   - `REPLACE_WITH_COMPUTER2_IP` → actual IP (e.g., `192.168.1.101`)
   - etc.

### Step 4: Generate Configs
Use the setup script (coming soon) or manually create process configs:

```bash
# Example for process_a.json on Computer 1
{
  "identity": "A",
  "role": "leader",
  "team": "green",
  "hostname": "192.168.1.100",
  "port": 50051,
  "neighbors": [
    {"process_id": "B", "hostname": "192.168.1.100", "port": 50052},
    {"process_id": "E", "hostname": "192.168.1.101", "port": 50055}
  ]
}
```

### Step 5: Distribute and Deploy
1. Copy project to each computer
2. Place generated configs in `configs/` directory
3. Start servers on each computer
4. Test connectivity

## Network Requirements

### Firewall
Ensure ports 50051-50056 are open on all computers:

**macOS:**
```bash
# Add firewall rules
sudo pfctl -a com.apple/250.ApplicationFirewallFilter -f /etc/pf.conf
```

**Linux (UFW):**
```bash
sudo ufw allow 50051:50056/tcp
```

**Windows:**
```bash
netsh advfirewall firewall add rule name="gRPC Ports" dir=in action=allow protocol=TCP localport=50051-50056
```

### Network Testing
Test connectivity between computers:

```bash
# From Computer 1, ping Computer 2
ping 192.168.1.101

# Test specific port
nc -zv 192.168.1.101 50055
# Or
telnet 192.168.1.101 50055
```

## Troubleshooting

### Problem: Can't reach other computer
**Check:**
1. Both on same network (same subnet)
2. Firewall allows traffic on ports 50051-50056
3. No VPN interfering
4. Correct IP addresses in configs

### Problem: DNS resolution fails
**Solution:** Use IP addresses instead of hostnames in configs.

### Problem: Port already in use
**Solution:** 
```bash
# Find what's using the port
lsof -i :50051
# Kill the process
kill -9 <PID>
```

## See Also
- `MULTI_COMPUTER_SETUP.md` - Detailed setup guide
- `scripts/setup_multi_computer.py` - Automated config generator
- `scripts/check_connectivity.py` - Network connectivity tester

