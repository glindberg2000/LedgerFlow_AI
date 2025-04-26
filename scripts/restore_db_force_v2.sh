#!/bin/bash

# Database connection details from .env.dev
DB_NAME="mydatabase"
DB_USER="newuser"
DB_PASSWORD="newpassword"
DB_HOST="postgres"
DB_PORT="5432"

# Backup file path
BACKUP_FILE="archives/docker_archive/database_backups/test_django_backup_20250420_013431.sql.gz"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Stopping Django container..."
docker compose -f docker-compose.dev.yml stop django

echo "Setting up database with newuser..."
# Create role if it doesn't exist
docker compose -f docker-compose.dev.yml exec -T postgres psql -U $DB_USER -d postgres -c "DO \$\$ BEGIN CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'; EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'Role already exists'; END \$\$;"

# Drop and recreate database
docker compose -f docker-compose.dev.yml exec -T postgres psql -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker compose -f docker-compose.dev.yml exec -T postgres psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "Decompressing backup..."
gunzip -c "$BACKUP_FILE" > temp_backup.sql

echo "Restoring database..."
cat temp_backup.sql | docker compose -f docker-compose.dev.yml exec -T postgres psql -U $DB_USER -d $DB_NAME

echo "Cleaning up..."
rm temp_backup.sql

echo "Starting Django container..."
docker compose -f docker-compose.dev.yml start django

echo "Database restore completed!" 