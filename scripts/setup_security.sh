#!/bin/bash
set -euo pipefail

# Configuration
DOCKER_REAL="/usr/local/bin/docker.real"
DOCKER_SHIM="/usr/local/bin/docker"
LEDGER_DOCKER="/usr/local/bin/ledger_docker"

# Ensure we're running as root or with sudo
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root or with sudo"
    exit 1
fi

# 1. Move original docker binary
if [ -f "$DOCKER_SHIM" ] && [ ! -f "$DOCKER_REAL" ]; then
    mv "$DOCKER_SHIM" "$DOCKER_REAL"
fi

# 2. Create symlink to our wrapper
ln -sf "$LEDGER_DOCKER" "$DOCKER_SHIM"

# 3. Add shell aliases for interactive shells
for shell_rc in ~/.bashrc ~/.zshrc; do
    if [ -f "$shell_rc" ]; then
        # Remove any existing docker function
        sed -i.bak '/^docker() {/,/^}/d' "$shell_rc"
        # Add our function
        echo '
# LedgerFlow safety wrapper
docker() { ledger_docker "$@"; }' >> "$shell_rc"
    fi
done

# 4. Create pre-commit hook for git
HOOK_DIR=".git/hooks"
if [ -d "$HOOK_DIR" ]; then
    cat > "$HOOK_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Check for dangerous docker commands
if git diff --cached -U0 | grep -P 'docker\s+compose\s+down\s+[-\w]*-v'; then
    echo "ERROR: Detected 'docker compose down -v' in staged changes."
    echo "This command is dangerous and could lead to data loss."
    exit 1
fi
EOF
    chmod +x "$HOOK_DIR/pre-commit"
fi

echo "✓ Security measures installed successfully"
echo "Please restart your shell or source your rc file to apply changes" 