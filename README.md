# Intelligent Multi-Modal Storage System

A professional, AI-powered storage system that intelligently processes and organizes any type of data with a unified frontend interface.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/intelligent_storage.git
cd intelligent_storage

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

Open browser: `http://localhost:8000`

---

## Features

### Media File Management
- **Intelligent File Detection**: Robust file type detection using magic bytes, MIME types, and file extensions
- **AI-Powered Categorization**: Uses Ollama/Llama3 for intelligent content analysis and categorization
- **Automatic Organization**: Files are automatically organized into `type/subcategory` directory structures
- **Batch Upload Support**: Upload multiple files simultaneously with progress tracking
- **Comprehensive Metadata**: Tracks file size, type, AI analysis, and user comments

### Structured Data (JSON) Management
- **Automatic SQL/NoSQL Detection**: AI analyzes JSON structure to recommend the best database type
- **Dynamic Schema Generation**: Automatically creates appropriate database schemas
- **Flexible Storage**: Supports both PostgreSQL (SQL) and MongoDB (NoSQL)
- **Manual Override**: Option to force specific database type if needed
- **Query Interface**: Built-in API to query stored data

## Architecture

```
intelligent_storage/
├── backend/                 # Django Backend
│   ├── core/               # Django project settings
│   ├── storage/            # Main storage app
│   │   ├── models.py       # Database models
│   │   ├── views.py        # API views
│   │   ├── serializers.py  # DRF serializers
│   │   ├── file_detector.py    # File type detection
│   │   ├── ai_analyzer.py      # Ollama/AI integration
│   │   └── db_manager.py       # Database management
│   └── manage.py
└── frontend/               # Frontend Interface
    ├── index.html         # Main HTML
    ├── styles.css         # Styling
    └── app.js             # JavaScript logic
```

## Prerequisites

### Required Software

1. **Python 3.10+**
   ```bash
   python --version
   ```

2. **PostgreSQL 15+**

   <details>
   <summary><b>Arch Linux</b></summary>

   ```bash
   # Install PostgreSQL
   sudo pacman -S postgresql

   # Initialize the database cluster
   sudo -u postgres initdb -D /var/lib/postgres/data

   # Start and enable PostgreSQL service
   sudo systemctl start postgresql
   sudo systemctl enable postgresql

   # Create a user and database (optional, for manual setup)
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb intelligent_storage_db
   ```
   </details>

   <details>
   <summary><b>Ubuntu/Debian</b></summary>

   ```bash
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```
   </details>

   <details>
   <summary><b>macOS</b></summary>

   ```bash
   brew install postgresql@15
   brew services start postgresql@15
   ```
   </details>

   <details>
   <summary><b>Windows</b></summary>

   Download from https://www.postgresql.org/download/windows/
   </details>

3. **MongoDB 7.0+**

   <details>
   <summary><b>Arch Linux</b></summary>

   ```bash
   # MongoDB is in AUR, install using yay or paru
   yay -S mongodb-bin

   # Or build from AUR manually
   git clone https://aur.archlinux.org/mongodb-bin.git
   cd mongodb-bin
   makepkg -si

   # Start and enable MongoDB service
   sudo systemctl start mongodb
   sudo systemctl enable mongodb

   # Verify installation
   mongosh --version
   ```
   </details>

   <details>
   <summary><b>Ubuntu/Debian</b></summary>

   ```bash
   # Import MongoDB GPG key
   wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

   # Add MongoDB repository
   echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

   # Install MongoDB
   sudo apt update
   sudo apt install -y mongodb-org

   # Start and enable MongoDB
   sudo systemctl start mongod
   sudo systemctl enable mongod
   ```
   </details>

   <details>
   <summary><b>macOS</b></summary>

   ```bash
   brew tap mongodb/brew
   brew install mongodb-community@7.0
   brew services start mongodb-community@7.0
   ```
   </details>

   <details>
   <summary><b>Windows</b></summary>

   Download from https://www.mongodb.com/try/download/community
   </details>

