#!/bin/bash

# Quick Start - Schema Retrieval Demo
# This script demonstrates the main features of the schema retrieval API

BASE_URL="http://localhost:8000/api/smart"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Schema Retrieval - Quick Start Demo      ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════╝${NC}\n"

# Step 1: Login
echo -e "${YELLOW}[1/6] Logging in...${NC}"
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}❌ Login failed! Please check credentials.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Logged in successfully${NC}\n"

# Step 2: Get Statistics
echo -e "${YELLOW}[2/6] Getting schema statistics...${NC}"
curl -s -X GET "$BASE_URL/schemas/stats" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
echo ""

# Step 3: Natural Language Query - "show me all SQL schemas"
echo -e "${YELLOW}[3/6] Natural Language Query: 'show me all SQL schemas'${NC}"
curl -s -X POST "$BASE_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "show me all SQL schemas"}' | jq '.schemas[] | {filename, database_type, created_at}'
echo ""

# Step 4: Natural Language Query - "find schemas from last week"
echo -e "${YELLOW}[4/6] Natural Language Query: 'find schemas from last week'${NC}"
curl -s -X POST "$BASE_URL/schemas/retrieve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "find schemas from last week"}' | jq '{count, parsed_query, schemas: .schemas[0:2]}'
echo ""

# Step 5: Structured Query - Get NoSQL schemas
echo -e "${YELLOW}[5/6] Structured Query: Get NoSQL schemas${NC}"
curl -s -X GET "$BASE_URL/schemas/retrieve?database_type=nosql&limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '{count, total_available, schemas: [.schemas[] | {filename, database_type}]}'
echo ""

# Step 6: View a specific schema
echo -e "${YELLOW}[6/6] View a specific schema (if available)${NC}"
SCHEMA_ID=$(curl -s -X GET "$BASE_URL/schemas/retrieve?limit=1" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.schemas[0].id // empty')

if [ -n "$SCHEMA_ID" ] && [ "$SCHEMA_ID" != "null" ]; then
    echo "Viewing schema ID: $SCHEMA_ID"
    curl -s -X GET "$BASE_URL/schemas/view/$SCHEMA_ID" \
      -H "Authorization: Bearer $TOKEN" | jq '{filename, database_type, content: (.content | split("\n")[0:5] | join("\n"))}'
else
    echo -e "${YELLOW}No schemas available yet. Upload some JSON data first!${NC}"
fi
echo ""

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Demo Complete!                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}Try these natural language queries:${NC}"
echo "  • 'show me all SQL schemas from last month'"
echo "  • 'find NoSQL schemas created yesterday'"
echo "  • 'get schemas with user in the name'"
echo "  • 'list all schemas from November'"
echo ""
echo -e "${GREEN}Or use structured filters:${NC}"
echo "  • ?database_type=sql&start_date=2025-11-01&end_date=2025-11-16"
echo "  • ?name_pattern=customer&limit=10"
echo ""
echo -e "See ${BLUE}SCHEMA_RETRIEVAL_GUIDE.md${NC} for complete documentation"
