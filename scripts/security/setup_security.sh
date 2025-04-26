#!/bin/bash

# Exit on any error
set -e

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 1. Create protected volumes
log "Creating protected volumes..."
docker volume create --label com.ledgerflow.protect=true ledger_dev_db_data
docker volume create --label com.ledgerflow.protect=true ledger_prod_db_data

# 2. Install Docker CLI wrapper
log "Installing Docker CLI wrapper..."
cat > /usr/local/bin/ledger_docker << 'EOF'
#!/bin/bash
if [[ "$*" == *"down"*"-v"* ]]; then
    echo "🔥 Refusing to remove volumes; use make nuke ENV=dev if you REALLY know."
    exit 1
fi
exec docker "$@"
EOF

chmod +x /usr/local/bin/ledger_docker

# 3. Update environment lock in manage.py
log "Updating manage.py with environment lock..."
cat > manage.py << 'EOF'
#!/usr/bin/env python
import os
import sys

def main():
    if os.getenv("LEDGER_ENV") == "prod" and os.getenv("ALLOW_DANGEROUS") != "1":
        sys.exit("Refusing to run mgmt commands directly in prod container.")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledgerflow.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
EOF

chmod +x manage.py

# 4. Create volume protection script
log "Creating volume protection script..."
cat > scripts/security/check_volumes.sh << 'EOF'
#!/bin/bash

# Check for protected volumes in docker-compose files
check_compose_file() {
    local file=$1
    if grep -q "com.ledgerflow.protect=true" "$file"; then
        if grep -q "\-v" "$file"; then
            echo "ERROR: Protected volume mounted with -v flag in $file"
            exit 1
        fi
    fi
}

check_compose_file docker-compose.yml
check_compose_file docker-compose.dev.yml
check_compose_file docker-compose.prod.yml
EOF

chmod +x scripts/security/check_volumes.sh

# 5. Update Makefile with safety measures
log "Updating Makefile with safety measures..."
cat > Makefile << 'EOF'
# NEVER deletes prod
nuke: ENV?=dev
	@if [ "$(ENV)" = "prod" ]; then echo "Refusing to nuke prod"; exit 1; fi
	@read -p "Type DESTROY to wipe $(ENV): " x; [ "$$x" = "DESTROY" ] && ledger_docker compose -p ledger-$(ENV) down -v

backup:
	ledger_docker compose -p ledger-prod exec postgres pg_dump -Fc --clean -U $$POSTGRES_USER -d $$POSTGRES_DB > backups/manual_`date +%F_%T`.dump

restore: FILE
	@if [ -z "$(FILE)" ]; then echo "Please specify FILE=path/to/backup"; exit 1; fi
	ledger_docker compose -p ledger-dev exec postgres pg_restore --exit-on-error --clean -U $$POSTGRES_USER -d $$POSTGRES_DB < $(FILE)

check-volumes:
	@./scripts/security/check_volumes.sh

.PHONY: nuke backup restore check-volumes
EOF

# 6. Create pre-commit hook for volume protection
log "Setting up pre-commit hook..."
mkdir -p .git/hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/security/check_volumes.sh
EOF

chmod +x .git/hooks/pre-commit

log "Security measures implemented successfully"
log "Please review the changes and ensure all scripts are working as expected" 