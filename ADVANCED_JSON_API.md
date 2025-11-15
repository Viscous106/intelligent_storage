# Advanced JSON Storage API - Complete Guide

## Overview

The Enhanced JSON Storage System provides powerful querying, filtering, pagination, search, and aggregation capabilities for efficiently managing and querying large JSON datasets.

---

## Key Features

✅ **Unified Storage** - Single table architecture instead of table-per-document
✅ **Advanced Filtering** - Field-level filtering with operators (`$gt`, `$lt`, `$gte`, `$lte`, `$in`, `$contains`)
✅ **Range Queries** - Query by date ranges, numeric ranges, string ranges
✅ **Pagination** - Both offset-based and cursor-based pagination
✅ **Full-Text Search** - PostgreSQL full-text search with ranking and highlighting
✅ **Aggregations** - Count, sum, avg, min, max with grouping
✅ **Large File Support** - Handles 100MB+ JSON files efficiently
✅ **Dual Database** - Auto-routing to PostgreSQL (SQL) or MongoDB (NoSQL)

---

## Authentication

All endpoints require Bearer token authentication.

### Get Token
```bash
POST /api/smart/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "your_password"
}

# Response
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "admin_id": "admin_123"
}
```

### Use Token
```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 1. Upload JSON Data

### Standard Upload (Auto Database Selection)
```bash
POST /api/smart/upload/json
Authorization: Bearer <token>
Content-Type: application/json

# Upload as JSON payload
{
    "name": "John Doe",
    "age": 30,
    "email": "john@example.com",
    "department": "engineering",
    "salary": 85000,
    "start_date": "2024-01-15"
}

# Or upload an array
[
    {"id": 1, "name": "Alice", "age": 28},
    {"id": 2, "name": "Bob", "age": 35},
    {"id": 3, "name": "Charlie", "age": 42}
]

# Response
{
    "success": true,
    "doc_id": "doc_20250116000000_a1b2c3d4e5f6",
    "database_type": "sql",
    "confidence": 0.85,
    "reasons": [
        "Highly consistent schema (100% field consistency)",
        "Shallow nesting (depth=1) - suitable for relational tables"
    ],
    "storage_info": {
        "database": "postgresql",
        "table_name": "json_documents",
        "indexed_fields": ["data (GIN)", "doc_id", "search_vector"]
    },
    "timestamp": "2025-01-16T00:00:00Z"
}
```

**Note**: The system now stores all JSON data in a unified `json_documents` table, not separate tables per document!

---

## 2. Advanced Query API

### Basic Query with Filters

```bash
POST /api/smart/query/json
Authorization: Bearer <token>
Content-Type: application/json

{
    "filter": {
        "data.age": {"$gt": 25, "$lt": 65},
        "data.department": "engineering",
        "data.status": "active"
    },
    "pagination": {
        "page": 1,
        "page_size": 50
    }
}

# Response
{
    "success": true,
    "data": [
        {
            "doc_id": "doc_123",
            "data": {
                "name": "John Doe",
                "age": 30,
                "department": "engineering",
                "status": "active"
            },
            "created_at": "2025-01-15T12:00:00Z"
        }
        // ... more results
    ],
    "pagination": {
        "total": 500,
        "page": 1,
        "page_size": 50,
        "total_pages": 10,
        "has_next": true,
        "has_prev": false
    },
    "query_time_ms": 45
}
```

### Range Queries

#### Date Range
```json
{
    "filter": {
        "data.created_at": {
            "$gte": "2024-01-01",
            "$lte": "2024-12-31"
        }
    }
}
```

#### Numeric Range
```json
{
    "filter": {
        "data.salary": {
            "$gte": 50000,
            "$lte": 100000
        },
        "data.age": {
            "$between": [25, 65]
        }
    }
}
```

#### Multiple Conditions
```json
{
    "filter": {
        "data.age": {"$gt": 25},
        "data.salary": {"$gte": 60000},
        "data.department": "engineering",
        "data.location": {"$in": ["NYC", "SF", "Austin"]},
        "tags": {"$contains": "employee"}
    }
}
```

### Sorting

```json
{
    "filter": {...},
    "sort": [
        {"field": "data.created_at", "order": "desc"},
        {"field": "data.name", "order": "asc"}
    ]
}
```

### Field Selection (Projection)

```json
{
    "filter": {...},
    "fields": ["data.name", "data.email", "data.age"]
}

# Response includes only selected fields
{
    "data": [
        {
            "doc_id": "doc_123",
            "data.name": "John Doe",
            "data.email": "john@example.com",
            "data.age": 30
        }
    ]
}
```

### Cursor-Based Pagination (Better for Large Datasets)

```json
{
    "filter": {...},
    "pagination": {
        "cursor": null,  // First page
        "limit": 50
    }
}

