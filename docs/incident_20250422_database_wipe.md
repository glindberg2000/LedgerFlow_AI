# Database Wipe Incident Report - April 22, 2025

## Summary
During an attempt to set up SearXNG, an unrelated action led to the accidental deletion of the production database. The system was restored from backup, but this incident highlights several critical vulnerabilities in our development and deployment processes.

## Timeline
1. Task: Set up SearXNG on port 8080
2. Unintended Action: Interfered with working database setup
3. Critical Error: Executed `docker compose down -v` which destroyed the database volume
4. Discovery: iCloud backup system failing silently (0-byte files)
5. System restored from `current_backup.sql` (April 19th backup)

## Impact
- Loss of all database changes since April 19th
- Discovery that automated iCloud backups were not working
- Development environment disruption

## Root Causes
1. Scope Violation
   - Task was only to set up SearXNG
   - Unnecessarily modified database configuration
2. Insufficient Safeguards
   - No confirmation required for destructive volume operations
   - No automatic backup before migrations
3. Backup System Failure
   - iCloud backup system creating empty files
   - No monitoring of backup success/failure
4. Process Failures
   - No separation of concerns between services
   - No checklist for database operations

## Immediate Actions Required
1. Restore from last good backup (April 19th)
2. Fix iCloud backup system
3. Implement backup verification
4. Add safeguards against accidental volume deletion

## Prevention Recommendations

### Process Changes
1. **Service Isolation**
   ```bash
   # Create separate compose files for each service
   docker-compose.searxng.yml
   docker-compose.core.yml
   ```

2. **Pre-operation Backup**
   ```bash
   # Create pre-migration backup
   BACKUP_FILE="pre_migration_$(date +%Y%m%d_%H%M%S).dump"
   docker compose -p "ledger-${ENV:-dev}" exec postgres pg_dump -U $POSTGRES_USER -Fc --clean > "backups/$BACKUP_FILE"
   ```

3. **Backup Verification**
   ```bash
   # Add to backup script
   if [ ! -s "$BACKUP_FILE" ]; then
     echo "ERROR: Backup file is empty"
     exit 1
   fi
   ```

### Technical Changes
1. **Backup Strategy**
   - Hourly incremental backups to `/icloud_backups/hourly/`
   - Daily consolidation to `/icloud_backups/daily/`
   - Backup size verification
   - Automated backup testing

2. **Volume Protection**
   ```yaml
   volumes:
     postgres_data:
       labels:
         - "com.ledgerflow.protect=true"
   ```

3. **Service Isolation**
   - Separate networks for different services
   - Independent scaling and deployment

## Recovery Steps
1. Stop all services:
   ```bash
   docker compose down
   ```

2. Restore from latest backup:
   ```bash
   ./restore_db_force_v2.sh /icloud_backups/hourly/latest.dump
   ```

## Action Items
- [ ] Fix iCloud backup system
- [ ] Implement backup verification
- [ ] Add volume protection
- [ ] Create service isolation
- [ ] Document recovery procedures
- [ ] Set up backup monitoring
- [ ] Create database operation checklist
- [ ] Implement automated testing of backups
- [ ] Add backup size verification
- [ ] Hourly backup automation

## Lessons Learned
1. Never modify unrelated services
2. Always verify backup integrity
3. Implement proper monitoring
4. Use separate compose files for different services
5. Add safeguards for critical operations

## Appendix

### Emergency Recovery Procedure

1. Stop affected services:
   ```bash
   docker compose -p ledger-{env} down
   ```

2. Restore from latest backup:
   ```bash
   ./restore_db_force_v2.sh /icloud_backups/hourly/latest.dump
   ```

3. Verify restoration:
   ```bash
   ./scripts/verify_restore.sh
   ```

### Emergency Contacts

- Database Administrator: Greg Johnson
- System Administrator: Greg Johnson
- Project Lead: Greg Johnson

### Reference Documents

- [Next-Step Action Plan - May 2025](../docs/action_plan_may_2025.md)
- [Production Deployment Guide](../docs/deployment.md)
- [Emergency Recovery Procedures](../docs/emergency_recovery.md) 