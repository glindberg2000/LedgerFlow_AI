# Developer Onboarding

## Safety Wrapper Setup

First, install the LedgerFlow safety wrapper to prevent accidental data loss:

```bash
# Install the safety wrapper
mkdir -p ~/bin
curl -s https://raw.githubusercontent.com/LedgerFlow/LedgerFlow/main/scripts/ledger_docker -o ~/bin/ledger_docker && chmod +x ~/bin/ledger_docker

# Add to your shell configuration
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
echo 'docker() { ledger_docker "$@"; }' >> ~/.zshrc
source ~/.zshrc

# Verify installation
docker compose down -v  # Should show 🚫 message
```

## Environment Setup

1. Copy the environment templates:
```bash
cp config/templates/.env.dev.template .env.dev
cp config/templates/.env.prod.template .env.prod
```

2. Edit the environment files with your secure values.

3. Start the development environment:
```bash
make dev
make safety-check
``` 