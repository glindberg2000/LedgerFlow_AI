# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LedgerFlow is a Django-based financial document processing application that handles PDF document upload, automated data extraction, transaction categorization, and business profile management. The project uses Docker for development and production deployments.

## ⚠️ CRITICAL: Database Safety Protocols

**MANDATORY: Before ANY database operation, ALWAYS run:**
```bash
./scripts/safe_db_operation.sh ledgerflow.sqlite3 "operation-description"
```

**This prevents data loss by:**
- Creating automatic backups in iCloud
- Detecting production vs demo data  
- Requiring explicit confirmation for production databases

**After September 4, 2025 data loss incident**, these safety measures are mandatory:
- ✅ Pre-commit git hook prevents accidental database commits
- ✅ Automated backup system with integrity checks
- ✅ Database health validation before operations
- ✅ Production data detection and warnings

**See SAFETY_PROTOCOLS.md for complete procedures**

## Development Setup and Commands

### Core Docker Commands
```bash
# Build and start development environment
make dev-build
make dev-up

# Stop development environment  
make dev-down

# Database operations
make migrate        # Run database migrations
make migrations     # Create new migrations
```

### Django Commands
```bash
# Access Django shell
make shell

# Create superuser
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec django python manage.py createsuperuser

# Run tests
make test

# Code quality
make lint    # Run linters
make format  # Format code
make clean   # Remove Python artifacts
```

### Custom Management Commands
```bash
# Simple Bootstrap (RECOMMENDED - Safe Database Operations)
python manage.py simple_bootstrap                    # Standard bootstrap with current database
python manage.py simple_bootstrap --fresh             # Create fresh demo data (skips if exists)
python manage.py simple_bootstrap --wipe              # ⚠️ Delete existing database (requires confirmation)
python manage.py simple_bootstrap --new-db=mydb.sqlite3  # Create new database file

# Legacy Bootstrap (use with caution)
python manage.py bootstrap_demo --quickstart

# Individual bootstrap commands (for advanced setup)
python manage.py bootstrap_organizer_forms
python manage.py bootstrap_binder_templates  
python manage.py bootstrap_binder_rows

# Initialize tax checklist data
python manage.py init_tax_checklist

# Import parsers
python manage.py import_parsers

# Check transactions
python manage.py check_transactions
```

## Architecture Overview

### Django Settings Structure
- **Main settings**: `/ledgerflow/settings.py` (the only active settings file)
- **Environment files**: `.env.dev` for development, `.env.prod` for production
- **Database**: PostgreSQL with automatic environment-based configuration

### Core Django Applications
- **`profiles`**: Core business logic, document processing, transaction management
- **`profiles.parsers_utilities`**: PDF parsing and data extraction utilities  
- **`simple_classifications`**: Transaction classification system
- **`reports`**: Reporting and analytics functionality
- **`organizers`**: Document organization and management

### Key Models Architecture
The main models are in `profiles/models.py`:

- **`BusinessProfile`**: Central business entity with auto-generated `client_id`
- **`UploadedFile`**: Handles PDF document uploads with hash-based deduplication
- **`Transaction`**: Financial transactions with AI-powered classification
- **`Agent`**: AI agents for document processing and classification
- **`ClientExpenseCategory`**: Business-specific expense categorization
- **`ProcessingTask`**: Async processing task management

**Important**: There's a known RecursionError issue in Django admin caused by bidirectional relationships between `UploadedFile` and `Transaction` models.

### Database Configuration
- **Development**: Uses `.env.dev` configuration (SQLite: `ledgerflow.sqlite3`)
- **Production**: Uses `.env.prod` configuration  
- **PostgreSQL**: Available but outdated (April 2025 data) - see migration section below
- **Docker service**: PostgreSQL container accessible at localhost:5435

## Development Workflow

### Access Points
- **Main application**: http://localhost:9002 (updated for conflict avoidance)
- **Django admin**: http://localhost:9002/admin
- **Adminer (DB management)**: http://localhost:8082

### Bootstrap and Testing

