# Active Context

## Current Focus
- Implementing and improving backup and restore functionality
- Enhancing deployment pipeline
- Setting up development and production environments
- Implementing security measures
- Documenting system architecture and processes
- Creating comprehensive onboarding materials for new team members
- Integrating MPC tools and dockerized development workflow

**Critical Schema Issue:**
- The `profiles_transactionclassification` table (for transaction classification history/audit) is missing from the database, even though the model and migrations exist and are marked as applied.
- This is a global schema/migration drift problem, not just a data or legacy file issue.
- Any admin action, cascade, or code that touches the classification history will fail for all clients, not just problematic files.

## Backup & Restore: Crucial Details

**Backup Storage Locations:**
- **Primary (iCloud):**
  - `~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/`
    - `dev/` (development backups)
    - `prod/` (production backups)
    - `test/` (test/restore)
    - `logs/` (backup logs)
    - `migrations/` (pre-migration backups)
- **Docker Bind Mounts:**
  - Dev: `~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev` → `/backups` in postgres/backup containers
  - Prod: `/Users/greg/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups` → `/icloud_backups` in backup container

**Backup Scripts & Automation:**
- **Manual/CLI:**
  - `make backup FILE=...` (see Makefile)
  - `scripts/db/backup_dev_db.sh` (hourly DB backup, integrity check, retention)
  - `scripts/db/backup_dev_full.sh` (daily full backup: DB, media, config, manifest)
- **Cron Jobs:**
  - Hourly DB: `0 * * * * /path/to/backup_dev_db.sh`
  - Daily full: `0 2 * * * /path/to/backup_dev_full.sh`
  - Logs: `~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev/logs/`
  - Setup: `scripts/db/setup_backup_cron.sh` (installs jobs, test run in 5 min)

**Restore Procedures:**
- **Makefile:**
  - `make restore FILE=...` (see Makefile for env/volume details)
- **Manual:**
  - `./restore_db_clean.sh -f path/to/backup.sql.gz` (see cline_docs/database_backup.md)
- **Test Restore:**
  - `make restore-test FILE=...` (restores to temp DB, verifies structure/data)

**Docker Compose: Key Services, Ports, Volumes**
- **Dev (docker-compose.dev.yml):**
  - `django`: 9000:8000, media: ledgerflow_dev_media
  - `postgres`: 5435:5432, data: ledgerflow_dev_postgres_data, backups: bind mount
  - `redis`: 6379:6379
  - `adminer`: 8082:8080
  - `searxng`: 8888:8080 (localhost only)
- **Prod (docker-compose.prod.yml):**
  - `django`: 9002:8000, media/static: bind mounts
  - `postgres`: 5436:5432, data: ledgerflow_postgres_data
  - `backup`: iCloud backup bind mount

**Volume Protection & Verification:**
- Run `make check-volumes` or `./scripts/verify_volumes.sh` to verify Docker volumes and backup directories exist and are writable.
- Key volumes: `ledgerflow_postgres_data`, `ledgerflow_media`, `searxng_data`, `redis_data`
- Key bind mounts: see docker-compose files and verify_volumes.sh

**Backup Integrity & Retention:**
- Minimum backup size: 10KB (checked in scripts)
- All backups are verified for size, structure, and test-restored to temp DB
- Retention: 7 days for hourly/daily, auto-cleanup in scripts
- iCloud sync: All backups/logs are synced automatically; check iCloud status if missing files

**Environment Variables/Config:**
- DB credentials: set in `.env.dev`/`.env.prod` and passed to containers
- Backup scripts use Docker Compose service/container names (see Makefile/scripts)
- SearXNG/Redis: see .env.dev and docker-compose for host/port config

**Logs & Troubleshooting:**
- Backup logs: `backups/dev/logs/` (iCloud)
- Script output: check cron logs, script logs, and Docker logs for backup/restore containers
- For errors: check backup size, permissions, iCloud sync, and container health

**Full Details:**
- See `cline_docs/database_backup.md` for a complete backup/restore reference, including safety, verification, and troubleshooting procedures.

## What I'm Working On Now

- Updating the batch uploader and parsing workflow to use a hybrid approach for account number:
  - Account number is **optional** on upload (batch uploader).
  - Account number is **mandatory** for parsing/processing (must be present before parsing, either by extraction or manual entry).
