# LedgerFlow Backup Procedures Guide

This guide explains how to work with the LedgerFlow backup system in plain language.

## Quick Reference

### Where are backups stored?
All backups are in iCloud under:
```
~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/
```

### Common Tasks

1. **Create a manual backup:**
   ```bash
   ./scripts/db/backup_dev_db.sh   # For database only
   ./scripts/db/backup_dev_full.sh  # For full system backup
   ```

2. **Restore from backup:**
   ```bash
   ./restore_db_clean.sh -f path/to/backup.sql.gz
   ```

3. **Check backup status:**
   ```bash
   ls -lh ~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev/
   ```

## Automated Backups

The system automatically creates:
- Hourly database backups
- Daily full system backups at 2 AM
- Pre-migration safety backups
- Pre-test safety backups

You don't need to do anything for these - they just work!

## When Things Go Wrong

1. **Need to restore a backup?**
   - Look in the iCloud backup folder
   - Find the backup you want (they're timestamped)
   - Use the restore command above
   - Ask for help if unsure!

2. **Backup seems too small?**
   - Normal backups should be at least 10KB
   - If smaller, it might be corrupted
   - Create a new backup manually
   - Contact the team if this keeps happening

3. **Can't find backups?**
   - Check iCloud sync status
   - Wait a few minutes for sync
   - Check your internet connection
   - Look for error messages in the logs

## Safety Tips

1. **Before big changes:**
   - Create a manual backup
   - Verify it appears in iCloud
   - Test a restore if you're worried

2. **After restoring:**
   - Check your data
   - Run some basic queries
   - Verify application functionality

3. **Monthly tasks:**
   - Check backup sizes
   - Try a test restore
   - Review error logs
   - Clean up old backups

## Getting Help

If you're unsure about anything:
1. Check the logs in `backups/dev/logs/`
2. Look for error messages
3. Contact the team before making changes
4. Don't delete backups unless you're sure

## Backup Types Explained

1. **Database Only Backup**
   - Just the database
   - Quick to create and restore
   - Good for quick safety copies
   - Found in `backups/dev/`

2. **Full System Backup**
   - Everything: database, files, config
   - Takes longer but more complete
   - Best for major changes
   - Found in `backups/dev/full_backup_*`

3. **Migration Backup**
   - Created before database changes
   - Automatic safety measure
   - Found in `backups/migrations/`

4. **Test Backup**
   - Before running tests
   - Automatic safety copy
   - Found in `backups/test/`

## Best Practices

1. **Always check backup size**
   - Should be at least 10KB
   - Larger is usually better
   - Tiny backups are suspicious

2. **Wait for iCloud**
   - Give it time to sync
   - Check for the cloud icon
   - Don't proceed until synced

3. **Keep it clean**
   - Old backups are auto-removed after 7 days
   - Don't keep unnecessary backups
   - But don't delete recent ones!

4. **Before big changes**
   - Create a fresh backup
   - Verify it's in iCloud
   - Have a restore plan
   - Test if unsure

## Questions?

Contact the team if you:
- Are unsure about any step
- Need to restore a backup
- See error messages
- Have backup problems

Better safe than sorry! 