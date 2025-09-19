#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Virtual environment name
VENV_NAME="venv"

# Check if virtual environment exists
if [ ! -d "$VENV_NAME" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv $VENV_NAME
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source $VENV_NAME/bin/activate

# Check if requirements need to be installed
if [ ! -f "$VENV_NAME/.requirements_installed" ] || [ "requirements.txt" -nt "$VENV_NAME/.requirements_installed" ]; then
    echo -e "${YELLOW}Installing/updating requirements...${NC}"
    pip install -r requirements.txt
    touch "$VENV_NAME/.requirements_installed"
    echo -e "${GREEN}Requirements installed.${NC}"
else
    echo -e "${GREEN}Requirements already up to date.${NC}"
fi

# Start the server
echo -e "${GREEN}Starting backend server...${NC}"
uvicorn app.main:app --reload --port 8000