# Intelligent Storage System - Windows Installation Guide

## Quick Start for Windows

### Prerequisites

1. **Python 3.10+**
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **PostgreSQL 15+**
   - Download: https://www.postgresql.org/download/windows/
   - Install with default settings
   - Remember your postgres password!

3. **MongoDB Community Edition** (Optional)
   - Download: https://www.mongodb.com/try/download/community
   - Install with default settings

4. **Git for Windows** (Optional, for cloning)
   - Download: https://git-scm.com/download/win

### Installation Methods

#### Method 1: Automated Setup (Recommended)

**Using PowerShell:**
```powershell
# Open PowerShell as Administrator
cd path\to\intelligent_storage\backend

# Allow script execution (first time only)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run setup script
.\setup_windows.ps1
```

**Using Command Prompt:**
```cmd
cd path\to\intelligent_storage\backend
setup_windows.bat
```

#### Method 2: Manual Installation

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1    # PowerShell
# OR
venv\Scripts\activate.bat      # Command Prompt

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install Windows-compatible dependencies
pip install -r requirements_windows.txt

# 5. Create .env file
copy .env.example .env
# Edit .env with your database credentials

# 6. Run migrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Run server
python manage.py runserver
```

## Windows-Specific Notes

### File Detection Library

The project uses `python-magic-bin` on Windows instead of `python-magic`:
- ✅ **Included in requirements_windows.txt**
- ✅ **No additional DLL installation needed**
- ✅ **Works out of the box**

### Database Setup (Windows)

**PostgreSQL:**
```powershell
# After installing PostgreSQL, create database:
# Open SQL Shell (psql) from Start Menu

# Enter your postgres password, then:
CREATE DATABASE intelligent_storage;
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE intelligent_storage TO your_user;

# Install pgvector extension
CREATE EXTENSION vector;
```

**MongoDB:**
```powershell
# MongoDB runs as a Windows Service automatically
# Check if running:
sc query MongoDB

# Start if not running:
net start MongoDB
```

### Running the Server (Windows)

**Development Server:**
```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run server
python manage.py runserver

# Access at: http://localhost:8000/
# Admin: http://localhost:8000/admin/
```

**Run in Background (PowerShell):**
```powershell
Start-Process python -ArgumentList "manage.py", "runserver" -NoNewWindow -PassThru
```

**Run in Background (Command Prompt):**
```cmd
start /B python manage.py runserver
```

## Management Commands (Windows)

All management commands work identically on Windows:

```powershell
# Check storage quotas
python manage.py check_quotas

# Clean up orphaned files
python manage.py cleanup_orphaned_files --all --dry-run

# Reindex a store
python manage.py reindex_store --store my-store

# Export store
python manage.py export_store my-store --output backup.json

# Sync statistics
python manage.py sync_storage_stats --fix-discrepancies

# Run tests
python manage.py test storage
```

## Common Windows Issues & Solutions

### Issue 1: "python-magic" import error

**Error:**
```
ImportError: failed to find libmagic
```

**Solution:**
```powershell
pip uninstall python-magic
pip install python-magic-bin
```

### Issue 2: PostgreSQL connection error

**Error:**
```
django.db.utils.OperationalError: could not connect to server
```

**Solution:**
```powershell
# Check if PostgreSQL is running:
sc query postgresql-x64-15  # Check service name

# Start if not running:
net start postgresql-x64-15

# Verify .env settings:
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
```

### Issue 3: Permission denied on file operations

**Error:**
```
PermissionError: [WinError 5] Access is denied
```

**Solution:**
```powershell
# Run PowerShell as Administrator
# OR
# Check antivirus isn't blocking Python
# Add exception for project folder
```

### Issue 4: Virtual environment activation error

**Error:**
```
Activate.ps1 cannot be loaded because running scripts is disabled
```

**Solution:**
```powershell
# Run as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## File Structure (Windows Paths)

```
C:\path\to\intelligent_storage\backend\
├── venv\                          # Virtual environment
├── storage\
│   ├── admin.py                   # Admin interface
│   ├── forms.py                   # Forms
│   ├── middleware.py              # Middleware
│   ├── signals.py                 # Signals
│   ├── management\
│   │   └── commands\              # Management commands
│   ├── tests\                     # Test suite
│   └── ...
├── media\                         # Uploaded files
├── static\                        # Static files
├── .env                           # Environment variables
├── manage.py
├── requirements_windows.txt       # Windows dependencies
├── setup_windows.ps1              # PowerShell setup script
└── setup_windows.bat              # Batch setup script
```

## Environment Variables (.env)

```ini
# Database Configuration
DB_NAME=intelligent_storage
DB_USER=postgres
DB_PASSWORD=YourPostgresPassword
DB_HOST=localhost
DB_PORT=5432

# MongoDB Configuration (Optional)
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=intelligent_storage

# Django Settings
SECRET_KEY=generate-a-random-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Media/Static Files (Windows paths)
MEDIA_ROOT=C:\path\to\intelligent_storage\backend\media
STATIC_ROOT=C:\path\to\intelligent_storage\backend\static

# Ollama Configuration (if using AI features)
OLLAMA_BASE_URL=http://localhost:11434
```

## Testing on Windows

```powershell
# Run all tests
python manage.py test storage

# Run specific test file
python manage.py test storage.tests.test_models

# Run with verbosity
python manage.py test storage --verbosity=2

# Run with coverage (install coverage first)
pip install coverage
coverage run --source='storage' manage.py test storage
coverage report
coverage html  # Generate HTML report
```

## Development Tools (Windows)

**Recommended:**
- **Visual Studio Code** with Python extension
- **PostgreSQL pgAdmin** for database management
- **MongoDB Compass** for MongoDB management
- **Postman** or **Insomnia** for API testing

## Performance on Windows

The application performs identically on Windows and Linux:
- ✅ Same database performance
- ✅ Same file upload speeds
- ✅ Same API response times
- ✅ All Django features work identically

## Production Deployment (Windows Server)

For production on Windows Server:

1. **Use IIS with wfastcgi**
   ```powershell
   pip install wfastcgi
   wfastcgi-enable
   ```

2. **Or use Waitress WSGI server**
   ```powershell
   pip install waitress
   waitress-serve --port=8000 core.wsgi:application
   ```

3. **Or use Apache with mod_wsgi**
   - Install Apache for Windows
   - Install mod_wsgi-httpd

## Support

For Windows-specific issues:
1. Check WINDOWS_COMPATIBILITY_REPORT.md
2. Ensure you're using requirements_windows.txt
3. Verify all prerequisites are installed
4. Check Windows Firewall isn't blocking ports

## Quick Reference

| Action | Command |
|--------|---------|
| Activate venv (PS) | `.\venv\Scripts\Activate.ps1` |
| Activate venv (CMD) | `venv\Scripts\activate.bat` |
| Run server | `python manage.py runserver` |
| Create superuser | `python manage.py createsuperuser` |
| Run migrations | `python manage.py migrate` |
| Run tests | `python manage.py test storage` |
| Check quotas | `python manage.py check_quotas` |
| Admin URL | http://localhost:8000/admin/ |
| API docs | http://localhost:8000/api/ |

## Summary

✅ **The Intelligent Storage System is fully compatible with Windows!**

All Django framework components work identically on Windows:
- Admin interface
- Forms and validation
- Middleware
- Signals
- Management commands
- Template views
- Authentication
- Permissions
- Testing
- Caching
- Optimization

The only difference is using `python-magic-bin` instead of `python-magic`, which is handled automatically by `requirements_windows.txt`.
