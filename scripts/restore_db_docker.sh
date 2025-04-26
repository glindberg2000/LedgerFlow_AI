#!/bin/bash

BACKUP_FILE="archives/docker_archive/database_backups/test_django_backup_20250420_013431.sql.gz"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Backup file ${BACKUP_FILE} not found!"
    exit 1
fi

# Decompress backup
echo "Decompressing backup..."
gunzip -c "${BACKUP_FILE}" > temp_backup.sql

# Restore database using docker compose
echo "Restoring database..."
docker compose -f docker-compose.dev.yml exec -T postgres psql -U newuser mydatabase < temp_backup.sql

# Clean up
rm temp_backup.sql

echo "Database restore completed!" 