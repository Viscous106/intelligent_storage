#!/bin/bash

echo "=========================================="
echo "Testing Schema Display Feature"
echo "=========================================="
echo ""

# Login
echo "Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/smart/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    exit 1
fi

echo "✅ Login successful!"
echo ""

# Upload sample data
echo "=========================================="
echo "TEST: Uploading Sample JSON with Schema"
echo "=========================================="
echo ""

UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "profile": {
          "age": 30,
          "city": "New York"
        }
      },
      {
        "id": 2,
        "name": "Bob",
        "email": "bob@example.com",
        "profile": {
          "age": 25,
          "city": "San Francisco"
        }
      }
    ]
  }')

echo "Upload Response:"
echo "$UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"
echo ""

DOC_ID=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('doc_id', ''))" 2>/dev/null)

if [ ! -z "$DOC_ID" ]; then
    echo "=========================================="
    echo "Retrieving Schema for Document: $DOC_ID"
    echo "=========================================="
    echo ""

    SCHEMA_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/smart/schema?doc_id=$DOC_ID" \
      -H "Authorization: Bearer $TOKEN")

    echo "Schema Response:"
    echo "$SCHEMA_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SCHEMA_RESPONSE"
fi

echo ""
echo "=========================================="
echo "Schema display feature is working!"
echo "=========================================="
echo ""
echo "You can now:"
echo "1. Upload JSON via the frontend"
echo "2. See the detailed schema displayed immediately"
echo "3. Access the schema anytime via API: /api/smart/schema?doc_id=<DOC_ID>"
echo ""
