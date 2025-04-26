# Production Bootstrap Runbook

## Prerequisites (Local Setup)
```bash
git checkout main && git pull           # everyone up to date
which docker                            # ⇒ /Users/greg/bin/ledger_docker
export LEDGER_ENV=prod                  # safety variable for every step
```

## Bootstrap Steps

### 1. Build/Pull Production Image
```bash
TAG=v20250424
docker build -t ledgerflow:$TAG .       # or docker pull registry/ledgerflow:$TAG
```

### 2. Create Production Infrastructure
```bash
make prod-bootstrap TAG=$TAG            # idempotent
```

### 3. Verify Container Health
```bash
make safety-check                       # checks wrapper + protected volumes
make logs                               # tail for 10s - look for 'Running...'
```

### 4. Create First Production Backup
```bash
make backup                             # writes to ~/iCloudLedger/backups/prod
ls -lh ~/iCloudLedger/backups/prod | tail -1  # size > 10 KB?
```

### 5. Verify Application Access
```bash
open http://localhost:9000              # or your real prod URL
```

### 6. Document Deployment
Example comment for PR:
```
Bootstrapped prod with tag v20250424 – first backup ledgerflow_prod_20250424_2031.dump (172 KB) – containers healthy
```

## Critical Guard-Rails ⚠️

1. **Wrapper Path Check**
   - `which docker` MUST point to ledger_docker before any command
   - Never use raw docker commands in production

2. **Backup Location**
   - Production backups go to `~/iCloudLedger/backups/prod/`
   - Always verify backup file size (> 10 KB)

3. **Bootstrap Safety**
   - Never rerun prod-bootstrap with a different tag on a live DB
   - Use `make prod-up TAG=...` for updates once backups exist

## Post-Deployment Steps

### 1. Tag Production State
```bash
git tag -a v20250424-prod -m "First clean prod"
git push origin v20250424-prod
```

### 2. Future Improvements
- [ ] Implement nightly test-restore automation (pending CI/CD work)
- [ ] Add monitoring for backup success/failure
- [ ] Set up alerting for container health
``` 