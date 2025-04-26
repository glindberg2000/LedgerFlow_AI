#!/bin/bash

# Default values
COMPOSE_FILE="docker-compose.dev.yml"
DB_USER="newuser"
DB_NAME="mydatabase"
ICLOUD_BACKUP_ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups"

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo
    echo "Restore a PostgreSQL database from a backup file"
    echo
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -f, --file FILE      Docker compose file to use (default: docker-compose.dev.yml)"
    echo "  -u, --user USER      Database user (default: newuser)"
    echo "  -d, --database DB    Database name (default: mydatabase)"
    echo
    echo "BACKUP_FILE can be either .sql.gz or .dump format"
    echo
    echo "Note: Backups should be stored in iCloud at:"
    echo "$ICLOUD_BACKUP_ROOT"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -u|--user)
            DB_USER="$2"
            shift 2
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Validate backup file
if [ -z "$BACKUP_FILE" ]; then
    echo "Error: No backup file specified"
    show_help
    exit 1
fi

# Convert potential iCloud Drive path to actual iCloud path
BACKUP_FILE="${BACKUP_FILE//'iCloud Drive'/'Library/Mobile Documents/com~apple~CloudDocs'}"

if [ ! -f "$BACKUP_FILE" ]; then
    # Try with full home path if relative path was provided
    if [[ "$BACKUP_FILE" != /* ]]; then
        BACKUP_FILE="$ICLOUD_BACKUP_ROOT/$BACKUP_FILE"
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file not found at $BACKUP_FILE"
        echo
        echo "Please ensure the backup is in the iCloud backup directory:"
        echo "$ICLOUD_BACKUP_ROOT"
        exit 1
    fi
fi

# Determine file type
file_ext="${BACKUP_FILE##*.}"

# Validate Docker Compose file
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: Docker compose file not found at $COMPOSE_FILE"
    exit 1
fi

# Check if Docker is running and the container is available
if ! docker compose -f "$COMPOSE_FILE" ps postgres >/dev/null 2>&1; then
    echo "Error: PostgreSQL container is not running"
    echo "Please start the containers with: docker compose -f $COMPOSE_FILE up -d"
    exit 1
fi

echo "Using backup file: $BACKUP_FILE"
echo "Note: This file should be synced to iCloud for safety"

echo "Dropping existing tables..."
if ! docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$DB_USER" "$DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; then
    echo "Error: Failed to drop existing tables"
    exit 1
fi

echo "Restoring from backup..."
case "$file_ext" in
    "gz")
        if ! gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "$DB_USER" "$DB_NAME"; then
            echo "Error: Failed to restore from .gz backup"
            exit 1
        fi
        ;;
    "dump")
        if ! docker compose -f "$COMPOSE_FILE" exec -T postgres pg_restore -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"; then
            echo "Error: Failed to restore from .dump backup"
            exit 1
        fi
        ;;
    *)
        echo "Error: Unsupported backup format. Only .sql.gz and .dump files are supported"
        exit 1
        ;;
esac

echo "Database restore completed successfully!" 