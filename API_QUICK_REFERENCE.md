# Gemini File Search - API Quick Reference

## Base URL
```
http://localhost:8000/api/
```

---

## 📦 File Search Stores

### List All Stores
```bash
GET /file-search-stores/
```

**Response**:
```json
[
  {
    "store_id": "uuid-here",
    "name": "company_docs",
    "display_name": "Company Documentation",
    "total_files": 45,
    "total_chunks": 1205,
    "storage_used_percentage": 23.5,
    "is_quota_exceeded": false
  }
]
```

### Create Store
```bash
POST /file-search-stores/
Content-Type: application/json

{
  "name": "project_knowledge",
  "display_name": "Project Knowledge Base",
  "description": "All project documentation",
  "chunking_strategy": "semantic",
  "max_tokens_per_chunk": 512,
  "max_overlap_tokens": 50,
  "storage_quota": 10737418240
}
```

### Get Store Details
```bash
GET /file-search-stores/{store_id}/
```

### Get Store Statistics
```bash
GET /file-search-stores/{store_id}/stats/
```

**Response**:
```json
{
  "store_id": "uuid",
  "name": "company_docs",
  "total_files": 45,
  "total_chunks": 1205,
  "storage_size_bytes": 52428800,
  "embeddings_size_bytes": 157286400,
  "total_size_bytes": 209715200,
  "storage_quota": 1073741824,
  "storage_used_percentage": 19.5,
  "is_quota_exceeded": false
}
```

### List Files in Store
```bash
GET /file-search-stores/{store_id}/files/
```

### List Chunks in Store
```bash
GET /file-search-stores/{store_id}/chunks/
```

### Update Store
```bash
PATCH /file-search-stores/{store_id}/
Content-Type: application/json

{
  "display_name": "Updated Name",
  "storage_quota": 21474836480
}
```

### Delete Store
```bash
DELETE /file-search-stores/{store_id}/
```

### Force Delete Store (with all data)
```bash
DELETE /file-search-stores/{store_id}/force_delete/
```

---

## 📄 File Indexing

### Index a File to Store
```bash
POST /file-search/index/
Content-Type: application/json

{
  "file_id": 123,
  "file_search_store_name": "company_docs",
  "chunking_strategy": "semantic",
  "max_tokens_per_chunk": 512,
  "max_overlap_tokens": 50,
  "custom_metadata": {
    "department": "engineering",
    "classification": "internal",
    "year": "2024",
    "author": "John Doe"
  }
}
```

**Response**:
```json
{
  "message": "File indexed successfully",
  "file_id": 123,
  "store": "company_docs",
  "chunks_created": 42,
  "total_tokens": 21504,
  "chunking_strategy": "semantic"
}
```

**Notes**:
- `file_search_store_name` is optional (file can be indexed without store)
- If store is specified, its config is used unless overridden
- Custom metadata enables advanced filtering

---

## 🔍 Semantic Search

### Search with Filters
```bash
POST /file-search/search/
Content-Type: application/json

{
  "query": "How do we handle user authentication?",
  "file_search_store_names": ["company_docs", "api_docs"],
  "metadata_filter": {
    "department": "engineering",
    "year": "2024"
  },
  "limit": 10,
  "include_citations": true
}
```

**Response**:
```json
{
  "query": "How do we handle user authentication?",
  "results_count": 5,
  "results": [
    {
      "chunk_id": 456,
      "chunk_text": "User authentication is handled through JWT tokens...",
      "file_name": "auth_guide.pdf",
      "file_type": "document",
      "chunk_index": 3,
      "metadata": {
        "department": "engineering",
        "year": "2024"
      },
      "citation": {
        "citation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "source_reference": "auth_guide.pdf, chunk 3",
        "source_file": "auth_guide.pdf",
        "chunk_index": 3
      }
    }
  ],
  "filters_applied": {
    "stores": ["company_docs"],
    "metadata": {"department": "engineering", "year": "2024"}
  }
}
```

**Filter Options**:
- `file_search_store_names`: Array of store names (optional)
- `metadata_filter`: JSON object for metadata filtering (optional)
- `limit`: Max results (1-100, default: 10)
- `include_citations`: Boolean (default: true)

---

## 📊 Statistics & Analytics

### RAG System Stats
```bash
GET /rag/stats/
```

**Response**:
```json
{
  "total_chunks": 15420,
  "indexed_files": 342,
  "file_types": [
    {"file_type": "document"},
    {"file_type": "code"},
    {"file_type": "spreadsheet"}
  ]
}
```

### Media Files Stats
```bash
GET /media-files/statistics/
```

