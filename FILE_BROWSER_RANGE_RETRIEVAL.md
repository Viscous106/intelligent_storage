# File Browser & Range-Based Retrieval

## Overview

The Intelligent Storage System now includes a comprehensive file browser with range-based data retrieval, allowing users to:
- Browse all their stored JSON documents
- View document metadata and schema information
- Retrieve specific ranges/intervals of data
- Download full documents or selected ranges

## Features

### 1. **File Browser**
- Visual grid of all your JSON documents
- Shows database type (SQL/NoSQL), creation date, and schema info
- One-click access to any document
- Beautiful card-based UI with hover effects

### 2. **Range Selection**
- Select exact data intervals (offset + limit)
- Perfect for large datasets - retrieve only what you need
- Real-time stats showing returned vs. total count
- "Has More" indicator for pagination

### 3. **Download Options**
- Download selected range as JSON file
- Download full document
- Properly formatted JSON with indentation

## How to Use

### Step 1: Browse Your Documents

1. Navigate to the "My JSON Documents" section
2. Click "Load My Documents"
3. View all your documents in a beautiful grid layout

Each document card shows:
- **Database Type Badge**: SQL or NoSQL
- **Creation Date**: When it was uploaded
- **Document ID**: Unique identifier
- **Schema Info**: Number of fields and nesting depth

### Step 2: Select a Document

Click on any document card or "View →" button to open the document viewer.

### Step 3: Select Your Range

In the document viewer:
1. **Start Index (Offset)**: Where to start (0 = first item)
2. **Number of Items (Limit)**: How many items to retrieve
3. Click "Retrieve Range"

**Examples**:
- Get first 10 items: `offset=0, limit=10`
- Get next 10 items: `offset=10, limit=10`
- Get items 50-100: `offset=50, limit=50`

### Step 4: View and Download

The retrieved data is displayed with:
- **Range Info**: Offset, limit, and count statistics
- **Data Preview**: Formatted JSON view
- **Download Options**:
  - Download just this range
  - Download full document

## API Endpoints

### List Documents
```bash
GET /api/smart/list/json
Headers: Authorization: Bearer <token>
```

**Response**:
```json
{
  "documents": [
    {
      "doc_id": "doc_20251115211708_630a1e7045f3",
      "database_type": "nosql",
      "created_at": "2025-11-15T21:17:08.816000",
      "metadata": {
        "schema_info": {
          "estimated_objects": 5,
          "max_nesting_depth": 4
        }
      }
    }
  ]
}
```

### Retrieve with Range
```bash
GET /api/smart/retrieve/json/<doc_id>/range?offset=0&limit=10
Headers: Authorization: Bearer <token>
```

**Query Parameters**:
- `offset` (optional): Starting index, default 0
- `limit` (optional): Number of items, default all
- `fields` (optional): Comma-separated field names to include

**Response**:
```json
{
  "success": true,
  "doc_id": "doc_xxx",
  "data": [...],  // Your data range
  "range_info": {
    "offset": 0,
    "limit": 10,
    "returned_count": 10,
    "total_count": 100,
    "has_more": true
  },
  "database_type": "sql",
  "timestamp": "2025-11-15T21:17:08.816000"
}
```

### Get Document Schema
```bash
GET /api/smart/schema?doc_id=<doc_id>
Headers: Authorization: Bearer <token>
```

**Response**:
```json
{
  "success": true,
  "doc_id": "doc_xxx",
  "schema_info": {
    "fields": {
      "id": { "type": "integer", "sample": "1" },
      "name": { "type": "string", "sample": "Alice" },
      "profile": {
        "type": "object",
        "fields": {
          "age": { "type": "integer", "sample": "30" }
        }
      }
    }
  },
  "database_type": "nosql",
  "metrics": {
    "max_depth": 4,
    "unique_fields": 7
  }
}
```

## Use Cases

### 1. Large Dataset Pagination
```javascript
// Get first page
fetch('/api/smart/retrieve/json/doc_xxx/range?offset=0&limit=20')

// Get second page
fetch('/api/smart/retrieve/json/doc_xxx/range?offset=20&limit=20')

// Get third page
fetch('/api/smart/retrieve/json/doc_xxx/range?offset=40&limit=20')
```

