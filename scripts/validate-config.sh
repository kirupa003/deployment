#!/bin/bash
# Configuration Validation Script for VPN Infrastructure
# Validates merged configuration from planet-proxy-devops-controller consolidation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}=== VPN Infrastructure Configuration Validation ===${NC}"
echo "Project Directory: $PROJECT_DIR"
echo

# Function to check if file exists
check_file() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$PROJECT_DIR/$file" ]]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file (missing)"
        return 1
    fi
}

# Function to validate ansible configuration
validate_ansible_config() {
    local config_file="$1"
    local env_name="$2"
    
    echo -e "\n${YELLOW}Validating $env_name configuration...${NC}"
    
    if [[ -f "$PROJECT_DIR/$config_file" ]]; then
        # Check ansible configuration syntax using Python configparser
        if python3 -c "
import configparser
try:
    config = configparser.ConfigParser()
    config.read('$PROJECT_DIR/$config_file')
    print('Configuration syntax is valid')
except Exception as e:
    print(f'Configuration syntax error: {e}')
    exit(1)
" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $config_file syntax is valid"
        else
            echo -e "${RED}✗${NC} $config_file has syntax errors"
            return 1
        fi
        
        # Check key settings by parsing the file
        local forks=$(grep "^forks" "$PROJECT_DIR/$config_file" | awk '{print $3}' | head -1)
        local timeout=$(grep "^timeout" "$PROJECT_DIR/$config_file" | awk '{print $3}' | head -1)
        
        if [[ -n "$forks" ]]; then
            echo -e "${GREEN}✓${NC} Forks setting: $forks"
        fi
        if [[ -n "$timeout" ]]; then
            echo -e "${GREEN}✓${NC} Timeout setting: $timeout"
        fi
    else
        echo -e "${RED}✗${NC} Configuration file not found: $config_file"
        return 1
    fi
}

# Function to validate requirements.yml
validate_requirements() {
    echo -e "\n${YELLOW}Validating requirements.yml...${NC}"
    
    if [[ -f "$PROJECT_DIR/requirements.yml" ]]; then
        # Check YAML syntax
        if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_DIR/requirements.yml'))" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} requirements.yml syntax is valid"
        else
            echo -e "${RED}✗${NC} requirements.yml has syntax errors"
            return 1
        fi
        
        # Count collections and roles
        local collections=$(grep -c "name:" "$PROJECT_DIR/requirements.yml" | head -1 || echo "0")
        echo -e "${GREEN}✓${NC} Found collections and roles in requirements.yml"
        
        # Check for essential collections
        local essential_collections=("community.general" "community.crypto" "community.docker" "community.hashi_vault")
        for collection in "${essential_collections[@]}"; do
            if grep -q "$collection" "$PROJECT_DIR/requirements.yml"; then
                echo -e "${GREEN}✓${NC} Essential collection found: $collection"
            else
                echo -e "${YELLOW}!${NC} Essential collection missing: $collection"
            fi
        done
    else
        echo -e "${RED}✗${NC} requirements.yml not found"
        return 1
    fi
}

# Function to validate inventory structure
validate_inventory() {
    echo -e "\n${YELLOW}Validating inventory structure...${NC}"
    
    local inventory_dirs=("inventories/production" "inventories/staging")
    
    for inv_dir in "${inventory_dirs[@]}"; do
        if [[ -d "$PROJECT_DIR/$inv_dir" ]]; then
            echo -e "${GREEN}✓${NC} Inventory directory exists: $inv_dir"
            
            # Check for hosts.yml
            if [[ -f "$PROJECT_DIR/$inv_dir/hosts.yml" ]]; then
                echo -e "${GREEN}✓${NC} Hosts file exists: $inv_dir/hosts.yml"
                
                # Validate YAML syntax
                if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_DIR/$inv_dir/hosts.yml'))" 2>/dev/null; then
                    echo -e "${GREEN}✓${NC} Hosts file syntax is valid: $inv_dir/hosts.yml"
                else
                    echo -e "${RED}✗${NC} Hosts file has syntax errors: $inv_dir/hosts.yml"
                fi
            else
                echo -e "${YELLOW}!${NC} Hosts file missing: $inv_dir/hosts.yml"
            fi
            
            # Check for group_vars
            if [[ -d "$PROJECT_DIR/$inv_dir/group_vars" ]]; then
                echo -e "${GREEN}✓${NC} Group vars directory exists: $inv_dir/group_vars"
            else
                echo -e "${YELLOW}!${NC} Group vars directory missing: $inv_dir/group_vars"
            fi
        else
            echo -e "${YELLOW}!${NC} Inventory directory missing: $inv_dir"
        fi
    done
}

# Function to check ansible installation and version
check_ansible() {
    echo -e "\n${YELLOW}Checking Ansible installation...${NC}"
    
    if command -v ansible >/dev/null 2>&1; then
        local ansible_version=$(ansible --version | head -1)
        echo -e "${GREEN}✓${NC} Ansible installed: $ansible_version"
        
        # Check for ansible-galaxy
        if command -v ansible-galaxy >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} ansible-galaxy available"
        else
            echo -e "${RED}✗${NC} ansible-galaxy not found"
        fi
        
        # Check for ansible-lint (optional)
        if command -v ansible-lint >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} ansible-lint available"
        else
            echo -e "${YELLOW}!${NC} ansible-lint not installed (recommended for validation)"
        fi
    else
        echo -e "${RED}✗${NC} Ansible not installed"
        return 1
    fi
}

# Main validation
main() {
    local exit_code=0
    
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Check Ansible installation
    check_ansible || exit_code=1
    
    # Check essential files
    echo -e "\n${YELLOW}Checking essential configuration files...${NC}"
    check_file "ansible.cfg" "Main Ansible configuration" || exit_code=1
    check_file "ansible-production.cfg" "Production Ansible configuration" || exit_code=1
    check_file "ansible-staging.cfg" "Staging Ansible configuration" || exit_code=1
    check_file "requirements.yml" "Galaxy requirements" || exit_code=1
    check_file ".gitignore" "Git ignore file" || exit_code=1
    
    # Validate configurations
    validate_ansible_config "ansible.cfg" "Default" || exit_code=1
    validate_ansible_config "ansible-production.cfg" "Production" || exit_code=1
    validate_ansible_config "ansible-staging.cfg" "Staging" || exit_code=1
    
    # Validate requirements
    validate_requirements || exit_code=1
    
    # Validate inventory
    validate_inventory || exit_code=1
    
    # Summary
    echo -e "\n${YELLOW}=== Validation Summary ===${NC}"
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✓ All validations passed successfully!${NC}"
        echo -e "${GREEN}✓ Configuration foundation is ready for production deployment${NC}"
    else
        echo -e "${RED}✗ Some validations failed. Please review the issues above.${NC}"
    fi
    
    return $exit_code
}

# Run main function
main "$@"