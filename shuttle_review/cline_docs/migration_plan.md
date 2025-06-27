# LedgerFlow Migration Plan

## Current State
- Working in `/Users/greg/iCloud Drive (Archive)/repos/LedgerFlow`
- Need to migrate from legacy system in `/Users/greg/iCloud Drive (Archive)/repos/PDF-extractor/test_django`
- Have Docker configuration files but need proper Django setup

## Files to Configure
1. Docker Configuration:
   - `docker-compose.dev.yml` - Development environment
   - `docker-compose.prod.yml` - Production environment
   - `Dockerfile` - Multi-stage build for dev/prod
   - `.env.dev` - Development environment variables

2. Django Files to Migrate:
   - `manage.py` from test_django
   - All Django apps from pdf_extractor_web
   - Database migrations
   - URL configurations
   - Settings files

3. Database:
   - SQL backups from `/Users/greg/iCloud Drive (Archive)/repos/PDF-extractor/pdf_extractor_web/backups`
   - Migration history
   - Current schema

## Migration Steps

### 1. Docker Configuration
- Using port 9000 for public access
- Internal Django server on 8000
- PostgreSQL setup with ledgerflow database
- Development environment with debug enabled

### 2. Django Setup
1. Copy core Django files:
   ```bash
   cp /Users/greg/iCloud Drive (Archive)/repos/PDF-extractor/test_django/manage.py .
   cp -r /Users/greg/iCloud Drive (Archive)/repos/PDF-extractor/pdf_extractor_web/* ledgerflow/
   ```

2. Update Django settings:
   - Database configuration
   - Static/media file paths
   - Security settings
   - Debug configuration

### 3. Database Migration
1. Copy latest backup:
   ```bash
   cp /Users/greg/iCloud Drive (Archive)/repos/PDF-extractor/pdf_extractor_web/backups/current_backup.sql backups/
   ```

2. Restore process:
   - Start PostgreSQL container
   - Apply schema
   - Import data
   - Verify migrations

## Directory Structure
```
LedgerFlow/
├── app/                 # Application code
├── ledgerflow/         # Django project
├── manage.py           # Django management
├── requirements/       # Python dependencies
├── docker/            # Docker support files
├── static/            # Static files
├── media/             # User uploads
└── backups/           # Database backups
```

## Environment Variables
Development environment needs:
- DEBUG=True
- DATABASE_URL
- SECRET_KEY
- ALLOWED_HOSTS

## Next Steps
1. Copy Django files
2. Update settings
3. Test database restore
4. Verify migrations
5. Start development environment 