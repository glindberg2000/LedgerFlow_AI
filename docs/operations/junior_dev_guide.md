# LedgerFlow – **Quick‑Start Guide for Junior Developers**

*(v2025‑05, Safety-First Workflow)*

---
## 0  What You're Working With
| Part | What it is | Where it lives |
|------|------------|----------------|
| **Code** | Django project + tools | local repo on your Mac (`~/repos/LedgerFlow`) |
| **Dev stack** | Django + Postgres + Search Services | Managed by **Docker Compose** (via safety wrapper) |
| **Prod stack** | Production containers with safety measures | Managed by senior team / CI |
| **Backups** | Hourly DB + Daily Full System | iCloud (`~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/`) |
| **Database** | Postgres data files | Local SSD (`~/LedgerFlow_data/pg`) |

> **Golden rule:** _Never use raw docker commands. Always use `make` targets and verify iCloud sync before proceeding._

---
## 1  One‑time setup
```bash
# Clone the repo
git clone https://github.com/your‑org/LedgerFlow.git
cd LedgerFlow

# Set up your environment
cp .env.example .env.dev
# → Edit .env.dev with your settings (never commit this!)

# Initialize development environment
make init

# Install safety wrapper (prevents accidental data loss)
curl -s https://raw.githubusercontent.com/ledgerflow/scripts/master/install_ledger_docker.sh | bash
# Re-open your terminal - all 'docker' commands now route through safety guard
```

---
## 2  Daily Development Workflow
Run `make help` to see all available safe commands.

Common operations:
| Step | Command | What happens |
|------|---------|--------------|
| Start system | `make dev` | Starts Django (port 9001) and dependencies |
| Check status | `make status` | Shows running services and health (including backup container) |
| Edit code | Use VS Code/Cursor | Hot reload enabled for development |
| DB changes | `make migrate-safe` | Creates verified backup, then runs migration |
| View logs | `make logs` | Shows all service logs |
| Run tests | `make test` | Runs tests with automatic backup |
| Start backup service | `make backup-cron` | Starts hourly backup container if not running |
| Shutdown | `make down` | Graceful shutdown with backup |

### Key Directories
```
app/                 # Django applications
requirements/        # Dependencies
scripts/db/          # Backup and restore scripts
docs/operations/     # Documentation
cline_docs/         # Technical documentation
~/LedgerFlow_data/pg  # Postgres data (NEVER in iCloud)
```

---
## 3  Backup System (Important!)
```bash
# Manual database backup
./scripts/db/backup_dev_db.sh

# Full system backup
./scripts/db/backup_dev_full.sh

# Check backup status and sync
ls -lh ~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev/

# CRITICAL: Verify iCloud sync completion
brctl log -w &   # watch iCloud sync; Ctrl-C when lines stop
mdls -name kMDItemFSSize backups/dev/last.sql.gz   # Must be >10240 bytes
```

### Verifying Backup Safety
1. Check backup size: Must be >10KB
2. Verify iCloud sync:
   - Watch sync complete with `brctl log -w`
   - Check Finder cloud icon is solid (not syncing)
   - Verify local file size with `mdls`
3. Only proceed when ALL checks pass

### Automatic Backups
- Hourly database backups (minute 0)
- Daily full system backup (2 AM)
- Pre-migration safety backups
- Pre-test safety backups

The backup container (`ledgerflow-backup`) must always be running.
Check with `make status` - if missing, run `make backup-cron`.

### Restore Process
```bash
./restore_db_clean.sh -f path/to/backup.sql.gz
```
**Always verify backup sync before restore!**

---
## 4  Version Control Workflow
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally
3. Before commit:
   - Verify backups are synced to iCloud
   - Check all tests pass
   - Review changes with `git status`
4. Commit and push:
   ```bash
   git add .
   git commit -m "feat: Your feature description"
   git push origin feature/your-feature
   ```
5. Open PR → CI runs tests + backup verification

---
## 5  Safety Checklist
Before any database operation:
- ✅ Check iCloud sync status (solid cloud icon)
- ✅ Verify backup size with `mdls` (>10KB)
- ✅ Confirm backup container is running
- ✅ Run `make test` if changing models
- ✅ Use safety scripts for migrations

After operations:
- ✅ Verify new backup was created
- ✅ Wait for iCloud sync to complete
- ✅ Test functionality if applicable

---
## 6  Never Do These Things
- ❌ Use raw `docker` or `docker compose` commands
- ❌ Store Postgres data in iCloud
  > **⚠️ Never store the live Postgres volume inside iCloud.**  
  > Use `~/LedgerFlow_data/pg` (local SSD) – backups go to iCloud automatically.
- ❌ Skip backup verification
- ❌ Ignore small backup warnings
- ❌ Delete backups without team approval
- ❌ Commit environment files
- ❌ Run raw database commands
- ❌ Force push to protected branches

---
## 7  Common Issues

**Q: Backup seems small (<10KB)?**  
A: Stop immediately and alert the team. Create a manual backup with:
```bash
./scripts/db/backup_dev_db.sh
# Then verify sync:
brctl log -w &
mdls -name kMDItemFSSize backups/dev/last.sql.gz
```

**Q: Can't find recent backup?**  
A: Check:
1. iCloud sync status (`brctl log -w`)
2. Internet connection
3. Logs in `backups/dev/logs/`
4. Backup container status (`make status`)
5. Run manual backup if needed

**Q: Need to restore after failed operation?**  
A: 
1. Check `backups/dev/` for recent backup
2. Verify backup size and sync status
3. Use `restore_db_clean.sh` script
4. Test application after restore

---
## 8  Getting Help
1. Run `make help` for available commands
2. Check `docs/operations/backup_procedures.md`
3. Review logs in `backups/dev/logs/`
4. Contact team in #ledgerflow-dev
5. **Don't proceed if unsure!**

Remember: _Better a careful backup than a hasty recovery!_

---
## 9  Documentation Map
- `docs/operations/backup_procedures.md` - Detailed backup guide
- `docs/operations/backup_status_report.md` - System status
- `cline_docs/database_backup.md` - Technical details

For full documentation, see `docs/operations/dev_deployment_guide.md` 