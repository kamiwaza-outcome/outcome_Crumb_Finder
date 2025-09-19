#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting App Garden Template locally...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Stop any existing containers
echo -e "${YELLOW}Stopping any existing containers...${NC}"
docker-compose -f docker-compose.local.yml down 2>/dev/null

# Build and start the services
echo -e "${YELLOW}Building and starting services...${NC}"
docker-compose -f docker-compose.local.yml up --build -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Check if services are running
if docker-compose -f docker-compose.local.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Services started successfully!${NC}"
    # Check which port frontend is mapped to
    FRONTEND_PORT=$(docker-compose -f docker-compose.local.yml port frontend 3000 2>/dev/null | cut -d':' -f2 || echo "3001")
    echo -e "${GREEN}Frontend: http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "${GREEN}Backend API: http://localhost:8000${NC}"
    echo -e "${GREEN}Health check: http://localhost:8000/api/health${NC}"
    echo ""
    echo -e "${YELLOW}To view logs:${NC} docker-compose -f docker-compose.local.yml logs -f"
    echo -e "${YELLOW}To stop:${NC} docker-compose -f docker-compose.local.yml down"
else
    echo -e "${RED}❌ Failed to start services. Check logs with:${NC}"
    echo "docker-compose -f docker-compose.local.yml logs"
    exit 1
fi