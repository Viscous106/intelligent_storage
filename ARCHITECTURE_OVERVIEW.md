# Intelligent Storage System - Comprehensive Architecture Overview

## Project Structure

```
intelligent_storage/
├── backend/                          # Django REST API Backend
│   ├── core/                         # Django project configuration
│   │   ├── settings.py              # Main configuration (databases, apps, middleware)
│   │   ├── urls.py                  # URL routing (main router)
│   │   ├── wsgi.py                  # Production WSGI configuration
│   │   └── asgi.py                  # ASGI configuration
│   ├── storage/                      # Main storage application
│   │   ├── models.py                # Database models (MediaFile, JSONDataStore, etc.)
│   │   ├── views.py                 # API endpoints and request handling
│   │   ├── serializers.py           # DRF serializers for data validation
│   │   ├── urls.py                  # App-specific URL routing
│   │   ├── admin.py                 # Django admin configuration
│   │   ├── file_detector.py         # File type detection (magic bytes, MIME, extension)
│   │   ├── ai_analyzer.py           # Ollama/LLM-based content analysis
│   │   ├── db_manager.py            # PostgreSQL & MongoDB abstraction
│   │   ├── embedding_service.py     # Vector embedding generation (Ollama)
│   │   ├── chunking_service.py      # Document text chunking for RAG
│   │   ├── rag_service.py           # Semantic search & RAG operations
│   │   ├── smart_db_selector.py     # SQL/NoSQL decision logic
│   │   ├── trie_search.py           # Search optimization
│   │   └── migrations/              # Database schema migrations
│   ├── api/                          # Empty app placeholder for future auth
│   ├── media/                        # User-uploaded files directory
│   │   ├── images/                  # Organized by type/subcategory
│   │   ├── videos/
│   │   ├── documents/
│   │   ├── audio/
│   │   ├── compressed/
│   │   ├── programs/
│   │   └── others/
│   ├── manage.py                    # Django management command
│   ├── requirements.txt             # Python dependencies
│   └── venv/                        # Python virtual environment
├── frontend/                         # Vanilla JavaScript Frontend
│   ├── index.html                  # Main HTML page
│   ├── app.js                      # JavaScript application logic
│   ├── styles.css                  # Styling (dark theme)
│   ├── package.json                # NPM metadata
│   ├── vite.config.js              # Vite build configuration
│   └── node_modules/               # NPM dependencies
└── README.md                        # Complete documentation
```

---

## 1. Backend Architecture & Framework

### Framework Stack
- **Django 5.0.1** - Web framework
- **Django REST Framework 3.14.0** - RESTful API development
- **Python 3.13** - Runtime
- **Gunicorn/Uvicorn** - WSGI/ASGI servers (production)

### Application Design Pattern
- **Django Apps**: Modular application structure
  - `core`: Project-level settings and configuration
  - `storage`: Main business logic for file and JSON data management
  - `api`: Placeholder for authentication/authorization features

### Architecture Diagram
```
HTTP Requests
     ↓
[Django URLs Router] → core/urls.py
     ↓
[Storage App URLs] → storage/urls.py
     ↓
[Views Layer] → storage/views.py
  ├─ FileUploadView (POST)
  ├─ BatchFileUploadView (POST)
  ├─ JSONDataUploadView (POST)
  ├─ MediaFileViewSet (CRUD)
  ├─ JSONDataViewSet (CRUD)
  └─ RAG Endpoints (semantic search)
     ↓
[Business Logic Layer]
  ├─ FileTypeDetector → file_detector.py
  ├─ OllamaAnalyzer → ai_analyzer.py
  ├─ DatabaseManager → db_manager.py
  ├─ RAGService → rag_service.py
  ├─ EmbeddingService → embedding_service.py
  └─ ChunkingService → chunking_service.py
     ↓
[Database Layer]
  ├─ PostgreSQL (SQL)
  ├─ MongoDB (NoSQL)
  └─ File System (Media Storage)
     ↓
Response JSON
```

---

## 2. Database Configuration & Connections

### PostgreSQL Configuration
**Purpose**: Stores structured data, file metadata, embeddings, and search queries