- Ensuring UI and backend logic reflect this policy.

## Recent Changes
- Committed: Improved category mapping, sorting, and clickable subtotals in all reports.
- IRS worksheet and all-categories reports now highlight unmapped business categories and allow direct navigation to filtered transactions.
- **NEW:** Classification logic now always sets `transaction.category` to the mapped, allowed LLM `category_name` for all classification actions (single, batch, escalation). This prevents legacy or custom category values (e.g., 'Staging Expenses') from persisting and ensures only allowed business/IRS categories are used. Escalation and retry logic is in place to enforce strict mapping and flag for review if the LLM cannot comply.
- Patched `normalize_parsed_data_df` to guarantee `source`, `file_path`, and `file_name` fields for all imports.
- Verified First Republic parser and all modular parsers now work with Django import.
- Cleaned up admin UI and removed legacy parser test utilities.
- Added and migrated ParsingRun model for import logging.
- Communicated with Extractor_Dev to coordinate and verify all parser/normalizer changes.
- Analyzed the batch uploader code and identified that account number is not currently required or set in batch uploads.
- Decided on hybrid approach for account number requirement after analysis and discussion.

## Outstanding Issue
- Custom business categories (e.g., 'Staging Expenses') are not mapped to IRS categories (e.g., 'Staging'), so their subtotals may not appear in IRS worksheet reports even if they show in the all-categories report.
- This results in a disconnect between custom/user-defined categories and standardized IRS worksheet categories.

## Next Steps / Recommendations
- **Parent Mapping:** Use the `parent_category` field in `BusinessExpenseCategory` to explicitly map custom categories to IRS categories. This allows aggregation and reporting to roll up custom categories under the correct IRS line.
- **Fuzzy Matching:** Implement a fuzzy string matching system to suggest or auto-map similar category names (e.g., 'Staging Expenses' → 'Staging'). This can be used as a fallback or for admin review.
- **Schema Enforcement During Classification:** During transaction classification, enforce or suggest selection from a controlled vocabulary (IRS + business categories), possibly with auto-complete or admin override, to reduce drift.
- **Admin UI for Mapping:** Build an admin interface to review, approve, and manage mappings between business and IRS categories, including suggestions for unmapped categories.
- **Reporting Logic:** Update report aggregation to use the parent mapping or fuzzy match when rolling up subtotals for IRS worksheet lines.

## Action Item
- Document and discuss the best approach for maintaining robust, user-friendly category mapping between custom business and IRS worksheet categories. Prioritize a solution that is maintainable and transparent for both admins and end users.

### MPC Tools Integration and Dockerized Workflow
1. Added MPC tools integration (GitHub, Discord, Task Manager, PostgreSQL)
2. Implemented dockerized development environments for all team roles
3. Updated onboarding documentation to reflect new tools and workflows
4. Enhanced security protocols for containerized environments
5. Prepared role-specific environment configurations

### Onboarding Documentation
1. Created comprehensive onboarding documentation in `docs/onboarding/`
2. Added role-specific guides for PM, DB Manager, Full Stack Dev, and Reviewer
3. Created Memory Bank guide to explain our documentation system
4. Added credentials and secrets management documentation
5. Prepared for onboarding new team members

### Backup System Implementation
1. Added backup target to Makefile
2. Improved path handling for spaces
3. Enhanced error handling
4. Added success/failure messages
5. Implemented backup verification

### Deployment Pipeline
1. Created docker-compose configurations
2. Set up development environment
3. Configured production settings
4. Implemented environment variables
5. Added deployment scripts

### Documentation
1. Created Memory Bank structure
2. Documented product context
3. Documented system patterns
4. Documented technical context
5. Documented project progress

## Current State
- **Parser import pipeline is robust and production-ready.**
    - All required fields (`source`, `file_path`, `file_name`) are now forcibly added to every row in every parser output, thanks to a patch in `normalize_parsed_data_df` (Extractor_Dev).
    - No more KeyErrors or missing fields during Django import, even for new or updated parsers (e.g., First Republic Bank).
- **Admin UI improvements:**
    - Parser assignment is always visible in the StatementFile admin.
    - Batch Parse and Normalize is blocked if no parser is assigned, with clear error messages.
