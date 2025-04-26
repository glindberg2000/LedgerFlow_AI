# Backup and Restore Operations Guide

## Overview

This document details the backup and restore procedures for LedgerFlow's database and associated data. These procedures are critical for data safety and business continuity.

## Backup Operations

### Automatic Backups

Backups are automatically created and stored in environment-specific locations:

```bash
# Production backups
~/iCloudLedger/backups/prod/

# Development backups
~/iCloudLedger/backups/dev/

# Test backups
~/iCloudLedger/backups/test/
```

### Manual Backup Commands

```bash
# Create a backup in the default location
make backup

# Create a backup with a specific filename
make backup FILE=custom_backup_name.dump

# Create a backup in development environment
LEDGER_ENV=dev make backup

# Create a backup in production environment
LEDGER_ENV=prod make backup
```

### Backup File Format

Backup files follow this naming convention:
```
ledgerflow_{env}_{date}_{time}.dump
```

Example: `ledgerflow_prod_20250424_2031.dump`

### Backup Verification

After each backup:

1. Check file exists in correct location
2. Verify file size (should be > 10KB for non-empty DB)
3. Verify file permissions (600 for security)
4. Optional: Test restore to verify backup integrity

## Restore Operations

### Prerequisites

Before restoring:

1. Ensure target environment is stopped
2. Verify backup file exists and is readable
3. Set correct environment variables
4. Have sufficient disk space (2x backup size)

### Restore Commands

```bash
# Restore from a specific backup file
make restore FILE=path/to/backup.dump

# Force restore (overwrites existing data)
make restore-force FILE=path/to/backup.dump

# Test restore (to verify backup)
make restore-test FILE=path/to/backup.dump
```

### Post-Restore Verification

After restore:

1. Check database connectivity
2. Verify application starts correctly
3. Sample check critical data
4. Review logs for any errors

## Safety Measures

### Environment Protection

The safety wrapper (`ledger_docker`) ensures:

1. Correct environment targeting
2. Protected volume handling
3. Backup location validation

### Required Environment Variables

```bash
LEDGER_ENV=dev|test|prod    # Required for all operations
```

### Common Issues and Solutions

1. **Backup Creation Fails**
   - Check disk space
   - Verify database connectivity
   - Check file permissions

2. **Restore Fails**
   - Verify backup file exists
   - Check file permissions
   - Ensure target DB is not in use

3. **Permission Issues**
   - Use ledger_docker wrapper
   - Check file ownership
   - Verify directory permissions

## Emergency Procedures

### Data Recovery

If primary backup fails:

1. Check archive locations
2. Use most recent valid backup
3. Document incident and recovery

### Backup Rotation

- Production: Keep 30 days
- Development: Keep 7 days
- Test: Keep 3 days

### Monitoring

Monitor for:

1. Backup creation success/failure
2. Backup file size anomalies
3. Storage space usage
4. Backup completion time

## Best Practices

1. Always use `make` commands
2. Never skip verification steps
3. Document all manual operations
4. Test restores regularly
5. Keep backup metadata current

## Future Improvements

- [ ] Implement backup encryption
- [ ] Add automated restore testing
- [ ] Improve backup compression
- [ ] Add backup integrity checking 