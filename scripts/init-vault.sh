#!/bin/bash
# Initialize Ansible Vault password and encrypt secrets
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_PASSWORD_FILE="$PROJECT_ROOT/.vault_password"

echo "=== Ansible Vault Initialization ==="
echo ""

# Check if vault password already exists
if [ -f "$VAULT_PASSWORD_FILE" ]; then
    echo "Warning: Vault password file already exists at $VAULT_PASSWORD_FILE"
    read -p "Do you want to generate a new password? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Keeping existing vault password."
        exit 0
    fi
fi

# Generate secure random password
echo "Generating secure vault password..."
openssl rand -base64 32 > "$VAULT_PASSWORD_FILE"
chmod 600 "$VAULT_PASSWORD_FILE"

echo "✓ Vault password generated at $VAULT_PASSWORD_FILE"
echo ""
echo "IMPORTANT: Store this password securely!"
echo "  - Add to your password manager"
echo "  - Store in CI/CD secrets"
echo "  - NEVER commit to git"
echo ""

# Encrypt vault files
echo "Looking for vault.yml files to encrypt..."
find "$PROJECT_ROOT/inventories" -name "vault.yml" -type f | while read -r vault_file; do
    # Check if file is already encrypted
    if head -1 "$vault_file" | grep -q '^\$ANSIBLE_VAULT'; then
        echo "  ⊘ Already encrypted: $vault_file"
    else
        echo "  → Encrypting: $vault_file"
        ansible-vault encrypt "$vault_file" --vault-password-file "$VAULT_PASSWORD_FILE"
        echo "  ✓ Encrypted: $vault_file"
    fi
done

echo ""
echo "=== Initialization Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit secrets: ansible-vault edit inventories/production/group_vars/all/vault.yml"
echo "  2. Run playbook: ansible-playbook playbooks/deploy/site.yml"
echo ""
