# System Patterns

## System Architecture

### Docker-based Development
- Multi-container setup with Docker Compose
- Separate containers for:
  - Django application
  - PostgreSQL database
  - Redis cache
- Persistent volumes for database data
- Hot-reload for development

### Database Management
- PostgreSQL as primary database
- Regular backup strategy using backup_database.sh
- Restore capability using restore_database.sh
- Migration management through Django

### Development Workflow
1. Environment setup through .env files
2. Docker container orchestration
3. Database migrations
4. Static file collection
5. Superuser creation

### Backup and Restore Pattern
1. Automated backup creation
2. Compressed SQL dumps (.sql.gz)
3. Restore process:
   - Decompress backup
   - Drop existing tables
   - Restore from SQL
   - Apply migrations if needed

### Error Handling
- Database connection retries
- Redis connection fallback
- Static file serving fallback
- Migration conflict resolution

### Security Patterns
- Environment-based configuration
- No hardcoded credentials
- Secure password storage
- Limited port exposure

## Architecture Overview

### System Architecture
- Django-based monolithic application
- Containerized services using Docker
- PostgreSQL for data persistence
- Environment-based configuration

### Design Patterns

#### Application Structure
- Django apps for modular functionality
- Model-View-Template (MVT) pattern
- Class-based views for consistency
- URL routing for RESTful endpoints

#### Data Layer
- Django ORM for database operations
- Migration-based schema management
- Automated backup/restore procedures
- Data validation through Django forms

#### Authentication & Authorization
- Django authentication system
- Role-based access control
- Session management
- Secure password handling

#### File Management
- Media file handling
- Static file serving
- File upload processing
- Backup management

### Development Patterns

