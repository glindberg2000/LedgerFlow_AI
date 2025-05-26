# Active Context

## Current Focus
- Implementing and improving backup and restore functionality
- Enhancing deployment pipeline
- Setting up development and production environments
- Implementing security measures
- Documenting system architecture and processes
- Creating comprehensive onboarding materials for new team members
- Integrating MPC tools and dockerized development workflow

## Recent Changes

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

### Working Features
1. Basic Django application
2. Docker containerization
3. Database integration
4. Development environment
5. Backup system
6. Dockerized development workflow
7. MPC tools integration

### Active Issues
1. Path handling in backup/restore
2. Environment configuration
3. Deployment automation
4. Security implementation
5. Documentation completion
6. MPC tools configuration optimization

## Next Steps

### Immediate Tasks
1. Onboard new team members (PM, DB Manager, Full Stack Dev, Reviewer)
2. Complete restore functionality
3. Implement CI/CD pipeline
4. Set up monitoring
5. Configure TLS
6. Finalize MPC tools integration

### Short-term Goals
1. Team training on Memory Bank and safety protocols
2. Production deployment
3. Security hardening
4. Performance optimization
5. Documentation updates
6. Dockerized workflow refinement

### Upcoming Features
1. Advanced document processing
2. Workflow automation
3. API development
4. Security enhancements
5. Analytics implementation
6. Expanded MPC tools integration

## Technical Notes

### Environment Setup
- Development using docker-compose.dev.yml
- Production using docker-compose.prod.yml
- Environment variables in .env files
- Separate database instances
- Backup storage configuration
- Dockerized role-specific environments
- MPC tools configured for each role

### Current Configuration
- Python 3.11+
- Django 5.2
- PostgreSQL 15+
- Docker/Docker Compose
- Nginx (pending)
- GitHub integration
- Discord/Matrix integration
- Task Manager integration

### Development Status
- Local development functional
- Dockerized development functional
- Testing environment pending
- Staging environment pending
- Production environment pending
- CI/CD pipeline in progress
- MPC tools integration in progress

## Implementation Details

### Backup System
```python
# Current backup implementation
make backup FILE=path/to/backup.sql
```

### Restore System
```python
# Current restore implementation
make restore FILE=path/to/backup.sql
```

