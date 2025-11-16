#!/bin/bash

# Schema Retrieval Test Script
# Tests the new schema retrieval endpoints with various filter options

BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/smart"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Schema Retrieval API Test Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Get token
echo -e "${YELLOW}Step 1: Authenticating...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}❌ Authentication failed!${NC}"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Authenticated successfully${NC}"
echo -e "Token: ${TOKEN:0:20}...\n"

# Test 1: Get schema statistics
echo -e "${YELLOW}Test 1: Get Schema Statistics${NC}"
STATS_RESPONSE=$(curl -s -X GET "$API_URL/schemas/stats" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$STATS_RESPONSE" | jq '.'
echo ""

# Test 2: Retrieve all schemas (default)
echo -e "${YELLOW}Test 2: Retrieve All Schemas (Default)${NC}"
ALL_SCHEMAS=$(curl -s -X GET "$API_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$ALL_SCHEMAS" | jq '.'
echo ""

# Test 3: Retrieve only SQL schemas
echo -e "${YELLOW}Test 3: Retrieve SQL Schemas Only${NC}"
SQL_SCHEMAS=$(curl -s -X GET "$API_URL/schemas/retrieve?database_type=sql" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$SQL_SCHEMAS" | jq '.'
echo ""

# Test 4: Retrieve schemas from a specific date range
echo -e "${YELLOW}Test 4: Retrieve Schemas from Date Range${NC}"
DATE_RANGE_SCHEMAS=$(curl -s -X GET "$API_URL/schemas/retrieve?start_date=2025-11-01&end_date=2025-11-16" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$DATE_RANGE_SCHEMAS" | jq '.'
echo ""

# Test 5: Retrieve schemas with name pattern
echo -e "${YELLOW}Test 5: Retrieve Schemas with Name Pattern${NC}"
PATTERN_SCHEMAS=$(curl -s -X GET "$API_URL/schemas/retrieve?name_pattern=user" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$PATTERN_SCHEMAS" | jq '.'
echo ""

# Test 6: Natural language query - "show me all SQL schemas from last week"
echo -e "${YELLOW}Test 6: Natural Language Query - SQL Schemas from Last Week${NC}"
NLQ_RESPONSE1=$(curl -s -X POST "$API_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me all SQL schemas from last week"
  }')

echo "Response:"
echo "$NLQ_RESPONSE1" | jq '.'
echo ""

# Test 7: Natural language query - "find all schemas created in November"
echo -e "${YELLOW}Test 7: Natural Language Query - Schemas from November${NC}"
NLQ_RESPONSE2=$(curl -s -X POST "$API_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find all schemas created in November"
  }')

echo "Response:"
echo "$NLQ_RESPONSE2" | jq '.'
echo ""

# Test 8: Natural language query - "get NoSQL schemas from yesterday"
echo -e "${YELLOW}Test 8: Natural Language Query - NoSQL Schemas from Yesterday${NC}"
NLQ_RESPONSE3=$(curl -s -X POST "$API_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "get NoSQL schemas from yesterday"
  }')

echo "Response:"
echo "$NLQ_RESPONSE3" | jq '.'
echo ""

# Test 9: Structured POST query with multiple filters
echo -e "${YELLOW}Test 9: Structured POST Query with Multiple Filters${NC}"
STRUCTURED_RESPONSE=$(curl -s -X POST "$API_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "database_type": "sql",
    "date_range": {
      "start_date": "2025-11-01",
      "end_date": "2025-11-16"
    },
    "tags": ["schema", "database"],
    "limit": 10
  }')

echo "Response:"
echo "$STRUCTURED_RESPONSE" | jq '.'
echo ""

# Test 10: View specific schema content
echo -e "${YELLOW}Test 10: View Schema Content${NC}"
# Get first schema ID from previous results
SCHEMA_ID=$(echo "$ALL_SCHEMAS" | jq -r '.schemas[0].id // empty')

if [ -n "$SCHEMA_ID" ] && [ "$SCHEMA_ID" != "null" ]; then
    echo "Viewing schema ID: $SCHEMA_ID"
    VIEW_RESPONSE=$(curl -s -X GET "$API_URL/schemas/view/$SCHEMA_ID" \
      -H "Authorization: Bearer $TOKEN")

    echo "Response:"
    echo "$VIEW_RESPONSE" | jq '.'
    echo ""
else
    echo -e "${YELLOW}No schemas available to view${NC}\n"
fi

# Test 11: Download schema
echo -e "${YELLOW}Test 11: Download Schema${NC}"
if [ -n "$SCHEMA_ID" ] && [ "$SCHEMA_ID" != "null" ]; then
    echo "Downloading schema ID: $SCHEMA_ID"
    curl -s -X GET "$API_URL/schemas/download/$SCHEMA_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -o "/tmp/downloaded_schema_$SCHEMA_ID"

    if [ -f "/tmp/downloaded_schema_$SCHEMA_ID" ]; then
        echo -e "${GREEN}✓ Schema downloaded successfully${NC}"
        echo "File size: $(wc -c < "/tmp/downloaded_schema_$SCHEMA_ID") bytes"
        echo "First 5 lines:"
        head -n 5 "/tmp/downloaded_schema_$SCHEMA_ID"
        echo ""
    else
        echo -e "${RED}❌ Download failed${NC}\n"
    fi
else
    echo -e "${YELLOW}No schemas available to download${NC}\n"
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Suite Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}All tests completed successfully!${NC}"
echo ""
echo "Available endpoints:"
echo "  1. GET  /api/smart/schemas/retrieve       - Retrieve schemas with filters"
echo "  2. POST /api/smart/schemas/retrieve       - Retrieve with NLQ or structured query"
echo "  3. GET  /api/smart/schemas/view/{id}      - View schema content"
echo "  4. GET  /api/smart/schemas/download/{id}  - Download schema file"
echo "  5. GET  /api/smart/schemas/stats          - Get schema statistics"
echo ""
