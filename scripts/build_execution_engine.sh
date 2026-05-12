#!/bin/bash
# Build C++ Execution Engine (Linux/macOS)
# =========================================

set -e

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
CPP_DIR="$PROJECT_DIR/src/execution/cpp"
BUILD_DIR="$CPP_DIR/build"

echo "========================================="
echo "Mini-Medallion C++ Execution Engine"
echo "Building for Linux/macOS"
echo "========================================="
echo ""

# Check for required tools
if ! command -v cmake &> /dev/null; then
    echo "ERROR: cmake not found. Install with: brew install cmake (macOS) or apt install cmake (Linux)"
    exit 1
fi

if ! command -v make &> /dev/null; then
    echo "ERROR: make not found. Install with: brew install make (macOS) or apt install make (Linux)"
    exit 1
fi

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "CMake Configuration..."
# Check for CUDA availability
if command -v nvcc &> /dev/null; then
    echo "  CUDA found: $(nvcc --version | head -n 1)"
    cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_CUDA=ON ..
else
    echo "  CUDA not found, building without GPU support"
    cmake -DCMAKE_BUILD_TYPE=Release ..
fi

echo ""
echo "Building..."
make -j$(nproc)

echo ""
echo "========================================="
echo "Build completed!"
echo "Output: $BUILD_DIR/order_router_demo"
echo "========================================="
echo ""
echo "To run the demo:"
echo "  $BUILD_DIR/order_router_demo"