```python
# Location: core/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_NAME', 'intelligent_storage_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres123'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
```

**Tables Created**:
- `storage_mediafile` - Uploaded file metadata
- `storage_jsondatastore` - JSON dataset tracking
- `storage_uploadbatch` - Batch operation tracking
- `storage_documentchunk` - Text chunks with vector embeddings (pgvector)
- `storage_searchquery` - Search history with embeddings
- Django auth tables (User, Group, Permission)

**Key Features**:
- pgvector extension for vector embeddings (768 dimensions)
- Indexed fields for performance: `detected_type`, `storage_category`, `uploaded_at`
- Automatic timestamp tracking (created_at, updated_at)

### MongoDB Configuration
**Purpose**: Stores unstructured JSON data with flexible schema

```python
# Location: core/settings.py

MONGODB_SETTINGS = {
    'HOST': os.environ.get('MONGODB_HOST', 'localhost'),
    'PORT': int(os.environ.get('MONGODB_PORT', 27017)),
    'USER': os.environ.get('MONGODB_USER', 'admin'),
    'PASSWORD': os.environ.get('MONGODB_PASSWORD', 'admin123'),
    'DB': os.environ.get('MONGODB_DB', 'intelligent_storage_nosql'),
}
```

**Features**:
- Dynamic collection creation based on dataset names
- Schema-free storage for complex nested structures
- Automatic document insertion with auto-generated IDs

### File System Storage
**Purpose**: Direct file storage with organized directory structure

**Configuration**:
```python
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

STORAGE_DIRS = {
    'images': os.path.join(MEDIA_ROOT, 'images'),
    'videos': os.path.join(MEDIA_ROOT, 'videos'),
    'compressed': os.path.join(MEDIA_ROOT, 'compressed'),
    'programs': os.path.join(MEDIA_ROOT, 'programs'),
    'documents': os.path.join(MEDIA_ROOT, 'documents'),
    'audio': os.path.join(MEDIA_ROOT, 'audio'),
    'others': os.path.join(MEDIA_ROOT, 'others'),
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
```

**Organization Pattern**:
```
media/
├── {category}/
│   └── {subcategory}/
│       └── YYYYMMDD_HHMMSS_{original_filename}
```

### Connection Management
- **PostgreSQL**: Django ORM with connection pooling
- **MongoDB**: PyMongo client with singleton pattern
- **File System**: Direct OS operations with path validation
- **Redis**: Connection pool for Celery task queue (optional)

---

## 3. Upload Handling Mechanisms

### Single File Upload Flow
**Endpoint**: `POST /api/upload/file/`

```python
# Location: storage/views.py → FileUploadView.post()

1. Receive Request
   └─ FileUploadSerializer validates input
      ├─ file: FileField (required)
      └─ user_comment: CharField (optional)

2. Save to Temp Directory
   └─ UUID-based temp filename
   └─ Path: media/temp/{uuid}_{original_name}

3. File Type Detection
   └─ file_detector.detect_file_type()
   └─ Multi-layer detection:
      ├─ Magic bytes (libmagic) - highest weight
      ├─ MIME type detection - medium weight
      └─ File extension - lowest weight

4. AI Content Analysis
   └─ ai_analyzer.analyze_image() OR analyze_file_content()
   └─ Ollama API call (llama3 or llama3.2-vision)
   └─ Returns: {category, tags, description}

5. Organize File
   └─ Move: media/temp → media/{category}/{subcategory}/
   └─ Filename: {YYYYMMDD_HHMMSS}_{original_name}

6. Create Database Record
   └─ MediaFile.objects.create()
   └─ Stores: name, size, types, paths, AI analysis, metadata

7. Return Response
   └─ 201 Created + MediaFile serialized data
```

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/upload/file/ \
  -F "file=@photo.jpg" \
  -F "user_comment=vacation photo"
