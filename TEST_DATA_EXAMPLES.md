# Test Data Examples - SQL vs NoSQL Routing

## How to Test Database Routing

### Check What Database Was Chosen

When you upload JSON, the response shows:
```json
{
  "database_type": "sql" or "nosql",
  "confidence": 0.85,
  "decision_explanation": {
    "summary": "PostgreSQL..." or "MongoDB...",
    "why_chosen": [...]
  }
}
```

---

## Examples That Go to **NoSQL** (MongoDB)

### 1. Deeply Nested JSON (Depth > 2)
```json
{
  "user": {
    "profile": {
      "personal": {
        "contacts": {
          "email": "user@example.com",
          "phone": "+1234567890"
        }
      }
    }
  }
}
```

**Test**:
```bash
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "profile": {
        "personal": {
          "contacts": {
            "email": "user@example.com",
            "phone": "+1234567890"
          }
        }
      }
    }
  }'
```

**Result**: `"database_type": "nosql"` (Deep nesting depth=5)

---

### 2. Variable Schema
```json
[
  {
    "id": 1,
    "type": "article",
    "title": "Article Title",
    "content": "...",
    "author": "Alice"
  },
  {
    "id": 2,
    "type": "video",
    "url": "https://example.com/video.mp4",
    "duration": 300,
    "thumbnail": "..."
  },
  {
    "id": 3,
    "type": "image",
    "path": "/images/photo.jpg",
    "dimensions": {"width": 1920, "height": 1080},
    "filters": ["grayscale", "contrast"]
  }
]
```

**Test**:
```bash
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {"id": 1, "type": "article", "title": "Title", "content": "..."},
    {"id": 2, "type": "video", "url": "https://...", "duration": 300},
    {"id": 3, "type": "image", "path": "/img.jpg", "dimensions": {"width": 1920}}
  ]'
```

**Result**: `"database_type": "nosql"` (Variable schema - different fields per type)

---

### 3. Nested Arrays
```json
{
  "order_id": 123,
  "items": [
    {
      "product": "Phone",
      "variants": [
        {"color": "black", "storage": "128GB"},
        {"color": "white", "storage": "256GB"}
      ]
    }
  ]
}
```

**Test**:
```bash
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 123,
    "items": [
      {
        "product": "Phone",
        "variants": [
          {"color": "black", "storage": "128GB"},
          {"color": "white", "storage": "256GB"}
        ]
      }
    ]
  }'
```

**Result**: `"database_type": "nosql"` (Nested arrays)

---

### 4. Complex Event Logs
```json
{
  "session_id": "abc123",
  "user_id": 456,
  "events": [
    {
      "type": "page_view",
      "url": "/products",
      "metadata": {
        "referrer": "google",
        "device": "mobile",
        "location": {"lat": 37.7749, "lon": -122.4194}
      }
    },
    {
      "type": "click",
      "element": "buy_button",
      "position": {"x": 150, "y": 200}
    },
    {
      "type": "purchase",
      "items": [{"id": 1, "qty": 2}],
      "total": 59.99
    }
  ]
}
```

**Test**:
```bash
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "events": [
      {
        "type": "page_view",
        "metadata": {"referrer": "google", "device": "mobile"}
      },
      {
        "type": "click",
        "element": "buy_button"
      }
    ]
  }'
```

**Result**: `"database_type": "nosql"` (Variable event types, deep nesting)

---

### 5. Configuration/Settings
```json
{
  "app_name": "MyApp",
  "version": "1.0.0",
  "features": {
    "authentication": {
      "enabled": true,
      "providers": {
        "google": {"client_id": "...", "enabled": true},
        "github": {"client_id": "...", "enabled": false}
      }
    },
    "notifications": {
      "email": {
        "enabled": true,
        "smtp": {"host": "smtp.gmail.com", "port": 587}
      },
      "push": {"enabled": false}
    }
  }
}
```

**Test**:
```bash
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "MyApp",
    "features": {
      "authentication": {
        "providers": {
          "google": {"enabled": true}
        }
      }
    }
  }'
```

