#!/bin/bash

# Configuration
BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev"
RETENTION_DAYS=7
COMPOSE_FILE="docker-compose.dev.yml"
DB_CONTAINER="ledger-dev-postgres-1"
DB_USER="newuser"
DB_NAME="mydatabase"
MIN_BACKUP_SIZE=10240  # 10KB minimum size

# Exit on any error
set -e

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ledgerflow_backup_$TIMESTAMP.sql.gz"

# Create backup
log "Creating backup: $BACKUP_FILE"
docker compose -f $COMPOSE_FILE exec -T postgres pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_FILE"

# Check backup size
BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE")
if [ "$BACKUP_SIZE" -lt "$MIN_BACKUP_SIZE" ]; then
    log "ERROR: Backup file is too small ($BACKUP_SIZE bytes)! Minimum size: $MIN_BACKUP_SIZE bytes"
    rm "$BACKUP_FILE"
    exit 1
fi

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    # Test the backup by restoring to temporary container
    log "Verifying backup integrity..."
    TEMP_CONTAINER="pg_temp_verify_$TIMESTAMP"
    
    # Start temporary container
    docker run --name $TEMP_CONTAINER -e POSTGRES_USER=newuser -e POSTGRES_PASSWORD=newuser -e POSTGRES_DB=mydatabase -d postgres:15

    # Wait for container to be ready
    sleep 5

    # Attempt to restore
    if gunzip < "$BACKUP_FILE" | docker exec -i $TEMP_CONTAINER psql -U newuser mydatabase; then
        log "Backup verified successfully"
        # Check if data is present
        TRANSACTION_COUNT=$(docker exec -i $TEMP_CONTAINER psql -U newuser mydatabase -t -c "SELECT COUNT(*) FROM profiles_transaction;")
        log "Verified transaction count: $TRANSACTION_COUNT"
        BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
        log "Backup size: $BACKUP_SIZE bytes"
        
        # Additional data integrity checks
        TABLE_COUNT=$(docker exec -i $TEMP_CONTAINER psql -U newuser mydatabase -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        log "Verified table count: $TABLE_COUNT"
    else
        log "ERROR: Backup verification failed"
        rm "$BACKUP_FILE"
        docker stop $TEMP_CONTAINER
        docker rm $TEMP_CONTAINER
        exit 1
    fi

    # Cleanup temporary container
    docker stop $TEMP_CONTAINER
    docker rm $TEMP_CONTAINER
fi

# Implement retention policy
log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "ledgerflow_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List remaining backups
log "Current backups:"
ls -lh "$BACKUP_DIR"

# Final size verification
FINAL_SIZE=$(stat -f%z "$BACKUP_FILE")
log "Final backup size: $FINAL_SIZE bytes"
if [ "$FINAL_SIZE" -lt "$MIN_BACKUP_SIZE" ]; then
    log "ERROR: Final backup file is too small!"
    exit 1
fi

log "Backup completed successfully"
log "Note: Backup is stored in iCloud and will be synced automatically" 