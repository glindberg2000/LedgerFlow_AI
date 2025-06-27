# LedgerFlow Database Backup System

## Overview

LedgerFlow uses a comprehensive backup system that stores all backups in iCloud for safety and accessibility. The system includes automatic backups, manual backups, and safety measures for database operations.

## Backup Storage

All backups are stored in iCloud at:
```
~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/
```

This directory contains several subdirectories:
- `dev/`: Development environment backups
- `test/`: Test environment backups
- `prod/`: Production environment backups
- `migrations/`: Pre-migration backups
- `logs/`: Backup operation logs

## Backup Types

1. **Hourly Database Backups**
   - Runs every hour via cron
   - Stores compressed SQL dumps
   - 7-day retention policy
   - Includes basic integrity checks

2. **Daily Full Backups**
   - Runs at 2 AM daily via cron
   - Includes database, media files, and configuration
   - Creates a complete system snapshot
   - 7-day retention policy

3. **Pre-Migration Backups**
   - Created before running migrations
   - Stored in the migrations directory
   - Includes full database state
   - Verified before allowing migration

4. **Safety Test Backups**
   - Created before destructive operations
   - Includes integrity verification
   - Temporary backups for immediate restore

## Backup Scripts

1. `backup_dev_db.sh`
   - Hourly database backups
   - Verifies backup integrity
   - Implements retention policy
   - Logs operations

2. `backup_dev_full.sh`
   - Complete system backup
   - Includes media and config files
   - Creates detailed manifest
   - Archives all components

3. `safe_migrate.sh`
   - Pre-migration safety backups
   - Verifies database consistency
   - Prevents unsafe migrations
   - Production environment protection

4. `safe_db_test.sh`
   - Test environment protection
   - Creates safety backups
   - Verifies restore capability
   - Prevents data loss

5. `backup_guard.sh`
   - Backup verification tool
   - Checks backup integrity
   - Verifies iCloud sync
   - Monitors backup sizes

## Cron Jobs

The following backup jobs are automatically scheduled:
```bash
# Hourly database backup
0 * * * * /path/to/backup_dev_db.sh

# Daily full backup at 2 AM
0 2 * * * /path/to/backup_dev_full.sh
```

## Backup Verification

All backups are verified for:
1. Minimum size requirements (10KB)
2. Database integrity
3. Restore capability
4. iCloud sync status
5. Proper permissions

## Restore Process

To restore from a backup:

```bash
# Development environment
./restore_db_clean.sh -f path/to/backup.sql.gz

# Production environment
./restore_db_clean.sh -e prod -f path/to/backup.sql.gz -u $DB_USER -d $DB_NAME
```

## Safety Features

1. **Pre-operation Backups**
   - Automatic backups before risky operations
   - Verified before proceeding
   - Easy rollback capability

2. **iCloud Integration**
   - All backups synced to iCloud
   - Protected from local system failures
   - Accessible from multiple devices

3. **Integrity Checks**
   - Size verification
   - Structure validation
   - Restore testing
   - Permission verification

4. **Retention Policies**
   - Automated cleanup
   - Configurable retention periods
   - Space management
   - Log rotation

## Monitoring

1. **Backup Logs**
   - Stored in iCloud
   - Include operation details
   - Track success/failure
   - Size information

2. **Verification Reports**
   - Integrity check results
   - Sync status
   - Error notifications
   - Performance metrics

## Best Practices

1. **Regular Testing**
   - Test restores monthly
   - Verify backup integrity
   - Check iCloud sync
   - Update documentation

2. **Maintenance**
   - Monitor backup sizes
   - Check retention policies
   - Verify cron jobs
   - Update paths if needed

3. **Security**
   - Use secure permissions
   - Verify user access
   - Protect backup files
   - Monitor access logs

4. **Documentation**
   - Keep paths updated
   - Document changes
   - Track issues
   - Update procedures 