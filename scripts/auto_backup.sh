#!/bin/bash
# Auto-backup script for LedgerFlow database protection

set -euo pipefail

DB_FILE="${1:-ledgerflow.sqlite3}"
BACKUP_ROOT="/Users/greg/Library/Mobile Documents/com~apple~CloudDocs/Archives/LedgerFlow"
BACKUP_DIR="$BACKUP_ROOT/$(date +%Y%m%d)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with verification
if [ -f "$DB_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/${DB_FILE%.sqlite3}_backup_$TIMESTAMP.sqlite3"
    
    echo "Creating backup: $BACKUP_FILE"
    cp "$DB_FILE" "$BACKUP_FILE"
    
    # Verify backup integrity
    sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" > /dev/null
    
    # Check that backup has actual data
    PROFILE_COUNT=$(sqlite3 "$BACKUP_FILE" "SELECT COUNT(*) FROM profiles_businessprofile WHERE company_name != 'ACME Corp';" 2>/dev/null || echo "0")
    
    if [ "$PROFILE_COUNT" -gt 0 ]; then
        echo "✅ PRODUCTION DATA BACKUP CREATED: $BACKUP_FILE ($PROFILE_COUNT real profiles)"
    else
        echo "⚠️  Demo data backup created: $BACKUP_FILE"
    fi
    
    # Keep only last 3 backups per day
    ls -t $BACKUP_DIR/*.sqlite3 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
    
    # Clean up old backup directories (keep last 30 days)
    find "$BACKUP_ROOT" -maxdepth 1 -type d -name "20*" -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
    
    echo "$BACKUP_FILE"
else
    echo "❌ Database file $DB_FILE not found"
    exit 1
fi