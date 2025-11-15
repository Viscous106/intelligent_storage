# Windows Setup - Fixed Issues

## Issue Fixed: SyntaxError in db_manager.py

### Problem
```
File "C:\Users\kanha\Downloads\HACK\intelligent_storage\backend\storage\db_manager.py", line 270
    );"""
         ^
SyntaxError: f-string expression part cannot include a backslash
```

### Root Cause
Python f-strings cannot contain backslash characters (like `\n`) inside the expression part `{}`. This is a Python language limitation.

**Before (BROKEN)**:
```python
create_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
    {',\n    '.join(columns)}  # ❌ \n inside f-string expression
);"""
```

**After (FIXED)**:
```python
# Join columns with newlines (can't use \n in f-string)
columns_str = ',\n    '.join(columns)
create_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
    {columns_str}  # ✓ No backslash in f-string
);"""
```

### Fix Applied
The fix extracts the join operation outside the f-string, storing the result in `columns_str` variable, then using that in the f-string.

---

## How to Set Up on Windows (CORRECTED)

### Step 1: Navigate to Backend Directory
```powershell
cd C:\Users\kanha\Downloads\HACK\intelligent_storage\backend
```

### Step 2: Run Setup Script (PowerShell)
```powershell
# In PowerShell, use .\ prefix
.\setup_windows.ps1
```

**OR** if you prefer Command Prompt:
```cmd
# In CMD, use .\ prefix
.\setup_windows.bat
```

**Note**: PowerShell requires `.\` prefix to run scripts in current directory for security reasons.

---

## Alternative: Manual Setup on Windows

If the scripts don't work, here's the manual process:

### 1. Create Virtual Environment
```powershell
python -m venv venv
```

### 2. Activate Virtual Environment
```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# OR Command Prompt
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies
```powershell
pip install -r requirements_windows.txt
```

### 4. Create .env File
Copy `.env.example` to `.env` and configure:
```
POSTGRES_NAME=intelligent_storage_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 5. Run Migrations
```powershell
python manage.py migrate
```

### 6. Create Superuser
```powershell
python create_admin.py
```
This creates admin user:
- Username: `Viscous106`
- Password: `787898`

### 7. Run Server
```powershell
python manage.py runserver
```

---

## PostgreSQL Setup on Windows

### Option 1: Install PostgreSQL
1. Download from https://www.postgresql.org/download/windows/
2. Install and note the password you set
3. Create database:
```sql
CREATE DATABASE intelligent_storage_db;
CREATE EXTENSION IF NOT EXISTS vector;
```

### Option 2: Use Docker (Recommended)
```powershell
# Install Docker Desktop for Windows first
# Then run PostgreSQL with pgvector:

docker run -d `
  --name postgres-pgvector `
  -e POSTGRES_PASSWORD=postgres123 `
  -e POSTGRES_DB=intelligent_storage_db `
  -p 5432:5432 `
  ankane/pgvector:latest

# Wait for container to start
Start-Sleep -Seconds 5

# Create the vector extension
docker exec postgres-pgvector psql -U postgres -d intelligent_storage_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Common Windows Issues & Solutions

### Issue 1: PowerShell Execution Policy
**Error**: "cannot be loaded because running scripts is disabled"

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue 2: Python Not Found
**Error**: "'python' is not recognized"

**Solution**:
- Install Python from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- Or use full path: `C:\Users\YourName\AppData\Local\Programs\Python\Python310\python.exe`

### Issue 3: Port Already in Use
**Error**: "Error: That port is already in use"

**Solution**:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use different port
python manage.py runserver 8001
```

### Issue 4: PostgreSQL Connection Error
**Error**: "could not connect to server"

**Solution**:
- Ensure PostgreSQL is running:
  - Windows Services → PostgreSQL → Start
  - Or Docker: `docker start postgres-pgvector`
- Check `.env` file has correct credentials
- Verify PostgreSQL port 5432 is open

### Issue 5: python-magic Error (SHOULD BE FIXED)
**Error**: "failed to find libmagic"

**Solution**: This is already handled by `requirements_windows.txt` which uses `python-magic-bin` instead of `python-magic`. If you still get this error:
```powershell
pip uninstall python-magic
pip install python-magic-bin
```

---

## Verify Installation

### Test Python Syntax
```powershell
python -m py_compile storage/db_manager.py
# Should show no errors
```

### Test Database Connection
```powershell
python manage.py check
```

### Test Server
```powershell
python manage.py runserver
```
Visit: http://localhost:8000/admin/

---

## Quick Start Commands (Windows)

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create admin user
python create_admin.py

# Run tests
python manage.py test storage

# Check quotas
python manage.py check_quotas

# Cleanup orphaned files
python manage.py cleanup_orphaned_files --all --dry-run

# Access web interfaces
# Admin: http://localhost:8000/admin/
# File Browser: http://localhost:8000/files/browse/
# API: http://localhost:8000/api/
```

---

## What's Working Now

After the fix, all of these should work:
- ✓ Virtual environment creation
- ✓ Dependency installation (python-magic-bin)
- ✓ Python syntax (no more f-string error)
- ✓ Database migrations
- ✓ Admin user creation
- ✓ Server startup
- ✓ File organization system
- ✓ Frontend file browser
- ✓ All API endpoints

---

## Next Steps

1. **Fix Applied**: The f-string syntax error in `db_manager.py` is now fixed
2. **Try Again**: Run the setup script:
   ```powershell
   .\setup_windows.ps1
   ```
3. **Or Manual**: Follow the manual setup steps above
4. **Start Server**:
   ```powershell
   python manage.py runserver
   ```
5. **Access**: http://localhost:8000/files/browse/

---

## Support

If you encounter any other issues:
1. Check the error message carefully
2. Ensure PostgreSQL is running
3. Verify all dependencies installed: `pip list`
4. Check Python version: `python --version` (should be 3.10+)
5. Try deactivating and reactivating virtual environment

**Admin Credentials**:
- Username: `Viscous106`
- Password: `787898`
- URL: http://localhost:8000/admin/
