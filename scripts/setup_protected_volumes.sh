#!/bin/bash

# LedgerFlow Volume Protection Setup
# This script creates and protects all required volumes for both dev and prod environments

set -e

# Function to create or update protected volume
create_protected_volume() {
    local volume_name=$1
    local env=$2

    if ! docker volume ls | grep -q "$volume_name"; then
        echo "Creating protected volume: $volume_name..."
        docker volume create \
            --label com.ledgerflow.protect=true \
            --label com.ledgerflow.environment="$env" \
            "$volume_name"
        echo "✅ Volume created with protection labels"
    else
        echo "Volume exists: $volume_name, checking protection..."
        if ! docker volume inspect "$volume_name" | grep -q "com.ledgerflow.protect.*true"; then
            echo "⚠️ Adding protection to existing volume..."
            # Create temporary volume
            temp_volume="${volume_name}_temp"
            docker volume create --name "$temp_volume"
            
            # Copy data
            echo "📦 Backing up data..."
            docker run --rm -v "$volume_name":/source -v "$temp_volume":/dest alpine cp -av /source/. /dest/
            
            # Remove old volume
            docker volume rm "$volume_name"
            
            # Create new protected volume
            docker volume create \
                --label com.ledgerflow.protect=true \
                --label com.ledgerflow.environment="$env" \
                "$volume_name"
            
            # Restore data
            echo "📦 Restoring data..."
            docker run --rm -v "$temp_volume":/source -v "$volume_name":/dest alpine cp -av /source/. /dest/
            
            # Cleanup
            docker volume rm "$temp_volume"
        fi
        echo "✅ Volume protection verified"
    fi
}

echo "🔒 Setting up protected volumes..."

# Development volumes
echo "\n📁 Setting up development volumes..."
create_protected_volume "ledger-dev_ledgerflow_dev_postgres_data" "development"
create_protected_volume "ledger-dev_ledgerflow_dev_media" "development"
create_protected_volume "ledger-dev_ledgerflow_redis_data_dev" "development"
create_protected_volume "ledger-dev_searxng_data_dev" "development"

# Production volumes
echo "\n📁 Setting up production volumes..."
create_protected_volume "ledger-prod_ledgerflow_prod_postgres_data" "production"
create_protected_volume "ledger-prod_ledgerflow_prod_media" "production"
create_protected_volume "ledger-prod_ledgerflow_redis_data_prod" "production"
create_protected_volume "ledger-prod_searxng_data_prod" "production"

echo "\n✅ All volumes protected successfully!"
echo "Run 'make check-volumes ENV=dev' or 'make check-volumes ENV=prod' to verify." 