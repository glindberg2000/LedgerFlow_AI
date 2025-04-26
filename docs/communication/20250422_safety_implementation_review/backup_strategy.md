# Database Backup Strategy

## Overview
This document outlines the comprehensive backup strategy for the LedgerFlow development environment, incorporating lessons learned from the 2025-04-22 incident.

## Security Measures

### Volume Protection
1. Protected volumes with labels:
   ```bash
   docker volume create --label com.ledgerflow.protect=true ledger_dev_db_data
   docker volume create --label com.ledgerflow.protect=true ledger_prod_db_data
   ```

### Command Safety
1. Docker CLI wrapper (`ledger_docker`) prevents accidental volume deletion
2. Environment lock in `manage.py` prevents direct prod commands
3. Volume protection checks in pre-commit hooks
4. Safe Makefile targets with confirmation prompts

## Backup Implementation

### Comprehensive Backup (`backup_dev_full.sh`)
1. Database dump with size verification
2. Media files backup
3. Configuration files
4. Application state (fixtures)
5. Container versions and state
6. Git commit information
7. Compressed archive with verification

### Database-Only Backup (`backup_dev_db.sh`)
1. Compressed SQL dumps with size verification
2. Backup integrity verification
3. Transaction count validation
4. Table structure verification
5. Automatic cleanup of old backups

### Storage Location
- Primary: `/Users/greg/iCloud Drive (Archive)/repos/LedgerFlow_Archive/backups/dev/`
- Format: 
  - Full backups: `.tar.gz` archives
  - DB-only: `.sql.gz` files
- Naming: `ledgerflow_[type]_backup_YYYYMMDD_HHMMSS.*`

### Backup Features
1. Automated daily backups at 2 AM
2. 7-day retention policy
3. Minimum size verification (10KB)
4. Backup integrity checking
5. Cloud storage via iCloud Drive
6. Comprehensive logging
7. Full state capture

### Backup Process
1. Database:
   - Full pg_dump with compression
   - Size verification
   - Integrity check via test restore
   - Transaction count verification

2. Application State:
   - Media files backup
   - Configuration files
   - Environment variables
   - Container state
   - Git information

3. Verification:
   - Archive integrity check
   - Size verification
   - Data consistency check
   - Container state validation

### Automated Schedule
- Daily full backup at 2 AM
- Hourly database-only backups
- 7-day retention for full backups
- 48-hour retention for hourly backups

## Monitoring
- Backup logs in `backups/dev/backup.log`
- Size verification alerts
- Restore test results
- Transaction count tracking
- Table structure validation

## Recovery Process
1. Choose backup type:
   ```bash
   # For database only
   ./restore_db_force_v2.sh backups/dev/ledgerflow_backup_YYYYMMDD_HHMMSS.sql.gz

   # For full restore
   ./scripts/db/restore_full_backup.sh backups/dev/ledgerflow_full_backup_YYYYMMDD_HHMMSS.tar.gz
   ```

2. Verification steps:
   - Check transaction count
   - Verify media files
   - Test application functionality
   - Validate configuration

## Best Practices
1. Never use `docker compose down -v` directly
2. Always use `ledger_docker` wrapper
3. Verify backup integrity immediately
4. Monitor backup sizes
5. Test restores regularly
6. Keep security measures active

## Security Considerations
1. Protected volumes
2. Command restrictions
3. Environment separation
4. Access controls
5. Backup encryption (if needed)
6. iCloud security

## Emergency Procedures
1. Stop all services:
   ```bash
   ledger_docker compose down
   ```

2. Restore from latest backup:
   ```bash
   make restore FILE=backups/dev/latest.sql.gz
   ```

3. Verify restoration:
   ```bash
   docker compose exec django python manage.py check
   ```

## Git Integration
- Git handles code version control
- Backup system handles:
  - Database state
  - Media files
  - Configuration
  - Runtime state

## Monitoring Setup
1. Size alerts (< 10KB)
2. Backup success/failure
3. Restore test results
4. Transaction count changes
5. Configuration changes 