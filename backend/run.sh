#!/bin/bash
# Helper script to run Django commands with the virtual environment
# Usage: ./run.sh [command]

VENV_PYTHON="./venv/bin/python"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please create it first:"
    echo "  python3 -m venv venv"
    echo "  ./venv/bin/pip install -r requirements_minimal.txt"
    exit 1
fi

case "$1" in
    server|runserver|run)
        echo -e "${GREEN}Starting Django server...${NC}"
        $VENV_PYTHON manage.py runserver 0.0.0.0:8000
        ;;

    shell)
        echo -e "${GREEN}Starting Django shell...${NC}"
        $VENV_PYTHON manage.py shell
        ;;

    test|tests)
        echo -e "${GREEN}Running tests...${NC}"
        if [ -n "$2" ]; then
            $VENV_PYTHON manage.py test "$2"
        else
            $VENV_PYTHON manage.py test storage
        fi
        ;;

    migrate)
        echo -e "${GREEN}Running migrations...${NC}"
        $VENV_PYTHON manage.py migrate
        ;;

    makemigrations)
        echo -e "${GREEN}Creating migrations...${NC}"
        $VENV_PYTHON manage.py makemigrations
        ;;

    superuser|createsuperuser)
        echo -e "${GREEN}Creating superuser...${NC}"
        $VENV_PYTHON manage.py createsuperuser
        ;;

    quotas|check-quotas)
        echo -e "${GREEN}Checking storage quotas...${NC}"
        $VENV_PYTHON manage.py check_quotas "$@"
        ;;

    cleanup)
        echo -e "${YELLOW}Cleaning up orphaned files...${NC}"
        $VENV_PYTHON manage.py cleanup_orphaned_files --all --dry-run
        ;;

    reindex)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Store name required${NC}"
            echo "Usage: ./run.sh reindex <store-name>"
            exit 1
        fi
        echo -e "${GREEN}Reindexing store: $2${NC}"
        $VENV_PYTHON manage.py reindex_store --store "$2"
        ;;

    export)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Store name required${NC}"
            echo "Usage: ./run.sh export <store-name> [output-file]"
            exit 1
        fi
        if [ -n "$3" ]; then
            $VENV_PYTHON manage.py export_store "$2" --output "$3"
        else
            $VENV_PYTHON manage.py export_store "$2"
        fi
        ;;

    sync-stats)
        echo -e "${GREEN}Syncing storage statistics...${NC}"
        $VENV_PYTHON manage.py sync_storage_stats --fix-discrepancies
        ;;

    check)
        echo -e "${GREEN}Running Django checks...${NC}"
        $VENV_PYTHON manage.py check
        ;;

    collectstatic)
        echo -e "${GREEN}Collecting static files...${NC}"
        $VENV_PYTHON manage.py collectstatic --noinput
        ;;

    pip)
        shift
        echo -e "${GREEN}Running pip: $@${NC}"
        ./venv/bin/pip "$@"
        ;;

    install)
        echo -e "${GREEN}Installing dependencies...${NC}"
        ./venv/bin/pip install -r requirements_minimal.txt
        ;;

    help|--help|-h)
        echo -e "${GREEN}Intelligent Storage System - Helper Script${NC}"
        echo ""
        echo "Usage: ./run.sh [command] [args]"
        echo ""
        echo "Commands:"
        echo "  server, runserver, run      Start Django development server"
        echo "  shell                       Start Django shell"
        echo "  test [test_name]            Run tests"
        echo "  migrate                     Run database migrations"
        echo "  makemigrations              Create new migrations"
        echo "  superuser                   Create superuser"
        echo "  quotas                      Check storage quotas"
        echo "  cleanup                     Clean up orphaned files (dry-run)"
        echo "  reindex <store>             Reindex a store"
        echo "  export <store> [file]       Export store data"
        echo "  sync-stats                  Sync storage statistics"
        echo "  check                       Run Django system checks"
        echo "  collectstatic               Collect static files"
        echo "  pip [args]                  Run pip with virtual environment"
        echo "  install                     Install dependencies"
        echo ""
        echo "Examples:"
        echo "  ./run.sh server"
        echo "  ./run.sh test storage.tests.test_models"
        echo "  ./run.sh reindex my-store"
        echo "  ./run.sh export my-store backup.json"
        echo "  ./run.sh pip list"
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run './run.sh help' for usage information"
        exit 1
        ;;
esac