```

**Response Example**:
```json
{
  "success": true,
  "file": {
    "id": 1,
    "original_name": "photo.jpg",
    "file_path": "/home/user/media/images/nature/20241115_143022_photo.jpg",
    "detected_type": "images",
    "ai_category": "landscape",
    "ai_tags": ["mountain", "sunset", "nature"],
    "ai_description": "Beautiful mountain landscape during sunset",
    "storage_category": "images",
    "storage_subcategory": "nature"
  },
  "message": "File uploaded and organized in images/nature/"
}
```

### Batch File Upload Flow
**Endpoint**: `POST /api/upload/batch/`

```python
# Location: storage/views.py → BatchFileUploadView.post()

1. Create Upload Batch Record
   └─ UploadBatch.objects.create()
   └─ batch_id: UUID
   └─ status: 'processing'
   └─ total_files: count

2. Process Each File
   └─ Loop through files array
   └─ For each file:
      ├─ Save temp file
      ├─ Detect type
      ├─ AI analysis
      ├─ Organize
      ├─ Create MediaFile record
      └─ Collect results (success/fail)

3. Track Progress
   └─ Update batch:
      ├─ processed_files += 1
      ├─ failed_files += 1
      └─ completed_at = now()

4. Return Batch Summary
   └─ 201 Created
   └─ batch_id, total, processed, failed, detailed results
```

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/upload/batch/ \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.jpg" \
  -F "files=@document.pdf" \
  -F "user_comment=my documents"
```

### JSON Data Upload Flow
**Endpoint**: `POST /api/upload/json/`

```python
# Location: storage/views.py → JSONDataUploadView.post()

1. Receive & Validate
   └─ JSONUploadSerializer validates input
   └─ data: JSONField (required)
   └─ name: Optional dataset name
   └─ user_comment: Optional metadata
   └─ force_db_type: Optional SQL/NoSQL override

2. AI Database Type Analysis
   └─ ai_analyzer.analyze_json_for_db_choice()
   └─ Evaluates:
      ├─ Structure depth
      ├─ Nested objects presence
      ├─ Array usage
      ├─ Schema consistency
      └─ Returns: {database_type, confidence, schema, reasoning}

3. Database Type Decision
   └─ if force_db_type: use it
   └─ else: use AI recommendation

4. Store Data
   └─ if 'NoSQL':
      ├─ db_manager._store_in_mongodb()
      └─ Create collection, insert documents
   └─ if 'SQL':
      ├─ db_manager._store_in_postgresql()
      └─ Create table, insert rows

5. Create Tracking Record
   └─ JSONDataStore.objects.create()
   └─ Stores: name, db_type, schema, reasoning, sample_data

6. Return Response
   └─ 201 Created
   └─ Storage metadata + AI analysis + generated schema
```

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/upload/json/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"id": 1, "name": "John", "email": "john@example.com"},
      {"id": 2, "name": "Jane", "email": "jane@example.com"}
    ],
    "name": "users",
    "user_comment": "User contact list",
    "force_db_type": "SQL"
  }'
```

---

## 4. Authentication & Authorization Setup

### Current Implementation Status
**Status**: Not yet implemented - credentials are placeholder only

### Planned Architecture (from requirements.txt)
The following packages are installed but not yet integrated:
- `djangorestframework-simplejwt` - JWT token-based auth
- `django-allauth` - Multi-provider OAuth/social auth
- `dj-rest-auth` - REST endpoints for auth

### Current Configuration
```python
# Location: core/settings.py

# CORS Configuration (all origins allowed for development)
CORS_ALLOW_ALL_ORIGINS = True
ALLOWED_HOSTS = ["*"]

# Security Settings (DEBUG enabled - unsafe for production)
SECRET_KEY = 'django-insecure-...'  # CHANGE IN PRODUCTION
DEBUG = True

# No authentication backend configured yet
```

### Middleware Stack
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Endpoints Access Control
**Current**: No authentication required
**Recommended for Production**:
- JWT-based token authentication
- Per-endpoint permission classes
- User-based file ownership
- Role-based access control (RBAC)

### Future Implementation Options
1. **JWT Authentication**:
   - Token generation on login
   - Token validation on each request
   - Refresh token rotation

2. **OAuth Integration**:
   - Google OAuth via django-allauth
   - GitHub OAuth
   - Support for multi-provider logins

3. **Multi-Tenancy**:
   - User-scoped data isolation
   - Separate media directories per user
   - Database row-level security

---

## 5. Media Storage Implementation

### File Organization Strategy
**Logic**: `{category}/{subcategory}/{timestamp}_{filename}`

**Category Detection Hierarchy**:
```python
# Location: storage/file_detector.py → FILE_TYPE_CATEGORIES

