#!/bin/bash

# Intelligent Storage System - Status Checker
# Shows the status of all services

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
echo "  Intelligent Storage System Status"
echo "==========================================${NC}"
echo ""

RUNNING_COUNT=0
TOTAL_SERVICES=3

# Function to check service status
check_service() {
    local name=$1
    local pid_file=$2
    local port=$3
    local fallback_process=$4  # Optional fallback process name

    printf "%-15s " "$name:"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}● Running${NC} (PID: $pid, Port: $port)"
            RUNNING_COUNT=$((RUNNING_COUNT + 1))
            return 0
        else
            echo -e "${RED}● Stopped${NC} (stale PID file)"
            rm -f "$pid_file"
            return 1
        fi
    elif [ -n "$fallback_process" ] && pgrep -x "$fallback_process" > /dev/null; then
        local pid=$(pgrep -x "$fallback_process" | head -1)
        echo -e "${GREEN}● Running${NC} (PID: $pid, Port: $port)"
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
        return 0
    else
        echo -e "${RED}● Stopped${NC}"
        return 1
    fi
}

# Check each service
check_service "MongoDB" "$MONGO_PID_FILE" "27017" "mongod"
check_service "Backend" "$BACKEND_PID_FILE" "8000"
check_service "Frontend" "$FRONTEND_PID_FILE" "3000"

echo ""
echo -e "${CYAN}Overall Status:${NC} $RUNNING_COUNT/$TOTAL_SERVICES services running"
echo ""

if [ $RUNNING_COUNT -eq $TOTAL_SERVICES ]; then
    echo -e "${GREEN}✓ All services are running${NC}"
    echo ""
    echo -e "${BLUE}Access the application:${NC}"
    echo -e "  Frontend:  ${GREEN}http://localhost:3000${NC}"
    echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
    echo -e "  API:       ${GREEN}http://localhost:8000/api/${NC}"
    echo -e "  Admin:     ${GREEN}http://localhost:8000/admin/${NC}"
    echo -e "  MongoDB:   ${GREEN}mongodb://localhost:27017${NC}"
elif [ $RUNNING_COUNT -eq 0 ]; then
    echo -e "${RED}✗ No services are running${NC}"
    echo -e "${YELLOW}  Start services with: ./start.sh${NC}"
else
    echo -e "${YELLOW}⚠ Some services are not running${NC}"
    echo -e "${YELLOW}  Restart all services: ./stop.sh && ./start.sh${NC}"
fi

echo ""

# Show log file sizes if they exist
if [ -f "$SCRIPT_DIR/backend.log" ] || [ -f "$SCRIPT_DIR/frontend.log" ]; then
    echo -e "${CYAN}Log Files:${NC}"

    if [ -f "$SCRIPT_DIR/backend.log" ]; then
        local size=$(du -h "$SCRIPT_DIR/backend.log" | cut -f1)
        echo -e "  Backend:   $size (tail -f backend.log)"
    fi

    if [ -f "$SCRIPT_DIR/frontend.log" ]; then
        local size=$(du -h "$SCRIPT_DIR/frontend.log" | cut -f1)
        echo -e "  Frontend:  $size (tail -f frontend.log)"
    fi

    if [ -f "$SCRIPT_DIR/mongodb_logs/mongodb.log" ]; then
        local size=$(du -h "$SCRIPT_DIR/mongodb_logs/mongodb.log" | cut -f1)
        echo -e "  MongoDB:   $size (tail -f mongodb_logs/mongodb.log)"
    fi

    echo ""
fi

# Show management commands
echo -e "${CYAN}Management Commands:${NC}"
echo "  Start:   ./start.sh"
echo "  Stop:    ./stop.sh"
echo "  Restart: ./stop.sh && ./start.sh"
echo ""
