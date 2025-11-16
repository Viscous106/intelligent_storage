# JSON Schema Files - Auto-Saved & Accessible

## Feature Overview

When you upload JSON data, the system now **automatically saves the generated schema** as a file that you can access, download, and use from the File Browser!

### What Gets Saved:
- **SQL Schemas** → Saved as `.sql` files with complete CREATE TABLE statements
- **NoSQL Schemas** → Saved as `.json` files with document structure

## How It Works

### 1. Upload JSON Data
```bash
curl -X POST http://localhost:8000/api/upload/json/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "John Doe",
      "email": "john@example.com",
      "age": 30
    },
    "name": "user_data",
    "user_comment": "User profile information"
  }'
```

### 2. Schema File Automatically Created

**SQL Example** (`employee_data_schema.sql`):
```sql
-- SQL Schema for: employee_data
-- Generated: 2025-11-16 00:27:35
-- Database Type: PostgreSQL
-- Table Name: employee_data

CREATE TABLE IF NOT EXISTS employee_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    age INTEGER,
    role VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Column Definitions:
-- name: VARCHAR(255)
-- email: VARCHAR(255)
-- age: INTEGER
-- role: VARCHAR(255)
```

**NoSQL Example** (JSON format for MongoDB schemas - when complex nested data is detected).

### 3. Access from File Browser

Schema files are saved to:
```
backend/media/schemas/YEAR/MONTH/schema_name.sql
backend/media/schemas/YEAR/MONTH/schema_name.json
```

## Accessing Schema Files

### Method 1: File Browser API

Get all schema files:
```bash
curl "http://localhost:8000/api/media-files/?storage_category=schemas"
```

Get specific schema file:
```bash
curl "http://localhost:8000/api/media-files/11/"
```

Response:
```json
{
  "id": 11,
  "original_name": "employee_data_schema.sql",
  "file_path": "/home/.../backend/media/schemas/2025/11/employee_data_schema.sql",
  "file_size": 444,
  "detected_type": "documents",
  "mime_type": "application/sql",
  "file_extension": ".sql",
  "ai_category": "SQL Schema",
  "ai_subcategory": "Database Schema",
  "ai_tags": ["schema", "sql", "database", "generated"],
  "ai_description": "Generated SQL schema for employee_data",
  "storage_category": "schemas",
  "storage_subcategory": "sql",
  "relative_path": "schemas/2025/11/employee_data_schema.sql"
}
```

### Method 2: Download Schema File

```bash
curl -O "http://localhost:8000/api/download/11/"
```

### Method 3: Preview Schema File

```bash
curl "http://localhost:8000/api/preview/11/"
```

### Method 4: Search for Schemas

Search by name:
```bash
curl "http://localhost:8000/files/api/search/fuzzy/?q=employee"
```

Filter by schema category:
```bash
curl "http://localhost:8000/api/media-files/?storage_category=schemas&storage_subcategory=sql"
```

## Schema File Details

### SQL Schema Files (.sql)

**Includes:**
- Schema name and generation timestamp
- Database type (PostgreSQL)
- Table name
- Complete CREATE TABLE statement
- Column definitions with data types

**Use Cases:**
- Run directly in PostgreSQL
- Share with other developers
- Documentation for your database
- Migration scripts
- Database design reference

### NoSQL Schema Files (.json)

**Includes:**
- Schema name and generation timestamp
- Database type (MongoDB)
- Collection name
- Document structure/fields
- Sample document data

**Use Cases:**
- MongoDB collection planning
- API documentation
- Data modeling reference
- Schema validation

## Response Fields

When you upload JSON, the response includes:
```json
{
  "success": true,
  "doc_id": "14",
  "database_type": "SQL",
  "schema_file_id": 11,  // ← ID of the saved schema file
  "schema": {
    "type": "SQL",
    "table_name": "employee_data",
    "create_statement": "CREATE TABLE ...",
    "columns": { ... }
  }
}
```

Use `schema_file_id` to:
- Download the file
- Preview the file
- Get file metadata
- Share with others

## File Organization

Schema files are organized by:
1. **Category**: `schemas/`
2. **Year**: `schemas/2025/`
3. **Month**: `schemas/2025/11/`
4. **Type**: SQL or NoSQL subcategory
5. **Tags**: `['schema', 'sql'/'nosql', 'database', 'generated']`