#### Simple Bootstrap (RECOMMENDED)
The new simple_bootstrap command provides safe, predictable database operations:

```bash
# Standard bootstrap (creates demo data in current active database)
python manage.py simple_bootstrap

# Create fresh demo data (skips if already exists) 
python manage.py simple_bootstrap --fresh

# Create new database file with demo data
python manage.py simple_bootstrap --new-db=my_project.sqlite3
# Updates .env.dev suggestion: DATABASE_URL=sqlite:///my_project.sqlite3

# Wipe existing database and recreate (with safety warnings)
python manage.py simple_bootstrap --wipe
# Shows current data stats, requires confirmation: "DELETE filename"
# Creates automatic backup before deletion
```

**Features**:
- ✅ **Safety-First**: Creates backups before any destructive operations
- ✅ **Clear Confirmations**: Requires explicit confirmation for database deletion
- ✅ **Current Database**: Works with whatever database is currently configured
- ✅ **Valid Credentials**: Creates working demo user (demo/demo1234) and business profile
- ✅ **Production Data Detection**: Shows existing user/business counts before wiping

#### Legacy Bootstrap
```bash
# Quick setup with demo data (works with current active database)
python manage.py bootstrap_demo --quickstart

# Alternative: Create just demo user in current database
python manage.py create_demo_user

# Demo credentials: demo/demo1234
# Admin credentials: admin/admin123
```

### File Processing Pipeline
1. Upload PDFs through web interface or admin
2. Automatic hash-based deduplication
3. AI-powered data extraction using registered parsers
4. Transaction categorization with business-specific rules
5. Manual review and correction workflow

## Bootstrap System and PostgreSQL Migration

### Understanding the Bootstrap System

The LedgerFlow application includes a comprehensive bootstrap system that can populate a database from scratch with demo data and configuration. This system is designed to help with both development onboarding and PostgreSQL migration.

### PostgreSQL Population Strategy

**Current Situation**:
- SQLite database (`ledgerflow.sqlite3`) has current personal/business data (July 2025)
- PostgreSQL database has outdated data (April 2025) and missing several models (TaxYear, BinderItem, Organizers)

**To populate PostgreSQL from scratch in the future**:

1. **Switch to PostgreSQL Configuration**:
```bash
# Update .env.dev to use PostgreSQL (currently commented out)
# DATABASE_URL=postgres://newuser:newpassword@localhost:5435/mydatabase

# Or create fresh database for clean start:
# DATABASE_URL=postgres://newuser:newpassword@localhost:5435/ledgerflow_fresh
```

2. **Run Complete Bootstrap Process**:
```bash
# Apply migrations to create schema
python manage.py migrate

# Bootstrap all components in order:
python manage.py bootstrap_demo --force --i-understand-danger
python manage.py bootstrap_organizer_forms
python manage.py bootstrap_binder_templates
python manage.py bootstrap_binder_rows
python manage.py init_tax_checklist --client_id=acme_corp_demo --tax_year=2024
python manage.py import_parsers
```

### Bootstrap System Components

**Core Bootstrap Script**: `profiles/management/commands/bootstrap_demo.py`

This comprehensive script creates:

1. **Business Profiles**: Creates demo company (ACME Corp) with client_id `acme_corp_demo`
2. **Tax Years**: Creates TaxYear (Binder) objects for current and previous year
3. **IRS Worksheets**: Loads worksheet configurations from `profiles/bootstrap/worksheets.json`
4. **Expense Categories**: 
   - IRS categories from `profiles/bootstrap/categories_6A.json`
   - Business-specific categories from `profiles/bootstrap/business_expense_categories.json`
5. **AI Agents**: Loads 4 AI agents from `profiles/bootstrap/agents.json`:
   - Payee Lookup Agent (GPT-4.1-mini)
   - Classification Agent (o4-mini)
   - Classification Escalation Agent (o4-mini)  
   - Business Profile Generator Agent
6. **Sample Transactions**: Imports sample CSV data with 10 demo transactions
7. **Binder Items**: Creates tax form binder items with fields
8. **Demo User**: Creates superuser with credentials `demo/demo1234`

