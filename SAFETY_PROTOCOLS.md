# LedgerFlow Database Safety Protocols

## Critical Incident: September 4, 2025
**Data Loss Event**: Production SQLite database containing weeks of user work was accidentally overwritten during database operations without backup.

**Root Cause**: Failure to follow basic backup protocols before file operations.

**Lesson**: Never perform database operations without creating verified backups first.

## Mandatory Safety Procedures

### 🛡️ Before ANY Database Operation

**ALWAYS run this command first:**
```bash
./scripts/safe_db_operation.sh ledgerflow.sqlite3 "your-operation-description"
```

This will:
- Create automatic backup in iCloud
- Verify database integrity
- Check for production data
- Require explicit confirmation for production databases

### 📊 Database Health Checks

**Check database status:**
```bash
python scripts/db_health_check.py ledgerflow.sqlite3
```

**Example output:**
```
🔍 Analyzing database: ledgerflow.sqlite3
✅ Database integrity: OK
📊 Business profiles: 3 total, 2 real  
💰 Transactions: 1,247
📁 Uploaded files: 23
🚨 This appears to be PRODUCTION DATA - handle with extreme care!
🏢 Real businesses: Cubik Media, Gregory Lindberg
```

### 💾 Manual Backup Creation

**Create immediate backup:**
```bash
./scripts/auto_backup.sh ledgerflow.sqlite3
```

**Backup location:** `/Users/greg/Library/Mobile Documents/com~apple~CloudDocs/Archives/LedgerFlow/YYYYMMDD/`

**Retention policy:**
- Keep last 3 backups per day (not 10!)
- Automatically delete backup folders older than 30 days
- Prevents drive space bloat while maintaining safety

### 🚫 Git Protection

**Pre-commit hook installed** - automatically prevents:
- Committing `.sqlite3` files with production data
- Warns about backup files being committed
- Blocks commit and provides clear remediation steps

**To bypass for demo databases only:**
```bash
git commit --no-verify  # Use ONLY for confirmed demo data
```

## Recovery Procedures

### 📂 Backup Locations to Check

1. **iCloud Backups (Primary):**
   `/Users/greg/Library/Mobile Documents/com~apple~CloudDocs/Archives/LedgerFlow/`

2. **Git History:**
   ```bash
   git log --all --full-history -- "*.sqlite3"
   git show <commit>:database.sqlite3 > recovered.sqlite3
   ```

3. **Local Backup Files:**
   ```bash
   find . -name "*backup*.sqlite3" -o -name "*.bak"
   ```

### 🔄 Database Recovery Process

1. **Stop all Django processes**
2. **Verify backup integrity:**
   ```bash
   python scripts/db_health_check.py backup_file.sqlite3
   ```
3. **Create safety backup of current (possibly corrupted) database**
4. **Restore from backup:**
   ```bash
   cp backup_file.sqlite3 ledgerflow.sqlite3
   ```
5. **Verify restoration:**
   ```bash
   python scripts/db_health_check.py ledgerflow.sqlite3
   ```

## Database Operation Checklist

**Before modifying database:**
- [ ] Run `./scripts/safe_db_operation.sh`
- [ ] Verify backup created successfully
- [ ] Confirm operation on correct database
- [ ] Test operation on copy first if destructive

**After database operation:**
- [ ] Run health check to verify integrity
- [ ] Verify data still accessible via Django admin
- [ ] Create additional backup if major changes made

## File Naming Conventions

**Production Database:** `ledgerflow.sqlite3` (protected by all safety systems)

**Demo/Test Databases:** Use clear naming:
- `demo_bootstrap.sqlite3` - Clean demo data
- `test_migration.sqlite3` - Testing migrations  
- `backup_YYYYMMDD_HHMMSS.sqlite3` - Timestamped backups

## Emergency Contacts & Escalation

**Data Loss Event:**
1. **STOP immediately** - don't make changes that might overwrite recovery options
2. Document exactly what happened
3. Check all backup locations listed above
4. Run `find / -name "*.sqlite3" -newer backup_reference_file` to locate any newer copies

## Testing Safety Systems

**Test backup system:**
```bash
./scripts/auto_backup.sh demo_bootstrap.sqlite3
```

**Test health check:**
```bash
python scripts/db_health_check.py demo_bootstrap.sqlite3
```

**Test git hook:**
```bash
git add ledgerflow.sqlite3
git commit -m "test commit"  # Should be blocked
```

---

**Remember: Data loss is catastrophic and largely preventable. These protocols exist because production data containing weeks of work was lost due to inadequate safety procedures. Always err on the side of caution.**