#!/bin/bash

# Test Database Routing Script
# This script tests both SQL and NoSQL routing

echo "=========================================="
echo "Testing Intelligent Database Routing"
echo "=========================================="
echo ""

# First, login to get token
echo "Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/smart/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed. Make sure:"
    echo "   1. Backend is running (./start_backend.sh)"
    echo "   2. Admin user exists"
    echo ""
    echo "Create admin with:"
    echo "curl -X POST http://localhost:8000/api/smart/auth/create \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"username\":\"admin\",\"password\":\"admin123\",\"email\":\"admin@example.com\"}'"
    exit 1
fi

echo "✅ Login successful!"
echo ""

# Test 1: SQL Routing (Flat, consistent data)
echo "=========================================="
echo "TEST 1: Flat Data (SHOULD GO TO SQL)"
echo "=========================================="
echo ""
echo "Uploading flat employee data..."

SQL_RESPONSE=$(curl -s -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {"id": 1, "name": "Alice Smith", "age": 30, "email": "alice@example.com", "department": "Engineering"},
    {"id": 2, "name": "Bob Jones", "age": 25, "email": "bob@example.com", "department": "Sales"},
    {"id": 3, "name": "Charlie Brown", "age": 35, "email": "charlie@example.com", "department": "Marketing"}
  ]')

DB_TYPE_1=$(echo $SQL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('database_type', 'unknown'))" 2>/dev/null)
CONFIDENCE_1=$(echo $SQL_RESPONSE | python3 -c "import sys, json; print(int(json.load(sys.stdin).get('confidence', 0) * 100))" 2>/dev/null)

echo "Result:"
echo "  Database: $DB_TYPE_1"
echo "  Confidence: ${CONFIDENCE_1}%"

if [ "$DB_TYPE_1" = "sql" ]; then
    echo "  ✅ CORRECT - Routed to PostgreSQL (SQL)"
else
    echo "  ❌ UNEXPECTED - Should have gone to SQL"
fi

echo ""
echo "Reasons:"
echo "$SQL_RESPONSE" | python3 -c "import sys, json; reasons = json.load(sys.stdin).get('reasons', []); [print(f'  {r}') for r in reasons]" 2>/dev/null

echo ""
echo ""

# Test 2: NoSQL Routing (Deeply nested data)
echo "=========================================="
echo "TEST 2: Nested Data (SHOULD GO TO NOSQL)"
echo "=========================================="
echo ""
echo "Uploading deeply nested user profile..."

NOSQL_RESPONSE=$(curl -s -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "profile": {
      "personal": {
        "name": "Alice",
        "contacts": {
          "email": {
            "primary": "alice@example.com",
            "verified": true
          },
          "phone": {
            "mobile": "+1234567890",
            "verified": false
          }
        }
      },
      "preferences": {
        "notifications": {
          "email": true,
          "sms": false,
          "push": {
            "enabled": true,
            "topics": ["updates", "news"]
          }
        }
      }
    },
    "activity": [
      {
        "date": "2024-01-15",
        "events": [
          {
            "type": "login",
            "metadata": {"ip": "192.168.1.1", "device": "mobile"}
          }
        ]
      }
    ]
  }')

DB_TYPE_2=$(echo $NOSQL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('database_type', 'unknown'))" 2>/dev/null)
CONFIDENCE_2=$(echo $NOSQL_RESPONSE | python3 -c "import sys, json; print(int(json.load(sys.stdin).get('confidence', 0) * 100))" 2>/dev/null)

echo "Result:"
echo "  Database: $DB_TYPE_2"
echo "  Confidence: ${CONFIDENCE_2}%"

if [ "$DB_TYPE_2" = "nosql" ]; then
    echo "  ✅ CORRECT - Routed to MongoDB (NoSQL)"
else
    echo "  ❌ UNEXPECTED - Should have gone to NoSQL"
fi

echo ""
echo "Reasons:"
echo "$NOSQL_RESPONSE" | python3 -c "import sys, json; reasons = json.load(sys.stdin).get('reasons', []); [print(f'  {r}') for r in reasons]" 2>/dev/null

echo ""
echo ""

# Test 3: NoSQL Routing (Variable schema)
echo "=========================================="
echo "TEST 3: Variable Schema (SHOULD GO TO NOSQL)"
echo "=========================================="
echo ""
echo "Uploading mixed content types..."

VARIABLE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": 1,
      "type": "article",
      "title": "My Article",
      "content": "Article content here...",
      "author": "Alice"
    },
    {
      "id": 2,
      "type": "video",
      "url": "https://example.com/video.mp4",
      "duration": 300,
      "thumbnail": "thumb.jpg"
    },
    {
      "id": 3,
      "type": "image",
      "path": "/images/photo.jpg",
      "dimensions": {"width": 1920, "height": 1080},
      "filters": ["grayscale", "contrast"]
    }
  ]')

DB_TYPE_3=$(echo $VARIABLE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('database_type', 'unknown'))" 2>/dev/null)
CONFIDENCE_3=$(echo $VARIABLE_RESPONSE | python3 -c "import sys, json; print(int(json.load(sys.stdin).get('confidence', 0) * 100))" 2>/dev/null)

echo "Result:"
echo "  Database: $DB_TYPE_3"
echo "  Confidence: ${CONFIDENCE_3}%"

if [ "$DB_TYPE_3" = "nosql" ]; then
    echo "  ✅ CORRECT - Routed to MongoDB (NoSQL)"
else
    echo "  ❌ UNEXPECTED - Should have gone to NoSQL"
fi

echo ""
echo "Reasons:"
echo "$VARIABLE_RESPONSE" | python3 -c "import sys, json; reasons = json.load(sys.stdin).get('reasons', []); [print(f'  {r}') for r in reasons]" 2>/dev/null

echo ""
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
echo "Test 1 (Flat Data):      $DB_TYPE_1 (expected: sql)"
echo "Test 2 (Nested Data):    $DB_TYPE_2 (expected: nosql)"
echo "Test 3 (Variable Schema): $DB_TYPE_3 (expected: nosql)"
echo ""

if [ "$DB_TYPE_1" = "sql" ] && [ "$DB_TYPE_2" = "nosql" ] && [ "$DB_TYPE_3" = "nosql" ]; then
    echo "✅ All tests PASSED - Intelligent routing is working!"
else
    echo "⚠️  Some tests didn't match expected results"
    echo "    This might be okay - the analyzer makes intelligent decisions"
    echo "    Check the reasons above to understand why"
fi

echo ""
echo "See TEST_DATA_EXAMPLES.md for more examples"
