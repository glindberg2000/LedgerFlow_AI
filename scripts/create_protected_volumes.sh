#!/bin/bash

# Create protected production database volume if it doesn't exist
if ! docker volume ls | grep -q "ledger_prod_db_data"; then
    echo "Creating protected production database volume..."
    docker volume create --label com.ledgerflow.protect=true ledger_prod_db_data
    echo "✅ Production database volume created with protection label"
else
    echo "Production volume exists, updating protection label..."
    docker volume inspect ledger_prod_db_data | grep -q "com.ledgerflow.protect"
    if [ $? -ne 0 ]; then
        echo "⚠️ Warning: Existing volume found without protection label"
        echo "Please backup data and recreate volume with protection"
        exit 1
    fi
    echo "✅ Production volume already protected"
fi

# Verify protection
if docker volume inspect ledger_prod_db_data | grep -q "com.ledgerflow.protect.*true"; then
    echo "✅ Volume protection verified"
else
    echo "❌ Volume protection verification failed"
    exit 1
fi 