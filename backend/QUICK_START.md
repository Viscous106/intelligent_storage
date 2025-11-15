# Quick Start Guide - IMPORTANT!

## ⚠️ Common Error: ModuleNotFoundError

If you see this error:
```
ModuleNotFoundError: No module named 'rest_framework'
```

**You're using the wrong Python!** You need to use the virtual environment.

---

## ✅ Correct Way to Run

### Option 1: Use venv Python directly (RECOMMENDED)
```bash
./venv/bin/python manage.py runserver
```

### Option 2: Activate venv first
```bash
# Activate virtual environment
source venv/bin/activate

# Now you can use 'python' directly
python manage.py runserver
```

### Option 3: Create an alias
```bash
# Add to ~/.bashrc or ~/.zshrc
alias vpy='/home/viscous/Viscous/intelligent_storage/backend/venv/bin/python'
alias vpm='/home/viscous/Viscous/intelligent_storage/backend/venv/bin/python manage.py'

# Then use:
vpm runserver
```

---

## 🔍 How to Verify

### Check which Python you're using:
```bash
# WRONG - System Python (no packages)
which python
# Output: /usr/bin/python  ❌

# RIGHT - Virtual environment Python
which venv/bin/python
# Output: /path/to/venv/bin/python  ✅
```

### Check installed packages:
```bash
# WRONG - System packages
python -m pip list

# RIGHT - Virtual environment packages
./venv/bin/pip list
```

---

## 📋 All Commands (Use Virtual Environment)

```bash
# Server
./venv/bin/python manage.py runserver

# Migrations
./venv/bin/python manage.py migrate

# Create superuser
./venv/bin/python manage.py createsuperuser

# Run tests
./venv/bin/python manage.py test storage

# Management commands
./venv/bin/python manage.py check_quotas
./venv/bin/python manage.py cleanup_orphaned_files --all --dry-run
./venv/bin/python manage.py reindex_store --store my-store

# Shell
./venv/bin/python manage.py shell
```

---

## 🚀 Quick Fix for Your Current Error

**Stop the current server:**
```bash
# Find and kill the process
ps aux | grep runserver
kill <PID>
```

**Start with correct Python:**
```bash
./venv/bin/python manage.py runserver 0.0.0.0:8000
```

---

## 💡 Pro Tip: Create a Helper Script

Create `run.sh` in the backend directory:

```bash
#!/bin/bash
# Save as: run.sh

VENV_PYTHON="./venv/bin/python"

case "$1" in
    server|runserver)
        $VENV_PYTHON manage.py runserver 0.0.0.0:8000
        ;;
    shell)
        $VENV_PYTHON manage.py shell
        ;;
    test)
        $VENV_PYTHON manage.py test storage
        ;;
    migrate)
        $VENV_PYTHON manage.py migrate
        ;;
    superuser)
        $VENV_PYTHON manage.py createsuperuser
        ;;
    quotas)
        $VENV_PYTHON manage.py check_quotas
        ;;
    *)
        echo "Usage: ./run.sh [server|shell|test|migrate|superuser|quotas]"
        ;;
esac
```

Make it executable:
```bash
chmod +x run.sh
```

Use it:
```bash
./run.sh server
./run.sh test
./run.sh quotas
```

---

## 🔧 Why This Happens

**Virtual environments isolate Python packages:**
- System Python: `/usr/bin/python` (no Django installed)
- Virtual env Python: `./venv/bin/python` (has all packages)

When you run `python manage.py runserver`, it uses **system Python** which doesn't have Django/REST framework installed.

When you run `./venv/bin/python manage.py runserver`, it uses the **virtual environment Python** which has everything installed.

---

## ✅ Verification Checklist

Before running the server:

```bash
# 1. Check you're in the right directory
pwd
# Should output: /home/viscous/Viscous/intelligent_storage/backend

# 2. Check virtual environment exists
ls venv/bin/python
# Should output: venv/bin/python

# 3. Check packages are installed
./venv/bin/pip list | grep Django
# Should show: Django 5.2.8

# 4. Check packages are installed
./venv/bin/pip list | grep djangorestframework
# Should show: djangorestframework 3.16.1

# 5. Now run server
./venv/bin/python manage.py runserver
```

---

## 🎯 Remember

**Always use one of these:**
1. `./venv/bin/python manage.py <command>`
2. `source venv/bin/activate` then `python manage.py <command>`
3. Create alias or helper script

**Never use:**
- ❌ `python manage.py <command>` (uses system Python)
- ❌ `/usr/bin/python manage.py <command>` (system Python)