This makes them easy to:
- ✅ Find in file browser
- ✅ Filter by type (SQL/NoSQL)
- ✅ Search by name
- ✅ Download individually
- ✅ Track by date

## Example Usage Workflow

### 1. Upload JSON Data
```bash
curl -X POST http://localhost:8000/api/upload/json/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"name": "Alice", "role": "Engineer"},
    "name": "team_members"
  }'
```

**Response**:
```json
{
  "success": true,
  "doc_id": "15",
  "database_type": "SQL",
  "schema_file_id": 12,  // ← Note this ID
  "message": "Data stored in SQL database"
}
```

### 2. Get Schema File Details
```bash
curl "http://localhost:8000/api/media-files/12/"
```

**Response**:
```json
{
  "id": 12,
  "original_name": "team_members_schema.sql",
  "relative_path": "schemas/2025/11/team_members_schema.sql",
  "storage_category": "schemas",
  "ai_description": "Generated SQL schema for team_members"
}
```

### 3. Download Schema File
```bash
curl "http://localhost:8000/api/download/12/" -o team_members_schema.sql
```

### 4. Use the Schema
```bash
# Run in PostgreSQL
psql -U postgres -d mydb -f team_members_schema.sql
```

## Frontend Integration

The schema file ID is returned in the upload response, so the frontend can:

1. **Show Download Button**:
```javascript
if (data.schema_file_id) {
  showButton(`Download Schema`,
    `http://localhost:8000/api/download/${data.schema_file_id}/`);
}
```

2. **Display in File Browser**:
- Schema files appear in the file browser automatically
- Categorized under "Schemas"
- Tagged with database type (SQL/NoSQL)
- Searchable by name

3. **Preview Schema**:
```javascript
fetch(`http://localhost:8000/api/preview/${data.schema_file_id}/`)
  .then(res => res.text())
  .then(schema => displaySchema(schema));
```

## Benefits

✅ **Instant Access** - Schema saved automatically on upload
✅ **File Browser Integration** - Appears in file browser immediately
✅ **Downloadable** - Get .sql or .json files to use anywhere
✅ **Searchable** - Find schemas by name using fuzzy search
✅ **Organized** - Auto-organized by date and type
✅ **Shareable** - Download and share with team members
✅ **Documentation** - Built-in database documentation
✅ **Versioned** - Track schema changes over time
✅ **No Manual Work** - Completely automated

## Schema File Locations

All schema files are stored in:
```
backend/media/schemas/
  └── 2025/
      └── 11/
          ├── employee_data_schema.sql
          ├── product_catalog_schema.sql
          ├── user_profile_test_schema.sql
          └── users_nosql_schema.sql
```

## API Endpoints for Schemas

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/media-files/?storage_category=schemas` | GET | List all schema files |
| `/api/media-files/{id}/` | GET | Get schema file details |
| `/api/download/{id}/` | GET | Download schema file |
| `/api/preview/{id}/` | GET | Preview schema content |
| `/files/api/search/fuzzy/?q=schema` | GET | Search for schemas |

## Testing

### Test SQL Schema Generation:
```bash
curl -X POST http://localhost:8000/api/upload/json/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "product_name": "Widget",
      "price": 29.99,
      "in_stock": true
    },
    "name": "products"
  }'
```

Check response for `schema_file_id`, then:
```bash
curl "http://localhost:8000/api/media-files/{schema_file_id}/"
curl "http://localhost:8000/api/download/{schema_file_id}/" -o schema.sql
cat schema.sql
```

### View All Generated Schemas:
```bash
curl "http://localhost:8000/api/media-files/?storage_category=schemas" | jq
```

### Search for Specific Schema:
```bash
curl "http://localhost:8000/files/api/search/fuzzy/?q=employee"
```

## Notes

- Schema files are linked to their JSONDataStore records
- Each JSON upload creates exactly one schema file
- Schema files inherit the storage category "schemas"
- SQL schemas use `.sql` extension
- NoSQL schemas use `.json` extension
- Files are automatically categorized and tagged
- No manual intervention required

## Summary

Every time you upload JSON data:
1. ✅ System analyzes and chooses SQL or NoSQL
2. ✅ Data is stored in the appropriate database
3. ✅ Schema is automatically generated
4. ✅ Schema is saved as a file (.sql or .json)
5. ✅ File appears in File Browser instantly
6. ✅ You get the schema_file_id to download/preview
7. ✅ Schema is searchable and accessible anytime

**No extra steps needed - it just works!** 🎉
