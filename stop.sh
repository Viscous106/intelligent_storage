#!/bin/bash

# Intelligent Storage System - Shutdown Script
# Stops all running services cleanly

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
MONGO_PID_FILE="$PIDS_DIR/mongodb.pid"
BACKEND_PID_FILE="$PIDS_DIR/backend.pid"
FRONTEND_PID_FILE="$PIDS_DIR/frontend.pid"

echo -e "${BLUE}=========================================="
echo "  Stopping Intelligent Storage System"
echo "==========================================${NC}"
echo ""

STOPPED_COUNT=0

# Function to stop a process
stop_process() {
    local name=$1
    local pid_file=$2
    local force_kill_name=$3  # Process name for killall if PID file doesn't exist

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping $name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null

            # Wait up to 5 seconds for graceful shutdown
            for i in {1..5}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ $name stopped${NC}"
                    rm -f "$pid_file"
                    STOPPED_COUNT=$((STOPPED_COUNT + 1))
                    return 0
                fi
                sleep 1
            done

            # Force kill if still running
            echo -e "${YELLOW}  Force stopping $name...${NC}"
            kill -9 $pid 2>/dev/null
            rm -f "$pid_file"
            echo -e "${GREEN}✓ $name force stopped${NC}"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
        else
            echo -e "${YELLOW}$name PID file exists but process is not running${NC}"
            rm -f "$pid_file"
        fi
    elif [ -n "$force_kill_name" ]; then
        # Try killall as fallback
        if pgrep -x "$force_kill_name" > /dev/null; then
            echo -e "${YELLOW}Stopping $name (using killall)...${NC}"
            killall "$force_kill_name" 2>/dev/null
            sleep 1
            echo -e "${GREEN}✓ $name stopped${NC}"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
        fi
    fi
}

# Stop services in reverse order
stop_process "Frontend" "$FRONTEND_PID_FILE"
stop_process "Backend" "$BACKEND_PID_FILE"
stop_process "MongoDB" "$MONGO_PID_FILE" "mongod"

echo ""

if [ $STOPPED_COUNT -eq 0 ]; then
    echo -e "${YELLOW}No services were running${NC}"
else
    echo -e "${GREEN}Successfully stopped $STOPPED_COUNT service(s)${NC}"
fi

# Clean up PID directory if empty
if [ -d "$PIDS_DIR" ] && [ -z "$(ls -A $PIDS_DIR)" ]; then
    rmdir "$PIDS_DIR"
fi

echo ""