- **Legacy/unused admin parser utilities and models have been removed** for clarity and maintainability.
- **ParsingRun model** logs all real parsing/import actions, including status, errors, and rows imported, for full audit/history.
- **All code and database migrations are up to date and working.**
- **All recent changes have been committed.**

### Working Features
1. Basic Django application
2. Docker containerization
3. Database integration
4. Development environment
5. Backup system
6. Dockerized development workflow
7. MPC tools integration

### Active Issues
1. Path handling in backup/restore
2. Environment configuration
3. Deployment automation
4. Security implementation
5. Documentation completion
6. MPC tools configuration optimization

## Next Steps

### Immediate Tasks
1. Onboard new team members (PM, DB Manager, Full Stack Dev, Reviewer)
2. Complete restore functionality
3. Implement CI/CD pipeline
4. Set up monitoring
5. Configure TLS
6. Finalize MPC tools integration

### Short-term Goals
1. Team training on Memory Bank and safety protocols
2. Production deployment
3. Security hardening
4. Performance optimization
5. Documentation updates
6. Dockerized workflow refinement

### Upcoming Features
1. Advanced document processing
2. Workflow automation
3. API development
4. Security enhancements
5. Analytics implementation
6. Expanded MPC tools integration

## Technical Notes

### Environment Setup
- Development using docker-compose.dev.yml
- Production using docker-compose.prod.yml
- Environment variables in .env files
- Separate database instances
- Backup storage configuration
- Dockerized role-specific environments
- MPC tools configured for each role

### Current Configuration
- Python 3.11+
- Django 5.2
- PostgreSQL 15+
- Docker/Docker Compose
- Nginx (pending)
- GitHub integration
- Discord/Matrix integration
- Task Manager integration

### Development Status
- Local development functional
- Dockerized development functional
- Testing environment pending
- Staging environment pending
- Production environment pending
- CI/CD pipeline in progress
- MPC tools integration in progress

## Implementation Details

### Backup System
```python
# Current backup implementation
make backup FILE=path/to/backup.sql
```

### Restore System
```python
# Current restore implementation
make restore FILE=path/to/backup.sql
```

