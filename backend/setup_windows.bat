@echo off
REM Windows Batch Setup Script for Intelligent Storage System
REM Run this script to set up the project on Windows (Command Prompt)

echo ========================================
echo Intelligent Storage System - Windows Setup
echo ========================================
echo.

REM Check Python version
echo Checking Python version...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies (Windows version)...
pip install -r requirements_windows.txt

REM Verify python-magic-bin
echo.
echo Verifying python-magic-bin installation...
python -c "import magic; print('✓ python-magic-bin works!')"

REM Create .env file if it doesn't exist
if not exist .env (
    echo.
    echo Creating .env file...
    (
        echo # Database Configuration
        echo DB_NAME=intelligent_storage
        echo DB_USER=postgres
        echo DB_PASSWORD=your_password
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo.
        echo # MongoDB Configuration
        echo MONGO_URI=mongodb://localhost:27017/
        echo MONGO_DB=intelligent_storage
        echo.
        echo # Django Settings
        echo SECRET_KEY=your-secret-key-here-change-in-production
        echo DEBUG=True
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo.
        echo # Ollama Configuration
        echo OLLAMA_BASE_URL=http://localhost:11434
    ) > .env
    echo ✓ Created .env file - Please update it with your configuration
)

REM Run migrations
echo.
echo Running database migrations...
python manage.py migrate

REM Collect static files
echo.
echo Collecting static files...
python manage.py collectstatic --noinput

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update .env file with your database credentials
echo 2. Create superuser: python manage.py createsuperuser
echo 3. Run server: python manage.py runserver
echo 4. Access admin: http://localhost:8000/admin/
echo.
echo Useful commands:
echo   python manage.py test storage          # Run tests
echo   python manage.py check_quotas          # Check storage quotas
echo   python manage.py cleanup_orphaned_files --all --dry-run
echo.
pause
