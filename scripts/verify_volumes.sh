#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Verifying Docker volumes and backup locations..."

# Check Docker volumes
echo -e "\n${YELLOW}Checking Docker volumes...${NC}"
volumes=("ledgerflow_postgres_data" "ledgerflow_media" "searxng_data" "redis_data")
for volume in "${volumes[@]}"; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Volume $volume exists${NC}"
    else
        echo -e "${RED}✗ Volume $volume is missing${NC}"
    fi
done

# Check bind mount directories
echo -e "\n${YELLOW}Checking bind mount directories...${NC}"
directories=(
    "/Users/greg/LedgerFlow_data/pg"
    "/Users/greg/iCloud Drive (Archive)/repos/LedgerFlow_Archive/backups"
    "./searxng/settings.yml"
)

for dir in "${directories[@]}"; do
    if [ -e "$dir" ]; then
        echo -e "${GREEN}✓ Directory/file $dir exists${NC}"
        # Check if directory is writable
        if [ -w "$dir" ]; then
            echo -e "${GREEN}  ✓ Directory/file is writable${NC}"
        else
            echo -e "${RED}  ✗ Directory/file is not writable${NC}"
        fi
    else
        echo -e "${RED}✗ Directory/file $dir is missing${NC}"
    fi
done

# Check backup configuration
echo -e "\n${YELLOW}Checking backup configuration...${NC}"
backup_dir="/Users/greg/iCloud Drive (Archive)/repos/LedgerFlow_Archive/backups"
if [ -d "$backup_dir" ]; then
    # Check for recent backups (last 24 hours)
    recent_backups=$(find "$backup_dir" -type f -name "*.sql" -mtime -1 | wc -l)
    if [ "$recent_backups" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $recent_backups backup(s) from the last 24 hours${NC}"
    else
        echo -e "${RED}✗ No recent backups found in the last 24 hours${NC}"
    fi
    
    # Check backup directory size
    backup_size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
    echo -e "${GREEN}✓ Backup directory size: $backup_size${NC}"
else
    echo -e "${RED}✗ Backup directory is missing${NC}"
fi

# Check SearXNG configuration
echo -e "\n${YELLOW}Checking SearXNG configuration...${NC}"
if [ -f "./searxng/settings.yml" ]; then
    echo -e "${GREEN}✓ SearXNG settings.yml exists${NC}"
    # Check if settings.yml contains required configurations
    if grep -q "redis:" "./searxng/settings.yml" && grep -q "base_url:" "./searxng/settings.yml"; then
        echo -e "${GREEN}✓ SearXNG settings.yml contains required configurations${NC}"
    else
        echo -e "${RED}✗ SearXNG settings.yml is missing required configurations${NC}"
    fi
else
    echo -e "${RED}✗ SearXNG settings.yml is missing${NC}"
fi

echo -e "\n${YELLOW}Verification complete.${NC}" 