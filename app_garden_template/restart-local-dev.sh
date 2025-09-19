#!/bin/bash

# Restart local development servers (without Docker)
# This script stops any running dev servers and starts them again

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Restarting App Garden Template (Development Mode)...${NC}"

# First stop any running servers
if [ -f "stop-local-dev.sh" ]; then
    ./stop-local-dev.sh
    sleep 2
else
    # Fallback to stop-dev.sh if stop-local-dev.sh doesn't exist
    if [ -f "stop-dev.sh" ]; then
        ./stop-dev.sh
        sleep 2
    fi
fi

# Start the servers again
echo -e "${GREEN}Starting development servers...${NC}"
./start-dev.sh