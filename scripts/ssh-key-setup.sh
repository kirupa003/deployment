#!/bin/bash
# SSH Key Setup Script for VPN Infrastructure
# Generates SSH key pairs for Ansible controller to access all VPN servers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_DIR="${PROJECT_ROOT}/files/ssh"
KEY_NAME="${1:-vpn-infra}"
KEY_TYPE="${2:-ed25519}"
KEY_COMMENT="${3:-vpn-infra@ansible-controller}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create SSH directory
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

PRIVATE_KEY="${SSH_DIR}/${KEY_NAME}"
PUBLIC_KEY="${SSH_DIR}/${KEY_NAME}.pub"

# Check if key already exists
if [[ -f "$PRIVATE_KEY" ]]; then
    log_warn "SSH key already exists: $PRIVATE_KEY"
    read -p "Overwrite existing key? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Keeping existing key"
        exit 0
    fi
    # Backup existing key
    BACKUP_DIR="${SSH_DIR}/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    mv "$PRIVATE_KEY" "$BACKUP_DIR/"
    mv "$PUBLIC_KEY" "$BACKUP_DIR/" 2>/dev/null || true
    log_info "Backed up existing key to $BACKUP_DIR"
fi

# Generate SSH key pair
log_info "Generating $KEY_TYPE SSH key pair..."
ssh-keygen -t "$KEY_TYPE" -C "$KEY_COMMENT" -f "$PRIVATE_KEY" -N "" -q

# Set correct permissions
chmod 600 "$PRIVATE_KEY"
chmod 644 "$PUBLIC_KEY"

log_info "SSH key pair generated successfully!"
echo ""
echo "Private key: $PRIVATE_KEY"
echo "Public key:  $PUBLIC_KEY"
echo ""
log_info "Public key content:"
cat "$PUBLIC_KEY"
echo ""

# Create ansible.cfg SSH settings if not exists
ANSIBLE_CFG="${PROJECT_ROOT}/ansible.cfg"
if [[ -f "$ANSIBLE_CFG" ]]; then
    if ! grep -q "private_key_file" "$ANSIBLE_CFG"; then
        log_info "Adding SSH key path to ansible.cfg..."
        sed -i.bak '/\[defaults\]/a\
private_key_file = files/ssh/'"${KEY_NAME}"'
' "$ANSIBLE_CFG"
    fi
fi

echo ""
log_info "Next steps:"
echo "  1. Copy the public key to your VPN servers (see bootstrap options below)"
echo "  2. Update inventories/*/group_vars/all.yml with ansible_ssh_private_key_file"
echo ""
echo "Bootstrap options:"
echo "  a) For new servers with cloud-init:"
echo "     Add the public key to your cloud-init user-data"
echo ""
echo "  b) For existing servers with root password:"
echo "     ./scripts/bootstrap-ssh.sh <server-ip> [username]"
echo ""
echo "  c) For bulk bootstrap with password auth:"
echo "     ansible-playbook playbooks/security/ssh-bootstrap.yml -k"
