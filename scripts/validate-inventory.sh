#!/bin/bash
# Inventory validation script for VPN infrastructure

set -e

INVENTORY_FILE="inventories/production"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== VPN Infrastructure Inventory Validation ==="
echo "Project Root: $PROJECT_ROOT"
echo "Inventory File: $INVENTORY_FILE"
echo

# Check if inventory file exists
if [[ ! -f "$PROJECT_ROOT/$INVENTORY_FILE" ]]; then
    echo "❌ ERROR: Inventory file not found: $INVENTORY_FILE"
    exit 1
fi

echo "✅ Inventory file found"

# Validate inventory syntax
echo "🔍 Validating inventory syntax..."
if ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list > /dev/null 2>&1; then
    echo "✅ Inventory syntax is valid"
else
    echo "❌ ERROR: Invalid inventory syntax"
    ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list
    exit 1
fi

# Check required groups
echo "🔍 Checking required inventory groups..."
REQUIRED_GROUPS=(
    "vpn_servers"
    "wireguard_servers" 
    "openvpn_servers"
    "europe"
    "north_america"
    "asia_pacific"
)

for group in "${REQUIRED_GROUPS[@]}"; do
    if ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list | jq -r "._meta.hostvars | keys[]" | grep -q "^${group}"; then
        echo "✅ Group '$group' found"
    else
        # Check if group exists in the groups section
        if ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list | jq -r "keys[]" | grep -q "^${group}$"; then
            echo "✅ Group '$group' found"
        else
            echo "❌ ERROR: Required group '$group' not found"
            exit 1
        fi
    fi
done

# Count servers by region
echo "🔍 Counting servers by region..."
REGIONS=("europe" "north_america" "asia_pacific")

for region in "${REGIONS[@]}"; do
    count=$(ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list | jq -r ".${region}.hosts // [] | length")
    if [[ "$count" -eq 10 ]]; then
        echo "✅ Region '$region': $count servers (expected: 10)"
    else
        echo "❌ ERROR: Region '$region': $count servers (expected: 10)"
        exit 1
    fi
done

# Count servers by protocol
echo "🔍 Counting servers by protocol..."
wg_count=$(ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list | jq -r ".wireguard_servers.hosts // [] | length")
ovpn_count=$(ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list | jq -r ".openvpn_servers.hosts // [] | length")

echo "✅ WireGuard servers: $wg_count"
echo "✅ OpenVPN servers: $ovpn_count"

total_servers=$(ansible-inventory -i "$PROJECT_ROOT/$INVENTORY_FILE" --list | jq -r ".vpn_servers.hosts // [] | length")
if [[ "$total_servers" -eq 30 ]]; then
    echo "✅ Total VPN servers: $total_servers (expected: 30)"
else
    echo "❌ ERROR: Total VPN servers: $total_servers (expected: 30)"
    exit 1
fi

# Check group_vars files
echo "🔍 Checking group_vars files..."
GROUP_VARS_FILES=(
    "inventories/group_vars/all.yml"
    "inventories/group_vars/vpn_servers.yml"
    "inventories/group_vars/wireguard_servers.yml"
    "inventories/group_vars/openvpn_servers.yml"
    "inventories/group_vars/europe.yml"
    "inventories/group_vars/north_america.yml"
    "inventories/group_vars/asia_pacific.yml"
)

for file in "${GROUP_VARS_FILES[@]}"; do
    if [[ -f "$PROJECT_ROOT/$file" ]]; then
        echo "✅ Found: $file"
        # Validate YAML syntax
        if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/$file'))" 2>/dev/null; then
            echo "  ✅ Valid YAML syntax"
        else
            echo "  ❌ ERROR: Invalid YAML syntax in $file"
            exit 1
        fi
    else
        echo "❌ ERROR: Missing group_vars file: $file"
        exit 1
    fi
done

# Check host_vars examples
echo "🔍 Checking host_vars examples..."
HOST_VARS_EXAMPLES=(
    "inventories/host_vars/eu-vpn-wg-01.example.com.yml"
    "inventories/host_vars/na-vpn-wg-01.example.com.yml"
    "inventories/host_vars/ap-vpn-wg-01.example.com.yml"
    "inventories/host_vars/eu-vpn-ovpn-01.example.com.yml"
)

for file in "${HOST_VARS_EXAMPLES[@]}"; do
    if [[ -f "$PROJECT_ROOT/$file" ]]; then
        echo "✅ Found: $file"
        # Validate YAML syntax
        if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/$file'))" 2>/dev/null; then
            echo "  ✅ Valid YAML syntax"
        else
            echo "  ❌ ERROR: Invalid YAML syntax in $file"
            exit 1
        fi
    else
        echo "❌ ERROR: Missing host_vars example: $file"
        exit 1
    fi
done

echo
echo "🎉 Inventory validation completed successfully!"
echo "📊 Summary:"
echo "   - Total servers: 30"
echo "   - Regions: 3 (10 servers each)"
echo "   - Protocols: WireGuard ($wg_count), OpenVPN ($ovpn_count)"
echo "   - Group variables: 7 files"
echo "   - Host variables: 4 example files"
echo