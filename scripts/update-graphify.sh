#!/bin/bash
#
# Graphify Update Script
# Manual trigger to update the knowledge graph
#
# Usage:
#   ./scripts/update-graphify.sh              # Full update
#   ./scripts/update-graphify.sh --force      # Force rebuild
#   ./scripts/update-graphify.sh --quick      # AST-only (fast)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Graphify Knowledge Graph Update Tool     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"

# Check if graphify is installed
if ! command -v graphify &> /dev/null; then
    echo -e "${RED}✗ graphify not found${NC}"
    echo -e "${YELLOW}Install it with:${NC}"
    echo "  pip install graphify"
    exit 1
fi

echo -e "${GREEN}✓ graphify found${NC}"

# Parse arguments
FORCE_FLAG=""
if [ "$1" == "--force" ]; then
    FORCE_FLAG="--force"
    echo -e "${YELLOW}Mode: Full rebuild${NC}"
elif [ "$1" == "--quick" ]; then
    echo -e "${YELLOW}Mode: AST-only update (fast)${NC}"
else
    echo -e "${YELLOW}Mode: Normal update${NC}"
fi

# Check if graphify-out exists
if [ -d "graphify-out" ]; then
    CURRENT_SIZE=$(du -sh graphify-out | cut -f1)
    echo -e "${YELLOW}Current graph size: $CURRENT_SIZE${NC}"
fi

# Run update
echo -e "${YELLOW}Updating graph...${NC}"
echo ""

graphify update . $FORCE_FLAG

echo ""
echo -e "${GREEN}✓ Update complete${NC}"

# Show new size
if [ -d "graphify-out" ]; then
    NEW_SIZE=$(du -sh graphify-out | cut -f1)
    echo -e "${YELLOW}New graph size: $NEW_SIZE${NC}"
fi

# Show stats
if [ -f "graphify-out/GRAPH_REPORT.md" ]; then
    STATS=$(head -20 graphify-out/GRAPH_REPORT.md | grep -E "nodes|edges|communities" || true)
    if [ ! -z "$STATS" ]; then
        echo -e "${BLUE}Graph Statistics:${NC}"
        echo "$STATS"
    fi
fi

echo -e "${GREEN}✓ Done${NC}"
