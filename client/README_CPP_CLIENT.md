# C++ Client for Fire Query Service

## Overview

This C++ client connects to Process A (Gateway) and queries fire air quality data using gRPC.

## Features

- ✅ Connects to gateway server
- ✅ Sends Query requests with filters
- ✅ Receives streaming QueryResponseChunk responses
- ✅ Implements GetStatus RPC
- ✅ Implements CancelRequest RPC
- ✅ Prints results in human-readable format

## Prerequisites

### macOS (using Homebrew)
```bash
brew install grpc protobuf cmake
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install -y build-essential cmake
sudo apt-get install -y libgrpc++-dev libprotobuf-dev protobuf-compiler-grpc
```

## Building

### Option 1: Using the build script
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
bash scripts/build_cpp_client.sh
```

### Option 2: Manual build
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
mkdir -p build
cd build
cmake ..
make -j$(nproc)
```

## Running

### 1. Start the Gateway Server (Python)

In one terminal:
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc/gateway
source ../venv/bin/activate
python server.py ../configs/process_a.json
```

### 2. Run the C++ Client

In another terminal:
```bash
cd /Users/indraneelsarode/Desktop/mini-2-grpc
./build/fire_client
```

Or connect to a different server:
```bash
./build/fire_client localhost:50051
```

## Expected Output

```
Fire Query Service C++ Client
==============================
Connecting to: localhost:50051

=== Sending Query ===
Request ID: 12345
Parameters: PM2.5 PM10 
AQI range: 0 - 100

--- Received Chunk #0 ---
  Measurements in chunk: 0
  Total results: 0
  Total chunks: 1
  Is last chunk: Yes

✓ Query completed successfully
Total measurements received: 0

=== Checking Status ===
Request ID: 12345
Status: pending
Chunks delivered: 0/0

=== Cancelling Request ===
Request ID: 12345
Status: cancelled

=== All tests completed ===
```

## Code Structure

### Main Components

1. **FireQueryClient class**
   - `Query()` - Send query and receive streaming results
   - `GetStatus()` - Check request status
   - `CancelRequest()` - Cancel ongoing request

2. **main() function**
   - Creates client
   - Runs test queries
   - Demonstrates all RPC methods

### Key Features

- **Streaming support**: Handles multiple chunks in Query response
- **Error handling**: Gracefully handles connection errors
- **Flexible**: Server address can be specified via command line
- **Sample output**: Shows first 3 measurements from each chunk

## Testing with Full Network

To test with all 6 processes running:

1. Start all Python servers (A, B, C, D, E, F)
2. Run the C++ client
3. Watch messages flow through the network

The client will connect to A, which forwards to B and E, which forward to workers C, D, F.

## Troubleshooting

### Build Errors

**Error: gRPC not found**
```bash
# macOS
brew install grpc

# Linux
sudo apt-get install libgrpc++-dev
```

**Error: protobuf not found**
```bash
# macOS
brew install protobuf

# Linux
sudo apt-get install libprotobuf-dev
```

### Runtime Errors

**Connection refused**
- Make sure Process A (gateway) is running
- Check the server address and port

**Library not found (macOS)**
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
```

## Next Steps

- Add more query filters (geographic, temporal)
- Implement custom query types
- Add performance benchmarking
- Test with actual data loaded in servers

