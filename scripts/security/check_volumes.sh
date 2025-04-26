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
