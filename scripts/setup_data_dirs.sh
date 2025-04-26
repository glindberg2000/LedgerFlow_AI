#!/bin/bash

# Exit on error
set -e

# Define paths
DATA_ROOT="$HOME/LedgerFlow_data"
PG_DATA="$DATA_ROOT/pg"
BACKUP_ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups"

echo "Setting up LedgerFlow data directories..."

# Create data root directory
mkdir -p "$DATA_ROOT"
chmod 755 "$DATA_ROOT"

# Create PostgreSQL data directory with secure permissions
mkdir -p "$PG_DATA"
chmod 700 "$PG_DATA"

# Create backup directories in iCloud
mkdir -p "$BACKUP_ROOT/dev"
mkdir -p "$BACKUP_ROOT/test"
chmod -R 755 "$BACKUP_ROOT"

# Create .gitignore files
cat > "$DATA_ROOT/.gitignore" << EOL
# Ignore all files in this directory
*
# Except this .gitignore file
!.gitignore
# And the README
!README.md
EOL

cat > "$BACKUP_ROOT/.gitignore" << EOL
# Ignore all files in this directory
*
# Except this .gitignore file
!.gitignore
# And the README
!README.md
# And subdirectories
!*/
EOL

# Create README files
cat > "$DATA_ROOT/README.md" << EOL
# LedgerFlow Data Directory

This directory contains persistent data for LedgerFlow services:

- \`pg/\`: PostgreSQL data directory
  - Permissions: 700 (user access only)
  - Used by: PostgreSQL container

## Usage

- Do not modify these directories directly
- Use make commands to manage data:
  - \`make backup\`: Create a backup
  - \`make restore\`: Restore from backup
  - \`make clean\`: Clean data directories

Note: Backups are stored in iCloud at:
$BACKUP_ROOT
EOL

cat > "$BACKUP_ROOT/README.md" << EOL
# LedgerFlow Backups (iCloud Storage)

This directory contains database backups stored in iCloud for safety:

- \`dev/\`: Development environment backups
- \`test/\`: Test environment backups

## Usage

- Backups are automatically timestamped and synced to iCloud
- Use make commands to manage backups:
  - \`make backup\`: Create a new backup
  - \`make restore FILE=<path>\`: Restore from backup
  - \`make verify-backup FILE=<path>\`: Verify backup integrity

## Important Note

This directory is stored in iCloud and synced automatically. Do not move or rename
this directory as it will break the sync process. The path should always be:
$BACKUP_ROOT
EOL

echo "✅ Data directories setup complete!"
echo "📁 Data root: $DATA_ROOT"
echo "📁 PostgreSQL data: $PG_DATA"
echo "📁 Backups (iCloud): $BACKUP_ROOT"
echo
echo "Note: Backups are stored in iCloud and will be synced automatically."

# Create PostgreSQL data directory
PG_DATA_DIR=~/LedgerFlow_data/pg
echo "Setting up PostgreSQL data directory at $PG_DATA_DIR..."
mkdir -p "$PG_DATA_DIR"
chmod 700 "$PG_DATA_DIR"

# Create backup directories
BACKUP_DIR=~/Library/Mobile\ Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups
echo "Setting up backup directories at $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"/{dev,prod,test}/logs

echo "✅ Data directories created successfully"
echo "PostgreSQL data: $PG_DATA_DIR"
echo "Backups: $BACKUP_DIR" 