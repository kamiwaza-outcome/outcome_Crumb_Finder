#!/bin/bash

# Stop Docker-based local development servers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping App Garden Template Docker containers...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}Docker is not running. Falling back to stopping local processes...${NC}"
    
    # Fallback: Kill processes on common development ports
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
        echo "Stopping backend server on port 8000..."
        kill -9 $(lsof -Pi :8000 -sTCP:LISTEN -t)
    fi
    
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
        echo "Stopping frontend server on port 3000..."
        kill -9 $(lsof -Pi :3000 -sTCP:LISTEN -t)
    fi
    
    if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null ; then
        echo "Stopping frontend server on port 3001..."
        kill -9 $(lsof -Pi :3001 -sTCP:LISTEN -t)
    fi
    
    pkill -f "next dev" 2>/dev/null
    pkill -f "uvicorn" 2>/dev/null
    
    echo -e "${GREEN}✅ Local processes stopped!${NC}"
else
    # Stop Docker containers
    if docker-compose -f docker-compose.local.yml ps -q | grep -q .; then
        echo -e "${YELLOW}Stopping Docker containers...${NC}"
        docker-compose -f docker-compose.local.yml down
        echo -e "${GREEN}✅ Docker containers stopped!${NC}"
    else
        echo -e "${YELLOW}No running Docker containers found.${NC}"
    fi
fi