### 2. Sampling Large Data
```javascript
// Get first 100 items for preview
fetch('/api/smart/retrieve/json/doc_xxx/range?offset=0&limit=100')
```

### 3. Field Filtering (Objects Only)
```bash
# Get only specific fields
GET /api/smart/retrieve/json/doc_xxx/range?fields=name,email,age
```

### 4. Data Export
```bash
# Export range 1000-2000 for analysis
GET /api/smart/retrieve/json/doc_xxx/range?offset=1000&limit=1000
# Download the JSON and use in your tools
```

## Frontend Implementation

### HTML Structure
```html
<!-- File Browser Section -->
<section id="browser" class="section">
    <!-- Load button -->
    <button id="loadDocumentsBtn">Load My Documents</button>

    <!-- Documents grid -->
    <div id="documentsList">
        <div id="documentsGrid"></div>
    </div>

    <!-- Document viewer with range selection -->
    <div id="documentViewer">
        <input id="rangeOffset" type="number">
        <input id="rangeLimit" type="number">
        <button onclick="fetchDocumentRange()">Retrieve Range</button>
        <div id="viewerContent"></div>
    </div>
</section>
```

### JavaScript Functions
- `displayDocuments(documents)` - Show document grid
- `openDocumentViewer(docId)` - Open document viewer
- `fetchDocumentRange()` - Retrieve data range
- `displayRangeData(data)` - Display retrieved data
- `downloadJSON(filename, data)` - Download range
- `downloadFullDocument(docId)` - Download full doc

## Benefits

### For Small Datasets (< 1000 records)
- Quick preview of data structure
- Easy access to all records
- Simple download for local processing

### For Medium Datasets (1000 - 100,000 records)
- Pagination support for browsing
- Retrieve only needed ranges
- Reduced bandwidth usage
- Faster load times

### For Large Datasets (> 100,000 records)
- Essential for performance
- Prevents browser memory issues
- Allows targeted data extraction
- Supports data sampling and analysis

## Performance Characteristics

### SQL (PostgreSQL)
- **Range Query**: Uses `LIMIT` and `OFFSET` clauses
- **Performance**: Excellent for first pages, degrades slightly for high offsets
- **Best For**: Structured data with consistent schema

### NoSQL (MongoDB)
- **Range Query**: Uses `skip()` and `limit()` methods
- **Performance**: Fast for all ranges with proper indexing
- **Best For**: Flexible schemas and nested data

## Examples

### Example 1: Customer Data Analysis
```bash
# Upload 50,000 customer records
POST /api/smart/upload/json
Body: [{"id": 1, "name": "Alice", ...}, ...]

# Browse and find your doc_id
# Retrieve first 1000 for analysis
GET /api/smart/retrieve/json/doc_xxx/range?offset=0&limit=1000

# Download and analyze in Excel/Python
```

### Example 2: Log File Processing
```bash
# Upload large log file (100,000 entries)
POST /api/smart/upload/json
Body: [{"timestamp": "...", "event": "..."}, ...]

# Get latest 100 logs
GET /api/smart/retrieve/json/doc_xxx/range?offset=99900&limit=100

# Or get middle section for debugging
GET /api/smart/retrieve/json/doc_xxx/range?offset=50000&limit=100
```

### Example 3: Product Catalog
```bash
# Upload 10,000 products
# Browse in pages of 50
GET /api/smart/retrieve/json/doc_xxx/range?offset=0&limit=50    # Page 1
GET /api/smart/retrieve/json/doc_xxx/range?offset=50&limit=50   # Page 2
GET /api/smart/retrieve/json/doc_xxx/range?offset=100&limit=50  # Page 3
```

## Summary

The File Browser & Range Retrieval feature provides:

✅ **User-Friendly Browsing**: Visual file browser with metadata
✅ **Precise Data Access**: Get exactly the data you need
✅ **Performance Optimized**: Works efficiently with large datasets
✅ **Multiple Download Options**: Range or full document
✅ **Schema Visibility**: See your data structure at a glance
✅ **Database Agnostic**: Works with both SQL and NoSQL

**No more downloading entire datasets when you only need a sample!** 🚀
