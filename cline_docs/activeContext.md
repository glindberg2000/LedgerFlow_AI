[MEMORY BANK: ACTIVE]

# Active Context (Updated)

## Current Focus
- Dashboard backend and frontend are now fully integrated and working.
- Tiles for transaction count, client count, and statement file count are live, using real data from the legacy database.
- All backend models and queries are mapped to the correct legacy tables and columns.
- Statement file count uses 'profiles_uploadedfile'.
- All previous SQL errors are resolved.

## Next Steps
- Add more dashboard metrics as needed.
- Polish UI and add data visualizations.
- Connect additional backend data as required.

## Recent Changes
- Incremental integration milestone: dashboard metrics now live and accurate.
- All previous environment, path, and SQL issues resolved.

## Key Developments
- All model-level circular relationships (M2M, FK) were removed, but RecursionError persisted.
- Error traced to a custom admin index monkey-patch in profiles/admin.py (custom_admin_index and get_urls override).
- Commented out the custom admin index logic and restored the default Django admin index.
- Next step: Confirm admin loads and document this as a known pitfall for future customizations.

## Key Findings
- The error is not caused by admin customizations, relationships, or template tags.
- The error is triggered by the mere presence of the `StatementFile`/`UploadedFile` model in the `profiles` app.
- Database was never truly empty due to lingering objects, causing migration failures.
- `.env.dev` is the authoritative source for the database connection.
- Deleting all `profiles`-related files did not resolve the recursion error.

## Task Master
- Ensure all steps and findings are tracked in Task Master and cline_docs/problem_report_20250627_admin_recursion.md.
- Avoid repeating previous steps; document each isolation attempt.

## Outstanding Issue
- Custom business categories (e.g., 'Staging Expenses') are not mapped to IRS categories (e.g., 'Staging'), so their subtotals may not appear in IRS worksheet reports even if they show in the all-categories report.
- This results in a disconnect between custom/user-defined categories and standardized IRS worksheet categories.

## Recommendations
- Use the `parent_category` field in `BusinessExpenseCategory` to explicitly map custom categories to IRS categories.
- Implement a fuzzy string matching system to suggest or auto-map similar category names.
- Enforce or suggest selection from a controlled vocabulary during transaction classification.
- Build an admin interface to review, approve, and manage mappings between business and IRS categories.
- Update report aggregation to use the parent mapping or fuzzy match when rolling up subtotals for IRS worksheet lines.

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
- Migrating legacy Django-based LedgerFlow to FastAPI (backend) and React (frontend)
- Multi-user support, background processing, modular architecture
- Submodules: internal_chat_mcp (chat microservice), PDF-extractor (PDF parsing)
- Documentation and planning files are up to date

## Key Directories & Files
- Project root: /Users/greg/repos/LedgerFlor_AI_FastAPI/
- Backend: LedgerFlow_AI/ (app/, core/, etc.)
- Legacy Django: _deprecated/, ledgerflow/, profiles/, reports/, templates/
- Submodules: internal_chat_mcp/, PDF-extractor/
- Docs: LedgerFlow_AI/docs/, LedgerFlow_AI/cline_docs/
- Config: requirements/, docker/, .env, .cursor/mcp.json

## Plan & Next Steps
1. Refactor/migrate core Django functionality to FastAPI
2. Integrate submodules (internal_chat_mcp, PDF-extractor)
3. Scaffold and connect React frontend
4. Maintain and update cline_docs/ and docs/
5. Write/port tests and validate feature parity
6. Use Docker Compose for deployment

## Where to Find What
- Overview/setup: README.md, docs/development_guide.md, docs/onboarding/
- Current work: cline_docs/activeContext.md, cline_docs/progress.md
- System/tech: cline_docs/systemPatterns.md, cline_docs/techContext.md
- Legacy: _deprecated/, ledgerflow/, profiles/, reports/, templates/
- Submodules: internal_chat_mcp/, PDF-extractor/
- Config: .env, docker/, .cursor/mcp.json, requirements/

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

# Active Context (as of 2024-06-27)

## Current Focus
- Debugging persistent Django admin `RecursionError: maximum recursion depth exceeded`.

## Latest Findings
- Even with a minimal `app_list.html` (only extends and an empty content block), the RecursionError persists.
- All circular references and template loader issues have been excluded.
- This suggests a deeper Django template system bug or a project-specific misconfiguration.
- Next steps may require external review or advanced debugging.

## Current State
- The working database is now `ledgerflow_test_restore` (restored, fixed, and fully in sync with migrations).
- All migration drift and missing tables have been resolved.
- Admin bulk actions are enabled (DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000).
- All backup scripts have been updated to use the new database.
- Codebase and migrations are committed and pushed to remote.
- No secrets or `.env*` files are in version control; these are backed up separately.

## Backup/Restore Process
- Use `scripts/db/backup_dev_db.sh` for database-only backups (now points to `ledgerflow_test_restore`).
- Use `scripts/db/backup_dev_full.sh` for full backups (DB, media, config, state). If not using Dockerized Django, skip media/config container steps.
- All backup files are stored in iCloud and are automatically synced.
- After any major schema or data change, take a fresh backup and verify it.
- To restore: create a new DB, gunzip and psql the backup, then run Django migrations if needed.

## Commit/Version Control
- All code, migrations, and scripts are committed to Git.
- No secret files are committed; `.env*` and sensitive configs are only on the backup drive.

## Next Steps
- Continue using `ledgerflow_test_restore` as the main DB.
- Back up `.env*` and secrets to backup drive after any change.
- If switching to Dockerized Django, ensure config and volumes are in sync.
- Do not delete the old database until the new process is proven over time.
- Update this doc and README after any major process change. 

## Current Mission
Refactor the ingestion pipeline to consume the new ParserOutput contract from all parsers, standardizing how transaction data and statement metadata are processed throughout the system.

- **Branch:** `refactor/parser-ingestion-contract`
- **Status:** In progress

## Next Steps
1. Define and implement ParserOutput contract classes (ParserOutput, TransactionRecord, StatementMetadata)
2. Identify and document all parser output consumption points
3. Update one reference parser to implement ParserOutput
4. Refactor ingestion pipeline to consume ParserOutput
5. Update remaining parsers and documentation

## Task Master Alignment
- Task #13: Refactor Ingestion Pipeline for ParserOutput Contract
  - Subtasks:
    1. Define and implement ParserOutput contract classes
    2. Identify and document all parser output consumption points
    3. Update one reference parser to implement ParserOutput
    4. Refactor ingestion pipeline to consume ParserOutput
    5. Update remaining parsers and documentation

## Notes
- This is a critical architectural update for long-term maintainability and extensibility.
- All code that processes parser output will be updated to use the new contract.
- Documentation and team communication will be updated accordingly.

---
[2025-06-26] Active Context Update
- Wells Fargo Mastercard parser bug (logger scoping) resolved in PDF-extractor submodule. No main repo changes needed.
- All logger usage now consistent, debug prints and legacy code removed, parser contract-compliant.
- Next: Repo cleanup (remove logs, temp files, ensure no sensitive CSV/PDFs are committed).
- After cleanup: Update Task Master tasks and proceed to UI review/cleanup.
---

_Last updated: 2025-06-12_ 