### Deployment Process
```bash
# Development deployment
docker-compose -f docker-compose.dev.yml up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Dockerized Session Start
```bash
# Start role-specific dockerized session
make <role>-session  # e.g., make reviewer-session
```

## Pending Decisions

### Technical Decisions
1. Cloud storage integration
2. Redis implementation
3. TLS configuration
4. Monitoring solution
5. Backup retention policy
6. MPC tools scalability approach

### Architecture Decisions
1. Service scaling strategy
2. Cache implementation
3. Search optimization
4. Security measures
5. Integration patterns
6. Dockerized environment standardization

## Known Limitations

### Current Limitations
1. Local backup storage
2. Manual deployment steps
3. Basic error handling
4. Limited monitoring
5. Incomplete documentation
6. Initial MPC tools configuration

### Technical Debt
1. Path handling improvements
2. Error handling enhancement
3. Configuration management
4. Test coverage
5. Documentation gaps
6. Docker image optimization

## Testing Status

### Implemented Tests
1. Basic unit tests
2. Database connectivity
3. Backup functionality
4. Environment validation
5. Configuration testing
6. Docker environment testing

### Pending Tests
1. Integration tests
2. Performance tests
3. Security tests
4. Load tests
5. End-to-end tests
6. MPC tools integration tests

## Security Considerations

### Implemented Security
1. Basic authentication
2. Environment isolation
3. Database security
4. Docker security
5. Backup encryption
6. Containerized role isolation

### Pending Security
1. TLS implementation
2. Advanced authentication
3. Access control
4. Security monitoring
5. Vulnerability scanning
6. MPC tools security hardening

## Documentation Status

### Completed Documentation
1. Product context
2. System patterns
3. Technical context
4. Project progress
5. Active context
6. Onboarding documentation
7. MPC tools integration guide

### Pending Documentation
1. API documentation
2. Deployment guide
3. Security guide
4. Testing guide
5. User manual
6. Advanced MPC tools configuration

## Resource Allocation

### Current Resources
1. Development environment
2. Local testing
3. Version control
4. Documentation system
5. Backup storage
6. Dockerized environments
7. MPC tools infrastructure

### Required Resources
1. Production servers
2. Monitoring systems
3. CI/CD pipeline
4. Security tools
5. Testing infrastructure
6. Advanced MPC tools

## Timeline

### Current Week
1. Onboard new team members
2. Complete backup/restore
3. Implement CI/CD
4. Configure security
5. Update documentation
6. Finalize MPC tools integration

### Next Week
1. Team training on Memory Bank and safety protocols
2. Production deployment
3. Security hardening
4. Performance testing
5. Documentation review
6. MPC tools optimization

### Month Ahead
1. Feature development
2. System optimization
3. Security auditing
4. Integration testing
5. User acceptance testing
6. Advanced MPC tools implementation

## 2024-04-25 Major Cleanup and Codebase Confirmation

- Moved legacy/duplicate app folders (`app/ledgerflow`, `app/core`, `app/profiles`, `pdf_extractor_web`) to `deprecated/`.
- Deleted SQL dumps, logs, and stray files from project root.
- Moved all shell scripts to `scripts/`.
- Confirmed live dev codebase is `core/` (via docker-compose.dev.yml) and prod is `ledgerflow/` (via docker-compose.prod.yml).
- Restarted all containers (except vsc-ai-coder-bot) and verified site is up and data is available on port 9000.
- No dependency on deprecated folders for live site.

## 2024-05-04 Onboarding Documentation Creation

- Created comprehensive onboarding documentation in `docs/onboarding/`
- Added role-specific guides for Project Manager, Database Manager, Full Stack Developer, and Reviewer
- Created guide explaining the Memory Bank system
- Added documentation about credentials and secrets management
- Prepared for onboarding new team members with Discord/Matrix communication

## 2024-05-10 MPC Tools and Dockerized Development Integration

- Added MPC tools integration (GitHub, Discord, Task Manager, PostgreSQL)
- Implemented dockerized development environments for all team roles
- Updated onboarding documentation to reflect new tools and workflows
- Enhanced security protocols for containerized environments
- Added role-specific environment configurations

## Current State
- Django app can run both outside Docker and inside Docker Compose.
- SearXNG integration is robust: uses SEARXNG_HOST env var in both environments.
- Cloud Postgres DB (Neon) is now the main dev database.

## How to Start the App

### Outside Docker (Local Dev)
1. Ensure Docker containers for SearXNG and Redis are running:
   - `docker compose -f docker-compose.dev.yml up -d searxng redis`
2. In `ledgerflow/.env.dev`, set:
   - `SEARXNG_HOST=http://localhost:8888`
   - `DATABASE_URL=postgres://newuser:neonpassword2024@ep-floral-mode-aaxawm69-pooler.westus3.azure.neon.tech:5432/neondb?sslmode=require`
3. Run:
   - `source venv/bin/activate`
   - `python manage.py runserver`

### Inside Docker Compose
1. In `docker-compose.yml`, Django service sets:
   - `SEARXNG_HOST: http://searxng:8080`
   - `DATABASE_URL` as needed (can use Neon or local Postgres)
2. Start all services:
   - `docker compose -f docker-compose.dev.yml up -d`

## Cloud DB Migration (Neon)
- All devs now use a shared Neon Postgres instance for development.
- Migration steps:
  1. Exported local DB and imported to Neon.
  2. Updated all configs to use Neon connection string.
  3. Granted privileges to dev user.
- Benefits:
  - All devs can connect from anywhere, any environment.
  - DB manager can spin up isolated dev DBs for each dev or feature branch.
  - No need to expose local DBs or manage local Postgres installs.
  - Easy to grant/revoke access and manage DB lifecycle.

## Next Steps
- Document DB access policy for new devs.
- Optionally automate per-dev DB provisioning for feature isolation.

## SearXNG Multi-Environment Configuration
- Always use the SEARXNG_HOST env var in code and config.
- Supported values:
  - Local dev (host): http://localhost:8888
  - Docker Compose: http://searxng:8080
  - Docker container accessing host: http://host.docker.internal:8888
  - Cloud/remote: http://<public-ip>:8888
- See onboarding docs and .env.dev for details and troubleshooting.

