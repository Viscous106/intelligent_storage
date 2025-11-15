#!/usr/bin/env python
"""
Quick setup verification script for Windows and Linux
Run this to check if everything is configured correctly
"""

import sys
import os

def test_python_version():
    """Check Python version"""
    print("1. Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Need Python 3.10+")
        return False

def test_imports():
    """Test critical imports"""
    print("\n2. Testing critical imports...")

    tests = [
        ("Django", "django"),
        ("Django REST Framework", "rest_framework"),
        ("PostgreSQL adapter", "psycopg2"),
        ("MongoDB driver", "pymongo"),
        ("pgvector", "pgvector"),
        ("Python-magic", "magic"),
        ("Pillow", "PIL"),
        ("Requests", "requests"),
    ]

    all_passed = True
    for name, module in tests:
        try:
            __import__(module)
            print(f"   ✓ {name}")
        except ImportError as e:
            print(f"   ❌ {name} - {e}")
            all_passed = False

    return all_passed

def test_django_setup():
    """Test Django configuration"""
    print("\n3. Testing Django setup...")

    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        import django
        django.setup()
        print("   ✓ Django configured")
        return True
    except Exception as e:
        print(f"   ❌ Django setup failed - {e}")
        return False

def test_models():
    """Test model imports"""
    print("\n4. Testing model imports...")

    try:
        from storage.models import MediaFile, FileSearchStore, DocumentChunk
        print("   ✓ Models imported")
        return True
    except Exception as e:
        print(f"   ❌ Model import failed - {e}")
        return False

def test_syntax():
    """Test Python file syntax"""
    print("\n5. Testing Python syntax...")

    import py_compile
    import glob

    all_valid = True
    files_to_check = [
        'storage/*.py',
        'api/*.py',
        'core/*.py',
    ]

    for pattern in files_to_check:
        for filepath in glob.glob(pattern):
            try:
                py_compile.compile(filepath, doraise=True)
            except py_compile.PyCompileError as e:
                print(f"   ❌ {filepath} - Syntax error")
                all_valid = False

    if all_valid:
        print("   ✓ All Python files have valid syntax")

    return all_valid

def test_database_config():
    """Test database configuration"""
    print("\n6. Testing database configuration...")

    try:
        from django.conf import settings

        # Check PostgreSQL settings
        db_config = settings.DATABASES.get('default', {})
        if db_config.get('ENGINE') == 'django.db.backends.postgresql':
            print(f"   ✓ PostgreSQL configured")
            print(f"      Host: {db_config.get('HOST', 'localhost')}")
            print(f"      Port: {db_config.get('PORT', '5432')}")
            print(f"      Database: {db_config.get('NAME', 'N/A')}")
        else:
            print(f"   ⚠ Database engine: {db_config.get('ENGINE', 'Not set')}")

        # Check MongoDB settings
        if hasattr(settings, 'MONGODB_SETTINGS'):
            mongo = settings.MONGODB_SETTINGS
            print(f"   ✓ MongoDB configured")
            print(f"      Host: {mongo.get('HOST', 'localhost')}")
            print(f"      Port: {mongo.get('PORT', 27017)}")

        return True
    except Exception as e:
        print(f"   ❌ Database config error - {e}")
        return False

def test_file_organizer():
    """Test file organizer module"""
    print("\n7. Testing file organizer...")

    try:
        from storage.file_organizer import file_organizer
        print("   ✓ File organizer imported")
        print("   ✓ File organization system ready")
        return True
    except Exception as e:
        print(f"   ❌ File organizer error - {e}")
        return False

def test_media_directories():
    """Test media directory configuration"""
    print("\n8. Testing media directories...")

    try:
        from django.conf import settings

        media_root = settings.MEDIA_ROOT
        print(f"   ✓ MEDIA_ROOT: {media_root}")

        if hasattr(settings, 'STORAGE_DIRS'):
            storage_dirs = settings.STORAGE_DIRS
            print(f"   ✓ Storage directories configured:")
            for folder_type, path in storage_dirs.items():
                exists = "✓" if os.path.exists(path) else "⚠"
                print(f"      {exists} {folder_type}: {path}")

        return True
    except Exception as e:
        print(f"   ❌ Media directories error - {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("Intelligent Storage System - Setup Verification")
    print("="*60)

    results = [
        test_python_version(),
        test_imports(),
        test_django_setup(),
        test_models(),
        test_syntax(),
        test_database_config(),
        test_file_organizer(),
        test_media_directories(),
    ]

    print("\n" + "="*60)
    print("Summary")
    print("="*60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        print("\nYour setup is ready! Run:")
        print("  python manage.py runserver")
        sys.exit(0)
    else:
        print(f"⚠ {total - passed} test(s) failed ({passed}/{total} passed)")
        print("\nPlease fix the issues above before running the server.")
        sys.exit(1)

if __name__ == '__main__':
    main()
