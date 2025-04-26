#!/bin/bash

# Configuration
BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev"
COMPOSE_FILE="docker-compose.dev.yml"
MIN_BACKUP_SIZE=10240  # 10KB minimum size
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DJANGO_CONTAINER="ledger-dev-django-1"
POSTGRES_CONTAINER="ledger-dev-postgres-1"

# Exit on any error
set -e

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if container exists and is running
check_container() {
    local container=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log "ERROR: Container $container is not running!"
        exit 1
    fi
}

# Check required containers
check_container $DJANGO_CONTAINER
check_container $POSTGRES_CONTAINER

# Create backup directories
mkdir -p "$BACKUP_DIR/full_backup_$TIMESTAMP"/{db,media,config,logs}

# 1. Database Backup
log "Starting database backup..."
DB_BACKUP_FILE="$BACKUP_DIR/full_backup_$TIMESTAMP/db/database.sql.gz"
docker compose -f $COMPOSE_FILE exec -T postgres pg_dump -U newuser mydatabase | gzip > "$DB_BACKUP_FILE"

# Check DB backup size
DB_SIZE=$(stat -f%z "$DB_BACKUP_FILE")
if [ "$DB_SIZE" -lt "$MIN_BACKUP_SIZE" ]; then
    log "ERROR: Database backup file is too small ($DB_SIZE bytes)!"
    exit 1
fi

# 2. Media Files Backup
log "Backing up media files..."
docker cp $DJANGO_CONTAINER:/app/media/. "$BACKUP_DIR/full_backup_$TIMESTAMP/media/"

# 3. Configuration Backup
log "Backing up configuration..."
# Environment files
cp .env.dev "$BACKUP_DIR/full_backup_$TIMESTAMP/config/"
cp docker-compose.dev.yml "$BACKUP_DIR/full_backup_$TIMESTAMP/config/"

# 4. Application State
log "Backing up application state..."
docker compose -f $COMPOSE_FILE exec -T django python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > "$BACKUP_DIR/full_backup_$TIMESTAMP/db/fixtures.json"

# 5. Create manifest
log "Creating backup manifest..."
cat > "$BACKUP_DIR/full_backup_$TIMESTAMP/manifest.txt" << EOF
LedgerFlow Development Backup
============================
Timestamp: $(date)
Database Size: $(ls -lh "$DB_BACKUP_FILE" | awk '{print $5}')
Media Files: $(find "$BACKUP_DIR/full_backup_$TIMESTAMP/media" -type f | wc -l) files
Configuration Files: $(ls -1 "$BACKUP_DIR/full_backup_$TIMESTAMP/config" | wc -l) files

Git Commit: $(git rev-parse HEAD)
Git Branch: $(git rev-parse --abbrev-ref HEAD)

Container Versions:
------------------
$(docker compose -f $COMPOSE_FILE ps)

Database Tables:
---------------
$(docker compose -f $COMPOSE_FILE exec -T postgres psql -U newuser mydatabase -c "\dt" 2>/dev/null)

Note: This backup is stored in iCloud and will be synced automatically.
Location: $BACKUP_DIR
EOF

# 6. Create compressed archive
log "Creating compressed archive..."
cd "$BACKUP_DIR" && tar czf "ledgerflow_full_backup_$TIMESTAMP.tar.gz" "full_backup_$TIMESTAMP"

# 7. Verify archive
log "Verifying archive..."
if tar tzf "$BACKUP_DIR/ledgerflow_full_backup_$TIMESTAMP.tar.gz" > /dev/null; then
    log "Archive verified successfully"
else
    log "ERROR: Archive verification failed!"
    exit 1
fi

# 8. Cleanup
log "Cleaning up temporary files..."
rm -rf "$BACKUP_DIR/full_backup_$TIMESTAMP"

# 9. Implement retention policy (keep last 7 days)
log "Implementing retention policy..."
find "$BACKUP_DIR" -name "ledgerflow_full_backup_*.tar.gz" -mtime +7 -delete

log "Full backup completed successfully"
log "Backup location: $BACKUP_DIR/ledgerflow_full_backup_$TIMESTAMP.tar.gz"
log "Note: Backup is stored in iCloud and will be synced automatically" 