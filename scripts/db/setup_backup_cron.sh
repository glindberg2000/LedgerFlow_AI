#!/bin/bash

# Get the absolute path to the backup scripts
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DB_BACKUP_SCRIPT="$SCRIPT_DIR/backup_dev_db.sh"
FULL_BACKUP_SCRIPT="$SCRIPT_DIR/backup_dev_full.sh"
BACKUP_LOG_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev/logs"

# Create log directory
mkdir -p "$BACKUP_LOG_DIR"

# Create a temporary cron file
TEMP_CRON=$(mktemp)
crontab -l > "$TEMP_CRON" 2>/dev/null

# Get current time and add 5 minutes for test
CURRENT_MIN=$(date +%M)
TEST_MIN=$(( (CURRENT_MIN + 5) % 60 ))
TEST_HOUR=$(date +%H)
if [ $TEST_MIN -lt $CURRENT_MIN ]; then
    TEST_HOUR=$(( (TEST_HOUR + 1) % 24 ))
fi

# Add backup jobs if they don't exist
if ! grep -q "backup_dev_db.sh" "$TEMP_CRON"; then
    # Hourly database backup
    echo "0 * * * * $DB_BACKUP_SCRIPT >> \"$BACKUP_LOG_DIR/db_backup.log\" 2>&1" >> "$TEMP_CRON"
    # Daily full backup at 2 AM
    echo "0 2 * * * $FULL_BACKUP_SCRIPT >> \"$BACKUP_LOG_DIR/full_backup.log\" 2>&1" >> "$TEMP_CRON"
    # Test run in 5 minutes
    echo "$TEST_MIN $TEST_HOUR * * * $FULL_BACKUP_SCRIPT >> \"$BACKUP_LOG_DIR/test_backup.log\" 2>&1" >> "$TEMP_CRON"
    crontab "$TEMP_CRON"
    echo "Backup cron jobs installed successfully"
    echo "Test backup scheduled for $(date -v +5M '+%H:%M')"
    echo "Note: Backup logs will be stored in iCloud at: $BACKUP_LOG_DIR"
else
    echo "Backup cron jobs already exist"
fi

# Clean up
rm "$TEMP_CRON"

# Show current cron jobs
echo "Current cron jobs:"
crontab -l 