**Result**: `"database_type": "nosql"` (Deeply nested configuration)

---

## Examples That Go to **SQL** (PostgreSQL)

### 1. Flat, Consistent Schema
```json
[
  {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
  {"id": 2, "name": "Bob", "age": 25, "email": "bob@example.com"},
  {"id": 3, "name": "Charlie", "age": 35, "email": "charlie@example.com"}
]
```

**Result**: `"database_type": "sql"` (Consistent schema, shallow)

---

### 2. Relational Data with Foreign Keys
```json
[
  {
    "order_id": 1001,
    "customer_id": 5,
    "product_id": 200,
    "quantity": 2,
    "price": 29.99,
    "order_date": "2024-01-15"
  }
]
```

**Result**: `"database_type": "sql"` (Has customer_id, product_id - relational)

---

### 3. Transactional Data
```json
[
  {
    "transaction_id": "TX001",
    "account_id": "ACC123",
    "amount": 150.00,
    "currency": "USD",
    "type": "debit",
    "timestamp": "2024-01-15T14:30:00Z"
  }
]
```

**Result**: `"database_type": "sql"` (Consistent, needs ACID)

---

## Why Your Data Might Be Going to SQL

Your data is likely:
1. **Flat structure** (depth ≤ 2 levels)
2. **Consistent schema** (all records have same fields)
3. **No nested arrays**
4. **Has ID fields** (like user_id, order_id)
5. **Strong typing** (same field always same type)

---

## How to Force NoSQL (For Testing)

If you want to test NoSQL storage, use one of these patterns:

### Option 1: Deep Nesting
```json
{
  "level1": {
    "level2": {
      "level3": {
        "level4": {
          "data": "value"
        }
      }
    }
  }
}
```

### Option 2: Variable Schema
```json
[
  {"id": 1, "field_a": "value"},
  {"id": 2, "field_b": "value"},
  {"id": 3, "field_c": "value"}
]
```

### Option 3: Nested Arrays
```json
{
  "data": [
    {
      "items": [
        {"nested": [1, 2, 3]}
      ]
    }
  ]
}
```

---

## Verify Database Choice

After uploading, check the response:

```json
{
  "success": true,
  "database_type": "nosql",  // ← This tells you where it was stored
  "confidence": 0.88,
  "decision_explanation": {
    "summary": "MongoDB (Document Database) - Best for flexible, nested data",
    "why_chosen": [
      "✓ NoSQL: Deep nesting (depth=5) - optimal for document storage",
      "✓ NoSQL: Complex nested arrays - better suited for document storage",
      ...
    ]
  },
  "storage_info": {
    "database": "mongodb",  // ← Confirms MongoDB was used
    "collection": "json_documents"
  }
}
```

---

## Test Script

Save this as `test_routing.sh`:

```bash
#!/bin/bash

TOKEN="YOUR_TOKEN_HERE"

echo "=== Testing SQL Routing (Flat Data) ==="
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {"id": 1, "name": "Alice", "age": 30},
    {"id": 2, "name": "Bob", "age": 25}
  ]' | jq '.database_type, .confidence, .decision_explanation.summary'

echo ""
echo "=== Testing NoSQL Routing (Nested Data) ==="
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "profile": {
        "personal": {
          "contacts": {
            "email": "test@example.com"
          }
        }
      }
    }
  }' | jq '.database_type, .confidence, .decision_explanation.summary'
```

Run:
```bash
chmod +x test_routing.sh
./test_routing.sh
```

---

## Summary

The analyzer **IS working**:
- ✅ Flat, consistent data → SQL
- ✅ Deep, nested, variable data → NoSQL

If your data is always going to SQL, it's because your data **actually is** better suited for SQL! Check if your JSON has:
- Consistent fields across all records
- Shallow nesting (1-2 levels)
- No nested arrays
- Relational patterns (foreign keys)

Try uploading one of the **NoSQL examples** above to verify the routing works!
