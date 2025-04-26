# Django Project Migration Plan

## Current State Analysis

### Issues to Address
1. ~~Nested Django projects causing import path confusion~~ (Resolved in test instance)
2. ~~Multiple PostgreSQL instances (ports 5432, 5433) with inconsistent connections~~ (Test instance uses single DB)
3. No clear separation between dev and prod environments (Partially addressed with Docker setup for LedgerFlow)
4. Manual database management without proper backup procedures (In progress)
5. Complex directory structure making maintenance difficult (Being streamlined with LedgerFlow focus)

### Critical Data to Preserve
1. Database contents from test instance (clean, squashed migrations) - Using fresh archive from docker_archive
2. Migration history (from test instance) - Not needed due to fresh start
3. Custom application code (LedgerFlow specific features)
4. Configuration settings (Updated for LedgerFlow)
5. Business rules and profiles (LedgerFlow context)
6. Static files (CSS/JS/images) - Managed in current setup

## Migration Strategy

### Option 1: New Repository (Recommended - In Progress)
**Pros:**
- Clean slate without technical debt (Achieved with LedgerFlow focus)
- Proper structure from the start (Docker setup established)
- No risk of breaking existing functionality
- Clear separation of concerns
- Leverages clean setup from docker_archive

**Cons:**
- Requires careful data migration (Not needed due to fresh archive)
- Temporary loss of git history (Accepted for clean start)
- Additional setup time (Already invested in LedgerFlow)

### Recommended Approach: New Repository (Current Path)

### Phase 1: Preparation (Completed)
1. **Document Current State**:
   - Map database schema from test instance (Not needed, using fresh archive)
   - Document custom configurations (`settings.py`, environment variables) - Done for LedgerFlow
   - List dependencies (`pip freeze > requirements.txt`) and compare with latest guide's `requirements/base.txt` and `requirements/dev.txt` - Completed
   - Document business rules (LedgerFlow logic) - In progress
   - Identify static files and their locations - Managed in current setup

2. **Create Backup Strategy** (Adjusted)**:
   - Backup test instance database: Not needed, using fresh archive from docker_archive
   - Export configuration files - Completed for LedgerFlow
   - Document environment variables - Completed in `.env.example`
   - **Note**: Backups will be established for LedgerFlow as part of Docker workflow

### Phase 2: New Repository Setup (In Progress)
1. **Initialize New Repository** (Completed):
   ```bash
   mkdir LedgerFlow
   cd LedgerFlow
   git init
   git checkout --orphan initial
   echo "MIT License" > LICENSE
   git add LICENSE
   git commit -m "Initial commit with LICENSE"
   git switch -c develop
   ```

2. **Set Up Docker Environment** (Partially Completed):
   - Implement basic Docker workflow with single `docker-compose.yml` (In place)
   - Use environment variables to toggle dev/prod settings (e.g., `DEBUG`, `DATABASE_URL`) - Configured
   - Set up health checks for Postgres (To be updated for PostgreSQL 17.4):
     ```yaml
     healthcheck:
       test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"]
       interval: 5s
       retries: 5
     ```
   - Use `Makefile` shortcuts (`make up`, `make collect`, `make logs`) - To be implemented

3. **Migrate Code** (Adjusted):
   - Copy core application code from fresh archive in docker_archive - Not needed
   - Update import paths to match new `app/` structure - In progress for LedgerFlow
   - Implement settings structure with `django-environ` - Configured
   - Copy static files to `app/static/` - Managed
   - For local dev, install `requirements/base.txt` and `requirements/dev.txt` separately; Docker handles dependencies via the `Dockerfile` - Set up

### Phase 3: Data Migration (Adjusted)
1. **Database Migration**:
   - Create new PostgreSQL instance with version 17.4 (To be updated from 15)
   - Migrate data from test instance: Not needed, starting fresh
   - Validate data integrity (e.g., row counts, transaction records) - Will be done for new data
   - Set up basic backup procedures - To be implemented

2. **Configuration Migration** (Completed):
   - Migrate environment variables to `.env` - Done
   - Update Django settings per latest guide - Done
   - Configure database connection - Set for PostgreSQL 17.4
   - Set up basic logging - In place

3. **Static Files Migration** (Completed):
   - Copy static files from test instance to `app/static/` - Managed
   - Run:
     ```bash
     docker compose -p ledgerflow-prod exec django python manage.py collectstatic --noinput
     ```
   - Validate static file serving - Working

### Phase 4: Testing & Validation (Next Step)
1. **Functional Testing**:
   - Test core features (LedgerFlow specific functionality)
   - Verify data integrity using Adminer (`http://localhost:8082`)
   - Check import/export functionality
   - Validate business rules
   - If a cache backend env var is set (e.g., `CACHE_URL`), verify cache hits; otherwise skip
   - Create superuser:
     ```bash
     docker compose -p ledgerflow-prod exec django python manage.py createsuperuser
     ```
   - Verify CSS/JS load in container

