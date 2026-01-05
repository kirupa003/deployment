#!/bin/bash
# CoreDNS Role Validation Script
# Validates the CoreDNS role structure and templates

set -euo pipefail

ROLE_DIR="roles/coredns"
ERRORS=0

echo "=== CoreDNS Role Validation ==="
echo "Validating role structure and templates..."

# Check required directories
REQUIRED_DIRS=(
    "$ROLE_DIR/tasks"
    "$ROLE_DIR/templates"
    "$ROLE_DIR/defaults"
    "$ROLE_DIR/handlers"
    "$ROLE_DIR/meta"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✓ Directory exists: $dir"
    else
        echo "✗ Missing directory: $dir"
        ((ERRORS++))
    fi
done

# Check required task files
REQUIRED_TASKS=(
    "$ROLE_DIR/tasks/main.yml"
    "$ROLE_DIR/tasks/system.yml"
    "$ROLE_DIR/tasks/install.yml"
    "$ROLE_DIR/tasks/configure.yml"
    "$ROLE_DIR/tasks/adblock.yml"
    "$ROLE_DIR/tasks/firewall.yml"
    "$ROLE_DIR/tasks/service.yml"
    "$ROLE_DIR/tasks/validate.yml"
)

for task in "${REQUIRED_TASKS[@]}"; do
    if [[ -f "$task" ]]; then
        echo "✓ Task file exists: $task"
        # Basic YAML syntax check
        if python3 -c "import yaml; yaml.safe_load(open('$task'))" 2>/dev/null; then
            echo "  ✓ YAML syntax valid"
        else
            echo "  ✗ YAML syntax error"
            ((ERRORS++))
        fi
    else
        echo "✗ Missing task file: $task"
        ((ERRORS++))
    fi
done

# Check required template files
REQUIRED_TEMPLATES=(
    "$ROLE_DIR/templates/Corefile.j2"
    "$ROLE_DIR/templates/coredns.service.j2"
    "$ROLE_DIR/templates/coredns.env.j2"
    "$ROLE_DIR/templates/update-blocklists.sh.j2"
    "$ROLE_DIR/templates/process-blocklist.py.j2"
    "$ROLE_DIR/templates/validation-report.txt.j2"
)

for template in "${REQUIRED_TEMPLATES[@]}"; do
    if [[ -f "$template" ]]; then
        echo "✓ Template exists: $template"
    else
        echo "✗ Missing template: $template"
        ((ERRORS++))
    fi
done

# Check configuration files
CONFIG_FILES=(
    "$ROLE_DIR/defaults/main.yml"
    "$ROLE_DIR/handlers/main.yml"
    "$ROLE_DIR/meta/main.yml"
)

for config in "${CONFIG_FILES[@]}"; do
    if [[ -f "$config" ]]; then
        echo "✓ Config file exists: $config"
        # Basic YAML syntax check
        if python3 -c "import yaml; yaml.safe_load(open('$config'))" 2>/dev/null; then
            echo "  ✓ YAML syntax valid"
        else
            echo "  ✗ YAML syntax error"
            ((ERRORS++))
        fi
    else
        echo "✗ Missing config file: $config"
        ((ERRORS++))
    fi
done

# Validate playbook syntax
echo ""
echo "=== Playbook Validation ==="
if ansible-playbook --syntax-check playbooks/deploy-coredns.yml >/dev/null 2>&1; then
    echo "✓ Playbook syntax valid: playbooks/deploy-coredns.yml"
else
    echo "✗ Playbook syntax error: playbooks/deploy-coredns.yml"
    ((ERRORS++))
fi

# Check for required variables in defaults
echo ""
echo "=== Variable Validation ==="
REQUIRED_VARS=(
    "coredns_version"
    "coredns_user"
    "coredns_group"
    "coredns_home"
    "coredns_config_dir"
    "coredns_data_dir"
    "coredns_log_dir"
    "coredns_listen_port"
    "coredns_adblock_enabled"
    "coredns_adblock_lists"
    "coredns_upstream_resolvers"
)

for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}:" "$ROLE_DIR/defaults/main.yml"; then
        echo "✓ Variable defined: $var"
    else
        echo "✗ Missing variable: $var"
        ((ERRORS++))
    fi
done

# Summary
echo ""
echo "=== Validation Summary ==="
if [[ $ERRORS -eq 0 ]]; then
    echo "✓ All validations passed! CoreDNS role is ready for deployment."
    exit 0
else
    echo "✗ Found $ERRORS error(s). Please fix before deployment."
    exit 1
fi