Categories and Examples:
├── images
│   ├── .jpg, .jpeg, .png, .gif, .bmp, .svg, .webp, .ico, .tiff, .heic, .raw
│   └── Subcategories: PNG, JPG, JPEG, GIF, SVG, etc. (by extension)
├── videos
│   ├── .mp4, .avi, .mov, .wmv, .flv, .mkv, .webm, .m4v, .mpg, .mpeg
│   └── Subcategories: MP4, AVI, MOV, MKV, etc.
├── audio
│   ├── .mp3, .wav, .flac, .aac, .ogg, .wma, .m4a, .opus, .ape, .alac
│   └── Subcategories: MP3, WAV, FLAC, etc.
├── documents
│   ├── .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .odt, .ods, .odp, .txt, .csv, .md, .html, .xml, .json
│   └── Subcategories: pdf, word, spreadsheets, general
├── compressed
│   ├── .zip, .rar, .7z, .tar, .gz, .bz2, .xz, .tar.gz, .tar.bz2, .tar.xz
│   └── Subcategory: archives
├── programs
│   ├── .exe, .dll, .so, .dylib, .app, .bin, .sh, .bat, .cmd, .msi, .deb, .rpm, .apk, .jar
│   └── Subcategories: windows, libraries, scripts, executables
└── others
    └── Everything else (uncategorized)
```

### Detection Algorithm
**Location**: `storage/file_detector.py → FileTypeDetector.detect_file_type()`

```python
def detect_file_type(file_path):
    """
    Multi-layer detection with scoring:
    - Magic bytes (weight: 3) - most reliable
    - MIME type (weight: 2)
    - File extension (weight: 1)
    
    Category = argmax(scores)
    """
    
    # 1. Get metadata
    extension = file_path.suffix.lower()
    mime_type = magic.Magic(mime=True).from_file(file_path)
    magic_desc = magic.Magic().from_file(file_path)
    
    # 2. Score each category
    scores = {}
    for category, patterns in FILE_TYPE_CATEGORIES.items():
        score = 0
        if extension in patterns['extensions']:
            score += 1
        if any(mime_type.startswith(p) for p in patterns['mime_prefixes']):
            score += 2
        if any(p.lower() in magic_desc.lower() for p in patterns['magic_patterns']):
            score += 3
        scores[category] = score
    
    # 3. Return highest scoring category
    return max(scores, key=scores.get)
```

### Subcategory Determination
**Method 1**: File extension-based (default)
```python
images: PNG, JPG, GIF, SVG, WEBP, etc.
videos: MP4, AVI, MOV, MKV, etc.
documents: pdf, word, spreadsheets, general
programs: windows, libraries, scripts, executables
```

**Method 2**: AI-enhanced (if analysis succeeds)
```python
if ai_analysis['category']:
    return sanitize(ai_analysis['category'])
```

### File Metadata Storage
**Location**: `storage/models.py → MediaFile`

```python
class MediaFile(models.Model):
    # File information
    original_name = CharField(max_length=255)
    file_path = CharField(max_length=1024)
    file_size = BigIntegerField()
    
    # Type detection
    detected_type = CharField(max_length=50)  # images, videos, etc.
    mime_type = CharField(max_length=100)
    file_extension = CharField(max_length=20)
    magic_description = TextField()
    
    # AI Analysis
    ai_category = CharField(max_length=255, nullable)
    ai_subcategory = CharField(max_length=255, nullable)
    ai_tags = JSONField(default=[])
    ai_description = TextField(nullable)
    
    # User input
    user_comment = TextField(nullable)
    
    # Storage organization
    storage_category = CharField(max_length=100)
    storage_subcategory = CharField(max_length=100)
    relative_path = CharField(max_length=1024)
    
    # Metadata
    uploaded_at = DateTimeField(auto_now_add=True)
    processed_at = DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            Index(fields=['detected_type']),
            Index(fields=['storage_category']),
            Index(fields=['uploaded_at']),
        ]