2. **Performance Testing**:
   - Check database performance with PostgreSQL 17.4 (e.g., query response times)
   - Verify container health (`docker inspect`)
   - Test backup/restore procedures:
     ```bash
     cat prod_<timestamp>.dump | docker exec -i ledgerflow-prod_postgres_1 pg_restore -U user -d db --clean --no-owner --no-privileges --exit-on-error
     ```

3. **Automated Testing**:
   - Set up basic `pytest` for core features (e.g., LedgerFlow specific features)
   - Write smoke tests to validate basic functionality

### Phase 5: Transition Plan (Upcoming)
1. **Parallel Operation (2 days)**:
   - Run both systems in parallel if needed
   - Perform at least one data sync if applicable:
     ```bash
     pg_dump -U <user> -d <db_name> -Fc --clean --if-exists --no-owner > sync_db.dump
     cat sync_db.dump | docker exec -i ledgerflow-prod_postgres_1 pg_restore -U user -d db --clean --if-exists --no-owner --exit-on-error
     ```
   - Verify new system functionality
   - Compare results (e.g., transaction data, outputs)
   - Document discrepancies
   - **Note**: For databases >1GB, consider `pglogical` or `pg_dump --data-only --inserts` post-migration to optimize syncs

2. **Cutover Strategy**:
   - Rehearse dump/restore in dev to estimate downtime (pad by 20%):
     ```bash
     time (cat test_db.dump | docker exec -i ledgerflow-dev_postgres_1 pg_restore -U user -d db --clean --no-owner --no-privileges --exit-on-error)
     ```
   - Schedule maintenance window (e.g., 15-30 minutes)
   - Perform final data sync if needed
   - Update Let's Encrypt/Cloudflare origin certificates if using a reverse proxy
   - Switch DNS/endpoints to the new system
   - Monitor with:
     ```bash
     docker compose -p ledgerflow-prod logs -f django
     ```

## Migration Timeline
**Note**: The four-day timeline assumes a database <1GB and no major schema issues. If unforeseen schema conflicts arise, Day 4 may extend by 1 day for fixes. Adjusted for current progress.

### Day 1: Preparation (Completed)
- Document current state (schema, configs, dependencies, static files) - Adjusted for LedgerFlow
- Create backup - Not needed due to fresh archive
- Set up new repository - Done

### Day 2: Development (In Progress)
- Complete Docker setup with PostgreSQL 17.4
- Migrate core code and static files - Adjusted for LedgerFlow
- Begin data migration - Not needed

### Day 3: Testing (Next)
- Complete data migration - N/A
- Functional and performance testing with PostgreSQL 17.4
- Set up basic `pytest`
- Bug fixes using Adminer and logs

### Day 4: Transition (Upcoming)
- Parallel operation (2 days) if needed
- Final validation
- Cutover

## Risk Mitigation

### Technical Risks
1. **Data Loss**:
   - Multiple backups if needed
   - Validation checks (row counts, key records)
   - Rollback procedures (restore from dump)

2. **Configuration Issues**:
   - Thorough testing in dev environment
   - Detailed documentation for LedgerFlow
   - Validation scripts for settings and dependencies

### Business Risks
1. **Downtime**:
   - Rehearsed maintenance window (15-30 minutes)
   - Clear communication plan
   - Rollback procedures

2. **Data Integrity**:
   - Validation procedures
   - Verification steps for transaction data

## Success Criteria

### Technical
- All features working in new environment with PostgreSQL 17.4
- No data loss or corruption
- Proper backup/restore functionality (backup job completes ≤3 minutes per deploy)
- Clean import paths for LedgerFlow
- Correct static file serving
- Processing time <5 seconds per document (p95)

### Business
- No disruption to operations
- All reports generating correctly
- Business rules functioning properly in LedgerFlow
- Performance maintained or improved with PostgreSQL 17.4

## Next Steps

1. **Immediate Actions**:
   - Review and approve updated migration plan
   - Complete Docker configuration with PostgreSQL 17.4
   - Update Docker Compose to use latest PostgreSQL version

2. **Required Resources**:
   - Development time (prioritize critical features for LedgerFlow)
   - Testing environment (dev container)
   - Backup storage (to be set up)

3. **Dependencies**:
   - Team availability
   - Maintenance window approval
   - Stakeholder buy-in
   - Resource allocation

## Conclusion
The migration to the new Docker-based workflow for LedgerFlow provides:
- Clean, maintainable structure
- Proper database management with robust backups using PostgreSQL 17.4
- Streamlined deployment procedures
- Efficient development workflow

This updated plan reflects current progress with LedgerFlow, using a fresh archive from docker_archive, ensuring a smooth transition with minimal risk. It's tailored for a solo developer, balancing speed with essential safeguards like dev/prod isolation, static file validation, and basic automated testing. If schema issues arise, a one-day buffer is included to address them.