4. **Ollama with Llama3**

   <details>
   <summary><b>Arch Linux</b></summary>

   ```bash
   # Install Ollama from AUR
   yay -S ollama

   # Or install official binary
   curl -fsSL https://ollama.com/install.sh | sh

   # Start Ollama service
   sudo systemctl start ollama
   sudo systemctl enable ollama

   # Pull required models
   ollama pull llama3:latest
   ollama pull llama3.2-vision  # For image analysis

   # Verify installation
   ollama list
   ```
   </details>

   <details>
   <summary><b>Ubuntu/Debian/macOS</b></summary>

   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh

   # Pull Llama3 model
   ollama pull llama3:latest

   # For vision capabilities (image analysis)
   ollama pull llama3.2-vision

   # Verify installation
   ollama list
   ```
   </details>

   <details>
   <summary><b>Windows</b></summary>

   Download from https://ollama.com/download/windows
   Then run:
   ```powershell
   ollama pull llama3:latest
   ollama pull llama3.2-vision
   ```
   </details>

5. **libmagic** (for file type detection)

   <details>
   <summary><b>Arch Linux</b></summary>

   ```bash
   sudo pacman -S file
   # libmagic is part of the 'file' package and is likely already installed
   ```
   </details>

   <details>
   <summary><b>Ubuntu/Debian</b></summary>

   ```bash
   sudo apt install libmagic1
   ```
   </details>

   <details>
   <summary><b>macOS</b></summary>

   ```bash
   brew install libmagic
   ```
   </details>

   <details>
   <summary><b>Windows</b></summary>

   Download from https://github.com/pidydx/libmagicwin64
   </details>

6. **Python Virtual Environment (Arch Linux specific note)**

   <details>
   <summary><b>Arch Linux - Important!</b></summary>

   Arch Linux uses PEP 668 externally managed environments. You **must** use a virtual environment:

   ```bash
   # The system will prevent global pip installs
   # Always create a virtual environment for Python projects
   python -m venv venv
   source venv/bin/activate

   # Or use pipx for standalone applications
   sudo pacman -S python-pipx
   ```
   </details>

## Installation & Setup

### Quick Start for Arch Linux Users

#### Automated Setup (Recommended)

Run the automated setup script:

```bash
cd intelligent_storage
chmod +x setup_arch.sh
./setup_arch.sh
```

The script will:
- Install all required system packages
- Set up PostgreSQL, MongoDB, and Ollama
- Create virtual environment and install Python dependencies
- Configure databases
- Run Django migrations

After the script completes, just start the servers and you're ready to go!

#### Manual Setup

If you prefer manual setup or want to understand each step, here's the full process:

```bash
# 1. Install all prerequisites
sudo pacman -S postgresql mongodb-bin file python

# 2. Install Ollama from AUR
yay -S ollama

# 3. Initialize and start services
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl start postgresql mongodb ollama
sudo systemctl enable postgresql mongodb ollama

# 4. Pull AI models
ollama pull llama3:latest
ollama pull llama3.2-vision

# 5. Setup the project
cd intelligent_storage/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements_minimal.txt

# 6. Configure database (create .env file)
cat > .env << 'EOF'
POSTGRES_NAME=intelligent_storage_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USER=admin
MONGODB_PASSWORD=admin123
MONGODB_DB=intelligent_storage_nosql

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:latest

DJANGO_SECRET_KEY=your-secret-key-change-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# 7. Setup databases
sudo -u postgres psql << 'EOF'
CREATE DATABASE intelligent_storage_db;
CREATE USER postgres WITH PASSWORD 'postgres123';
GRANT ALL PRIVILEGES ON DATABASE intelligent_storage_db TO postgres;
\q
EOF

mongosh << 'EOF'
use admin
db.createUser({
  user: "admin",
  pwd: "admin123",
  roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
})
exit
EOF

# 8. Run migrations
python manage.py makemigrations
python manage.py migrate

# 9. Start the server
python manage.py runserver

# 10. In another terminal, serve the frontend
cd ../frontend
python -m http.server 3000
```

Then open http://localhost:3000 in your browser!

---

### Setup Instructions

#### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd intelligent_storage/backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure PostgreSQL**:
   ```bash
   # Access PostgreSQL
   sudo -u postgres psql

   # Create database and user
   CREATE DATABASE intelligent_storage_db;
   CREATE USER postgres WITH PASSWORD 'postgres123';
   GRANT ALL PRIVILEGES ON DATABASE intelligent_storage_db TO postgres;
   \q
   ```

5. **Configure MongoDB**:
   ```bash
   # Access MongoDB
   mongosh

   # Create admin user
   use admin
   db.createUser({
     user: "admin",
     pwd: "admin123",
     roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
   })

   # Create database
   use intelligent_storage_nosql
   exit
   ```

6. **Set environment variables** (create `.env` file in backend/):
   ```env
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

   # Ollama
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=llama3:latest

   # Django
   DJANGO_SECRET_KEY=your-secret-key-here
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   ```

7. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

8. **Create superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

9. **Start development server**:
   ```bash
   python manage.py runserver
   ```

   The API will be available at: http://localhost:8000

#### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd intelligent_storage/frontend
   ```

2. **Serve with a simple HTTP server**:

   **Option A - Python**:
   ```bash
   python -m http.server 3000
   ```

   **Option B - Node.js (http-server)**:
   ```bash
   npm install -g http-server
   http-server -p 3000
   ```

   **Option C - PHP**:
   ```bash
   php -S localhost:3000
   ```

