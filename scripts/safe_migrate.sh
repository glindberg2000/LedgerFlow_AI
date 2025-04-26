#!/bin/bash

# Safe migration script for LedgerFlow
# Ensures backups are made and verified before running migrations

set -e

# Configuration
BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/migrations"
MIN_BACKUP_SIZE=10240  # 10KB minimum
POSTGRES_CONTAINER="ledgerflow-postgres-1"

# Ensure we're in production
if [ "$LEDGER_ENV" != "prod" ]; then
    echo "❌ This script is for production use only"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
BACKUP_FILE="$BACKUP_DIR/pre_migration_$(date +%Y%m%d_%H%M%S).dump"
echo "📦 Creating backup: $BACKUP_FILE"
echo "Note: This backup will be stored in iCloud at: $BACKUP_DIR"

docker compose exec -T postgres pg_dump -Fc --clean -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_FILE"

# Verify backup size
BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE")
if [ "$BACKUP_SIZE" -lt "$MIN_BACKUP_SIZE" ]; then
    echo "❌ ERROR: Backup file is too small ($BACKUP_SIZE bytes)"
    echo "Migration aborted for safety"
    exit 1
fi

# Verify backup can be restored
echo "🔍 Verifying backup integrity..."
docker compose -f docker-compose.dev.yml exec -T postgres pg_restore --list "$BACKUP_FILE" > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Backup verification failed"
    echo "Migration aborted for safety"
    exit 1
fi

echo "✅ Backup verified successfully"

# Run migrations with ALLOW_DANGEROUS=1
echo "🔄 Running migrations..."
ALLOW_DANGEROUS=1 docker compose exec django python manage.py migrate

echo "✅ Migrations completed successfully"
echo "Backup location: $BACKUP_FILE"
echo "Note: Backup is stored in iCloud and will be synced automatically" 