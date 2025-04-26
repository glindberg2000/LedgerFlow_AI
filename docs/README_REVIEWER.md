# LedgerFlow Reviewer Guide

## Project Overview
LedgerFlow is a secure financial data processing system with strict safety requirements around database operations and backups.

### Key Safety Rules
1. **NEVER** run raw docker commands - always use `ledger_docker` wrapper
2. **NEVER** commit real `.env` files or secrets
3. **NEVER** write to `~/iCloudLedger` or production volumes

## Directory Structure
```
LedgerFlow/
├── app/                 # Django application code
│   ├── core/           # Core application logic
│   ├── documents/      # Document processing
│   └── profiles/       # User profiles and transactions
├── config/             # Configuration templates
│   └── templates/      # Environment templates
├── docker/             # Docker configuration
├── docs/               # Documentation
│   └── runbooks/       # Operational runbooks
├── scripts/            # Utility scripts
│   └── ledger_docker   # Safety wrapper for docker commands
└── tests/              # Test suite
```

## Running Tests Safely

1. **Environment Setup**
```bash
# Verify safety wrapper is in PATH
which docker  # Should point to ledger_docker

# Copy environment template
cp config/templates/.env.dev.template .env.dev

# Edit .env.dev with development values
```

2. **Safety Checks**
```bash
# Verify volumes and containers
make safety-check ENV=dev

# Start development environment
make dev
```

3. **Running Tests**
```bash
# Run test suite
make test

# Run specific test
make test TEST_PATH=tests/test_specific.py
```

## Review Guidelines

1. **Pre-Review Checklist**
   - [ ] Safety wrapper (`ledger_docker`) is in PATH
   - [ ] Development environment is running (`make dev`)
   - [ ] All tests pass (`make test`)

2. **Key Review Areas**
   - Safety: No direct docker commands, proper use of Make targets
   - Security: No committed secrets or real `.env` files
   - Data Safety: Proper backup verification and volume protection
   - Code Quality: Readability, documentation, test coverage

3. **Common Issues to Watch**
   - Direct `docker compose` commands instead of `make` targets
   - Missing backup size verification
   - Hardcoded credentials or API keys
   - Unprotected volume operations

## Getting Help
- Check `docs/runbooks/` for operational procedures
- Review `Makefile` for available safety targets
- Issue #1 tracks env-template improvements 