# 🖥️ Platform-Specific Setup Guide

Choose your operating system for automated installation.

---

## 📋 Supported Platforms

| Platform | Version | Setup Script | Status |
|----------|---------|--------------|--------|
| **🐧 Ubuntu/Debian** | 20.04+ / 11+ | [setup/ubuntu/](setup/ubuntu/) | ✅ Ready |
| **🪟 Windows** | 10/11 | [setup/windows/](setup/windows/) | ✅ Ready |
| **🍎 macOS** | 11+ (Big Sur+) | [setup/macos/](setup/macos/) | ✅ Ready |
| **⚡ Arch Linux** | Latest | [setup/arch/](setup/arch/) | ✅ Ready |

---

## 🚀 Quick Start by Platform

### 🐧 Ubuntu/Debian

```bash
cd setup/ubuntu
chmod +x setup.sh
./setup.sh
```

**Installs:**
- Python 3.8+
- PostgreSQL 14
- MongoDB 7.0
- Redis
- All system dependencies

**Full Guide:** [setup/ubuntu/README.md](setup/ubuntu/README.md)

---

### 🪟 Windows

**Run PowerShell as Administrator:**

```powershell
cd setup\windows
.\setup.ps1
```

**Installs:**
- Chocolatey package manager
- Python 3.11
- PostgreSQL 14
- MongoDB 7.0
- Redis
- Visual C++ Build Tools

**Full Guide:** [setup/windows/README.md](setup/windows/README.md)

---

### 🍎 macOS

```bash
cd setup/macos
chmod +x setup.sh
./setup.sh
```

**Installs:**
- Homebrew (if not present)
- Python 3.11
- PostgreSQL 14
- MongoDB 7.0
- Redis
- System libraries

**Full Guide:** [setup/macos/README.md](setup/macos/README.md)

**Apple Silicon (M1/M2/M3):** Fully supported!

---

### ⚡ Arch Linux

```bash
cd setup/arch
chmod +x setup.sh
./setup.sh
```

**Installs:**
- Python 3.11
- PostgreSQL
- MongoDB
- Redis
- Build essentials

**Full Guide:** [setup/arch/README.md](setup/arch/README.md)

**Works on:** Arch Linux, Manjaro, EndeavourOS, ArcoLinux

---

## ⚙️ What Gets Installed

All platforms install:

### Core Services
- ✅ **Python 3.8+** - Backend runtime
- ✅ **PostgreSQL** - SQL database
- ✅ **MongoDB** - NoSQL database
- ✅ **Redis** - Caching layer

### System Libraries
- ✅ **libpq** - PostgreSQL client
- ✅ **libmagic** - File type detection
- ✅ **Pillow/JPEG** - Image processing
- ✅ **zlib** - Compression

### Python Packages
- Django 5.2+
- djangorestframework
- psycopg2-binary
- pymongo
- python-magic
- Pillow
- And more... (see `requirements_minimal.txt`)

---

## 📝 After Installation

### 1. Run Migrations

```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
python manage.py migrate
```

### 2. Start Server

```bash
python manage.py runserver
```

### 3. Access File Manager

Open browser:
```
http://localhost:8000/api/filemanager/
```

### 4. Create Admin User

```bash
curl -X POST http://localhost:8000/api/smart/auth/create \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123","email":"admin@example.com"}'
```

---

## 🔍 Platform Comparison

| Feature | Ubuntu | Windows | macOS | Arch |
|---------|--------|---------|-------|------|
| **Setup Time** | ~5-10 min | ~10-15 min | ~5-10 min | ~5 min |
| **Package Manager** | apt | Chocolatey | Homebrew | pacman |
| **Auto-start Services** | ✅ systemd | ✅ Services | ✅ launchd | ✅ systemd |
| **Python Version** | 3.8+ | 3.11 | 3.11 | 3.11 |
| **PostgreSQL** | 14 | 14 | 14 | Latest |
| **MongoDB** | 7.0 | 7.0 | 7.0 | Latest |

---

## 🛠️ Manual Installation

If you prefer manual setup, each platform guide includes detailed manual steps:

- [Ubuntu Manual Setup](setup/ubuntu/README.md#-manual-installation)
- [Windows Manual Setup](setup/windows/README.md#-manual-installation)
- [macOS Manual Setup](setup/macos/README.md#-manual-installation)
- [Arch Manual Setup](setup/arch/README.md#-manual-installation)

---

## 🔧 Troubleshooting

### General Issues

**Services Not Running:**
```bash
# Ubuntu/Arch
sudo systemctl status postgresql
sudo systemctl status mongodb
sudo systemctl status redis

# macOS
brew services list

# Windows
Get-Service | Where-Object {$_.Name -match "postgres|mongo|redis"}
```

**Database Connection Failed:**
- Check service is running
- Verify database was created
- Check connection settings in backend

**Python Packages Failed:**
- Ensure virtual environment is activated
- Install system dependencies first
- Check Python version (3.8+)

### Platform-Specific

See platform-specific troubleshooting:
- [Ubuntu Troubleshooting](setup/ubuntu/README.md#-troubleshooting)
- [Windows Troubleshooting](setup/windows/README.md#-troubleshooting)
- [macOS Troubleshooting](setup/macos/README.md#-troubleshooting)
- [Arch Troubleshooting](setup/arch/README.md#-troubleshooting)

---

## 📚 Additional Documentation

After setup, check out:

1. **[README_SMART_SYSTEM.md](README_SMART_SYSTEM.md)** - System overview
2. **[FILE_MANAGER_GUIDE.md](FILE_MANAGER_GUIDE.md)** - Web interface guide
3. **[SMART_FOLDERS_GUIDE.md](SMART_FOLDERS_GUIDE.md)** - 59 folder categories
4. **[QUICK_START.md](QUICK_START.md)** - Quick start guide
5. **[SMART_UPLOAD_GUIDE.md](SMART_UPLOAD_GUIDE.md)** - API documentation

---

## 🎯 Next Steps

1. **Choose your platform** from above
2. **Run the setup script**
3. **Start the server**
4. **Access file manager**
5. **Upload files** and enjoy!

---

## 💡 Tips

### For Developers

- Use **Ubuntu/Arch** for production-like environment
- Use **macOS** for native Apple development
- Use **Windows** if that's your primary OS

### For Production

All platforms are production-ready, but:
- **Ubuntu/Debian** - Most common for servers
- **Native Python** - Simpler deployment with virtual environments

### For Testing

- **Any platform** works great for development
- **Virtual environments** keep everything isolated
- **Services** can be stopped when not in use

---

## 🔄 Updates

To update the system:

```bash
# Pull latest changes
git pull

# Update Python packages
source venv/bin/activate  # or activate on your platform
pip install -U -r requirements_minimal.txt

# Run any new migrations
python manage.py migrate
```

---

**Choose your platform above and get started in minutes! 🚀**
