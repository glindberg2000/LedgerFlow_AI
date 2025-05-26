# LedgerFlow Product Context

## Product Overview
LedgerFlow is a modern, modular platform for automated document processing, financial data extraction, and workflow management. It is designed to streamline the ingestion, classification, and analysis of financial documents (such as bank statements, invoices, and receipts) for businesses, accountants, and financial professionals.

## Why This Project Exists
- Manual processing of financial documents is time-consuming, error-prone, and costly.
- Businesses and accountants need a secure, automated way to extract, classify, and analyze financial data from a variety of document sources.
- LedgerFlow provides a unified, extensible system to automate these workflows, reduce human error, and accelerate financial operations.

## Problems Solved
- Automated extraction of structured data from unstructured documents (PDFs, images, etc.).
- Classification and normalization of financial transactions.
- Secure backup and restore of sensitive financial data.
- Workflow automation for document review, approval, and reporting.
- Integration with external services (e.g., SearxNG for search, Redis for caching, Postgres for data storage).

## How It Works
1. **Document Ingestion:** Users upload or sync financial documents.
2. **Data Extraction:** The system uses OCR and parsing tools to extract structured data.
3. **Classification:** Transactions and entities are classified using rules and ML models.
4. **Workflow Automation:** Tasks such as review, approval, and reporting are managed via a workflow engine.
5. **Backup & Restore:** Automated, secure backups to iCloud or other storage, with easy restore options.
6. **APIs & Integrations:** Extensible APIs for integration with other business tools.

## Tech Stack
- **Backend:** Python 3.11+, Django 5.2
- **Database:** PostgreSQL 15+
- **Containerization:** Docker, Docker Compose
- **Search:** SearxNG (optional, for federated search)
- **Cache/Queue:** Redis
- **Web Server:** Gunicorn (prod), Django dev server (dev)
- **Backup Storage:** iCloud (via local sync), with support for other cloud storage planned
- **Other:** Nginx (planned), Pre-commit hooks, CI/CD (planned)

## Main Services & Components
- **Django Apps:**
  - `core/` (main dev app)
  - `ledgerflow/` (main prod app)
  - `profiles/` (user and business profile management)
  - `experimental_admin/`, `simple_classifications/`, etc. (modular, extensible)
- **Scripts:**
  - Automated backup/restore, migration, and deployment scripts in `scripts/`
- **Docker Services:**
  - `django` (web app)
  - `postgres` (database)
  - `redis` (cache/queue)
  - `adminer` (DB admin UI)
  - `searxng` (optional search)
- **Memory Bank:**
  - `cline_docs/` contains all critical product, system, and technical documentation for continuity and onboarding.

## Security & Compliance
- Environment isolation (dev/prod)
- Encrypted backups
- Role-based access (planned)
- Audit logging (planned)

## Future Directions
- Advanced analytics and reporting
- More integrations (QuickBooks, Xero, etc.)
- Enhanced workflow automation
- Improved security and compliance features

## Cloud Database (Neon) for Distributed Development
- The project now uses a Neon Postgres cloud database for all development work.
- This enables all developers to connect from any location and environment (local, Docker, CI, etc.).
- The DB manager can easily spin up isolated dev databases for each developer or feature branch, improving safety and parallel development.
- No need for local Postgres installs or exposing local DBs.
- Access can be granted/revoked as needed, and DBs can be managed centrally.

---

*For more details, see the Memory Bank files in `cline_docs/`.* 