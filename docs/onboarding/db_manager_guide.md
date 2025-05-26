# Database Manager Onboarding Guide

Welcome to the LedgerFlow team as the Database Manager! This guide will help you understand your role, responsibilities, and the tools you'll need to be effective.

## Your Role

As the Database Manager for LedgerFlow, you are responsible for:

1. Maintaining and optimizing database structure and performance
2. Managing database migrations
3. Ensuring data integrity and security
4. Implementing and maintaining backup and restore procedures
5. Monitoring database health and performance
6. Collaborating with developers on data-related features

## Essential Information

### Database Architecture

LedgerFlow uses PostgreSQL as its primary database with the following configuration:

- **Development**: PostgreSQL 15 in Docker
- **Production**: PostgreSQL 15 in Docker with volume persistence
- **Access**: Adminer for GUI access (development only)
- **Backups**: Regular dumps with verification
- **Migration Management**: Django ORM migration system

### Critical Safety Protocols

**EXTREMELY IMPORTANT**: Our project has implemented strict safety protocols to prevent data loss:

1. **Volume Protection**:
   - Database volumes are protected from accidental deletion
   - **NEVER** run raw `docker compose down -v` commands
   - Always use `make` commands or the safety wrapper (`ledger_docker`)

2. **Backup System**:
   - Backups are stored in `~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups`
   - Backups must be verified >10KB in size
   - Automatic verification is performed

3. **Restore Testing**:
   - Always test restores in a temporary database before applying to main DB
   - Use `make restore-test FILE=path/to/backup.dump`

## Required Access

You'll need access to:

- [ ] GitHub repository
- [ ] Discord/Matrix channels
- [ ] Database credentials in `.env.dev` and `.env.prod`
- [ ] Cloud storage access (for accessing backups)
- [ ] SSH access to production servers (if applicable)

## Technical Setup

### Local Environment Setup

1. Follow the general setup in the main onboarding guide
2. Install the safety wrapper (CRITICAL):
```bash
mkdir -p ~/bin
curl -s https://raw.githubusercontent.com/LedgerFlow/LedgerFlow/main/scripts/ledger_docker -o ~/bin/ledger_docker && chmod +x ~/bin/ledger_docker

# Add to your shell configuration
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
echo 'docker() { ledger_docker "$@"; }' >> ~/.zshrc
source ~/.zshrc
```

3. Additional database tools (recommended):
   - pgAdmin or DBeaver for GUI management
   - psql CLI for direct access
   - pg_dump and pg_restore for manual operations

### Database Access

#### Development Environment

- **Host**: localhost
- **Port**: 5432 (internal Docker network)
- **Database**: ledgerflow
- **Username**: ledgerflow
- **Password**: From `.env.dev` file
- **Adminer URL**: http://localhost:8082

#### Production Environment

Access details will be provided separately through secure channels.

## Key Workflows

### Database Backup

```bash
# Create backup
make backup ENV=dev  # for development
make backup ENV=prod  # for production

# Verify backup exists and has proper size
ls -la "~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/dev/"
```

### Database Restore

```bash
# Test restore (always test first)
make restore-test FILE=path/to/backup.dump

# If test is successful, perform actual restore
make restore FILE=path/to/backup.dump
```

### Migration Management

```bash
# Create migrations
docker compose -f docker-compose.dev.yml exec django python manage.py makemigrations

# Apply migrations
docker compose -f docker-compose.dev.yml exec django python manage.py migrate

# Show migration status
docker compose -f docker-compose.dev.yml exec django python manage.py showmigrations
```

### Database Shell Access

```bash
# Django DB shell
docker compose -f docker-compose.dev.yml exec django python manage.py dbshell

# Direct PostgreSQL shell
docker compose -f docker-compose.dev.yml exec postgres psql -U ledgerflow -d ledgerflow
```

## Important Files

- `docker-compose.dev.yml` - Development database configuration
- `docker-compose.prod.yml` - Production database configuration
- `scripts/db/` - Database scripts
- `*/migrations/` - Migration files in Django apps
- `.env.dev` and `.env.prod` - Database credentials
- `Makefile` - Contains database management commands

## Required Credentials

The following credentials are not stored in the repository and must be obtained separately:

- Database credentials (username/password)
- Cloud storage access (for backups)
- Production server access (if applicable)
- Admin dashboard credentials

## Responsibilities Timeline

### Daily
- Monitor database health and performance
- Verify successful backups
- Review logs for any database issues

### Weekly
- Test restore procedures
- Check disk space usage
- Review slow queries and optimize

### Monthly
- Security audit
- Full backup verification
- Review and clean up unused data (if applicable)
- Performance optimization

## First Week Tasks

- [ ] Review the Memory Bank (`cline_docs/`)
- [ ] Set up local development environment
- [ ] Get familiar with the database structure
- [ ] Review existing migrations
- [ ] Test backup and restore procedures
- [ ] Create database documentation

## Contact Information

For access to credentials or with questions about your role, please contact:
- Team Lead: [Name and contact information to be provided separately] 