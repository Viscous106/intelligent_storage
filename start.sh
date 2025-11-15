#!/bin/bash

# Intelligent Storage System - Unified Startup Script
# Starts MongoDB, Django Backend, and Frontend in the background
# Usage: ./start.sh [--no-mongodb] [--backend-only] [--frontend-only]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# PID file locations
PIDS_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PIDS_DIR"

MONGO_PID_FILE="$PIDS_DIR/mongodb.pid"
BACKEND_PID_FILE="$PIDS_DIR/backend.pid"
FRONTEND_PID_FILE="$PIDS_DIR/frontend.pid"

# Parse arguments
START_MONGO=true
START_BACKEND=true
START_FRONTEND=true

for arg in "$@"; do
    case $arg in
        --no-mongodb)
            START_MONGO=false
            ;;
        --backend-only)
            START_FRONTEND=false
            START_MONGO=false
            ;;
        --frontend-only)
            START_BACKEND=false
            START_MONGO=false
            ;;
        --help|-h)
            echo "Intelligent Storage System - Startup Script"
            echo ""
            echo "Usage: ./start.sh [options]"
            echo ""
            echo "Options:"
            echo "  --no-mongodb      Start without MongoDB (PostgreSQL only)"
            echo "  --backend-only    Start only backend server"
            echo "  --frontend-only   Start only frontend server"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Default: Starts MongoDB, Backend, and Frontend"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}=========================================="
echo "  Intelligent Storage System"
echo "==========================================${NC}"
echo ""

# Function to check if process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    return 1
}

# Step 1: Start MongoDB
if [ "$START_MONGO" = true ]; then
    echo -e "${YELLOW}[1/3] Starting MongoDB...${NC}"

    if pgrep -x "mongod" > /dev/null; then
        echo -e "${GREEN}✓ MongoDB is already running${NC}"
        pgrep -x "mongod" | head -1 > "$MONGO_PID_FILE"
    else
        ./start_mongodb.sh
        if [ $? -eq 0 ]; then
            pgrep -x "mongod" | head -1 > "$MONGO_PID_FILE"
            echo -e "${GREEN}✓ MongoDB started successfully${NC}"
        else
            echo -e "${RED}✗ MongoDB failed to start${NC}"
            echo -e "${YELLOW}  System will continue with PostgreSQL only${NC}"
        fi
    fi
    echo ""
fi

# Step 2: Start Django Backend
if [ "$START_BACKEND" = true ]; then
    echo -e "${YELLOW}[2/3] Starting Django Backend...${NC}"

    if is_running "$BACKEND_PID_FILE"; then
        echo -e "${GREEN}✓ Backend is already running (PID: $(cat $BACKEND_PID_FILE))${NC}"
    else
        cd "$SCRIPT_DIR/backend"

        # Check if venv exists
        if [ ! -d "venv" ]; then
            echo -e "${RED}✗ Virtual environment not found!${NC}"
            echo "  Please run: cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements_minimal.txt"
            exit 1
        fi

        # Start backend in background
        nohup ./venv/bin/python manage.py runserver 0.0.0.0:8000 > "$SCRIPT_DIR/backend.log" 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > "$BACKEND_PID_FILE"

        # Wait and verify
        sleep 3
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend started successfully (PID: $BACKEND_PID)${NC}"
            echo -e "  ${BLUE}http://localhost:8000${NC}"
        else
            echo -e "${RED}✗ Backend failed to start${NC}"
            echo "  Check logs: tail -f $SCRIPT_DIR/backend.log"
            rm -f "$BACKEND_PID_FILE"
            exit 1
        fi

        cd "$SCRIPT_DIR"
    fi
    echo ""
fi

# Step 3: Start Frontend
if [ "$START_FRONTEND" = true ]; then
    echo -e "${YELLOW}[3/3] Starting Frontend...${NC}"

    if is_running "$FRONTEND_PID_FILE"; then
        echo -e "${GREEN}✓ Frontend is already running (PID: $(cat $FRONTEND_PID_FILE))${NC}"
    else
        cd "$SCRIPT_DIR/frontend"

        if [ ! -f "index.html" ]; then
            echo -e "${RED}✗ Frontend files not found!${NC}"
            exit 1
        fi

        # Start frontend in background
        nohup python3 -m http.server 3000 > "$SCRIPT_DIR/frontend.log" 2>&1 &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > "$FRONTEND_PID_FILE"

        # Wait and verify
        sleep 2
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
            echo -e "  ${BLUE}http://localhost:3000${NC}"
        else
            echo -e "${RED}✗ Frontend failed to start${NC}"
            echo "  Check logs: tail -f $SCRIPT_DIR/frontend.log"
            rm -f "$FRONTEND_PID_FILE"
            exit 1
        fi

        cd "$SCRIPT_DIR"
    fi
    echo ""
fi

# Summary
echo -e "${GREEN}=========================================="
echo "  Services Started Successfully!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Access the application:${NC}"

if [ "$START_FRONTEND" = true ]; then
    echo -e "  Frontend:  ${GREEN}http://localhost:3000${NC}"
fi
if [ "$START_BACKEND" = true ]; then
    echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
    echo -e "  API:       ${GREEN}http://localhost:8000/api/${NC}"
    echo -e "  Admin:     ${GREEN}http://localhost:8000/admin/${NC}"
fi
if [ "$START_MONGO" = true ]; then
    echo -e "  MongoDB:   ${GREEN}mongodb://localhost:27017${NC}"
fi

echo ""
echo -e "${YELLOW}Management commands:${NC}"
echo "  Check status:  ./status.sh"
echo "  Stop services: ./stop.sh"
echo "  View logs:     tail -f backend.log frontend.log"
echo ""