**Response**:
```json
{
  "total_files": 523,
  "by_type": {
    "document": 245,
    "image": 178,
    "video": 50,
    "code": 50
  },
  "total_size": 5368709120
}
```

---

## 🎯 Common Workflows

### Workflow 1: Create Store and Index Files

```bash
# 1. Create store
curl -X POST http://localhost:8000/api/file-search-stores/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "engineering_docs",
    "display_name": "Engineering Documentation",
    "chunking_strategy": "semantic",
    "storage_quota": 5368709120
  }'

# 2. Upload file (existing endpoint)
curl -X POST http://localhost:8000/api/upload/file/ \
  -F "file=@/path/to/document.pdf" \
  -F "user_comment=Engineering documentation"

# Response: {"id": 123, ...}

# 3. Index the file
curl -X POST http://localhost:8000/api/file-search/index/ \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": 123,
    "file_search_store_name": "engineering_docs",
    "custom_metadata": {
      "department": "engineering",
      "type": "specification"
    }
  }'
```

### Workflow 2: Search Across Multiple Stores

```bash
curl -X POST http://localhost:8000/api/file-search/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deployment procedures",
    "file_search_store_names": [
      "engineering_docs",
      "operations_docs"
    ],
    "limit": 20
  }'
```

### Workflow 3: Filtered Metadata Search

```bash
curl -X POST http://localhost:8000/api/file-search/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "security best practices",
    "metadata_filter": {
      "department": "security",
      "classification": "confidential",
      "year": "2024"
    },
    "limit": 5,
    "include_citations": true
  }'
```

---

## 💡 Tips & Best Practices

### Chunking Strategy Selection

| File Type | Recommended Strategy | Tokens | Overlap |
|-----------|---------------------|--------|---------|
| Documentation | `semantic` | 512 | 50 |
| Code | `whitespace` | 1024 | 100 |
| Books/Articles | `semantic` | 512 | 50 |
| API Responses | `fixed` | 256 | 25 |
| Mixed Content | `auto` | 512 | 50 |

### Metadata Best Practices

**Good Metadata Structure**:
```json
{
  "department": "engineering",
  "classification": "internal|confidential|public",
  "year": "2024",
  "quarter": "Q4",
  "author": "john.doe",
  "project": "project_name",
  "tags": ["deployment", "security"],
  "version": "1.0"
}
```

### Storage Quota Guidelines

| Use Case | Recommended Quota |
|----------|-------------------|
| Small team docs | 1-5 GB |
| Department knowledge | 10-50 GB |
| Company-wide | 100-500 GB |
| Enterprise archive | 1 TB+ |

---

## 🔒 Security Considerations

1. **Metadata Filtering**: Always filter by classification level
2. **Store Access**: Implement auth middleware for stores
3. **Quota Enforcement**: Monitor and enforce quotas
4. **File Validation**: Validate file types before indexing

---

## 📈 Performance Optimization

### Chunking Performance
- Use `whitespace` for fastest chunking
- Use `semantic` for best retrieval quality
- Use `auto` for balanced performance

### Search Performance
- Limit results to 10-20 for best UX
- Use store filtering to reduce search space
- Add metadata filters for precision

### Storage Optimization
- Archive unused stores
- Remove duplicate chunks
- Monitor embeddings size growth

---

## ❌ Error Handling

### Common Errors

**Store Not Found**:
```json
{
  "error": "File search store not found"
}
```

**Quota Exceeded**:
```json
{
  "error": "Storage quota exceeded for this store"
}
```

**Invalid Chunking Strategy**:
```json
{
  "chunking_strategy": ["Invalid choice: must be one of auto, whitespace, semantic, fixed"]
}
```

**File Not Found**:
```json
{
  "error": "File not found"
}
```

---

## 🎨 Response Formats

### Success Response (201 Created)
```json
{
  "message": "Resource created successfully",
  "id": 123,
  ...data
}
```

### Success Response (200 OK)
```json
{
  ...data
}
```

### Error Response (4xx/5xx)
```json
{
  "error": "Error message here"
}
```

or

```json
{
  "field_name": ["Validation error message"]
}
```

---

## 🔗 Related Endpoints

### File Management
- `GET /media-files/` - List all files
- `POST /upload/file/` - Upload file
- `GET /media-files/{id}/` - Get file details

### Legacy RAG Endpoints
- `POST /rag/index/{file_id}/` - Old indexing (still works)
- `POST /rag/search/` - Old search (still works)
- `POST /rag/query/` - RAG with AI response

---

*Last Updated: November 15, 2025*
*Version: 1.0.0*
