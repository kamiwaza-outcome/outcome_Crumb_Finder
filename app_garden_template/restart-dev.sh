#!/bin/bash

# Restart development servers
# This script stops any running servers and starts them again

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Restarting App Garden Template...${NC}"

# First stop any running servers
if [ -f "stop-dev.sh" ]; then
    ./stop-dev.sh
    sleep 2
fi

# Start the servers again
echo -e "${GREEN}Starting servers...${NC}"
./start-dev.sh