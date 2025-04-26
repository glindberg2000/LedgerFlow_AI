# Variables
ENV ?= dev
TEST_DB ?= test_restore_db
BACKUP_ROOT := /Users/greg/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups

# Default target
.DEFAULT_GOAL := help

# Help target
help:
	@echo "LedgerFlow Development Commands:"
	@echo "  make dev              Start development environment"
	@echo "  make backup          Backup database"
	@echo "  make restore FILE=x  Restore database from backup"
	@echo "  make check-volumes   Verify volume protection"
	@echo "  make nuke ENV=dev    Destroy environment (dev only)"
	@echo "  make restore-test FILE=x  Test restore in temporary database"
	@echo "  make prod-bootstrap TAG=x  First-time prod setup"

# Development environment
dev:
	ledger_docker compose -f docker-compose.dev.yml up -d

# Production bootstrap (first-time setup)
prod-bootstrap:
	@if [ -z "$(TAG)" ]; then echo "Please specify TAG=version"; exit 1; fi
	@echo "Starting production bootstrap with tag $(TAG)..."
	ledger_docker compose -p ledger-prod -f docker-compose.yml -f docker-compose.prod.yml up -d postgres
	@echo "Waiting for postgres..."
	@sleep 6
	ledger_docker compose -p ledger-prod -f docker-compose.yml -f docker-compose.prod.yml ps
	@echo "Running initial migrations..."
	ledger_docker compose -p ledger-prod -f docker-compose.yml -f docker-compose.prod.yml exec django python manage.py migrate --noinput
	@echo "Creating first backup..."
	make backup ENV=prod
	@echo "Starting remaining services..."
	ledger_docker compose -p ledger-prod -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "Bootstrap complete. Run 'make smoke ENV=prod' to verify."

# Database backup
backup:
	@mkdir -p "$(BACKUP_ROOT)/$(ENV)"
	@echo "Creating backup in $(BACKUP_ROOT)/$(ENV)..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec postgres pg_dump -Fc --clean -U $$POSTGRES_USER -d $$POSTGRES_DB > "$(BACKUP_ROOT)/$(ENV)/backup_`date +%Y%m%d_%H%M%S`.dump"
	@echo "Verifying backup size..."
	@test $$(stat -f%z "$(BACKUP_ROOT)/$(ENV)"/backup_*.dump) -gt 10240 || (echo "Error: Backup file is too small" && exit 1)
	@echo "Backup completed and verified"

# Database restore
restore:
	@if [ -z "$(FILE)" ]; then echo "Please specify FILE=path/to/backup in $(BACKUP_ROOT)/$(ENV)"; exit 1; fi
	@if [ ! -f "$(FILE)" ]; then echo "Error: Backup file $(FILE) not found"; exit 1; fi
	@echo "Restoring from $(FILE)..."
	cat "$(FILE)" | ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres pg_restore --no-owner --no-privileges --clean --if-exists -U $$POSTGRES_USER -d $$POSTGRES_DB

# Test restore in temporary database
restore-test:
	@if [ -z "$(FILE)" ]; then echo "Please specify FILE=path/to/backup in $(BACKUP_ROOT)/$(ENV)"; exit 1; fi
	@if [ ! -f "$(FILE)" ]; then echo "Error: Backup file $(FILE) not found"; exit 1; fi
	@echo "Creating temporary database $(TEST_DB)..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB -c "DROP DATABASE IF EXISTS $(TEST_DB)"
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB -c "CREATE DATABASE $(TEST_DB)"
	@echo "Restoring backup to temporary database..."
	cat "$(FILE)" | ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres pg_restore --no-owner --no-privileges --clean --if-exists -U $$POSTGRES_USER -d $(TEST_DB)
	@echo "Verifying database structure..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $(TEST_DB) -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'"
	@echo "Verifying data content..."
	@echo "1. Checking auth_user table..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $(TEST_DB) -c "SELECT COUNT(*) FROM auth_user"
	@echo "2. Checking profiles_processingtask table..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $(TEST_DB) -c "SELECT COUNT(*) FROM profiles_processingtask"
	@echo "3. Checking profiles_transaction table..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $(TEST_DB) -c "SELECT COUNT(*) FROM profiles_transaction"
	@echo "4. Sample of recent transactions..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $(TEST_DB) -c "\d profiles_transaction"
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $(TEST_DB) -c "SELECT id, transaction_date, amount FROM profiles_transaction ORDER BY transaction_date DESC LIMIT 5"
	@echo "Cleaning up..."
	ledger_docker compose -f docker-compose.$(ENV).yml exec -T postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB -c "DROP DATABASE $(TEST_DB)"
	@echo "Restore test completed successfully"

# Check volume protection
check-volumes:
	@./scripts/verify_volumes.sh $(ENV)

# Destroy environment (dev only)
nuke:
	@if [ "$(ENV)" = "prod" ]; then echo "Refusing to nuke prod"; exit 1; fi
	@read -p "Type DESTROY to wipe $(ENV): " x; [ "$$x" = "DESTROY" ] && ledger_docker compose -f docker-compose.$(ENV).yml down -v

# Declare phony targets
.PHONY: help dev backup restore restore-test check-volumes nuke prod-bootstrap
