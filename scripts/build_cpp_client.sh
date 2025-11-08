#!/bin/bash
# Build script for C++ client

set -e  # Exit on error

echo "======================================"
echo "Building C++ Fire Query Client"
echo "======================================"

cd "$(dirname "$0")/.."

# Create build directory
mkdir -p build
cd build

# Run CMake
echo ""
echo "Running CMake..."
cmake ..

# Build
echo ""
echo "Building..."
make -j$(sysctl -n hw.ncpu)

echo ""
echo "======================================"
echo "Build complete!"
echo "======================================"
echo ""
echo "Client executable: build/fire_client"
echo ""
echo "To run the client:"
echo "  ./build/fire_client"
echo "  ./build/fire_client <server_address>"
echo ""
echo "Example:"
echo "  ./build/fire_client localhost:50051"
echo ""

