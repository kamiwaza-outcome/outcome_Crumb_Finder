#!/bin/bash

# Restart Docker-based local development
# This script stops and restarts the Docker containers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Restarting App Garden Template Docker containers...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker Desktop first.${NC}"
    echo -e "${YELLOW}You can start Docker Desktop manually or run:${NC}"
    echo "  open -a Docker"
    exit 1
fi

# Stop existing containers
echo -e "${BLUE}Stopping existing containers...${NC}"
if [ -f "./stop-local.sh" ]; then
    ./stop-local.sh
else
    # Fallback if stop-local.sh doesn't exist
    docker-compose -f docker-compose.local.yml down
fi

# Extra cleanup for port conflicts
echo -e "${YELLOW}Ensuring ports are free...${NC}"
# Kill any process on port 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Killing process on port 3000..."
    kill -9 $(lsof -Pi :3000 -sTCP:LISTEN -t) 2>/dev/null || true
fi
# Kill any process on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Killing process on port 8000..."
    kill -9 $(lsof -Pi :8000 -sTCP:LISTEN -t) 2>/dev/null || true
fi

# Wait a moment for ports to be fully released
echo -e "${YELLOW}Waiting for ports to be released...${NC}"
sleep 3

# Start containers again
echo -e "${GREEN}Starting containers...${NC}"
if [ -f "./start-local.sh" ]; then
    ./start-local.sh
else
    # Fallback if start-local.sh doesn't exist
    docker-compose -f docker-compose.local.yml up --build -d
    
    # Wait for services to be ready
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 5
    
    # Check if services are running
    if docker-compose -f docker-compose.local.yml ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Services restarted successfully!${NC}"
        # Check which port frontend is mapped to
        FRONTEND_PORT=$(docker-compose -f docker-compose.local.yml ps --format json | grep frontend | head -1 | grep -o '"3[0-9]*:3000"' | cut -d':' -f1 | tr -d '"' || echo "3000")
        echo -e "${GREEN}Frontend: http://localhost:${FRONTEND_PORT}${NC}"
        echo -e "${GREEN}Backend API: http://localhost:8000${NC}"
        echo -e "${GREEN}Health check: http://localhost:8000/api/health${NC}"
    else
        echo -e "${RED}❌ Failed to restart services. Check logs with:${NC}"
        echo "docker-compose -f docker-compose.local.yml logs"
        exit 1
    fi
fi