## MIGRATION SNAPSHOT: End-of-Phase Summary (Pre-Repo Move)

### Major Accomplishments
- **Classification & Category Mapping:**
  - Unified all transaction update logic (admin + batch) using a single DRY function (`get_update_fields_from_response`).
  - LLM classification now strictly enforces allowed business/IRS categories; legacy/custom values are overwritten.
  - Escalation and retry logic in place for LLM failures, with fallback to a more precise agent.
  - Admin UI improvements: processed/unprocessed filter, reset action, and batch actions for classification/payee lookup.
  - 6A and all-categories reports now highlight unmapped categories and allow direct navigation to filtered transactions.

- **Batch Processing:**
  - Batch jobs for classification and payee lookup now update the DB identically to admin actions.
  - Real-time batch progress and log viewer in ProcessingTask detail page.
  - Sidebar and action UX improvements for transaction admin.

- **Memory Bank & Documentation:**
  - All critical context, system, and technical docs are up to date in `cline_docs/`.
  - Task-Master tasks reflect the current project state and priorities.

### Outstanding Issues
- **Data Quality:**
  - Some legacy transactions and parser outputs have inconsistent or unmapped categories.
  - Need to revisit parser integration and normalization to ensure clean, reliable data ingestion.

- **Parser Integration:**
  - Legacy PDF/CSV parsers (in subrepo) were partially integrated; some work in Django, others return blank results.
  - Dynamic import logic and sys.path patching are in place, but environment and data format mismatches remain.
  - Next step: Validate parsers in their original console environment, document their behavior, and plan robust re-integration.

### Next Steps (Post-Migration)
1. **Parser/Normalization Deep-Dive:**
   - Test legacy parsers in their original environment with known-good samples.
   - Document input/output, dependencies, and quirks for each parser.
   - Compare with Django integration and resolve any discrepancies.
   - Plan for robust, maintainable parser integration in the new repo.
2. **Data Quality Audit:**
   - Review and clean existing transaction/category data as needed.
   - Implement improved normalization and mapping logic as required.
3. **Continue Feature Development:**
   - Resume work on PDF upload, processing UI, and advanced reporting once parser foundation is solid.

### Notes for Migration
- This context snapshot should be preserved and imported into the new repo's memory bank before any further work.
- All code, docs, and task-master tasks are up to date as of this snapshot.
- Ready for a clean, focused start on parser/data normalization in the new environment.

# Post-Migration Next Steps

## Immediate Priorities
- **Parser Integration:**
  - Validate legacy PDF/CSV parsers in their original environment with known-good samples.
  - Document input/output, dependencies, and quirks for each parser.
  - Compare with Django integration and resolve discrepancies.
  - Plan robust, maintainable parser integration in the new repo.
- **Data Normalization:**
  - Review and clean existing transaction/category data as needed.
  - Implement improved normalization and mapping logic as required.
- **Reporting Improvements:**
  - Ensure all business/IRS category mapping is robust and transparent.
  - Update reports to use new mapping/normalization logic.
- **Batch Processing:**
  - Confirm batch jobs for classification and payee lookup update the DB identically to admin actions.
  - Monitor and improve batch progress/logging UX as needed.

## Context
- All classification, batch, and parser context is up to date as of the last migration snapshot.
- The system now enforces strict category mapping and DRY update logic for transactions.
- Outstanding issues: legacy data quality, parser integration, and normalization.

## What to Build Next
1. **Parser/Normalization Deep-Dive:**
   - Test and document all legacy parsers.
   - Build a robust ingestion pipeline.
2. **Data Quality Audit:**
   - Clean and normalize existing data.
3. **Continue Feature Development:**
   - Resume work on PDF upload, processing UI, and advanced reporting once parser foundation is solid.

## Current Debugging Process: Parser/Normalizer Integration

### 1. **Initial Issue**
- The new normalizer (`normalize_parsed_data_df`) outputs a SHA256 hash in the `transaction_id` field.
- In the Django model, `transaction_id` is for external/statement IDs, and `transaction_hash` is for deduplication.
- Fix: The normalizer was updated (by Extractor_Dev) to output the hash in `transaction_hash` and only set `transaction_id` if present in the source data.
- Django import logic was updated to map these fields correctly.

