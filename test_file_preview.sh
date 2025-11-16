#!/bin/bash

# File Preview Test Script
# Tests the enhanced preview functionality for various file formats

BASE_URL="http://localhost:8000/api/file_browser"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}File Preview Test Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Create test files
echo -e "${YELLOW}Step 1: Creating test files...${NC}"

# Create test directory
mkdir -p /tmp/preview_test

# Create SQL file
cat > /tmp/preview_test/test_schema.sql << 'EOF'
-- Test SQL Schema
-- Generated for testing preview functionality

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

INSERT INTO users (username, email) VALUES
    ('john_doe', 'john@example.com'),
    ('jane_smith', 'jane@example.com');
EOF

# Create CSV file
cat > /tmp/preview_test/test_data.csv << 'EOF'
id,name,age,department,salary
1,John Doe,30,Engineering,75000
2,Jane Smith,28,Marketing,65000
3,Bob Johnson,35,Sales,70000
4,Alice Williams,32,Engineering,80000
5,Charlie Brown,29,HR,60000
EOF

# Create JSON file
cat > /tmp/preview_test/test_config.json << 'EOF'
{
  "app_name": "Intelligent Storage",
  "version": "1.0.0",
  "database": {
    "postgresql": {
      "host": "localhost",
      "port": 5432
    },
    "mongodb": {
      "host": "localhost",
      "port": 27017
    }
  },
  "features": ["file_browser", "schema_retrieval", "preview"]
}
EOF

# Create Python file
cat > /tmp/preview_test/test_script.py << 'EOF'
#!/usr/bin/env python3
"""
Test Python Script
Demonstrates code preview functionality
"""

def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    for i in range(10):
        print(f"fib({i}) = {fibonacci(i)}")
EOF

# Create text file
cat > /tmp/preview_test/README.txt << 'EOF'
# Test README
This is a test file to demonstrate text file preview.

Features:
- Line 1: Basic text
- Line 2: Multiple lines
- Line 3: Preview support

EOF

echo -e "${GREEN}✓ Test files created${NC}\n"

# Upload test files using the file upload endpoint
echo -e "${YELLOW}Step 2: Uploading test files...${NC}"

# Get auth token first (using smart auth)
echo "Getting auth token..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/smart/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}❌ Authentication failed!${NC}"
    echo "Please make sure the backend is running and credentials are correct"
    exit 1
fi

echo -e "${GREEN}✓ Authenticated${NC}"

# Upload files and get their IDs
echo "Uploading SQL file..."
SQL_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/storage/upload/file/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/preview_test/test_schema.sql")
SQL_ID=$(echo $SQL_RESPONSE | jq -r '.id // empty')

echo "Uploading CSV file..."
CSV_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/storage/upload/file/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/preview_test/test_data.csv")
CSV_ID=$(echo $CSV_RESPONSE | jq -r '.id // empty')

echo "Uploading JSON file..."
JSON_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/storage/upload/file/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/preview_test/test_config.json")
JSON_ID=$(echo $JSON_RESPONSE | jq -r '.id // empty')

echo "Uploading Python file..."
PY_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/storage/upload/file/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/preview_test/test_script.py")
PY_ID=$(echo $PY_RESPONSE | jq -r '.id // empty')

echo "Uploading text file..."
TXT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/storage/upload/file/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/preview_test/README.txt")
TXT_ID=$(echo $TXT_RESPONSE | jq -r '.id // empty')

echo -e "${GREEN}✓ Files uploaded${NC}\n"

# Test previews
echo -e "${YELLOW}Step 3: Testing Preview Functionality${NC}\n"

# Test SQL Preview
if [ -n "$SQL_ID" ] && [ "$SQL_ID" != "null" ]; then
    echo -e "${BLUE}Test 1: SQL File Preview${NC}"
    curl -s "$BASE_URL/api/preview/$SQL_ID/" | jq '.'
    echo ""
else
    echo -e "${YELLOW}No SQL file ID available${NC}\n"
fi

# Test CSV Preview
if [ -n "$CSV_ID" ] && [ "$CSV_ID" != "null" ]; then
    echo -e "${BLUE}Test 2: CSV File Preview${NC}"
    curl -s "$BASE_URL/api/preview/$CSV_ID/" | jq '.csv_data'
    echo ""
else
    echo -e "${YELLOW}No CSV file ID available${NC}\n"
fi

# Test JSON Preview
if [ -n "$JSON_ID" ] && [ "$JSON_ID" != "null" ]; then
    echo -e "${BLUE}Test 3: JSON File Preview${NC}"
    curl -s "$BASE_URL/api/preview/$JSON_ID/" | jq '.json_data'
    echo ""
else
    echo -e "${YELLOW}No JSON file ID available${NC}\n"
fi

# Test Python Preview
if [ -n "$PY_ID" ] && [ "$PY_ID" != "null" ]; then
    echo -e "${BLUE}Test 4: Python File Preview${NC}"
    PREVIEW=$(curl -s "$BASE_URL/api/preview/$PY_ID/")
    echo "$PREVIEW" | jq '{filename, language, lines, can_preview}'
    echo ""
fi

# Test Text Preview
if [ -n "$TXT_ID" ] && [ "$TXT_ID" != "null" ]; then
    echo -e "${BLUE}Test 5: Text File Preview${NC}"
    curl -s "$BASE_URL/api/preview/$TXT_ID/" | jq '{filename, preview_type, lines, can_preview}'
    echo ""
fi

# Test browsing files with preview URLs
echo -e "${BLUE}Test 6: Browse Files${NC}"
curl -s "$BASE_URL/api/browse/?category=code" | jq '.'
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Suite Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}Preview API Endpoints:${NC}"
echo "  • GET /api/file_browser/api/preview/{file_id}/      - Get preview data"
echo "  • GET /api/file_browser/api/preview/content/{file_id}/ - Stream file content"
echo "  • GET /api/file_browser/api/download/{file_id}/     - Download file"
echo ""

echo -e "${GREEN}Supported Formats:${NC}"
echo "  ✓ SQL files (.sql)        - Syntax-highlighted code preview"
echo "  ✓ CSV files (.csv)        - Table preview with parsed data"
echo "  ✓ JSON files (.json)      - Formatted JSON with syntax highlighting"
echo "  ✓ Python files (.py)      - Syntax-highlighted code preview"
echo "  ✓ Text files (.txt, .md)  - Plain text preview"
echo "  ✓ Images (.jpg, .png)     - Image display"
echo "  ✓ Videos (.mp4, .webm)    - Video player"
echo "  ✓ Audio (.mp3, .wav)      - Audio player"
echo "  ✓ PDFs (.pdf)             - PDF viewer"
echo ""

# Cleanup
echo -e "${YELLOW}Cleaning up test files...${NC}"
rm -rf /tmp/preview_test
echo -e "${GREEN}✓ Cleanup complete${NC}"