3. **Access the frontend**:
   Open http://localhost:3000 in your browser

## Usage Guide

### Uploading Files

1. **Single File Upload**:
   - Click "Upload Files" tab
   - Drag and drop a file or click "Select Files"
   - Optionally add a comment to help AI categorization
   - Click "Upload Files"
   - The file will be automatically:
     - Analyzed for type using magic bytes
     - Categorized by AI
     - Organized into appropriate directory
     - Metadata saved to database

2. **Batch File Upload**:
   - Select multiple files
   - Add optional comment
   - Click "Upload Files"
   - Progress will be shown for each file

3. **File Organization**:
   Files are organized as:
   ```
   media/
   ├── images/
   │   ├── nature/
   │   ├── people/
   │   └── architecture/
   ├── videos/
   │   ├── tutorials/
   │   └── entertainment/
   ├── audio/
   ├── documents/
   │   ├── pdf/
   │   └── word/
   ├── compressed/
   ├── programs/
   │   ├── scripts/
   │   └── executables/
   └── others/
   ```

### Uploading JSON Data

1. **Navigate to Upload tab** and click "Upload JSON Data"

2. **Enter your JSON data**:
   ```json
   {
     "name": "John Doe",
     "email": "john@example.com",
     "age": 30
   }
   ```

   Or array of objects:
   ```json
   [
     {"id": 1, "name": "Product A", "price": 29.99},
     {"id": 2, "name": "Product B", "price": 49.99}
   ]
   ```

3. **Add optional metadata**:
   - Dataset name (e.g., "users", "products")
   - Comment to help AI decision (e.g., "User profiles with consistent structure")

4. **Database Type**:
   - **Auto**: Let AI decide based on structure analysis
   - **Force SQL**: Override to use PostgreSQL
   - **Force NoSQL**: Override to use MongoDB

5. **Click "Upload JSON Data"**

6. **AI Analysis**:
   The system will:
   - Analyze JSON structure depth
   - Check for nested objects and arrays
   - Evaluate schema consistency
   - Recommend SQL or NoSQL
   - Provide reasoning for the decision
   - Auto-generate appropriate schema

### Viewing Files

1. Navigate to "Files" tab
2. Filter by category using dropdown
3. View file details including:
   - File type and size
   - Storage location
   - AI-generated description
   - Upload timestamp

### Viewing JSON Datasets

1. Navigate to "JSON Data" tab
2. View all stored datasets with:
   - Database type (SQL/NoSQL)
   - Confidence score
   - Record count
   - Structure information

### Statistics

1. Navigate to "Statistics" tab
2. View:
   - Total files uploaded
   - Total storage size
   - Breakdown by file type

## API Endpoints

### File Upload
```bash
# Single file upload
curl -X POST http://localhost:8000/api/upload/file/ \
  -F "file=@/path/to/file.jpg" \
  -F "user_comment=Photo from vacation"

# Batch upload
curl -X POST http://localhost:8000/api/upload/batch/ \
  -F "files=@file1.jpg" \
  -F "files=@file2.jpg" \
  -F "user_comment=Vacation photos"
```

### JSON Upload
```bash
curl -X POST http://localhost:8000/api/upload/json/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"name": "John", "age": 30},
    "name": "users",
    "user_comment": "User data",
    "force_db_type": "SQL"
  }'
```

### List Files
```bash
# All files
curl http://localhost:8000/api/media-files/

# Filter by category
curl http://localhost:8000/api/media-files/?detected_type=images
```

### Statistics
```bash
curl http://localhost:8000/api/media-files/statistics/
```

### List JSON Datasets
```bash
curl http://localhost:8000/api/json-stores/
```

### Query JSON Data
```bash
curl http://localhost:8000/api/json-stores/1/query/?limit=100
```

### Health Check
```bash
curl http://localhost:8000/api/health/
```

## Technology Stack

### Backend
- **Django 5.0**: Web framework
- **Django REST Framework**: API development
- **PostgreSQL 15**: SQL database
- **MongoDB 7.0**: NoSQL database
- **Ollama + Llama3**: AI-powered analysis
- **python-magic**: File type detection
- **psycopg2**: PostgreSQL adapter
- **pymongo**: MongoDB driver

### Frontend
- **HTML5**: Markup
- **CSS3**: Modern styling with gradients and animations
- **Vanilla JavaScript**: No frameworks, pure JS
- **Fetch API**: HTTP requests

### AI/ML
- **Ollama**: Local LLM runtime
- **Llama3**: Language model for text analysis
- **Llama3.2 Vision**: Image content analysis

## Color Scheme

The frontend uses a modern, professional dark theme:
- Primary: Indigo (`#6366f1`)
- Secondary: Emerald (`#10b981`)
- Background: Slate dark (`#0f172a`)
- Accent: Gradient combinations

