#!/bin/bash

# Safe database testing script for LedgerFlow
# Ensures backups are made before any destructive testing

set -e

# Configuration
DEV_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/test"
PROD_BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/prod"
CONTAINER_BACKUP_DIR="/backups/test"
MIN_BACKUP_SIZE=10240  # 10KB minimum

# Determine environment
if [ "$LEDGER_ENV" = "prod" ]; then
    BACKUP_DIR="$PROD_BACKUP_DIR"
    COMPOSE_FILE="docker-compose.prod.yml"
    PROJECT_NAME="ledger-prod"
    source .env.prod
    DB_USER="$POSTGRES_USER"
    DB_NAME="$POSTGRES_DB"
else
    BACKUP_DIR="$DEV_BACKUP_DIR"
    COMPOSE_FILE="docker-compose.dev.yml"
    PROJECT_NAME="ledger-dev"
    DB_USER="newuser"
    DB_NAME="mydatabase"
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pre_test_${TIMESTAMP}.dump"
CONTAINER_BACKUP_FILE="$CONTAINER_BACKUP_DIR/pre_test_${TIMESTAMP}.dump"
echo "📦 Creating safety backup: $BACKUP_FILE"
echo "Note: This backup will be stored in iCloud at: $BACKUP_DIR"

# Ensure the backup directory is mounted
if ! docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" config | grep -q "$BACKUP_DIR"; then
    echo "❌ ERROR: Backup directory is not mounted in docker-compose config"
    echo "Please add this volume to the postgres service:"
    echo "    - $BACKUP_DIR:$CONTAINER_BACKUP_DIR"
    exit 1
fi

# Create backup
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T postgres \
    pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc --clean -f "$CONTAINER_BACKUP_FILE"

# Verify backup size
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERROR: Backup file was not created"
    exit 1
fi

BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE")
if [ "$BACKUP_SIZE" -lt "$MIN_BACKUP_SIZE" ]; then
    echo "❌ ERROR: Backup file is too small ($BACKUP_SIZE bytes)"
    echo "Testing aborted for safety"
    exit 1
fi

# Verify backup can be restored
echo "🔍 Verifying backup integrity..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T postgres \
    pg_restore --list "$CONTAINER_BACKUP_FILE" > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Backup verification failed"
    echo "Testing aborted for safety"
    exit 1
fi

# Test restore in temporary database
TEMP_DB="test_restore_${TIMESTAMP}"
echo "🔄 Testing restore in temporary database: $TEMP_DB"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T postgres \
    createdb -U "$DB_USER" "$TEMP_DB"

docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T postgres \
    pg_restore -U "$DB_USER" -d "$TEMP_DB" "$CONTAINER_BACKUP_FILE"

# Cleanup test database
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T postgres \
    dropdb -U "$DB_USER" "$TEMP_DB"

echo "✅ Safety backup created and verified"
echo "You can now proceed with database testing"
echo "To restore this backup:"
echo "  Development: ./restore_db_clean.sh -f $BACKUP_FILE"
echo "  Production:  ./restore_db_clean.sh -e prod -f $BACKUP_FILE -u $DB_USER -d $DB_NAME"
echo
echo "Note: Backup is stored in iCloud and will be synced automatically" 