### Deployment Process
```bash
# Development deployment
docker-compose -f docker-compose.dev.yml up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Dockerized Session Start
```bash
# Start role-specific dockerized session
make <role>-session  # e.g., make reviewer-session
```

## Pending Decisions

### Technical Decisions
1. Cloud storage integration
2. Redis implementation
3. TLS configuration
4. Monitoring solution
5. Backup retention policy
6. MPC tools scalability approach

### Architecture Decisions
1. Service scaling strategy
2. Cache implementation
3. Search optimization
4. Security measures
5. Integration patterns
6. Dockerized environment standardization

## Known Limitations

### Current Limitations
1. Local backup storage
2. Manual deployment steps
3. Basic error handling
4. Limited monitoring
5. Incomplete documentation
6. Initial MPC tools configuration

### Technical Debt
1. Path handling improvements
2. Error handling enhancement
3. Configuration management
4. Test coverage
5. Documentation gaps
6. Docker image optimization

## Testing Status

### Implemented Tests
1. Basic unit tests
2. Database connectivity
3. Backup functionality
4. Environment validation
5. Configuration testing
6. Docker environment testing

### Pending Tests
1. Integration tests
2. Performance tests
3. Security tests
4. Load tests
5. End-to-end tests
6. MPC tools integration tests

## Security Considerations

### Implemented Security
1. Basic authentication
2. Environment isolation
3. Database security
4. Docker security
5. Backup encryption
6. Containerized role isolation

### Pending Security
1. TLS implementation
2. Advanced authentication
3. Access control
4. Security monitoring
5. Vulnerability scanning
6. MPC tools security hardening

## Documentation Status

### Completed Documentation
1. Product context
2. System patterns
3. Technical context
4. Project progress
5. Active context
6. Onboarding documentation
7. MPC tools integration guide

### Pending Documentation
1. API documentation
2. Deployment guide
3. Security guide
4. Testing guide
5. User manual
6. Advanced MPC tools configuration

## Resource Allocation

### Current Resources
1. Development environment
2. Local testing
3. Version control
4. Documentation system
5. Backup storage
6. Dockerized environments
7. MPC tools infrastructure

### Required Resources
1. Production servers
2. Monitoring systems
3. CI/CD pipeline
4. Security tools
5. Testing infrastructure
6. Advanced MPC tools

## Timeline

### Current Week
1. Onboard new team members
2. Complete backup/restore
3. Implement CI/CD
4. Configure security
5. Update documentation
6. Finalize MPC tools integration

### Next Week
1. Team training on Memory Bank and safety protocols
2. Production deployment
3. Security hardening
4. Performance testing
5. Documentation review
6. MPC tools optimization

### Month Ahead
1. Feature development
2. System optimization
3. Security auditing
4. Integration testing
5. User acceptance testing
6. Advanced MPC tools implementation

## 2024-04-25 Major Cleanup and Codebase Confirmation

- Moved legacy/duplicate app folders (`app/ledgerflow`, `app/core`, `app/profiles`, `pdf_extractor_web`) to `deprecated/`.
- Deleted SQL dumps, logs, and stray files from project root.
- Moved all shell scripts to `scripts/`.
- Confirmed live dev codebase is `core/` (via docker-compose.dev.yml) and prod is `ledgerflow/` (via docker-compose.prod.yml).
- Restarted all containers (except vsc-ai-coder-bot) and verified site is up and data is available on port 9000.
- No dependency on deprecated folders for live site.

## 2024-05-04 Onboarding Documentation Creation

- Created comprehensive onboarding documentation in `docs/onboarding/`
- Added role-specific guides for Project Manager, Database Manager, Full Stack Developer, and Reviewer
- Created guide explaining the Memory Bank system
- Added documentation about credentials and secrets management
- Prepared for onboarding new team members with Discord/Matrix communication

## 2024-05-10 MPC Tools and Dockerized Development Integration

- Added MPC tools integration (GitHub, Discord, Task Manager, PostgreSQL)
- Implemented dockerized development environments for all team roles
- Updated onboarding documentation to reflect new tools and workflows
- Enhanced security protocols for containerized environments
- Added role-specific environment configurations

## Current State
- Django app can run both outside Docker and inside Docker Compose.
- SearXNG integration is robust: uses SEARXNG_HOST env var in both environments.
- Cloud Postgres DB (Neon) is now the main dev database.

## How to Start the App

### Outside Docker (Local Dev)
1. Ensure Docker containers for SearXNG and Redis are running:
   - `docker compose -f docker-compose.dev.yml up -d searxng redis`
2. In `ledgerflow/.env.dev`, set:
   - `SEARXNG_HOST=http://localhost:8888`
   - `DATABASE_URL=postgres://newuser:neonpassword2024@ep-floral-mode-aaxawm69-pooler.westus3.azure.neon.tech:5432/neondb?sslmode=require`
3. Run:
   - `source venv/bin/activate`
   - `python manage.py runserver`

### Inside Docker Compose
1. In `docker-compose.yml`, Django service sets:
   - `SEARXNG_HOST: http://searxng:8080`
   - `DATABASE_URL` as needed (can use Neon or local Postgres)
2. Start all services:
   - `docker compose -f docker-compose.dev.yml up -d`

## Cloud DB Migration (Neon)
- All devs now use a shared Neon Postgres instance for development.
- Migration steps:
  1. Exported local DB and imported to Neon.
  2. Updated all configs to use Neon connection string.
  3. Granted privileges to dev user.
- Benefits:
  - All devs can connect from anywhere, any environment.
  - DB manager can spin up isolated dev DBs for each dev or feature branch.
  - No need to expose local DBs or manage local Postgres installs.
  - Easy to grant/revoke access and manage DB lifecycle.

## Next Steps
- Document DB access policy for new devs.
- Optionally automate per-dev DB provisioning for feature isolation.

## SearXNG Multi-Environment Configuration
- Always use the SEARXNG_HOST env var in code and config.
- Supported values:
  - Local dev (host): http://localhost:8888
  - Docker Compose: http://searxng:8080
  - Docker container accessing host: http://host.docker.internal:8888
  - Cloud/remote: http://<public-ip>:8888
- See onboarding docs and .env.dev for details and troubleshooting. 