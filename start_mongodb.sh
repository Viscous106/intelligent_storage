#!/bin/bash

# MongoDB Startup Script for Intelligent Storage

echo "=========================================="
echo "Starting MongoDB"
echo "=========================================="
echo ""

# Create MongoDB data directory if it doesn't exist
MONGO_DATA_DIR="./mongodb_data"
MONGO_LOG_DIR="./mongodb_logs"

if [ ! -d "$MONGO_DATA_DIR" ]; then
    echo "Creating MongoDB data directory: $MONGO_DATA_DIR"
    mkdir -p "$MONGO_DATA_DIR"
fi

if [ ! -d "$MONGO_LOG_DIR" ]; then
    echo "Creating MongoDB log directory: $MONGO_LOG_DIR"
    mkdir -p "$MONGO_LOG_DIR"
fi

# Check if MongoDB is already running
if pgrep -x "mongod" > /dev/null; then
    echo "✅ MongoDB is already running"
    echo ""
    echo "MongoDB connection: mongodb://localhost:27017"
    echo "Database: intelligent_storage_nosql"
    echo ""
    echo "To stop: killall mongod"
    exit 0
fi

echo "Starting MongoDB server..."
echo "Data directory: $MONGO_DATA_DIR"
echo "Log directory: $MONGO_LOG_DIR"
echo ""

# Start MongoDB in the background
mongod \
    --dbpath "$MONGO_DATA_DIR" \
    --logpath "$MONGO_LOG_DIR/mongodb.log" \
    --port 27017 \
    --bind_ip 127.0.0.1 \
    --fork \
    2>&1

# Wait a bit for MongoDB to start
sleep 2

# Check if MongoDB started successfully
if pgrep -x "mongod" > /dev/null; then
    echo ""
    echo "✅ MongoDB started successfully!"
    echo ""
    echo "MongoDB is running at: mongodb://localhost:27017"
    echo "Database: intelligent_storage_nosql"
    echo "Data directory: $(pwd)/$MONGO_DATA_DIR"
    echo "Log file: $(pwd)/$MONGO_LOG_DIR/mongodb.log"
    echo ""
    echo "To view logs: tail -f $MONGO_LOG_DIR/mongodb.log"
    echo "To stop: killall mongod"
    echo ""
else
    echo "❌ Failed to start MongoDB"
    echo ""
    echo "Check logs: cat $MONGO_LOG_DIR/mongodb.log"
    exit 1
fi
