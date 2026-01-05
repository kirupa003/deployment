#!/bin/bash
# Generate OpenVPN PKI (CA, DH, TLS-Auth)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PKI_DIR="$PROJECT_ROOT/files/pki"
VAULT_PASSWORD_FILE="$PROJECT_ROOT/.vault_password"

echo "=== OpenVPN PKI Generation ==="
echo ""

# Check for openssl
if ! command -v openssl &> /dev/null; then
    echo "Error: OpenSSL not installed."
    exit 1
fi

# Check for vault password
if [ ! -f "$VAULT_PASSWORD_FILE" ]; then
    echo "Error: Vault password not found. Run init-vault.sh first."
    exit 1
fi

# Create PKI directory
mkdir -p "$PKI_DIR"

echo "This will generate:"
echo "  - CA certificate and key"
echo "  - DH parameters (2048-bit)"
echo "  - TLS-Auth key"
echo ""
read -p "Continue? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""

# Generate CA
echo "Generating CA certificate..."
openssl req -new -x509 -days 3650 -nodes \
    -keyout "$PKI_DIR/ca.key" \
    -out "$PKI_DIR/ca.crt" \
    -subj "/C=US/ST=State/L=City/O=Planet Proxy/OU=VPN/CN=VPN CA"
echo "✓ CA certificate generated"

# Generate DH parameters
echo "Generating DH parameters (this may take a while)..."
openssl dhparam -out "$PKI_DIR/dh.pem" 2048
echo "✓ DH parameters generated"

# Generate TLS-Auth key
echo "Generating TLS-Auth key..."
openvpn --genkey secret "$PKI_DIR/ta.key" 2>/dev/null || \
    openssl rand -base64 256 > "$PKI_DIR/ta.key"
echo "✓ TLS-Auth key generated"

# Set permissions
chmod 600 "$PKI_DIR"/*.key
chmod 644 "$PKI_DIR"/*.crt "$PKI_DIR"/*.pem

# Create encrypted vault file with PKI contents
echo ""
echo "Creating encrypted PKI vault file..."

VAULT_FILE="$PROJECT_ROOT/inventories/production/group_vars/openvpn_servers/vault.yml"
mkdir -p "$(dirname "$VAULT_FILE")"

cat > "$VAULT_FILE" << EOF
---
# OpenVPN PKI Secrets
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

openvpn_ca_cert: |
$(cat "$PKI_DIR/ca.crt" | sed 's/^/  /')

openvpn_ca_key: |
$(cat "$PKI_DIR/ca.key" | sed 's/^/  /')

openvpn_dh_params: |
$(cat "$PKI_DIR/dh.pem" | sed 's/^/  /')

openvpn_ta_key: |
$(cat "$PKI_DIR/ta.key" | sed 's/^/  /')
EOF

ansible-vault encrypt "$VAULT_FILE" --vault-password-file "$VAULT_PASSWORD_FILE"
echo "✓ PKI vault file created and encrypted"

# Clean up unencrypted files
echo ""
read -p "Remove unencrypted PKI files from files/pki/? (y/N): " cleanup
if [ "$cleanup" == "y" ] || [ "$cleanup" == "Y" ]; then
    rm -rf "$PKI_DIR"
    echo "✓ Unencrypted PKI files removed"
else
    echo "Warning: Unencrypted PKI files remain in $PKI_DIR"
    echo "Consider removing them after backup."
fi

echo ""
echo "=== PKI Generation Complete ==="
echo ""
echo "PKI is encrypted in: $VAULT_FILE"
echo ""
echo "To generate server certificates, use:"
echo "  ./scripts/generate-server-cert.sh <hostname>"
echo ""
