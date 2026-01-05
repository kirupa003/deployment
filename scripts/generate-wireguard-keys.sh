#!/bin/bash
# Generate WireGuard keys for all servers and store them
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_PASSWORD_FILE="$PROJECT_ROOT/.vault_password"
HOST_VARS_DIR="$PROJECT_ROOT/inventories/production/host_vars"

echo "=== WireGuard Key Generation ==="
echo ""

# Check for wg command
if ! command -v wg &> /dev/null; then
    echo "Error: WireGuard tools not installed. Install with:"
    echo "  brew install wireguard-tools  # macOS"
    echo "  apt install wireguard-tools   # Ubuntu/Debian"
    exit 1
fi

# Check for vault password
if [ ! -f "$VAULT_PASSWORD_FILE" ]; then
    echo "Error: Vault password not found. Run init-vault.sh first."
    exit 1
fi

# Get list of WireGuard and AmneziaWG servers
SERVERS=$(grep -E "^\s+(eu|na|apac)-(wg|awg)-[0-9]+:" "$PROJECT_ROOT/inventories/production/hosts.yml" | sed 's/://g' | awk '{print $1}')

if [ -z "$SERVERS" ]; then
    echo "No WireGuard/AmneziaWG servers found in inventory."
    exit 1
fi

echo "Found servers:"
echo "$SERVERS" | while read server; do echo "  - $server"; done
echo ""

read -p "Generate keys for all servers? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Generating keys..."

echo "$SERVERS" | while read server; do
    HOST_DIR="$HOST_VARS_DIR/$server"
    VAULT_FILE="$HOST_DIR/vault.yml"

    # Create host directory
    mkdir -p "$HOST_DIR"

    # Generate keys
    PRIVATE_KEY=$(wg genkey)
    PUBLIC_KEY=$(echo "$PRIVATE_KEY" | wg pubkey)

    # Determine protocol
    if [[ "$server" == *"-wg-"* ]]; then
        KEY_VAR="wireguard_private_key"
    else
        KEY_VAR="amneziawg_private_key"
    fi

    # Create vault file
    cat > "$VAULT_FILE" << EOF
---
# WireGuard keys for $server
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
${KEY_VAR}: "${PRIVATE_KEY}"
# Public key (for reference, not secret): ${PUBLIC_KEY}
EOF

    # Encrypt the file
    ansible-vault encrypt "$VAULT_FILE" --vault-password-file "$VAULT_PASSWORD_FILE" 2>/dev/null

    echo "✓ $server - Public key: ${PUBLIC_KEY:0:20}..."
done

echo ""
echo "=== Key Generation Complete ==="
echo ""
echo "Keys are encrypted in: $HOST_VARS_DIR/<hostname>/vault.yml"
echo ""
echo "To view a server's keys:"
echo "  ansible-vault view inventories/production/host_vars/eu-wg-001/vault.yml"
echo ""
