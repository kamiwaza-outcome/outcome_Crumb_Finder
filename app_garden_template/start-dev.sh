#!/bin/bash

# Start development servers without Docker
# This script finds available ports and starts both backend and frontend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting App Garden Template in development mode...${NC}"

# Function to find an available port
find_available_port() {
    local port=$1
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        echo -e "${YELLOW}Port $port is in use, trying next...${NC}" >&2
        ((port++))
    done
    echo $port
}

# Find available ports
BACKEND_PORT=$(find_available_port 8000)
FRONTEND_PORT=$(find_available_port 3000)

echo -e "${BLUE}Using ports:${NC}"
echo -e "  Backend:  ${GREEN}$BACKEND_PORT${NC}"
echo -e "  Frontend: ${GREEN}$FRONTEND_PORT${NC}"

# Create temporary env files with the ports
echo "NEXT_PUBLIC_API_URL=http://localhost:$BACKEND_PORT" > frontend/.env.local
echo "PORT=$FRONTEND_PORT" >> frontend/.env.local

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    # Kill the background processes
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    # Remove temporary env file
    rm -f frontend/.env.local
    echo -e "${GREEN}✅ Servers stopped${NC}"
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Start backend
echo -e "\n${YELLOW}Starting backend server...${NC}"
cd backend
uvicorn app.main:app --reload --port $BACKEND_PORT &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo -e "${YELLOW}Waiting for backend to start...${NC}"
sleep 3

# Check if backend is running
if ! curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null; then
    echo -e "${RED}❌ Backend failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend started${NC}"

# Start frontend
echo -e "\n${YELLOW}Starting frontend server...${NC}"
cd frontend
npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo -e "${YELLOW}Waiting for frontend to start...${NC}"
sleep 5

# Print access information
echo -e "\n${GREEN}✅ App Garden Template is running!${NC}"
echo -e "\n${BLUE}Access the application at:${NC}"
echo -e "  Frontend:     ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  Backend API:  ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  API Docs:     ${GREEN}http://localhost:${BACKEND_PORT}/api/docs${NC}"
echo -e "  Health Check: ${GREEN}http://localhost:${BACKEND_PORT}/api/health${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all servers${NC}"

# Keep script running
wait