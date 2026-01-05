#!/bin/bash
# Bulk SSH Key Bootstrap for VPN Infrastructure
# Distributes SSH keys to all servers defined in inventory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_DIR="${PROJECT_ROOT}/files/ssh"
KEY_NAME="${1:-vpn-infra}"
PUBLIC_KEY="${SSH_DIR}/${KEY_NAME}.pub"
PRIVATE_KEY="${SSH_DIR}/${KEY_NAME}"
INVENTORY="${2:-${PROJECT_ROOT}/inventories/production/hosts.yml}"
USERNAME="${3:-root}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

usage() {
    echo "Usage: $0 [key-name] [inventory-file] [username]"
    echo ""
    echo "Arguments:"
    echo "  key-name       - SSH key name (default: vpn-infra)"
    echo "  inventory-file - Ansible inventory file (default: inventories/production/hosts.yml)"
    echo "  username       - SSH username (default: root)"
    echo ""
    echo "This script will:"
    echo "  1. Extract all ansible_host IPs from the inventory"
    echo "  2. Attempt to copy SSH public key to each server"
    echo "  3. Report success/failure for each server"
    echo ""
    echo "Prerequisites:"
    echo "  - Run ./scripts/ssh-key-setup.sh first"
    echo "  - Have password access to all servers"
    echo "  - sshpass installed (apt install sshpass)"
    exit 1
}

# Check dependencies
check_dependencies() {
    if ! command -v sshpass &> /dev/null; then
        log_error "sshpass is required but not installed"
        echo "Install with: apt install sshpass (Debian/Ubuntu) or brew install hudochenkov/sshpass/sshpass (macOS)"
        exit 1
    fi

    if ! command -v yq &> /dev/null; then
        log_warn "yq not found, falling back to grep-based parsing"
        USE_YQ=false
    else
        USE_YQ=true
    fi
}

# Extract IPs from inventory
extract_ips() {
    local inventory="$1"

    if [[ "$USE_YQ" == "true" ]]; then
        # Use yq for proper YAML parsing
        yq eval '.. | select(has("ansible_host")) | .ansible_host' "$inventory" 2>/dev/null | grep -v "^---$" | grep -v "^null$"
    else
        # Fallback to grep
        grep -E "ansible_host:" "$inventory" | awk '{print $2}' | tr -d '"' | tr -d "'"
    fi
}

# Main
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    usage
fi

check_dependencies

# Check if public key exists
if [[ ! -f "$PUBLIC_KEY" ]]; then
    log_error "Public key not found: $PUBLIC_KEY"
    log_info "Run ./scripts/ssh-key-setup.sh first to generate SSH keys"
    exit 1
fi

# Check if inventory exists
if [[ ! -f "$INVENTORY" ]]; then
    log_error "Inventory file not found: $INVENTORY"
    exit 1
fi

log_info "Bulk SSH Key Bootstrap"
log_info "Using public key: $PUBLIC_KEY"
log_info "Using inventory: $INVENTORY"
log_info "Using username: $USERNAME"
echo ""

# Get SSH password
read -sp "Enter SSH password for servers: " SSH_PASSWORD
echo ""

# Extract all IPs
log_step "Extracting server IPs from inventory..."
SERVERS=$(extract_ips "$INVENTORY")
TOTAL=$(echo "$SERVERS" | wc -l | tr -d ' ')

log_info "Found $TOTAL servers"
echo ""

# Track results
SUCCESS=0
FAILED=0
FAILED_SERVERS=""

# Process each server
COUNT=0
for IP in $SERVERS; do
    COUNT=$((COUNT + 1))
    echo -n "[$COUNT/$TOTAL] Bootstrapping $IP... "

    # Skip placeholder IPs
    if [[ "$IP" == "185."* ]] && [[ "$IP" == *".1" ]]; then
        echo -e "${YELLOW}SKIPPED (placeholder IP)${NC}"
        continue
    fi

    # Try to copy SSH key
    if sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=accept-new -i "$PUBLIC_KEY" "${USERNAME}@${IP}" 2>/dev/null; then
        # Verify key works
        if ssh -i "$PRIVATE_KEY" -o PasswordAuthentication=no -o ConnectTimeout=5 "${USERNAME}@${IP}" "exit 0" 2>/dev/null; then
            echo -e "${GREEN}SUCCESS${NC}"
            SUCCESS=$((SUCCESS + 1))
        else
            echo -e "${YELLOW}KEY COPIED, VERIFY FAILED${NC}"
            FAILED=$((FAILED + 1))
            FAILED_SERVERS="${FAILED_SERVERS}${IP}\n"
        fi
    else
        echo -e "${RED}FAILED${NC}"
        FAILED=$((FAILED + 1))
        FAILED_SERVERS="${FAILED_SERVERS}${IP}\n"
    fi
done

# Summary
echo ""
echo "========================================="
log_info "Bootstrap Summary"
echo "========================================="
echo "Total servers: $TOTAL"
echo -e "Successful:    ${GREEN}$SUCCESS${NC}"
echo -e "Failed:        ${RED}$FAILED${NC}"

if [[ $FAILED -gt 0 ]]; then
    echo ""
    log_warn "Failed servers:"
    echo -e "$FAILED_SERVERS"
fi

echo ""
if [[ $SUCCESS -gt 0 ]]; then
    log_info "You can now run Ansible playbooks against the configured servers"
    echo "Example: ansible-playbook -i $INVENTORY playbooks/deploy/site.yml"
fi
