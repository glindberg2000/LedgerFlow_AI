#!/bin/bash

# Configuration backup script
# Backs up all critical configuration files and settings

# Set backup directory
BACKUP_DIR="backups/config_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup SearXNG configuration
echo "Backing up SearXNG configuration..."
mkdir -p "$BACKUP_DIR/searxng"
cp searxng/settings.yml "$BACKUP_DIR/searxng/"

# Backup Docker compose files
echo "Backing up Docker configuration..."
cp docker-compose*.y*ml "$BACKUP_DIR/"
cp .env* "$BACKUP_DIR/"

# Backup scripts
echo "Backing up scripts..."
mkdir -p "$BACKUP_DIR/scripts"
cp -r scripts/* "$BACKUP_DIR/scripts/"

# Backup documentation
echo "Backing up documentation..."
mkdir -p "$BACKUP_DIR/docs"
cp -r docs/* "$BACKUP_DIR/docs/"

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"

# Cleanup old backups (keep last 5)
ls -t backups/config_backup_*.tar.gz | tail -n +6 | xargs -r rm

echo "Backup rotation completed" 