```

### Media Root Structure
```
media/
├── temp/                        # Temporary upload directory
├── images/
│   ├── PNG/                    # Subcategories
│   ├── JPG/
│   ├── GIF/
│   └── nature/                 # AI-generated subcategories
│       └── 20241115_143022_landscape.jpg
├── videos/
│   ├── MP4/
│   ├── AVI/
│   └── tutorials/
│       └── 20241115_143022_guide.mp4
├── documents/
│   ├── pdf/
│   │   └── 20241115_143022_report.pdf
│   ├── word/
│   │   └── 20241115_143022_document.docx
│   └── spreadsheets/
│       └── 20241115_143022_data.xlsx
├── audio/
│   ├── MP3/
│   │   └── 20241115_143022_song.mp3
│   └── WAV/
├── compressed/
│   └── archives/
│       └── 20241115_143022_backup.zip
├── programs/
│   ├── windows/
│   ├── scripts/
│   └── executables/
└── others/
    └── 20241115_143022_unknown_file
```

### File Serving
**In Development**:
```python
# core/urls.py
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**In Production**: Use dedicated storage service (S3, Azure Blob, etc.)

---

## 6. Directory Structure & Key Files

### Complete Backend Structure
```
backend/
├── core/
│   ├── __init__.py
│   ├── settings.py              # Database, apps, middleware config
│   ├── urls.py                  # Main URL router
│   ├── wsgi.py                  # Production server config
│   ├── asgi.py                  # ASGI config (WebSockets)
│   └── __pycache__/
├── storage/                      # Main application
│   ├── migrations/
│   │   ├── 0001_initial.py      # MediaFile, JSONDataStore, UploadBatch
│   │   └── 0002_searchquery_documentchunk.py  # RAG models
│   ├── __init__.py
│   ├── admin.py                 # Django admin (currently empty)
│   ├── apps.py
│   ├── models.py                # 5 main models
│   ├── views.py                 # 7 API endpoints/viewsets
│   ├── serializers.py           # 6 serializers
│   ├── urls.py                  # 11 URL patterns
│   ├── tests.py
│   ├── file_detector.py         # FileTypeDetector class
│   ├── ai_analyzer.py           # OllamaAnalyzer class
│   ├── db_manager.py            # DatabaseManager class
│   ├── embedding_service.py     # EmbeddingService class
│   ├── chunking_service.py      # ChunkingService class
│   ├── rag_service.py           # RAGService class
│   ├── smart_db_selector.py     # SQL/NoSQL decision logic
│   ├── trie_search.py           # Search optimization
│   └── __pycache__/
├── api/                          # Placeholder app
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py                # Empty
│   ├── tests.py
│   └── views.py
├── media/                        # User uploads
├── staticfiles/                  # Collected static files (production)
├── manage.py                    # Django CLI
├── requirements.txt             # Python dependencies
├── requirements_minimal.txt     # Minimal dependencies
├── venv/                        # Virtual environment
└── __pycache__/
```

### Key Files & Their Responsibilities

#### Configuration Files
| File | Purpose | Key Configs |
|------|---------|------------|
| `core/settings.py` | Django configuration | DATABASES, INSTALLED_APPS, MIDDLEWARE, CORS, STORAGE_DIRS |
| `core/urls.py` | URL routing | Include storage.urls, media serving |
| `requirements.txt` | Python dependencies | 30+ packages (Django, DRF, AI, Database, etc.) |

#### Model Definitions
| File | Models | Purpose |
|------|--------|---------|
| `storage/models.py` | MediaFile | Uploaded file metadata + AI analysis |
| | JSONDataStore | JSON dataset tracking + schema info |
| | UploadBatch | Batch upload operation tracking |
| | DocumentChunk | Text chunks with vector embeddings (RAG) |
| | SearchQuery | Search query history with embeddings |