### 2. **Testing and Results**
- The parser and normalizer now output valid transactions with correct fields.
- However, a new error appeared: `null value in column "classification_method" of relation "profiles_transaction" violates not-null constraint`.
- This means the import logic must provide a value for `classification_method` (required by the model, choices: "AI", "Human", "None").

### 3. **How to Run and Test**
- **Backend:**
  - Activate the virtualenv: `source venv/bin/activate`
  - Run Django: `python manage.py runserver 8001`
  - Set any needed env vars in the shell before running.
- **Frontend:** (not covered in this session, check project docs if needed)
- **Testing Import:**
  - Use the Django admin UI to upload and parse statement files.
  - The parser/normalizer should now produce a DataFrame with all expected fields, including `transaction_hash`.
  - Transactions will fail to import if required fields (like `classification_method`) are missing.

### 4. **Robust Normalizer Usage**
- Always use `normalize_parsed_data_df(file_path, parser_name, client_name)`.
- The DataFrame will have all context columns, normalized dates, and deduplication hash.
- Map `transaction_hash` to the model's hash field, and `transaction_id` to the external/statement ID.

### 5. **Next Steps**
- Update the import logic to provide a default value for `classification_method` (e.g., "AI" or "None") if not present in the row.
- Retest import from the UI.
- If further errors occur, check for other required fields in the model.

### 6. **Crucial Details for New Context**
- Always check the model for required/not-null fields.
- Ensure the normalizer output is mapped to the correct model fields.
- If you see errors about missing fields, update the import logic to provide defaults or handle missing data.
- Use the memory bank and this file as your source of truth after a reset.

## [2025-06-05] Unification of Unclassified Transaction Defaulting
- All raw imports and admin resets now use the constant CLASSIFICATION_METHOD_UNCLASSIFIED (value: "None") for classification_method.
- This ensures consistency between admin actions and import workflows.
- The constant is defined in profiles/models.py and imported wherever needed.
- Next steps: verify in UI and DB that all unclassified transactions have classification_method = "None" after import or reset.

## [2025-06-05] Unification of Payee Extraction Method Defaulting
- All raw imports now use the constant PAYEE_EXTRACTION_METHOD_UNPROCESSED (value: "None") for payee_extraction_method.
- This ensures consistency between admin actions and import workflows for payee extraction status.
- The constant is defined in profiles/models.py and imported wherever needed.
- Next steps: verify in UI and DB that all unprocessed transactions have payee_extraction_method = "None" after import or reset.

## [2025-06-05] Robustness: Automatic Transaction ID Sequence Sync
- Transaction import and batch parse actions now automatically sync the primary key sequence before bulk creation.
- This prevents duplicate key errors for users, even if the DB sequence is out of sync.
- No manual DB intervention is ever required.

## Next Steps

1. Ensure batch uploader allows upload without account number.
2. Update parsing logic to require account number (raise error if missing, provide UI for manual entry if extraction fails).
3. Update admin/status UI to flag files missing account number before parsing.
4. Test the full workflow for both upload and parsing stages.

## What Was Done
- Confirmed the table is missing using a Django ORM script.
- All migrations for the `profiles` app are marked as applied, but the table is not present in the DB (classic migration drift).
- A full database-only backup was created and verified using `scripts/db/backup_dev_db.sh` (backup file: `ledgerflow_backup_20250609_095414.sql.gz`).
- No destructive schema changes have been made yet.

## Next Planned Steps
- Safely repair the schema by resetting and reapplying migrations for the `profiles` app (which will drop and recreate all tables in that app).
- This will destroy all data in `profiles` tables, so the backup is critical for restoration.
- Optionally, test the restore process in a new database before applying to production/dev.

## Reasoning
- The missing table is a permanent, global issue that will break classification features for all clients, now and in the future, unless fixed.
- The only safe, permanent fix is to recreate the table via migrations, which requires resetting the app's schema.
- All actions are being taken with full backups and data safety in mind.

## Key Details
- Backup script and location: `scripts/db/backup_dev_db.sh`, iCloud-synced backup folder.
- Table missing: `profiles_transactionclassification` (required for classification history/audit).
- All migrations for `profiles` are marked as applied, but the table is not present in the DB.
- Next step: schema repair/reset, then restore data as needed. 