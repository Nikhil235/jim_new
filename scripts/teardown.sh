#!/bin/bash
# Teardown: Stop and clean Docker stack
# ====================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "Mini-Medallion Infrastructure Teardown"
echo "========================================="
echo ""

read -p "Stop Docker stack and remove containers? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping containers..."
    docker-compose down
    echo ""
    echo "✓ Stack stopped and cleaned"
    echo ""
    echo "To remove volumes (data): docker-compose down -v"
else
    echo "Aborted"
    exit 1
fi