# Response
{
    "data": [...],
    "pagination": {
        "limit": 50,
        "has_next": true,
        "next_cursor": "eyJsYXN0X2lkIjoxNTB9"
    }
}

# Next page request
{
    "filter": {...},
    "pagination": {
        "cursor": "eyJsYXN0X2lkIjoxNTB9",
        "limit": 50
    }
}
```

---

## 3. Full-Text Search API

### Basic Search

```bash
POST /api/smart/search/json
Authorization: Bearer <token>
Content-Type: application/json

{
    "query": "john smith engineer",
    "limit": 20
}

# Response
{
    "success": true,
    "results": [
        {
            "doc_id": "doc_123",
            "data": {
                "name": "John Smith",
                "title": "Senior Engineer",
                "department": "engineering"
            },
            "score": 0.95,
            "highlight": "...John Smith...Senior Engineer..."
        }
    ],
    "total": 5,
    "query_time_ms": 23
}
```

### Search with Filters

```json
{
    "query": "python developer",
    "filters": {
        "data.department": "engineering",
        "data.experience": {"$gt": 5},
        "tags": {"$contains": "fulltime"}
    },
    "limit": 20
}
```

### Search Across Specific Database

```json
{
    "query": "machine learning",
    "database_type": "sql",  // or "nosql"
    "limit": 20
}
```

---

## 4. Aggregation API

### Count Documents

```bash
POST /api/smart/aggregate/json
Authorization: Bearer <token>
Content-Type: application/json

{
    "operation": "count",
    "filters": {
        "data.status": "active"
    }
}

# Response
{
    "success": true,
    "operation": "count",
    "result": {
        "value": 1250
    }
}
```

### Count with Grouping

```json
{
    "operation": "count",
    "group_by": "data.department"
}

# Response
{
    "result": {
        "engineering": 150,
        "sales": 75,
        "marketing": 50,
        "operations": 25
    }
}
```

### Sum

```json
{
    "operation": "sum",
    "field": "data.salary",
    "group_by": "data.department"
}

# Response
{
    "result": {
        "engineering": 12750000,
        "sales": 5625000,
        "marketing": 3750000
    }
}
```

### Average

```json
{
    "operation": "avg",
    "field": "data.age",
    "group_by": "data.department"
}

# Response
{
    "result": {
        "engineering": 32.5,
        "sales": 38.2,
        "marketing": 29.8
    }
}
```

### Min/Max

```json
{
    "operation": "max",
    "field": "data.salary"
}

# Response
{
    "result": {
        "value": 250000
    }
}
```

---

## 5. Complex Query Examples

### Example 1: Find Active Engineers with High Salary

```json
{
    "filter": {
        "data.department": "engineering",
        "data.status": "active",
        "data.salary": {"$gte": 100000},
        "data.years_experience": {"$gt": 5}
    },
    "sort": [
        {"field": "data.salary", "order": "desc"}
    ],
    "pagination": {
        "page": 1,
        "page_size": 25
    },
    "fields": ["data.name", "data.email", "data.salary", "data.title"]
}
```

### Example 2: Sales Data for Q1 2024

```json
{
    "filter": {
        "data.sale_date": {
            "$gte": "2024-01-01",
            "$lte": "2024-03-31"
        },
        "data.amount": {"$gt": 1000},
        "data.status": "completed"
    },
    "sort": [
        {"field": "data.sale_date", "order": "desc"}
    ]
}
```

### Example 3: Products in Specific Price Range

```json
{
    "filter": {
        "data.category": "electronics",
        "data.price": {
            "$gte": 500,
            "$lte": 2000
        },
        "data.in_stock": true,
        "data.rating": {"$gte": 4.0}
    },
    "sort": [
        {"field": "data.rating", "order": "desc"},
        {"field": "data.price", "order": "asc"}
    ]
}
```

---

## 6. Query Operators Reference

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `$eq` | Equals (default) | `"status": "active"` |
| `$gt` | Greater than | `"age": {"$gt": 25}` |
| `$gte` | Greater than or equal | `"salary": {"$gte": 50000}` |
| `$lt` | Less than | `"age": {"$lt": 65}` |
| `$lte` | Less than or equal | `"price": {"$lte": 1000}` |
| `$between` | Between two values | `"age": {"$between": [25, 65]}` |

### Array/Set Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `$in` | Value in array | `"city": {"$in": ["NYC", "SF"]}` |
| `$contains` | Array/tag contains | `"tags": {"$contains": "featured"}` |

### String Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `$regex` | Regular expression | `"name": {"$regex": "^John"}` |

---

## 7. Performance Best Practices

### Indexing

The unified `json_documents` table includes these indexes:
- `doc_id` - B-tree index for fast lookups
- `admin_id` - B-tree index for filtering by owner
- `created_at` - B-tree index (DESC) for time-based queries
- `tags` - GIN index for array containment queries
- `data` - GIN index (`jsonb_path_ops`) for fast JSON queries
- `search_vector` - GIN index for full-text search

### Query Optimization Tips

1. **Use specific field paths**: `data.user.email` is faster than querying the entire JSON
2. **Use indexes**: Queries on `doc_id`, `admin_id`, `created_at`, and `tags` are indexed
3. **Limit results**: Always use pagination with reasonable `page_size` (50-100)
4. **Use cursor pagination** for large datasets (faster than offset)
5. **Select specific fields**: Use `fields` parameter to reduce data transfer
6. **Cache frequent queries**: Results are automatically cached for 1 hour

### Large Dataset Tips

For datasets with 100,000+ records:
- Use cursor-based pagination instead of offset
- Use field selection to reduce response size
- Add filters to reduce result set
- Consider using aggregations instead of retrieving all data

---

## 8. Error Handling

### Common Errors

**400 Bad Request**
```json
{
    "success": false,
    "error": "Invalid JSON in request body"
}
```

**401 Unauthorized**
```json
{
    "success": false,
    "error": "Authentication required"
}
```

**500 Internal Server Error**
```json
{
    "success": false,
    "error": "Database connection error"
}
```

---

## 9. Migration from Old System

### Old System (Per-Document Tables)
```
Table: json_data_doc_20240115_abc123
Table: json_data_doc_20240115_def456
Table: json_data_doc_20240115_ghi789
... (potentially thousands of tables)
```

### New System (Unified Table)
```
Table: json_documents
  - doc_id: doc_20240115_abc123
  - doc_id: doc_20240115_def456
  - doc_id: doc_20240115_ghi789
  - ... (all documents in one table)