## Troubleshooting

### Arch Linux Specific Issues

#### Pip Install Blocked (PEP 668 Error)
```bash
# Arch uses externally managed Python environments
# ALWAYS use a virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements_minimal.txt

# Never use --break-system-packages (it can damage your system)
```

#### MongoDB Service Name
```bash
# On Arch, the service is 'mongodb', not 'mongod'
sudo systemctl status mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

#### PostgreSQL Not Initialized
```bash
# If PostgreSQL fails to start, initialize the database cluster
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl start postgresql
```

#### Ollama Service
```bash
# Check if Ollama service is running
sudo systemctl status ollama

# Start Ollama service (preferred on Arch)
sudo systemctl start ollama

# Or run manually
ollama serve
```

#### Python Version Compatibility
```bash
# Some packages may have issues with Python 3.13
# Check Python version
python --version

# If needed, use Python 3.11 or 3.12
# Install from AUR: python311 or python312
yay -S python311
python3.11 -m venv venv
```

---

### General Troubleshooting

#### Ollama Connection Error
```bash
# Check if Ollama is running
ollama list

# Check service status (Arch/systemd)
sudo systemctl status ollama

# Start Ollama service
sudo systemctl start ollama  # Arch
ollama serve                 # Manual start
```

#### PostgreSQL Connection Error
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# On Arch, check if initialized
sudo -u postgres initdb -D /var/lib/postgres/data
```

#### MongoDB Connection Error
```bash
# Check MongoDB status
# On Arch Linux: service name is 'mongodb'
sudo systemctl status mongodb  # Arch
sudo systemctl status mongod   # Ubuntu/Debian

# Start MongoDB
sudo systemctl start mongodb   # Arch
sudo systemctl start mongod    # Ubuntu/Debian
```

#### File Upload Error (Magic)
```bash
# Install libmagic
sudo pacman -S file            # Arch
sudo apt install libmagic1     # Ubuntu/Debian
brew install libmagic          # macOS
```

#### CORS Errors
- Ensure `corsheaders` is properly configured in Django settings
- Check that frontend is accessing correct API URL (http://localhost:8000)
- Verify CORS_ALLOW_ALL_ORIGINS is True in development

#### Database Connection Refused
```bash
# Check if databases are running
sudo systemctl status postgresql mongodb

# Check connection with psql
sudo -u postgres psql -c "SELECT version();"

# Check MongoDB connection
mongosh --eval "db.version()"

# Verify .env file has correct credentials
cat backend/.env
```

#### Pillow Build Errors
```bash
# If Pillow fails to build, install system dependencies
sudo pacman -S libjpeg-turbo zlib libtiff libwebp  # Arch
sudo apt install libjpeg-dev zlib1g-dev            # Ubuntu/Debian

# Then reinstall Pillow
pip install --upgrade Pillow
```

## Project Structure Details

### Backend Modules

1. **file_detector.py**: Multi-layer file detection
   - Magic bytes analysis
   - MIME type detection
   - Extension validation
   - Confidence scoring

2. **ai_analyzer.py**: AI-powered analysis
   - Image content analysis
   - Text file categorization
   - JSON structure analysis
   - Database recommendation logic

3. **db_manager.py**: Database abstraction
   - PostgreSQL table creation
   - MongoDB collection management
   - Schema generation
   - Data querying

4. **models.py**: Data models
   - MediaFile: File tracking
   - JSONDataStore: JSON dataset tracking
   - UploadBatch: Batch operation tracking

## Performance Considerations

- **File Size Limits**: Default 100MB (configurable in settings)
- **Batch Processing**: Processes files sequentially to avoid memory issues
- **AI Timeout**: 60 seconds per analysis
- **Database Connections**: Connection pooling enabled

## Security Notes

- Change default passwords in production
- Use environment variables for secrets
- Enable SSL/TLS for production databases
- Implement user authentication for production use
- Sanitize file uploads (currently development mode)

## Future Enhancements

- User authentication and multi-tenancy
- File preview generation (thumbnails)
- Advanced search and filtering
- Cloud storage integration (S3, Azure)
- Real-time upload progress with WebSockets
- File versioning
- Duplicate detection
- Compression and optimization

## Contributing

This is a professional implementation following best practices:
- Clean architecture with separation of concerns
- Comprehensive error handling
- Detailed logging
- Type hints and documentation
- Modular, reusable components

## License

[Your License Here]

## Support

For issues or questions:
- Check the troubleshooting section
- Review API documentation
- Examine logs in `backend/` directory
- Test with health check endpoint

## Credits

Built with:
- Django & DRF
- Ollama & Llama3
- PostgreSQL & MongoDB
- Modern web technologies
