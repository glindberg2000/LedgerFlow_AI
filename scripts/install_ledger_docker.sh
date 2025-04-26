#!/bin/bash

# LedgerFlow Docker Safety Guard Installation
# This script installs the LedgerFlow Docker wrapper to prevent unsafe operations

set -e

WRAPPER_PATH="/usr/local/bin/ledger_docker"
DOCKER_PATH=$(which docker)

echo "🔒 Installing LedgerFlow Docker Safety Guard..."

# Create wrapper script
cat > "$WRAPPER_PATH" << EOL
#!/bin/bash

# LedgerFlow Docker Safety Guard
# Prevents unsafe operations and enforces backup verification

ORIGINAL_DOCKER="$DOCKER_PATH"

check_backup() {
    local env=\$1
    local backup_dir="\$HOME/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups/\$env"
    local latest_backup=\$(ls -t "\$backup_dir"/*.sql.gz 2>/dev/null | head -1)
    
    if [ -z "\$latest_backup" ]; then
        echo "❌ No backup found in \$backup_dir"
        return 1
    fi
    
    local size=\$(stat -f%z "\$latest_backup")
    if [ \$size -lt 10240 ]; then
        echo "❌ Latest backup too small (\$size bytes)"
        return 1
    fi
    
    echo "✅ Backup verified: \$latest_backup (\$size bytes)"
    return 0
}

check_volumes() {
    local volumes=\$("$DOCKER_PATH" volume ls --format "{{.Name}}" | grep ledger)
    for vol in \$volumes; do
        if [ -n "\$vol" ]; then
            local labels=\$("$DOCKER_PATH" volume inspect \$vol --format '{{.Labels}}')
            if [[ \$labels != *"com.ledgerflow.protect"* ]]; then
                echo "⚠️ Warning: Volume \$vol is not protected"
            fi
        fi
    done
}

# Intercept dangerous commands
if [[ "\$*" == *"down -v"* ]]; then
    echo "🚫 ERROR: Volume deletion blocked for safety"
    echo "Use 'make nuke ENV=dev' for controlled environment cleanup"
    exit 1
fi

if [[ "\$*" == *"compose"* && "\$*" == *"prod"* ]]; then
    if ! check_backup "prod"; then
        echo "🚫 ERROR: Production operation blocked - backup verification failed"
        exit 1
    fi
fi

# Execute original docker command
exec "$DOCKER_PATH" "\$@"
EOL

# Make wrapper executable
chmod +x "$WRAPPER_PATH"

# Add alias to shell rc files
for rc in ~/.bashrc ~/.zshrc; do
    if [ -f "$rc" ]; then
        if ! grep -q "alias docker=" "$rc"; then
            echo "alias docker=ledger_docker" >> "$rc"
            echo "Added alias to $rc"
        fi
    fi
done

echo "✅ LedgerFlow Docker Safety Guard installed successfully!"
echo "🔄 Please restart your shell or run: source ~/.bashrc (or ~/.zshrc)"
echo "📝 Run 'which docker' to verify installation - should show: $WRAPPER_PATH" 