# Problem Report: Django Admin RecursionError (2025-06-27)

## Current State
- Task Master has been reset to track only the RecursionError debugging workflow.
- All unrelated tasks and PRD content have been removed.
- The PRD now contains only the RecursionError debugging steps, with all previous steps marked as done.
- The next step is to isolate and verify the UploadedFile model as the source of the error.

## Database State
- **Current DB:** A fresh, empty database is being used for debugging to rule out data/migration issues.
- **Original DB:** [FILL IN: path/connection string for original production database, e.g., `ledgerflow` or `ledgerflow_prod`]
- **Action:** After confirming the RecursionError is not database-related, consider switching back to the original database to verify the fix in a production-like environment.

## Workflow
- All debugging steps are tracked in Task Master for transparency and repeatability.
- This document should be updated as new findings emerge or if the debugging context changes.

## Recent Steps
- profiles app directory renamed to profiles_test and INSTALLED_APPS updated for isolation.
- Next: Restart Django and test admin access.

## Steps Taken
- [x] Minimized models.py to only UploadedFile for RecursionError isolation. Next: Restart Django and test admin access.

## Problem Summary

- **Error:** `RecursionError: maximum recursion depth exceeded while calling a Python object` in Django admin, triggered after navigation template changes and persisting through all subsequent attempts to revert or debug.
- **Context:** Occurs in the main project when accessing Django admin, but not in a minimal Django project or clean environment.
- **Trace:** Error appears deep in Django's template rendering, specifically in the i18n template tag, but only when the `StatementFile` (now `UploadedFile`) model is present in `profiles/models.py`.

---

## Environment
- **Django version:** 5.2.3
- **Python version:** 3.11
- **OS:** macOS (darwin 24.5.0)
- **Virtualenvs:** Both `venv` and `cleanenv` tested
- **Project:** LedgerFlow_AI

---

## Steps Taken

### 1. Template & Admin Customization Isolation
- Disabled all custom admin templates (`index.html`, `base_site.html`).
- Disabled all custom `admin.py` files in `profiles`, `reports`, and `profiles/parsers_utilities`.
- Cleared Python bytecode caches.
- **Result:** Error persisted.

### 2. App & Model Isolation
- Removed all custom apps from `INSTALLED_APPS`, leaving only Django built-ins: admin worked.
- Added apps back one by one; adding `profiles` brought back the RecursionError.
- Renamed `profiles/models.py` to disable all models: error disappeared.
- Uncommented models one by one:
  - `BusinessProfile`, `Transaction`, `IRSWorksheet`, `IRSExpenseCategory`, `BusinessExpenseCategory`: **No error**.
  - `StatementFile` (even as an empty class): **RecursionError returns**.

### 3. StatementFile Model Deep Dive
- Restored the full `StatementFile` model (all fields, relationships, methods).
- Fixed a `NameError` by moving `statement_upload_to_uuid` above the model.
- **RecursionError persists** even with all admin, forms, and template tag references to `StatementFile` commented out.

### 4. Template Tag & Navigation
- Commented out `"StatementFile"` from the custom admin navigation in `admin_filters.py`: no effect.

### 5. Environment & Django Version
- Created a clean virtual environment and a minimal Django project: admin works fine.
- The problem is isolated to the main project and specifically to the presence of the `StatementFile` model.

### 6. Error Trace
- The RecursionError is triggered deep in Django's template rendering, specifically in the i18n template tag, but only when the `StatementFile` model exists.

### 7. Full Database Reset & Table Drops (2025-06-27)
- Backed up the database.
- Created a new, empty database (`ledgerflow_fresh`).
- Updated all settings and `.env.dev` to point to the new DB.
- Dropped all tables, views, and sequences in the public schema using both Python scripts and direct Docker psql commands.
- Verified via direct SQL that the problematic table (`profiles_transactionclassification`) was gone.
- Ran `python manage.py migrate`—migrations completed successfully.
- Created a new superuser.
- **Result:** RecursionError still occurs on `/admin/` with a completely fresh DB and new user.

---

## What Was Ruled Out
- Not caused by admin, forms, or template tag code.
- Not caused by migrations or database schema.
- Not present in a minimal Django project.
- Not caused by a specific field in `StatementFile` (error occurs even when empty).
- Not caused by navigation template or custom admin sidebar.
- Not caused by environment or Python version.
- Not caused by database state, content types, or permissions (all reset).

---

## Current Theory (2025-06-27)
- The error is **not** due to database state or data corruption—this has been definitively ruled out by a full DB reset and fresh migrations.
- The issue is **code-level**: specifically, a recursion in Django's admin context generation caused by the bidirectional relationship between `UploadedFile` (formerly `StatementFile`) and `Transaction`.
  - `UploadedFile.transactions` is a `

## 2025-06-27 Update: Clean venv test

- Created a clean Django test project and venv: **No RecursionError** in admin.
- Rebuilt LedgerFlow_AI venv from scratch: **RecursionError persists** in admin.
- Confirms error is NOT system Python, global Django, or OS.
- Error is NOT just the venv; it is project-specific.

### Next Steps (to be scripted):
- Move/disable all custom templates (especially admin/ and base.html).
- Comment out all non-Django apps in INSTALLED_APPS.
- Test admin after each step.
- Document each isolation attempt in this file and Task Master.

## 2025-06-27 Update: Template/Tag Isolation Exhausted

- RecursionError persists after all template and templatetag isolation steps.
- No recursive extends, includes, or custom tags in use.
- Issue may be related to a previous attempt to replace the standard Django admin side navigation with a custom nav (possibly causing recursion in the admin context).
- Considering a full Mac reboot, but next step is to search for any custom admin navigation or context processors that could affect the admin templates.