# Schema Retrieval API Guide

## Overview

The Schema Retrieval API allows you to retrieve, filter, and download database schemas that have been generated when uploading JSON data. It supports both structured filtering and natural language queries powered by LLM.

## Features

✅ **Date Range Filtering** - Retrieve schemas from specific time periods
✅ **Database Type Filtering** - Filter by SQL, NoSQL, or all schemas
✅ **Name Pattern Matching** - Search schemas by name patterns
✅ **Tag-based Filtering** - Filter by specific tags
✅ **Natural Language Queries** - Use plain English to query schemas
✅ **LLM-Powered Parsing** - Automatically parse complex queries
✅ **Download & View** - Get schema content directly
✅ **Statistics** - View statistics about your schemas

---

## API Endpoints

### 1. Retrieve Schemas with Filters

**GET** `/api/smart/schemas/retrieve`
**POST** `/api/smart/schemas/retrieve`

Retrieve schemas using various filtering options.

#### Authentication
```bash
Header: Authorization: Bearer <your_token>
```

#### GET Request (Structured Filters)

**Query Parameters:**
- `database_type` - Filter by type: `sql`, `nosql`, or `all` (default: `all`)
- `start_date` - Start date in `YYYY-MM-DD` format
- `end_date` - End date in `YYYY-MM-DD` format
- `name_pattern` - Search pattern for schema names
- `tags` - Comma-separated list of tags
- `limit` - Max results (default: 20, max: 100)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/smart/schemas/retrieve?database_type=sql&start_date=2025-11-01&end_date=2025-11-16" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### POST Request (Natural Language Query)

**Body:**
```json
{
  "query": "show me all SQL schemas from last week"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/smart/schemas/retrieve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find all NoSQL schemas created in November"
  }'
```

#### POST Request (Structured Filters)

**Body:**
```json
{
  "database_type": "sql",
  "date_range": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-16"
  },
  "name_pattern": "user",
  "tags": ["schema", "database"],
  "limit": 20
}
```

#### Response:
```json
{
  "success": true,
  "count": 5,
  "total_available": 15,
  "schemas": [
    {
      "id": 123,
      "filename": "user_data_schema.sql",
      "database_type": "SQL",
      "file_path": "schemas/2025/11/user_data_schema.sql",
      "file_size": 2048,
      "created_at": "2025-11-16T10:30:00",
      "description": "Generated SQL schema for user_data",
      "tags": ["schema", "sql", "database", "generated"],
      "download_url": "/api/smart/schemas/download/123",
      "json_store": {
        "name": "user_data",
        "table_name": "user_data_table",
        "collection_name": null,
        "record_count": 1000,
        "confidence_score": 95
      }
    }
  ],
  "filters_applied": {
    "database_type": "sql",
    "start_date": "2025-11-01",
    "end_date": "2025-11-16",
    "name_pattern": null,
    "tags": null,
    "limit": 20
  },
  "parsed_query": {
    "database_type": "sql",
    "date_range": {
      "start_date": "2025-11-09",
      "end_date": "2025-11-16"
    },
    "limit": 20
  },
  "original_query": "show me all SQL schemas from last week"
}
```

---

### 2. View Schema Content

**GET** `/api/smart/schemas/view/<schema_id>`

View the content of a specific schema without downloading.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/smart/schemas/view/123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "schema_id": 123,
  "filename": "user_data_schema.sql",
  "database_type": "SQL",
  "mime_type": "application/sql",
  "content": "-- SQL Schema for: user_data\n-- Generated: 2025-11-16 10:30:00\n...",
  "created_at": "2025-11-16T10:30:00"
}
```

---

### 3. Download Schema File

**GET** `/api/smart/schemas/download/<schema_id>`

Download a schema file.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/smart/schemas/download/123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o user_data_schema.sql
```

Returns the file with appropriate `Content-Type` and `Content-Disposition` headers.

---

### 4. Get Schema Statistics

**GET** `/api/smart/schemas/stats`

Get statistics about your stored schemas.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/smart/schemas/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_schemas": 25,
    "sql_schemas": 15,
    "nosql_schemas": 10,
    "total_size_bytes": 51200,
    "oldest_schema": "2025-10-01T12:00:00",
    "newest_schema": "2025-11-16T10:30:00"
  }
}
```

---

## Natural Language Query Examples

The LLM-powered query parser can understand various natural language queries:

### Date-based Queries
```
"show me all SQL schemas from last week"
"get schemas created in November"
"find NoSQL schemas from yesterday"
"schemas from the last 30 days"
"show me schemas created in October 2025"
```

### Database Type Queries
```
"get all SQL schemas"
"find NoSQL database schemas"
"show me all MongoDB schemas"
"list PostgreSQL schemas"
```

### Name-based Queries
```
"find schemas with 'user' in the name"
"get schemas containing 'product'"
"schemas related to orders"
```

### Combined Queries
```
"show me SQL schemas with 'customer' from last month"
"find all NoSQL schemas created this week"
"get database schemas for user data from November"
```

---

## Common Use Cases

### 1. Review Recent Schema Changes
```bash
curl -X POST "http://localhost:8000/api/smart/schemas/retrieve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me schemas from the last 7 days"
  }'
