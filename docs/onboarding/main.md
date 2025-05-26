# LedgerFlow Onboarding Guide

Welcome to the LedgerFlow team! This guide will help you get started with our project and understand how we work together. 

## Table of Contents

1. [Project Overview](#project-overview)
2. [Onboarding Checklist](#onboarding-checklist)
3. [Development Environment Setup](#development-environment-setup)
4. [Credentials & Access](#credentials--access)
5. [Communication](#communication)
6. [Team Structure](#team-structure)
7. [Development Workflow](#development-workflow)
8. [Documentation](#documentation)
9. [Important Safety Notes](#important-safety-notes)
10. [Role-Specific Guides](#role-specific-guides)

## Project Overview

LedgerFlow is a modern, modular platform for automated document processing, financial data extraction, and workflow management. It streamlines the ingestion, classification, and analysis of financial documents (such as bank statements, invoices, and receipts) for businesses, accountants, and financial professionals.

**Key features:**
- Automated extraction of structured data from unstructured documents
- Classification and normalization of financial transactions
- Secure backup and restore of sensitive financial data
- Workflow automation for document review, approval, and reporting
- Integration with external services

## Onboarding Checklist

### All Team Members
- [ ] Review this onboarding guide
- [ ] Access granted to GitHub repository
- [ ] Access granted to communication channels (Discord/Matrix)
- [ ] Review Memory Bank (cline_docs/)
- [ ] Meet the team

### Additional for Technical Roles
- [ ] Local development environment setup
- [ ] Database access configured
- [ ] Access to necessary credentials/secrets
- [ ] Understanding of safety procedures
- [ ] Review role-specific documentation

## Development Environment Setup

### Prerequisites
- Docker Desktop
- Git
- Python 3.11+ (for local development outside Docker)
- Make (optional, for using Makefile commands)

### Setup Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ledgerflow.git
cd ledgerflow
```

2. Install the safety wrapper (CRITICAL):
```bash
mkdir -p ~/bin
curl -s https://raw.githubusercontent.com/LedgerFlow/LedgerFlow/main/scripts/ledger_docker -o ~/bin/ledger_docker && chmod +x ~/bin/ledger_docker

# Add to your shell configuration
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
echo 'docker() { ledger_docker "$@"; }' >> ~/.zshrc
source ~/.zshrc

# Verify installation
docker compose down -v  # Should show 🚫 message
```

3. Create environment files:
```bash
cp .env.example .env.dev
# Edit .env.dev with your development settings (get from team lead)
```

4. Start the development environment:
```bash
make dev
```

5. Run migrations (if needed):
```bash
make migrate
```

The application will be available at:
- Main application: http://localhost:9001
- Adminer (database management): http://localhost:8082

## Credentials & Access

**IMPORTANT: Credentials should NEVER be committed to the repository.**

You will need the following credentials that are not stored in the repository:

- GitHub repository access
- Database credentials (in .env.dev)
- Django admin credentials
- Discord/Matrix access
- Cloud storage credentials (if applicable)

Contact your team lead to obtain these credentials securely.

## Communication

We use Discord/Matrix for team communication. You'll receive an invitation to join the appropriate channels.

Key channels:
- #general - General discussion
- #technical - Technical discussion
- #standup - Daily updates
- #help - Questions and assistance
- #alerts - Automated system alerts

## Team Structure

Our team consists of:
- Project Manager (PM)
- Database Manager
- Full Stack Developer
- Reviewer

Each role has specific responsibilities and works together to deliver the project. See the role-specific guides for more details.

## Development Workflow

1. Work is organized in GitHub issues
2. Create a feature branch for each issue
3. Make changes and commit with descriptive messages
4. Submit a pull request for review
5. Address review feedback
6. Once approved, changes will be merged

### Key Commands

- `make help` - Show available commands
- `make dev` - Start development environment
- `make backup` - Create a database backup
- `make restore FILE=x` - Restore database from backup
- `make check-volumes` - Verify volume protection

## Documentation

Documentation is critical to our project. Key documentation sources:

- **Memory Bank**: `cline_docs/` directory contains critical documentation
- **README.md**: Project overview and basic setup
- **docs/**: Detailed guides and documentation
- **Code docstrings**: In-code documentation

## Important Safety Notes

### Volume Protection

We have implemented safety measures to protect database volumes from accidental deletion:

- **NEVER** run raw `docker` commands – always use `make` (which calls `ledger_docker`)
- **ALWAYS** verify backups (>10 KB) before any destructive step
- Prod volumes live on local SSD; backups live in iCloud

### Backup System

- Backups are stored in `~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups`
- Use `make backup` to create backups
- Use `make restore FILE=path/to/backup.dump` to restore
- Use `make restore-test FILE=path/to/backup.dump` to test a restore

## Role-Specific Guides

Please refer to your role-specific guide for detailed information:

- [Project Manager Guide](pm_guide.md)
- [Database Manager Guide](db_manager_guide.md)
- [Full Stack Developer Guide](full_stack_dev_guide.md)
- [Reviewer Guide](reviewer_guide.md) 