# Windows PowerShell Setup Script for Intelligent Storage System
# Run this script to set up the project on Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Intelligent Storage System - Windows Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.10+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies (Windows version)..." -ForegroundColor Yellow
pip install -r requirements_windows.txt

# Verify python-magic-bin
Write-Host ""
Write-Host "Verifying python-magic-bin installation..." -ForegroundColor Yellow
python -c "import magic; print('✓ python-magic-bin works!')"

# Create .env file if it doesn't exist
if (-Not (Test-Path .env)) {
    Write-Host ""
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    @"
# Database Configuration
DB_NAME=intelligent_storage
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=intelligent_storage

# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
"@ | Out-File -FilePath .env -Encoding UTF8
    Write-Host "✓ Created .env file - Please update it with your configuration" -ForegroundColor Green
}

# Run migrations
Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Yellow
python manage.py migrate

# Collect static files
Write-Host ""
Write-Host "Collecting static files..." -ForegroundColor Yellow
python manage.py collectstatic --noinput

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Update .env file with your database credentials" -ForegroundColor White
Write-Host "2. Create superuser: python manage.py createsuperuser" -ForegroundColor White
Write-Host "3. Run server: python manage.py runserver" -ForegroundColor White
Write-Host "4. Access admin: http://localhost:8000/admin/" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  python manage.py test storage          # Run tests" -ForegroundColor White
Write-Host "  python manage.py check_quotas          # Check storage quotas" -ForegroundColor White
Write-Host "  python manage.py cleanup_orphaned_files --all --dry-run" -ForegroundColor White
Write-Host ""
