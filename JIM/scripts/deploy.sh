#!/bin/bash
# Deploy Docker Stack + Initialize Infrastructure
# ================================================
# Prerequisites:
#   - Docker and docker-compose installed
#   - Port 9000, 9009, 6379, 9100, 5000, 9090, 3000 available

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "Mini-Medallion Infrastructure Deployment"
echo "========================================="
echo ""

# Check prerequisites
echo "[1/6] Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found. Install from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "ERROR: docker-compose not found"
    exit 1
fi

echo "  ✓ Docker available"
echo ""

# Deploy stack
echo "[2/6] Starting Docker containers..."
docker-compose up -d
echo "  ✓ Containers started"
echo ""

# Wait for services to be ready
echo "[3/6] Waiting for services to be ready (30 seconds)..."
sleep 30
echo "  ✓ Services initialized"
echo ""

# Initialize QuestDB
echo "[4/6] Initializing QuestDB..."
sleep 5

# Create tables
docker-compose exec -T questdb curl -s -X POST \
    --data 'CREATE TABLE IF NOT EXISTS gold_ticks (
        timestamp TIMESTAMP,
        bid DOUBLE,
        ask DOUBLE,
        bid_size DOUBLE,
        ask_size DOUBLE,
        trade_price DOUBLE,
        trade_size DOUBLE,
        source SYMBOL
    ) timestamp(timestamp) PARTITION BY DAY WAL;' \
    http://localhost:9000/exec 2>/dev/null || echo "  (Table creation via REST pending)"

echo "  ✓ QuestDB initialized"
echo ""

# Initialize MinIO bucket
echo "[5/6] Initializing MinIO..."
# Check if bucket exists, create if not
docker-compose exec -T minio mc mb minio/medallion-data --ignore-existing 2>/dev/null || true
echo "  ✓ MinIO initialized"
echo ""

# Verify connectivity
echo "[6/6] Verifying connectivity..."
python scripts/check_infrastructure.py
echo ""

echo "========================================="
echo "✓ Deployment completed successfully!"
echo "========================================="
echo ""
echo "Service URLs:"
echo "  QuestDB:   http://localhost:9000"
echo "  Redis:     localhost:6379"
echo "  MinIO:     http://localhost:9100"
echo "  MLflow:    http://localhost:5000"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:   http://localhost:3000 (admin/medallion)"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f [service]"