```

### Benefits
✅ Single table is easier to manage
✅ Cross-document queries possible
✅ Better indexing strategy
✅ Simpler database maintenance
✅ Faster queries with proper indexes

---

## 10. Complete API Endpoint Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/smart/auth/login` | POST | Login and get token |
| `/api/smart/auth/create` | POST | Create admin account |
| `/api/smart/upload/json` | POST | Upload JSON data |
| `/api/smart/query/json` | POST | Advanced query with filters |
| `/api/smart/search/json` | POST | Full-text search |
| `/api/smart/aggregate/json` | POST | Aggregation operations |
| `/api/smart/retrieve/json/<doc_id>` | GET | Get single document |
| `/api/smart/list/json` | GET | List documents (simple) |
| `/api/smart/delete/json/<doc_id>` | DELETE | Delete document |
| `/api/smart/stats` | GET | Get statistics |

---

## 11. Testing Examples

### Test Advanced Query
```bash
# Login first
curl -X POST http://localhost:8000/api/smart/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Save the token
export TOKEN="your_token_here"

# Upload test data
curl -X POST http://localhost:8000/api/smart/upload/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {"name": "Alice", "age": 28, "department": "engineering", "salary": 85000},
    {"name": "Bob", "age": 35, "department": "sales", "salary": 75000},
    {"name": "Charlie", "age": 42, "department": "engineering", "salary": 95000}
  ]'

# Query with filters
curl -X POST http://localhost:8000/api/smart/query/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "data.department": "engineering",
      "data.age": {"$gt": 25}
    },
    "sort": [{"field": "data.salary", "order": "desc"}],
    "pagination": {"page": 1, "page_size": 10}
  }'

# Search
curl -X POST http://localhost:8000/api/smart/search/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "alice engineer",
    "limit": 10
  }'

# Aggregate
curl -X POST http://localhost:8000/api/smart/aggregate/json \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "avg",
    "field": "data.salary",
    "group_by": "data.department"
  }'
```

---

## 12. Next Steps

1. **Run Migration**: Apply the database migration to create the unified table
   ```bash
   python manage.py migrate
   ```

2. **Test APIs**: Use the curl examples above to test functionality

3. **Migrate Data**: If you have existing data in old tables, run the migration script

4. **Update Frontend**: Update your frontend to use the new query API

5. **Monitor Performance**: Check query times and optimize indexes as needed

---

## Support

For issues or questions:
- Check Django logs: `tail -f backend/server.log`
- Enable debug mode: Set `DEBUG=True` in settings.py
- Run Django check: `python manage.py check`
- Test database connection: `python manage.py dbshell`

---

**The Enhanced JSON Storage System is now ready to handle large-scale JSON data with advanced querying capabilities!**
