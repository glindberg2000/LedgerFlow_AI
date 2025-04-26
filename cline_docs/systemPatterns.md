# System Patterns

## Architecture Overview

### System Architecture
1. **Core Components**
   - Django web framework
   - PostgreSQL database
   - Docker containerization
   - Nginx web server
   - Redis cache

2. **Service Layout**
   - Microservices architecture
   - Containerized services
   - RESTful APIs
   - Message queues
   - Cache layers

### Design Patterns

1. **Application Patterns**
   - MVC architecture
   - Repository pattern
   - Factory pattern
   - Observer pattern
   - Strategy pattern

2. **Database Patterns**
   - Migration-based schema
   - Connection pooling
   - Query optimization
   - Indexing strategy
   - Backup management

## Code Organization

### Project Structure
```
ledgerflow/
├── app/
│   ├── core/          # Core functionality
│   ├── documents/     # Document handling
│   ├── profiles/      # User profiles
│   └── ledgerflow/    # Main app
├── config/            # Configuration
├── docker/           # Docker setup
├── docs/             # Documentation
└── tests/            # Test suite
```

### Module Responsibilities

1. **Core Module**
   - Base classes
   - Shared utilities
   - System configuration
   - Common middleware
   - Error handling

2. **Documents Module**
   - Document processing
   - File management
   - Version control
   - Search indexing
   - Format handling

3. **Profiles Module**
   - User management
   - Authentication
   - Authorization
   - Profile data
   - Preferences

## Technical Decisions

### Framework Choice
1. **Django Framework**
   - Robust ORM
   - Admin interface
   - Security features
   - Scalability
   - Community support

2. **PostgreSQL Database**
   - ACID compliance
   - JSON support
   - Full-text search
   - Performance
   - Reliability

### Infrastructure

1. **Docker Implementation**
   - Container isolation
   - Environment consistency
   - Easy deployment
   - Scalability
   - Resource management

2. **Nginx Configuration**
   - Load balancing
   - SSL termination
   - Static file serving
   - Request routing
   - Security features

## Development Patterns

### Code Standards

1. **Python Standards**
   - PEP 8 compliance
   - Type hints
   - Docstring format
   - Import organization
   - Error handling

2. **Django Standards**
   - App organization
   - Model design
   - View patterns
   - URL structure
   - Template hierarchy

### Testing Strategy

1. **Test Types**
   - Unit tests
   - Integration tests
   - System tests
   - Performance tests
   - Security tests

2. **Test Implementation**
   - pytest framework
   - Factory Boy
   - Mock objects
   - Fixtures
   - Coverage tracking

## Security Patterns

### Authentication

1. **User Authentication**
   - Token-based auth
   - Session management
   - Password policies
   - 2FA support
   - OAuth integration

2. **API Security**
   - JWT tokens
   - Rate limiting
   - IP filtering
   - CORS policies
   - Request validation

### Data Protection

1. **Encryption**
   - Data at rest
   - Data in transit
   - Key management
   - Secure storage
   - Backup encryption

2. **Access Control**
   - Role-based access
   - Permission system
   - Resource isolation
   - Audit logging
   - Security headers

## Performance Patterns

### Optimization

1. **Database Optimization**
   - Query optimization
   - Index management
   - Connection pooling
   - Cache strategy
   - Batch processing

2. **Application Optimization**
   - Code profiling
   - Memory management
   - Resource caching
   - Async processing
   - Load balancing

### Scaling Strategy

1. **Horizontal Scaling**
   - Service replication
   - Load distribution
   - Session management
   - Data consistency
   - Cache synchronization

2. **Vertical Scaling**
   - Resource allocation
   - Performance tuning
   - Capacity planning
   - Monitoring
   - Optimization

## Error Handling

### Error Patterns

1. **Application Errors**
   - Exception hierarchy
   - Error logging
   - User feedback
   - Recovery procedures
   - Debugging support

2. **System Errors**
   - Failover handling
   - Service recovery
   - Data consistency
   - Backup restoration
   - System monitoring

### Logging Strategy

1. **Log Management**
   - Log levels
   - Log rotation
   - Log aggregation
   - Search capability
   - Retention policy

2. **Monitoring**
   - Performance metrics
   - Error tracking
   - Resource usage
   - User activity
   - System health

## Deployment Patterns

### Deployment Strategy

1. **Environment Management**
   - Development
   - Staging
   - Production
   - Testing
   - Disaster recovery

2. **Release Process**
   - Version control
   - CI/CD pipeline
   - Testing phases
   - Deployment automation
   - Rollback procedures

### Configuration Management

1. **Environment Config**
   - Environment variables
   - Config files
   - Secrets management
   - Feature flags
   - App settings

2. **Infrastructure Config**
   - Docker compose
   - Network setup
   - Service discovery
   - Resource limits
   - Monitoring setup

## Maintenance Patterns

### Update Strategy

1. **System Updates**
   - Package updates
   - Security patches
   - Feature releases
   - Hot fixes
   - Version control

2. **Database Updates**
   - Schema migrations
   - Data migrations
   - Backup strategy
   - Recovery testing
   - Performance tuning

### Backup Strategy

1. **Backup Management**
   - Regular backups
   - Incremental backups
   - Verification
   - Retention policy
   - Recovery testing

2. **Recovery Procedures**
   - Disaster recovery
   - Data restoration
   - System recovery
   - Service restoration
   - Validation checks

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

## Deployment Safety Patterns

### Golden Rules
1. **Never** run raw `docker` commands – always use `make` (which calls `ledger_docker`)
2. **Backups verified >10 KB** before any destructive step
3. Prod volumes live on local SSD; backups live in iCloud

### Safety Implementation
1. Docker Guard
   - All docker commands routed through safety wrapper
   - Prevents accidental volume deletion
   - Enforces backup verification
   - Checks environment safety

2. Volume Protection
   - All volumes marked as external
   - Proper naming scheme implemented
   - Deletion prevention via labels
   - Automatic recreation procedures

3. Backup System
   - iCloud integration at ~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups
   - Environment-specific directories (dev/prod)
   - Size verification (>10KB)
   - Sync verification before operations

4. Environment Safety
   - Service-specific configurations
   - No hardcoded credentials
   - Environment variable management
   - Proper restart policies

### Deployment Checklist
1. Pre-flight Checks
   - Docker guard installation
   - Make targets verification
   - Environment setup

2. Safety Checks
   - Backup presence and size
   - iCloud sync status
   - Volume protection labels
   - Environment isolation

3. Deployment Steps
   - Backup verification
   - Blue-green deployment
   - Migration safety
   - Health monitoring

4. Rollback Procedures
   - Quick code rollback
   - Data restoration
   - Service recovery

### Absolute "Do-Not" List
1. Never use `docker compose down -v`
2. Never point live Postgres volume at iCloud
3. Never push to `main` without passing tests & backup checks
4. Never edit `.env.prod` directly on server 