#### API Layer
| File | Components | Responsibilities |
|------|------------|------------------|
| `storage/views.py` | FileUploadView | Single file upload, type detection, organization |
| | BatchFileUploadView | Multiple file uploads |
| | JSONDataUploadView | JSON data upload + DB type analysis |
| | MediaFileViewSet | CRUD for media files + statistics |
| | JSONDataViewSet | CRUD for JSON datasets + querying |
| | RAG endpoints (5) | Document indexing, semantic search, RAG queries |
| | health_check | Service availability check |
| `storage/serializers.py` | MediaFileSerializer | Validate & serialize MediaFile |
| | JSONDataStoreSerializer | Validate & serialize JSONDataStore |
| | FileUploadSerializer | Validate single file upload |
| | BatchFileUploadSerializer | Validate batch upload |
| | JSONUploadSerializer | Validate JSON upload |
| `storage/urls.py` | 11 URL patterns | Route to views/viewsets |

#### Business Logic Services
| File | Class | Responsibility |
|------|-------|-----------------|
| `file_detector.py` | FileTypeDetector | Multi-layer file type detection |
| `ai_analyzer.py` | OllamaAnalyzer | Content analysis via Ollama API |
| `db_manager.py` | DatabaseManager | PostgreSQL & MongoDB abstraction |
| `embedding_service.py` | EmbeddingService | Vector embedding generation |
| `chunking_service.py` | ChunkingService | Document text chunking |
| `rag_service.py` | RAGService | Semantic search & RAG operations |
| `smart_db_selector.py` | SmartDBSelector | SQL/NoSQL decision logic |
| `trie_search.py` | TrieSearch | Optimized search structures |

### Frontend Structure
```
frontend/
├── index.html               # Main HTML (7 sections)
├── app.js                  # JavaScript application
├── styles.css              # CSS styling (dark theme)
├── app_old.js              # Legacy version
├── styles_old.css          # Legacy styles
├── index_old.html          # Legacy HTML
├── vite.config.js          # Vite bundler config
├── package.json            # NPM metadata
└── node_modules/           # Dependencies
```

---

## 7. API Endpoints Summary

### File Management
```
POST   /api/upload/file/           → Upload single file
POST   /api/upload/batch/          → Upload multiple files
GET    /api/media-files/           → List all files
GET    /api/media-files/?detected_type=images  → Filter by type
GET    /api/media-files/statistics/  → Get stats
GET    /api/media-files/{id}/      → Get file details
```

### JSON Data Management
```
POST   /api/upload/json/           → Upload JSON data
GET    /api/json-stores/           → List datasets
GET    /api/json-stores/{id}/query/ → Query dataset
GET    /api/json-stores/list_databases/ → List all tables/collections
```

### Semantic Search & RAG
```
POST   /api/rag/index/{file_id}/   → Index document for semantic search
POST   /api/rag/search/            → Semantic search across documents
POST   /api/rag/query/             → Ask question, get AI-generated answer
POST   /api/rag/reindex-all/       → Reindex all documents
GET    /api/rag/stats/             → Get RAG statistics
```

### System
```
GET    /api/health/                → Check service health
```

---

## 8. Technology Stack Details

### Backend Technologies
```
Core Framework:
├── Django 5.0.1
├── Django REST Framework 3.14.0
└── Python 3.13

Databases:
├── PostgreSQL 15 (SQL)
├── MongoDB 7.0 (NoSQL)
└── Redis 7.0 (Cache/Queue)

AI/ML:
├── Ollama (Local LLM runtime)
├── Llama3 (Text analysis)
└── Llama3.2-Vision (Image analysis)

Libraries:
├── psycopg2-binary (PostgreSQL driver)
├── pymongo (MongoDB driver)
├── python-magic (File detection)
├── Pillow (Image processing)
├── requests (HTTP client)
├── celery (Task queue)
├── djangorestframework-simplejwt (JWT)
├── django-allauth (OAuth)
└── pgvector (Vector embeddings)
```

