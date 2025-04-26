#!/bin/bash
set -euo pipefail

# Configuration
BACKUP_PATH="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups"
TEST_FILE="${BACKUP_PATH}/test_write"
MIN_SIZE_KB=10
EXPECTED_UID=$(id -u)

# Logging setup
LOG_FILE="${BACKUP_PATH}/logs/backup_guard.log"
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE" || { echo "Cannot access log file"; exit 1; }

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to verify backup file
verify_backup() {
    local backup_file="$1"
    
    # 1. Test write access with cleanup
    log "Testing write access to backup directory..."
    if ! touch "${TEST_FILE}"; then
        log "ERROR: Cannot write to backup location"
        exit 1
    fi
    
    # Check UID mapping
    local file_uid=$(stat -f%u "${TEST_FILE}")
    if [ "$file_uid" != "$EXPECTED_UID" ]; then
        log "ERROR: UID mismatch - expected $EXPECTED_UID, got $file_uid"
        rm -f "${TEST_FILE}"
        exit 1
    fi
    
    # Cleanup test file
    rm -f "${TEST_FILE}"
    
    # 2. Verify backup file exists
    if [ ! -f "$backup_file" ]; then
        log "ERROR: Backup file not found: $backup_file"
        exit 1
    fi
    
    # 3. Check file size
    local size_bytes=$(stat -f%z "$backup_file")
    if [ "$size_bytes" -lt $((MIN_SIZE_KB * 1024)) ]; then
        log "ERROR: Backup file too small (${size_bytes} bytes)"
        exit 1
    fi
    
    # 4. Verify dump is parseable
    log "Verifying backup integrity..."
    if ! pg_restore -l "$backup_file" >/dev/null 2>&1; then
        log "ERROR: Backup file is not a valid PostgreSQL dump"
        exit 1
    fi
    
    log "✓ Backup verification complete: $backup_file"
    log "Note: This backup is stored in iCloud and will be synced automatically"
    return 0
}

# Main execution
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <backup-file>"
    echo "Note: Backups are stored in iCloud at: $BACKUP_PATH"
    exit 1
fi

verify_backup "$1" 