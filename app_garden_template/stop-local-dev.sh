#!/bin/bash

# Stop local development servers (without Docker)
# This script stops both backend and frontend dev servers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping App Garden Template development servers...${NC}"

# Function to kill processes on a port
kill_port() {
    local port=$1
    local name=$2
    
    # Find PIDs using the port
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Stopping $name on port $port...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✅ $name stopped${NC}"
    else
        echo -e "${BLUE}ℹ️  No $name process found on port $port${NC}"
    fi
}

# Kill backend (check common ports)
echo -e "${BLUE}Checking backend ports...${NC}"
for port in 8000 8001 8002 8003; do
    kill_port $port "backend"
done

# Kill frontend (check common ports)
echo -e "${BLUE}Checking frontend ports...${NC}"
for port in 3000 3001 3002 3003; do
    kill_port $port "frontend"
done

# Also kill by process name as backup
echo -e "${BLUE}Cleaning up any remaining processes...${NC}"
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
pkill -f "next dev" 2>/dev/null

echo -e "${GREEN}✅ All development servers stopped${NC}"