### Frontend Technologies
```
Core:
├── HTML5
├── CSS3 (Flexbox, Grid, Animations)
└── Vanilla JavaScript (ES6+)

Build Tools:
├── Vite (bundler)
├── Node.js runtime
└── NPM (package manager)

No Framework Dependencies (minimalist approach)
```

### Infrastructure
```
Servers:
├── Gunicorn/Uvicorn (Django WSGI/ASGI)
└── Node.js (Frontend dev server - development only)

Monitoring (optional):
└── Health check endpoints
```

---

## 9. Data Flow Examples

### Complete File Upload Flow
```
User → Frontend (Drag & Drop)
  ↓
POST /api/upload/file/ + file binary
  ↓
FileUploadView (validate)
  ↓
Save to temp/ directory
  ↓
FileTypeDetector.detect_file_type()
  ├─ Read magic bytes → category: 'images'
  ├─ Check MIME type → 'image/jpeg'
  └─ Check extension → '.jpg'
  ↓
OllamaAnalyzer.analyze_image()
  ├─ Base64 encode image
  ├─ POST to Ollama API (llama3.2-vision)
  ├─ Parse JSON response
  └─ Return: {category: 'nature', tags: [...], description: '...'}
  ↓
Determine subcategory: 'nature' (from AI)
  ↓
Move file from temp/ to media/images/nature/
  ↓
MediaFile.objects.create() → Insert into PostgreSQL
  ↓
Serialize & Return 201 Response
  ↓
Frontend displays: "Uploaded to images/nature/"
```

### JSON Upload with DB Type Decision
```
User → Frontend (JSON Input)
  ↓
POST /api/upload/json/ + JSON data
  ↓
JSONDataUploadView (validate)
  ↓
OllamaAnalyzer.analyze_json_for_db_choice()
  ├─ Measure structure depth: 2
  ├─ Check for nested objects: False
  ├─ Check for arrays: True
  ├─ Prompt Ollama: "Is this more SQL or NoSQL?"
  └─ Return: {database_type: 'SQL', confidence: 85, reasoning: '...'}
  ↓
DatabaseManager.store_json_data(db_type='SQL')
  ├─ Create table: CREATE TABLE users (id INT, name TEXT, email TEXT)
  ├─ Insert rows: INSERT INTO users VALUES (...)
  └─ Return: {success: True, table: 'users'}
  ↓
JSONDataStore.objects.create() → Insert into PostgreSQL
  ↓
Return 201 with storage details + AI reasoning
  ↓
Frontend displays: "Stored in PostgreSQL table 'users'"
```

### Semantic Search (RAG) Flow
```
User → Frontend (Search Query)
  ↓
POST /api/rag/search/ + {query: "..."}
  ↓
RAGService.search()
  ├─ Generate embedding for query (Ollama)
  └─ Vector: [0.234, 0.567, ..., 0.891]
  ↓
Query PostgreSQL with pgvector:
  SELECT * FROM storage_documentchunk
  WHERE embedding <-> vector LIMIT 10
  ↓
Retrieve top 10 similar chunks (by cosine distance)
  ↓
Serialize & Return 200
  ↓
Frontend displays: Results with relevance scores
```

---

## 10. Configuration Summary

### Environment Variables
```bash
# PostgreSQL
POSTGRES_NAME=intelligent_storage_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USER=admin
MONGODB_PASSWORD=admin123
MONGODB_DB=intelligent_storage_nosql

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:latest

# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### REST Framework Configuration
```python
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

---

## Next Steps for Building Upon This System

### Recommended Extensions:
1. **Authentication** - Implement JWT + OAuth from installed packages
2. **User Isolation** - Add user ownership to files and datasets
3. **Search Optimization** - Leverage existing trie_search.py module
4. **Async Processing** - Use Celery for long-running tasks
5. **File Preview** - Generate thumbnails and document previews
6. **Advanced Querying** - Full-text search, filters, sorting
7. **Cloud Storage** - S3/Azure integration for scalability
8. **Monitoring** - Logging, metrics, error tracking
9. **Testing** - Unit, integration, and E2E tests
10. **Documentation** - OpenAPI/Swagger integration

---

**End of Comprehensive Overview**
