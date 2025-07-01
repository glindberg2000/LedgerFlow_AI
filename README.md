# LedgerFlow

LedgerFlow is a Django-based application designed to handle financial document processing and data extraction. It provides automated extraction of financial data from PDF documents, structured storage and categorization of financial transactions, and integration with accounting systems.

## Features

- PDF document upload and processing
- Automated data extraction
- Transaction categorization
- Business profile management
- Data validation and verification
- Modern web-based interface

## Prerequisites

- Docker Desktop
- Make (optional, for using Makefile commands)

## Development Setup

1. Clone the repository:
```bash
   git clone https://github.com/yourusername/ledgerflow.git
   cd ledgerflow
```

2. Create environment files:
   ```bash
   cp .env.dev.template .env.dev
   ```
   Edit `.env.dev` with your development settings.

3. Build and start the development environment:
```bash
   make dev-build
   make dev-up
```

4. Run migrations:
```bash
   make migrate
```

5. Create a superuser:
```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml exec django python manage.py createsuperuser
   ```

The application will be available at:
- Main application: http://localhost:9001
- Adminer (database management): http://localhost:8082

## Backup, Restore, and Migration Process (2025-06-09)

- The working development database is now `ledgerflow_test_restore` (see cline_docs/activeContext.md for context).
- All backup scripts (`scripts/db/backup_dev_db.sh` and `scripts/db/backup_dev_full.sh`) are updated to use this database.
- To back up the database, run:
  ```bash
  bash scripts/db/backup_dev_db.sh
  # or for a full backup (DB, media, config):
  bash scripts/db/backup_dev_full.sh
  ```
- Backups are stored in iCloud and automatically synced.
- To restore, create a new database, gunzip and psql the backup, then run Django migrations if needed.
- No secret files (like `.env*`) are committed to version control; these are backed up separately.
- For full details and the latest process, see `cline_docs/activeContext.md`.

## Development Commands

- `make help` - Show available commands
- `make dev-up` - Start development environment
- `make dev-down` - Stop development environment
- `make migrate` - Run database migrations
- `make migrations` - Create database migrations
- `make shell` - Open Django shell
- `make test` - Run tests
- `make lint` - Run linters
- `make format` - Format code
- `make clean` - Remove Python artifacts

## Production Deployment

1. Create and configure production environment file:
   ```bash
   cp .env.dev.template .env.prod
   ```
   Edit `.env.prod` with your production settings.

2. Build and start the production environment:
```bash
   make prod-build
   make prod-up
   ```

3. Run migrations:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec django python manage.py migrate
```

## Project Structure

```
ledgerflow/
├── app/                    # Django application
│   ├── core/              # Core functionality
│   ├── documents/         # Document processing
│   ├── profiles/          # Business profiles
│   └── ledgerflow/        # Project settings
├── requirements/          # Python dependencies
│   ├── base.txt          # Base requirements
│   └── dev.txt           # Development requirements
├── static/               # Static files
├── media/                # User-uploaded files
├── docker-compose.yml    # Base Docker configuration
├── docker-compose.dev.yml # Development configuration
├── docker-compose.prod.yml # Production configuration
└── Dockerfile           # Docker build instructions
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Demo Bootstrap & Quickstart

LedgerFlow provides a fully automated demo environment for onboarding, testing, and development. All demo data and config files are in `profiles/bootstrap/`.

**To bootstrap the demo environment:**

- **Quickstart (recommended for local/dev):**
  ```bash
  python manage.py bootstrap_demo --quickstart
  ```
  - Uses a new SQLite DB (`demo_bootstrap.sqlite3`), runs all migrations, and loads demo data with no prompts.

- **Force wipe and reload demo data:**
  ```bash
  python manage.py bootstrap_demo --force
  ```
  - Wipes all data in the current DB (asks for DB name confirmation), then loads demo data.

- **Other options:**
  - `--sqlite`: Always use a new SQLite DB for demo, regardless of settings.
  - `--dry-run`: Show what would be done, but make no changes.
  - `--i-understand-danger`: (DANGEROUS) Allow destructive actions on non-SQLite DBs.

**Demo superuser credentials:**
- Username: `demo`
- Password: `demo1234`
- **Change this password immediately in any real deployment!**

**Required files in `profiles/bootstrap/`:**
- `business_profile.json`
- `worksheets.json`
- `categories_6A.json`
- `business_expense_categories.json`
- `agents.json`
- `field_mapping.json`
- `sample_transactions.csv.example`
- `tax_checklist_index.json`

**What the bootstrap command does:**
- Loads all demo config/data from `profiles/bootstrap/`
- Creates demo objects: business profile, worksheets, categories, agents, and demo transactions
- Creates a demo superuser (`demo`/`demo1234`)
- Prints a summary of what was created

**Typical usage patterns:**

| Flag                   | What it does                                                                                      |
|------------------------|---------------------------------------------------------------------------------------------------|
| `--force`              | Wipes all data and reloads demo config. Requires DB name confirmation unless used with `--quickstart`. |
| `--quickstart`/`--yes` | Zero-friction: skips all prompts, uses defaults, and auto-creates a new SQLite DB if needed.      |
| `--sqlite`             | Forces use of a new SQLite DB for demo onboarding, regardless of current settings.                |
| `--dry-run`            | Shows what would be done, but makes no changes.                                                   |
| `--i-understand-danger`| (DANGEROUS) Allows destructive actions on non-SQLite DBs. Use only if you are 100% sure.          |

After bootstrapping, you can log in and explore the app with realistic demo data. For more details, see the code in `profiles/management/commands/bootstrap_demo.py`.