```

### 2. Find Schemas for a Specific Dataset
```bash
curl -X GET "http://localhost:8000/api/smart/schemas/retrieve?name_pattern=customer" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Compare SQL vs NoSQL Schemas
```bash
# Get SQL schemas
curl -X GET "http://localhost:8000/api/smart/schemas/retrieve?database_type=sql&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get NoSQL schemas
curl -X GET "http://localhost:8000/api/smart/schemas/retrieve?database_type=nosql&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Audit Schema Generation History
```bash
curl -X GET "http://localhost:8000/api/smart/schemas/retrieve?start_date=2025-10-01&end_date=2025-10-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Download Multiple Schemas
```bash
# First, get the list
SCHEMAS=$(curl -s -X GET "http://localhost:8000/api/smart/schemas/retrieve?database_type=sql" \
  -H "Authorization: Bearer YOUR_TOKEN")

# Extract IDs and download each
echo $SCHEMAS | jq -r '.schemas[].id' | while read SCHEMA_ID; do
  curl -X GET "http://localhost:8000/api/smart/schemas/download/$SCHEMA_ID" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -o "schema_${SCHEMA_ID}.sql"
done
```

---

## Integration Examples

### Python
```python
import requests
import json

BASE_URL = "http://localhost:8000/api/smart"

# Login
auth_response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
token = auth_response.json()['token']
headers = {"Authorization": f"Bearer {token}"}

# Natural language query
query_response = requests.post(
    f"{BASE_URL}/schemas/retrieve",
    headers=headers,
    json={"query": "show me all SQL schemas from last week"}
)
schemas = query_response.json()

print(f"Found {schemas['count']} schemas")
for schema in schemas['schemas']:
    print(f"  - {schema['filename']} ({schema['database_type']})")

# Download a schema
if schemas['schemas']:
    schema_id = schemas['schemas'][0]['id']
    download_response = requests.get(
        f"{BASE_URL}/schemas/download/{schema_id}",
        headers=headers
    )

    with open(f"schema_{schema_id}.sql", 'wb') as f:
        f.write(download_response.content)
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000/api/smart';

async function retrieveSchemas() {
  // Login
  const authResponse = await axios.post(`${BASE_URL}/auth/login`, {
    username: 'admin',
    password: 'admin123'
  });
  const token = authResponse.data.token;
  const headers = { Authorization: `Bearer ${token}` };

  // Natural language query
  const queryResponse = await axios.post(
    `${BASE_URL}/schemas/retrieve`,
    { query: 'find all NoSQL schemas from last month' },
    { headers }
  );

  console.log(`Found ${queryResponse.data.count} schemas`);
  queryResponse.data.schemas.forEach(schema => {
    console.log(`  - ${schema.filename} (${schema.database_type})`);
  });

  // View schema content
  if (queryResponse.data.schemas.length > 0) {
    const schemaId = queryResponse.data.schemas[0].id;
    const viewResponse = await axios.get(
      `${BASE_URL}/schemas/view/${schemaId}`,
      { headers }
    );
    console.log('\nSchema content:');
    console.log(viewResponse.data.content);
  }
}

retrieveSchemas();
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (invalid parameters)
- `401` - Unauthorized (invalid token)
- `404` - Schema not found
- `500` - Internal server error

---

## Testing

Run the comprehensive test suite:

```bash
./test_schema_retrieval.sh
```

This will test:
- ✅ Authentication
- ✅ Schema statistics
- ✅ Retrieving all schemas
- ✅ Filtering by database type
- ✅ Date range filtering
- ✅ Name pattern filtering
- ✅ Natural language queries
- ✅ Structured POST queries
- ✅ Viewing schema content
- ✅ Downloading schemas

---

## Best Practices

1. **Use Natural Language for Complex Queries**
   - The LLM can parse complex date expressions like "last week" or "last month"
   - Easier than manually calculating dates

2. **Use Structured Filters for Programmatic Access**
   - More predictable and faster
   - Better for automated scripts

3. **Set Reasonable Limits**
   - Default limit is 20, max is 100
   - Use pagination for large result sets

4. **Cache Downloaded Schemas**
   - Schemas don't change once created
   - Cache them locally to reduce API calls

5. **Monitor Schema Statistics**
   - Regularly check statistics to understand your schema usage
   - Helps with storage planning

---

## Architecture

### Components

1. **SchemaQueryParser**
   - Uses Ollama LLM to parse natural language queries
   - Converts queries to structured filters
   - Handles date expressions and database type detection

2. **SchemaRetrievalService**
   - Core service for retrieving schemas
   - Applies filters to MediaFile queries
   - Returns formatted results with metadata

3. **API Endpoints**
   - `/schemas/retrieve` - Main retrieval endpoint
   - `/schemas/view/{id}` - View content
   - `/schemas/download/{id}` - Download file
   - `/schemas/stats` - Statistics

### Data Flow

```
User Query
    ↓
Natural Language Parser (LLM)
    ↓
Structured Filters
    ↓
Database Query (MediaFile + JSONDataStore)
    ↓
Format Results
    ↓
JSON Response
```

---

## Troubleshooting

### LLM Query Parsing Fails
- Check that Ollama is running: `curl http://localhost:11434/api/generate`
- Verify the model is available: `ollama list`
- Falls back to default filters if parsing fails

### No Schemas Found
- Check if schemas were actually generated during JSON upload
- Verify date range is correct
- Check database type filter

### Download Fails
- Verify schema ID exists
- Check file permissions on schema files
- Ensure file path is accessible

---

## Future Enhancements

- [ ] Add pagination support for large result sets
- [ ] Support for schema comparison
- [ ] Schema versioning and history
- [ ] Export multiple schemas as ZIP
- [ ] Schema search by content (full-text search)
- [ ] Schema visualization
- [ ] Automatic schema diff when updating data

---

## Related Documentation

- [JSON Upload Guide](./JSON_STORAGE_IMPLEMENTATION.md)
- [Smart Database Routing](./INTELLIGENT_DB_ROUTING.md)
- [API Reference](./API_QUICK_REFERENCE.md)

---

**Need Help?**
Check the test script (`test_schema_retrieval.sh`) for working examples of all endpoints.
