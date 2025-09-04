#!/bin/bash
# Safety wrapper for any database operations

set -euo pipefail

DB_FILE="${1:-ledgerflow.sqlite3}"
OPERATION="${2:-unknown}"

echo "🛡️  SAFETY CHECK: About to perform '$OPERATION' on $DB_FILE"

# Always backup first
BACKUP_FILE=$(./scripts/auto_backup.sh "$DB_FILE")
echo "✅ Backup created: $BACKUP_FILE"

# Check if database has real data
if [ -f "$DB_FILE" ]; then
    REAL_PROFILES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM profiles_businessprofile WHERE company_name != 'ACME Corp';" 2>/dev/null || echo "0")
    TOTAL_TRANSACTIONS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM profiles_transaction;" 2>/dev/null || echo "0")
    
    if [ "$REAL_PROFILES" -gt 0 ] || [ "$TOTAL_TRANSACTIONS" -gt 100 ]; then
        echo "⚠️  WARNING: This database contains REAL PRODUCTION DATA!"
        echo "   - Real business profiles: $REAL_PROFILES"
        echo "   - Total transactions: $TOTAL_TRANSACTIONS"
        echo "   - Backup location: $BACKUP_FILE"
        echo ""
        read -p "Type 'CONFIRM' to proceed with $OPERATION: " confirmation
        if [ "$confirmation" != "CONFIRM" ]; then
            echo "❌ Operation cancelled for safety"
            exit 1
        fi
    fi
fi

echo "✅ Safety check passed. Backup secured at: $BACKUP_FILE"