#!/usr/bin/env bash
#
# Setup script for LedgerFlow reviewers
#
set -euo pipefail

# Configuration
REPO_URL="https://github.com/glindberg2000/LedgerFlow.git"
CLONE_DIR="ledgerflow-review"
TAG="v20250424-dev-gold"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Setting up LedgerFlow review environment...${NC}"

# Create and switch to review directory
echo -e "\n${YELLOW}Cloning repository...${NC}"
git clone "$REPO_URL" "$CLONE_DIR"
cd "$CLONE_DIR"

# Checkout specific tag
echo -e "\n${YELLOW}Checking out $TAG...${NC}"
git checkout "$TAG"

# Setup safety wrapper
echo -e "\n${YELLOW}Installing safety wrapper...${NC}"
mkdir -p ~/bin
cp scripts/ledger_docker ~/bin/
chmod +x ~/bin/ledger_docker

# Add to PATH if not already there
if ! grep -q "export PATH=\$HOME/bin:\$PATH" ~/.zprofile; then
    echo 'export PATH=$HOME/bin:$PATH' >> ~/.zprofile
    echo 'docker() { ledger_docker "$@"; }' >> ~/.zprofile
fi

# Copy environment template
echo -e "\n${YELLOW}Setting up environment...${NC}"
cp config/templates/.env.dev.template .env.dev

echo -e "\n${GREEN}Setup complete! Please:${NC}"
echo "1. Edit .env.dev with appropriate values"
echo "2. Run: source ~/.zprofile"
echo "3. Verify: which docker  # Should point to ledger_docker"
echo "4. Run: make safety-check ENV=dev" 