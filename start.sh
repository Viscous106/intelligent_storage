#!/bin/bash
# ============================================================================
# Intelligent Storage System - Quick Start Script (Linux/Mac)
# ============================================================================
# This script starts the entire application using Docker
# Works on: Linux, macOS, WSL2
# ============================================================================

set -e

echo "================================================"
echo "  Intelligent Storage - Docker Quick Start"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo -e "${YELLOW}  Install Docker from: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

# Check if Docker Compose is installed and set the command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo -e "${YELLOW}  Install Docker Compose from: https://docs.docker.com/compose/install/${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"
echo ""

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo -e "${YELLOW}  Start Docker Desktop or run: sudo systemctl start docker${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker daemon is running${NC}"
echo ""

# Stop and remove existing containers if -f flag is provided
if [ "$1" == "-f" ] || [ "$1" == "--force" ]; then
    echo -e "${YELLOW}Stopping and removing existing containers...${NC}"
    $DOCKER_COMPOSE down -v
    echo -e "${GREEN}✓ Cleaned up existing containers${NC}"
    echo ""
fi

# Build and start containers
echo -e "${CYAN}Building Docker images...${NC}"
echo -e "${YELLOW}This may take a few minutes on first run...${NC}"
echo ""

$DOCKER_COMPOSE build

echo ""
echo -e "${CYAN}Starting all services...${NC}"
echo ""

$DOCKER_COMPOSE up -d

echo ""
echo -e "${GREEN}✓ All services started!${NC}"
echo ""

# Wait for services to be ready
echo -e "${CYAN}Waiting for services to be ready...${NC}"
sleep 5

# Check service health
echo ""
echo -e "${CYAN}Service Status:${NC}"
$DOCKER_COMPOSE ps

echo ""
echo "================================================"
echo -e "${GREEN}  🚀 Application is ready!${NC}"
echo "================================================"
echo ""
echo -e "${CYAN}Access the application:${NC}"
echo -e "  🌐 File Browser:  ${GREEN}http://localhost:8000/files/browse/${NC}"
echo -e "  🔧 Admin Panel:   ${GREEN}http://localhost:8000/admin/${NC}"
echo -e "  📡 API Docs:      ${GREEN}http://localhost:8000/api/${NC}"
echo -e "  💾 Health Check:  ${GREEN}http://localhost:8000/api/health/${NC}"
echo ""
echo -e "${CYAN}Useful commands:${NC}"
echo -e "  View logs:        ${YELLOW}$DOCKER_COMPOSE logs -f${NC}"
echo -e "  View backend:     ${YELLOW}$DOCKER_COMPOSE logs -f backend${NC}"
echo -e "  Stop services:    ${YELLOW}$DOCKER_COMPOSE stop${NC}"
echo -e "  Restart:          ${YELLOW}$DOCKER_COMPOSE restart${NC}"
echo -e "  Remove all:       ${YELLOW}$DOCKER_COMPOSE down -v${NC}"
echo ""
echo -e "${YELLOW}Note: First run will download Ollama models (3-5GB).${NC}"
echo -e "${YELLOW}This happens automatically in the background.${NC}"
echo ""
