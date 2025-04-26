# Technical Context

## Technology Stack

### Core Technologies
- Python 3.12.10
- Django 5.2
- PostgreSQL 17.4
- Docker & Docker Compose

### Development Environment
- Docker containers for service isolation
- Development-specific environment variables
- Hot-reload enabled for development
- Debug mode enabled

### Production Environment
- Containerized deployment
- Production-grade PostgreSQL configuration
- Secure environment variable management
- Debug mode disabled

## Development Setup

### Prerequisites
- Docker Desktop
- Python 3.12+
- Git

### Environment Files
- `.env.example` - Template for environment variables
- `.env.dev` - Development environment configuration
- `.env.prod` - Production environment configuration

### Docker Configuration
- `docker-compose.yml` - Base configuration
- `docker-compose.dev.yml` - Development overrides
- `docker-compose.prod.yml` - Production overrides

### Database
- PostgreSQL 17.4
- Persistent volume: ledgerflow_postgres_data_dev
- Automated backup/restore scripts
- Migration management

## Technical Constraints

### Performance
- Database query optimization
- Caching strategies
- Asset compression
- Load balancing considerations

### Security
- HTTPS enforcement
- Secure password storage
- Role-based access control
- Regular security updates

### Scalability
- Horizontal scaling capability
- Database connection pooling
- Static file serving
- Cache management

## Development Workflow

### Version Control
- Git for source control
- Feature branch workflow
- Pull request reviews
- Version tagging

### Testing
- Unit tests
- Integration tests
- End-to-end testing
- Test coverage monitoring

### Deployment
- Automated deployment pipeline
- Environment-specific configurations
- Rollback capabilities
- Health monitoring

### Maintenance
- Regular dependency updates
- Security patch management
- Database maintenance
- Backup verification

## Documentation

### Code
- Docstrings
- Type hints
- README files
- API documentation

### System
- Architecture diagrams
- Setup guides
- Troubleshooting guides
- API references

### Operations
- Deployment procedures
- Backup/restore procedures
- Monitoring setup
- Incident response

## Tools & Utilities

### Development
- VS Code (recommended IDE)
- Docker Desktop
- Git client
- Database management tools

### Testing
- Django test framework
- Coverage.py
- pytest
- Selenium (if needed)

### Monitoring
- Django Debug Toolbar
- Log management
- Performance monitoring
- Error tracking

### Backup
- Automated backup scripts
- Restore procedures
- Backup verification
- Retention policies

## Tool Configuration
- Tools are configured in the database through the Django admin interface
- Module paths must point to the exact function to be called (e.g., `tools.search_tool.search_web`)
- Tool functions must be properly exposed through their module's `__init__.py`

## Database Management
- PostgreSQL 17.4 with persistent storage using Docker volumes
- Volume name: `ledgerflow_postgres_data_dev`
- IMPORTANT: Never use `docker compose down -v` in development as it wipes the database
- Use regular `docker compose down` to preserve data
- Backup and restore scripts available in project root

### Restore Procedures

The project uses a clean database restore script (`restore_db_clean.sh`) that handles full database restores from compressed backups. The procedure:

1. Accepts a gzipped SQL backup file (typically stored in `LedgerFlow_Archive/backups/dev/`)
2. Drops all existing tables in the target database
3. Recreates the public schema
4. Restores the database from the compressed backup

#### Verified Restore Test Results (2025-04-22)

A full restore test was performed with the following results:
- Total transactions restored: 1,666
- Date range: December 2024 - April 2025
- Data quality checks:
  - Transaction amounts properly formatted (with cents)
  - Descriptions intact
  - Categories preserved where assigned
  - Source information maintained (e.g. 'wellsfargo_bank_csv')
  - All related foreign keys and constraints preserved

#### Restore Command Reference

```bash
# Standard restore procedure
./restore_db_clean.sh

# Manual restore steps (if needed)
docker compose -f docker-compose.dev.yml exec -T postgres psql -U newuser mydatabase -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c [backup_file].sql.gz | docker compose -f docker-compose.dev.yml exec -T postgres psql -U newuser mydatabase
```

## Development Environment
- Docker & Docker Compose for service orchestration
- Django 5.2 with Python 3.12.10
- Development server runs on port 9001
- Adminer available on port 8082 for database management
- Redis for caching and session management

## Configuration Files
- `.env.dev` for development environment variables
- `docker-compose.dev.yml` for development services
- `docker-compose.prod.yml` for production setup
- `Dockerfile` with multi-stage builds

## Service Dependencies
- PostgreSQL 17.4
- Redis 7.2-alpine
- Adminer for database management
- SearXNG for web search functionality

## Development Workflow
1. Start services: `docker compose -f docker-compose.dev.yml up -d`
2. Apply migrations: `docker compose -f docker-compose.dev.yml exec django python manage.py migrate`
3. Create superuser if needed: `docker compose -f docker-compose.dev.yml exec django python manage.py createsuperuser`
4. Stop services: `docker compose -f docker-compose.dev.yml down` (without -v to preserve data)

## Backup and Restore
- Backup scripts available in project root
- Restore using `restore_db_force_v2.sh` with backup file path
- Backups stored in `archives/docker_archive/database_backups/`