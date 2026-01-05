#!/bin/bash
# Bootstrap SSH Access to a Single Server
# Use this for initial setup when you have password access

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_DIR="${PROJECT_ROOT}/files/ssh"
KEY_NAME="${3:-vpn-infra}"
PUBLIC_KEY="${SSH_DIR}/${KEY_NAME}.pub"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    echo "Usage: $0 <server-ip> [username] [key-name]"
    echo ""
    echo "Arguments:"
    echo "  server-ip  - IP address or hostname of the server"
    echo "  username   - SSH username (default: root)"
    echo "  key-name   - SSH key name (default: vpn-infra)"
    echo ""
    echo "Examples:"
    echo "  $0 185.10.1.1"
    echo "  $0 185.10.1.1 ubuntu"
    echo "  $0 185.10.1.1 root vpn-infra"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

SERVER_IP="$1"
USERNAME="${2:-root}"

# Check if public key exists
if [[ ! -f "$PUBLIC_KEY" ]]; then
    log_error "Public key not found: $PUBLIC_KEY"
    log_info "Run ./scripts/ssh-key-setup.sh first to generate SSH keys"
    exit 1
fi

log_info "Bootstrapping SSH access to $USERNAME@$SERVER_IP"
log_info "Using public key: $PUBLIC_KEY"
echo ""

# Copy SSH key to server
log_info "Copying SSH public key to server..."
ssh-copy-id -i "$PUBLIC_KEY" "${USERNAME}@${SERVER_IP}"

# Verify connection
log_info "Verifying SSH key authentication..."
PRIVATE_KEY="${SSH_DIR}/${KEY_NAME}"
if ssh -i "$PRIVATE_KEY" -o PasswordAuthentication=no "${USERNAME}@${SERVER_IP}" "echo 'SSH key authentication successful!'"; then
    echo ""
    log_info "SSH key setup complete for $SERVER_IP"
    log_info "You can now use: ssh -i $PRIVATE_KEY ${USERNAME}@${SERVER_IP}"
else
    log_error "SSH key verification failed"
    exit 1
fi
