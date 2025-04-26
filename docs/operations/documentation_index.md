# LedgerFlow Documentation Index

## Core System Documentation (Memory Bank)

### System Architecture and Patterns
- **[cline_docs/systemPatterns.md](../../cline_docs/systemPatterns.md)**
  - System architecture overview
  - Docker configuration patterns
  - Safety implementation patterns
  - Backup and restore patterns
  - Standardized container setup

### Technical Context
- **[cline_docs/techContext.md](../../cline_docs/techContext.md)**
  - Development environment setup
  - Database management procedures
  - Tool configuration
  - Backup and restore procedures
  - Service dependencies

### Security Implementation
- **[cline_docs/security_measures.md](../../cline_docs/security_measures.md)**
  - Volume protection implementation
  - Command safety measures
  - Environment isolation
  - Access controls

## Operational Guides

### Deployment and Setup
- **[docs/operations/dev_deployment_guide.md](./dev_deployment_guide.md)**
  - Initial setup instructions
  - Environment configuration
  - Container deployment
  - Development workflow

### Backup and Recovery
- **[docs/operations/backup_strategy.md](./backup_strategy.md)**
  - Backup procedures
  - Verification steps
  - Recovery processes
  - Monitoring setup

### Safety Implementation
- **[docs/operations/safety_implementation_report.md](./safety_implementation_report.md)**
  - Current implementation status
  - Test results
  - Pending items
  - Recommendations

### Incident Response
- **[docs/incident_20250422_database_wipe.md](../incident_20250422_database_wipe.md)**
  - Incident analysis
  - Resolution steps
  - Preventive measures
  - Lessons learned

## Scripts and Tools

### Database Management
- **[scripts/db/](../../scripts/db/)**
  - `backup_dev_db.sh`: Database-only backup
  - `backup_dev_full.sh`: Full system backup
  - `setup_backup_cron.sh`: Automated backup setup

### Security Setup
- **[scripts/security/](../../scripts/security/)**
  - `setup_security.sh`: Security initialization
  - `create_protected_volumes.sh`: Volume protection
  - `safe_migrate.sh`: Safe migration procedure
  - `ledger_docker`: Safety-enhanced Docker wrapper

## Configuration Templates
- `.env.example`: Environment configuration template
- `docker-compose.yml`: Base Docker configuration
- `docker-compose.dev.yml`: Development setup
- `docker-compose.prod.yml`: Production setup

## Quick Start Guides

### For Developers
1. Clone the repository
2. Copy `.env.example` to `.env.dev`
3. Run `scripts/create_protected_volumes.sh`
4. Use `ledger_docker compose up -d` to start services

### For Operations
1. Review `backup_strategy.md`
2. Set up automated backups using `setup_backup_cron.sh`
3. Configure monitoring as per `techContext.md`
4. Schedule regular restore tests

## Safety Procedures
1. Always use `ledger_docker` instead of direct Docker commands
2. Follow backup verification procedures
3. Test restores in isolated environment
4. Monitor backup integrity and sizes

## Support and Maintenance
- Regular backup verification
- Monthly security audits
- Quarterly recovery drills
- Documentation updates 