#### Code Organization
- Modular Django apps
- Separation of concerns
- DRY (Don't Repeat Yourself)
- SOLID principles

#### Testing
- Unit tests with Django test framework
- Integration testing
- Test fixtures and factories
- Coverage reporting

#### Deployment
- Docker-based deployment
- Environment separation
- Configuration management
- Backup procedures

### Best Practices

#### Code Quality
- PEP 8 compliance
- Documentation standards
- Type hints usage
- Code review process

#### Security
- Environment variables for secrets
- CSRF protection
- XSS prevention
- SQL injection protection

#### Performance
- Database optimization
- Query optimization
- Caching strategies
- Resource management

#### Maintenance
- Regular backups
- Version control
- Documentation updates
- Dependency management

## Key Technical Decisions
1. Port Configuration
   - Internal: 8000 (Django)
   - External: 9000 (Public)
   - Reason: Avoid conflicts with common ports

2. Database Setup
   - PostgreSQL 15
   - Dedicated user/database
   - Health checks enabled
   - Persistent volume storage

3. Development Environment
   - Hot reload enabled
   - Debug mode active
   - Environment variables in .env.dev
   - Direct volume mounting for code changes

## Docker Configuration
1. Development (docker-compose.dev.yml)
   ```yaml
   services:
     django:
       build:
         context: .
         target: dev
       volumes:
         - .:/app
       ports:
         - "9000:8000"
       environment:
         - DEBUG=1
         - DATABASE_URL=postgres://ledgerflow:ledgerflow@postgres:5432/ledgerflow
     postgres:
       image: postgres:15
       environment:
         - POSTGRES_DB=ledgerflow
         - POSTGRES_USER=ledgerflow
         - POSTGRES_PASSWORD=ledgerflow
   ```

2. Production (docker-compose.prod.yml)
   - Similar structure
   - No volume mounts
   - Gunicorn for serving
   - Collected static files

## Database Patterns
1. Migrations
   - Django ORM
   - Version controlled
   - Backup before migrations
   - Migration history preserved

2. Backup/Restore
   - Regular SQL dumps
   - Point-in-time recovery
   - Migration history included
   - Data integrity checks

## Development Workflow
1. Code Changes
   - Edit files locally
   - Auto-reload in container
   - Run migrations as needed
   - Test in development first

2. Database Changes
   - Create migrations
   - Back up current state
   - Apply changes
   - Verify integrity

## Security Patterns
1. Development
   - Debug enabled
   - Local environment only
   - Default credentials
   - All ports accessible

2. Production
   - Debug disabled
   - Secure credentials
   - Limited port exposure
   - HTTPS required

## Tool Architecture
- Tools are modular Python packages in the `tools/` directory
- Each tool package should have a clear `__init__.py` exposing its public interface
- Tool functions are registered in the database with exact module paths
- Tools should be self-contained with their own requirements and documentation

## Database Persistence
- Docker volumes used for persistent storage
- Volumes survive container restarts and rebuilds
- Never use `docker compose down -v` in development
- Regular backups stored in `archives/docker_archive/database_backups/`

## Search Integration
- SearXNG used as primary search engine
- Search tools exposed through standardized interface
- Tool configuration stored in database
- Module paths must point to exact function (e.g., `tools.search_tool.search_web`)

## Development Patterns
- Use Docker Compose for service orchestration
- Maintain persistent database state
- Document all tool interfaces
- Keep module paths up to date in admin
- Regular database backups
- Clear separation of development and production configs

## Backup and Restore Patterns

### Core Backup Strategy
The system implements a multi-tiered backup approach:

1. **Comprehensive Backup** (`backup_dev_full.sh`)
   - Full database dumps with verification
   - Media files and configurations
   - Application state and fixtures
   - Container versions and Git state
   - Compressed with integrity checks

2. **Database-Only Backup** (`backup_dev_db.sh`)
   - Compressed SQL dumps
   - Integrity verification
   - Transaction validation
   - Schema verification
   - Automatic rotation

### Storage Pattern
- Primary Location: `LedgerFlow_Archive/backups/dev/`
- Format Standards:
  - Full backups: `.tar.gz`
  - DB-only: `.sql.gz`
- Naming Convention: `ledgerflow_[type]_backup_YYYYMMDD_HHMMSS.*`

### Safety Patterns
1. Volume Protection
   ```bash
   docker volume create --label com.ledgerflow.protect=true ledger_dev_db_data
   docker volume create --label com.ledgerflow.protect=true ledger_prod_db_data
   ```

2. Command Safety
   - Docker CLI wrapper (`ledger_docker`)
   - Environment locks in `manage.py`
   - Protected volume checks
   - Safe Makefile targets

### Backup Schedule Pattern
- Daily full backups (2 AM)
- Hourly database-only backups
- 7-day retention (full)
- 48-hour retention (hourly)

### Monitoring Pattern
- Size verification (10KB minimum)
- Backup success logging
- Restore test validation
- Transaction count tracking
- Schema validation

### Recovery Pattern
1. Database-Only Recovery:
   ```bash
   ./restore_db_clean.sh backups/dev/[backup_file].sql.gz
   ```

2. Full System Recovery:
   ```bash
   ./scripts/db/restore_full_backup.sh backups/dev/[backup_file].tar.gz
   ```

3. Verification Steps:
   - Transaction count check
   - Media file verification
   - Application functionality test
   - Configuration validation

## Critical Safety Implementation Patterns

### Volume Protection Pattern
1. Protected Volume Creation:
   ```bash
   docker volume create --label com.ledgerflow.protect=true ledger_dev_db_data
   docker volume create --label com.ledgerflow.protect=true ledger_prod_db_data
   ```
2. Protection Verification:
   - Label persistence checks
   - Deletion attempt prevention
   - Recreation procedure validation

### Command Safety Pattern
1. Docker CLI Wrapper (`ledger_docker`):
   - Production environment detection
   - Protected volume verification
   - Command restriction enforcement
   - Makefile integration for safety

2. Environment Lock Pattern:
   - Production command restrictions in `manage.py`
   - Migration safeguards
   - Environment validation checks
   - Safe command execution paths

### Backup Safety Pattern
1. Verification Layers:
   - Size verification (10KB minimum)
   - Integrity checking
   - Transaction count validation
   - Schema structure verification

2. Automated Schedule:
   - Hourly database backups
   - Daily full system backups
   - 7-day retention policy
   - Integrity monitoring

### CI/CD Safety Integration
1. Automated Testing:
   - Restore-smoke tests
   - Backup verification jobs
   - Environment isolation tests
   - Safety measure validation

2. Pipeline Safeguards:
   - Pre-deployment checks
   - Volume protection verification
   - Backup integrity validation
   - Environment separation tests

### Emergency Response Pattern
1. Immediate Actions:
   ```bash
   # Stop all services safely
   ledger_docker compose down
   
   # Verify volume protection
   docker volume ls --filter label=com.ledgerflow.protect=true
   
   # Initiate emergency backup
   ./backup_dev_full.sh --emergency
   ```

2. Recovery Steps:
   - Validate backup integrity
   - Verify environment isolation
   - Test restore in safe environment
   - Verify data consistency

### Monitoring and Verification Pattern
1. Continuous Monitoring:
   - Backup size tracking
   - Volume protection status
   - Environment state validation
   - Command execution logging

2. Regular Verification:
   - Daily backup tests
   - Weekly restore tests
   - Monthly security audits
   - Quarterly recovery drills

## Standardized Container Configuration

### Development Environment
```yaml
services:
  django:
    image: ledgerflow-django
    ports:
      - "9001:8000"  # Development port
    
  postgres:
    image: postgres:17.4
    ports:
      - "5432:5432"  # Internal only, use adminer
    healthcheck:
      enabled: true
    
  redis:
    image: redis:7.2
    ports:
      - "6379:6379"  # Internal only
    
  adminer:
    image: adminer
    ports:
      - "8082:8080"  # Database management
    
  searxng:
    image: searxng/searxng:latest
    ports:
      - "127.0.0.1:8080:8080"  # Local only
    
  caddy:
    image: caddy:2-alpine
    # No direct port mapping, handles proxying
```

### Production Environment
Identical configuration except:
- No adminer service
- Different port mappings
- Additional security measures
- No exposed development ports 