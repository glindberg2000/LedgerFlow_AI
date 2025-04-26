#!/bin/bash

BACKUP_FILE="archives/docker_archive/database_backups/test_django_backup_20250420_013431.sql.gz"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Drop all tables with CASCADE
echo "Dropping all tables..."
docker compose -f docker-compose.dev.yml exec postgres psql -U newuser mydatabase << 'EOF'
DO $$ 
DECLARE
    r RECORD;
BEGIN
    -- Disable all triggers
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'ALTER TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' DISABLE TRIGGER ALL';
    END LOOP;

    -- Drop all tables
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
EOF

# Decompress backup
echo "Decompressing backup..."
gunzip -c "$BACKUP_FILE" > temp_backup.sql

# Restore database
echo "Restoring database..."
docker compose -f docker-compose.dev.yml exec -T postgres psql -U newuser mydatabase < temp_backup.sql

# Cleanup
rm temp_backup.sql

echo "Database restore completed!" 