**Bootstrap Data Files Location**: `profiles/bootstrap/`
- `business_profile.json` - ACME Corp demo profile
- `sample_transactions.csv` - 10 demo transactions ($3,945.67 total expenses)
- `agents.json` - AI agent configurations with detailed prompts
- `worksheets.json`, `categories_6A.json` - IRS tax form configurations
- `business_expense_categories.json` - Business-specific categories
- Various organizer form configurations

**Safety Features**:
- `--quickstart` flag automatically creates SQLite database for safe testing
- `--force` requires confirmation before wiping existing data
- `--i-understand-danger` required for non-SQLite database operations
- Comprehensive validation and error handling

### Bootstrap Flexibility

The bootstrap system is designed to be flexible:

```bash
# Quick demo setup (safe, uses new SQLite)
python manage.py bootstrap_demo --quickstart

# Individual components can be run separately:
python manage.py bootstrap_organizer_forms  # Form 15: Charitable contributions
python manage.py bootstrap_binder_templates # Binder/TaxYear templates  
python manage.py bootstrap_binder_rows     # Individual binder row configurations

# Advanced: Force bootstrap on existing database (DANGEROUS)
python manage.py bootstrap_demo --force --i-understand-danger
```

**Note**: The system includes safeguards to prevent accidental data loss. Never run `--force` on production data without complete backups.

## Database Operations and Backup System

### Backup Commands
```bash
# Backup current database
make backup ENV=dev

# Restore from backup
make restore FILE=path/to/backup ENV=dev  

# Test restore in temporary database
make restore-test FILE=path/to/backup ENV=dev
```

### Backup Location
- **Path**: `/Users/greg/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups`
- **Auto-sync**: iCloud integration for backup storage
- **Format**: PostgreSQL custom format (.dump files)

### Production Deployment
```bash
# First-time production setup
make prod-bootstrap TAG=version

# Access production logs
docker compose -p ledger-prod -f docker-compose.yml -f docker-compose.prod.yml logs
```

## Testing Strategy

### Test Structure
- Unit tests in `profiles/tests.py` and other app test files
- Integration tests in `/tests/` directory
- Custom test utilities for structured output testing

### Running Tests
```bash
make test  # Run all tests
python manage.py test profiles  # Run specific app tests
```

## Common Issues and Solutions

### Django Admin RecursionError
**Issue**: RecursionError when accessing Django admin with `UploadedFile` model
**Cause**: Bidirectional relationship between `UploadedFile.transactions` (M2M) and `Transaction.statement_file` (FK)
**Current Status**: Active debugging task (see .taskmaster/docs/prd.txt)

### Environment Variable Issues
- Ensure `.env.dev` or `.env.prod` files exist and are properly configured
- Check `DATABASE_URL` format in environment files
- Verify Docker container environment variable propagation

### Migration Issues
- Database migrations are in `profiles/migrations/`
- Backup migrations stored in `profiles/migrations_backup/`
- Use `make migrate` for applying migrations

## File Structure Highlights

```
ledgerflow/
├── ledgerflow/           # Django project settings
│   ├── settings.py       # Main settings file (ONLY ONE USED)
│   └── urls.py          # Root URL configuration
├── profiles/            # Core application
│   ├── models.py        # Main business models
│   ├── admin.py         # Django admin configuration
│   ├── agents.py        # AI agent definitions
│   ├── bootstrap/       # Demo data and initialization
│   └── parsers_utilities/  # PDF parsing utilities
├── docker-compose.yml   # Base Docker configuration
├── docker-compose.dev.yml   # Development overrides
├── docker-compose.prod.yml  # Production overrides
└── Makefile            # Development commands
```

## Task Master AI Integration

This project uses Task Master AI for task management. Key commands:
- `task-master next` - Get next available task
- `task-master show <id>` - View task details  
- `task-master set-status --id=<id> --status=done` - Mark task complete

See the existing task files in `.taskmaster/tasks/` for current development tasks.