#!/bin/bash

# Complete Startup Script for Intelligent Storage System
# Starts both MongoDB (NoSQL) and Django Backend (with PostgreSQL)

echo "=========================================="
echo "Starting Intelligent Storage System"
echo "=========================================="
echo ""

# Step 1: Start MongoDB
echo "Step 1: Starting MongoDB..."
./start_mongodb.sh

if [ $? -ne 0 ]; then
    echo "❌ MongoDB failed to start"
    echo "The system will still work with PostgreSQL only"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "=========================================="

# Step 2: Start Django Backend
echo "Step 2: Starting Django Backend..."
echo ""

cd backend
./start_backend.sh
