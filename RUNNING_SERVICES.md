# Running Services - Definitive Guide

This guide provides the **definitive way** to consistently run the Intelligent Storage System backend and frontend.

## Quick Start

### Start Everything
```bash
./start.sh
```

This single command starts:
- MongoDB (NoSQL database)
- Django Backend (API server on port 8000)
- Frontend (Web UI on port 3000)

All services run in the background, so you can close the terminal and they keep running.

### Check Status
```bash
./status.sh
```

Shows which services are running with their PIDs and ports.

### Stop Everything
```bash
./stop.sh
```

Cleanly stops all services.

## Advanced Usage

### Start Without MongoDB
If you only want to use PostgreSQL:
```bash
./start.sh --no-mongodb
```

### Start Only Backend
```bash
./start.sh --backend-only
```

### Start Only Frontend
```bash
./start.sh --frontend-only
```

### Restart Services
```bash
./stop.sh && ./start.sh
```

## Access Points

After starting services:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Main web interface |
| Backend API | http://localhost:8000/api/ | REST API endpoints |
| Admin Panel | http://localhost:8000/admin/ | Django admin |
| MongoDB | mongodb://localhost:27017 | Database connection |

## Logs

View logs in real-time:

```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log

# MongoDB logs
tail -f mongodb_logs/mongodb.log

# All logs
tail -f backend.log frontend.log
```

## Troubleshooting

### Services won't start

1. **Check if ports are already in use:**
   ```bash
   # Check if something is using port 8000
   lsof -i :8000

   # Check if something is using port 3000
   lsof -i :3000
   ```

2. **Kill processes using the ports:**
   ```bash
   # Kill process on port 8000
   kill -9 $(lsof -t -i:8000)

   # Kill process on port 3000
   kill -9 $(lsof -t -i:3000)
   ```

3. **Check virtual environment exists:**
   ```bash
   ls -la backend/venv/
   ```

   If missing, create it:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements_minimal.txt
   cd ..
   ```

### Services keep stopping

Check the logs for errors:
```bash
cat backend.log
cat frontend.log
```

### MongoDB won't start

Check if MongoDB is installed:
```bash
which mongod
```

If not installed on Arch Linux:
```bash
sudo pacman -S mongodb-bin
```

### Clean restart

If things are messed up:
```bash
# Stop everything
./stop.sh

# Kill any lingering processes
killall mongod 2>/dev/null
pkill -f "manage.py runserver" 2>/dev/null
pkill -f "http.server 3000" 2>/dev/null

# Remove PID files
rm -rf .pids/

# Start fresh
./start.sh
```

## Backend Development Commands

For development tasks, use the backend helper script:

```bash
# From project root
cd backend
./run.sh [command]

# Or from anywhere
backend/run.sh [command]
```

Available commands:
- `./run.sh server` - Start server (foreground, for development)
- `./run.sh shell` - Django shell
- `./run.sh test` - Run tests
- `./run.sh migrate` - Run migrations
- `./run.sh makemigrations` - Create migrations
- `./run.sh superuser` - Create admin user
- `./run.sh help` - Show all commands

## Process Management

The scripts use PID files stored in `.pids/` directory to track running processes:

- `.pids/mongodb.pid` - MongoDB process ID
- `.pids/backend.pid` - Django backend process ID
- `.pids/frontend.pid` - Frontend server process ID

These files are automatically created when services start and removed when they stop.

## Best Practices

1. **Always use the management scripts** (`start.sh`, `stop.sh`, `status.sh`) for consistency
2. **Check status before starting** to avoid duplicate processes
3. **Stop services cleanly** before shutting down to prevent orphaned processes
4. **Monitor logs** when debugging issues
5. **Use backend/run.sh** for Django-specific tasks during development

## What's Different From Before

### Old Way (Inconsistent)
- Multiple scripts with path issues
- Manual process management
- No way to check what's running
- Processes stop when terminal closes
- Scripts only work from specific directories

### New Way (Consistent)
- Single unified startup: `./start.sh`
- Automatic background process management
- Status checking: `./status.sh`
- Clean shutdown: `./stop.sh`
- Scripts work from any directory
- PID tracking for reliability

## Summary

**To run the system consistently:**

1. Start: `./start.sh`
2. Check: `./status.sh`
3. Stop: `./stop.sh`

That's it! Everything else is handled automatically.
