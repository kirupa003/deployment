#!/usr/bin/env python3
"""
Inventory validation script for VPN infrastructure
Validates the Ansible inventory structure without requiring Ansible to be installed
"""

import os
import sys
import yaml
import re
from pathlib import Path

def load_inventory_file(inventory_path):
    """Parse Ansible inventory file and return structured data"""
    inventory = {
        'groups': {},
        'hosts': {},
        'group_children': {},
        'group_vars': {}
    }
    
    current_group = None
    
    with open(inventory_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Group definition
            if line.startswith('[') and line.endswith(']'):
                group_name = line[1:-1]
                
                # Check for children groups
                if ':children' in group_name:
                    parent_group = group_name.replace(':children', '')
                    current_group = parent_group
                    inventory['group_children'][parent_group] = []
                else:
                    current_group = group_name
                    inventory['groups'][current_group] = []
                continue
            
            # Host or child group definition
            if current_group:
                if current_group in inventory['group_children']:
                    # This is a child group
                    inventory['group_children'][current_group].append(line)
                else:
                    # This is a host
                    host_parts = line.split()
                    hostname = host_parts[0]
                    host_vars = {}
                    
                    # Parse host variables
                    for part in host_parts[1:]:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            host_vars[key] = value
                    
                    inventory['groups'][current_group].append(hostname)
                    inventory['hosts'][hostname] = host_vars
    
    return inventory

def validate_inventory_structure():
    """Validate the complete inventory structure"""
    print("=== VPN Infrastructure Inventory Validation ===")
    print()
    
    # Check if inventory file exists
    inventory_path = Path("inventories/production")
    if not inventory_path.exists():
        print(f"❌ ERROR: Inventory file not found: {inventory_path}")
        return False
    
    print("✅ Inventory file found")
    
    # Load and parse inventory
    try:
        inventory = load_inventory_file(inventory_path)
        print("✅ Inventory parsed successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to parse inventory: {e}")
        return False
    
    # Check required groups
    print("🔍 Checking required inventory groups...")
    required_groups = [
        "vpn_servers", "wireguard_servers", "openvpn_servers",
        "europe", "north_america", "asia_pacific"
    ]
    
    all_groups = set(inventory['groups'].keys()) | set(inventory['group_children'].keys())
    
    for group in required_groups:
        if group in all_groups:
            print(f"✅ Group '{group}' found")
        else:
            print(f"❌ ERROR: Required group '{group}' not found")
            return False
    
    # Count servers by region
    print("🔍 Counting servers by region...")
    regions = ["europe", "north_america", "asia_pacific"]
    
    def count_hosts_in_group(group_name, inventory):
        """Recursively count hosts in a group including children"""
        total_hosts = set()
        
        # Add direct hosts
        if group_name in inventory['groups']:
            total_hosts.update(inventory['groups'][group_name])
        
        # Add hosts from child groups
        if group_name in inventory['group_children']:
            for child_group in inventory['group_children'][group_name]:
                child_hosts = count_hosts_in_group(child_group, inventory)
                total_hosts.update(child_hosts)
        
        return total_hosts
    
    total_servers = 0
    for region in regions:
        hosts = count_hosts_in_group(region, inventory)
        count = len(hosts)
        total_servers += count
        
        if count == 10:
            print(f"✅ Region '{region}': {count} servers (expected: 10)")
        else:
            print(f"❌ ERROR: Region '{region}': {count} servers (expected: 10)")
            return False
    
    # Count servers by protocol
    print("🔍 Counting servers by protocol...")
    wg_hosts = count_hosts_in_group("wireguard_servers", inventory)
    ovpn_hosts = count_hosts_in_group("openvpn_servers", inventory)
    
    print(f"✅ WireGuard servers: {len(wg_hosts)}")
    print(f"✅ OpenVPN servers: {len(ovpn_hosts)}")
    
    if total_servers == 30:
        print(f"✅ Total VPN servers: {total_servers} (expected: 30)")
    else:
        print(f"❌ ERROR: Total VPN servers: {total_servers} (expected: 30)")
        return False
    
    # Check group_vars files
    print("🔍 Checking group_vars files...")
    group_vars_files = [
        "inventories/group_vars/all.yml",
        "inventories/group_vars/vpn_servers.yml",
        "inventories/group_vars/wireguard_servers.yml",
        "inventories/group_vars/openvpn_servers.yml",
        "inventories/group_vars/europe.yml",
        "inventories/group_vars/north_america.yml",
        "inventories/group_vars/asia_pacific.yml"
    ]
    
    for file_path in group_vars_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ Found: {file_path}")
            try:
                with open(path, 'r') as f:
                    yaml.safe_load(f)
                print(f"  ✅ Valid YAML syntax")
            except yaml.YAMLError as e:
                print(f"  ❌ ERROR: Invalid YAML syntax in {file_path}: {e}")
                return False
        else:
            print(f"❌ ERROR: Missing group_vars file: {file_path}")
            return False
    
    # Check host_vars examples
    print("🔍 Checking host_vars examples...")
    host_vars_examples = [
        "inventories/host_vars/eu-vpn-wg-01.example.com.yml",
        "inventories/host_vars/na-vpn-wg-01.example.com.yml",
        "inventories/host_vars/ap-vpn-wg-01.example.com.yml",
        "inventories/host_vars/eu-vpn-ovpn-01.example.com.yml"
    ]
    
    for file_path in host_vars_examples:
        path = Path(file_path)
        if path.exists():
            print(f"✅ Found: {file_path}")
            try:
                with open(path, 'r') as f:
                    yaml.safe_load(f)
                print(f"  ✅ Valid YAML syntax")
            except yaml.YAMLError as e:
                print(f"  ❌ ERROR: Invalid YAML syntax in {file_path}: {e}")
                return False
        else:
            print(f"❌ ERROR: Missing host_vars example: {file_path}")
            return False
    
    print()
    print("🎉 Inventory validation completed successfully!")
    print("📊 Summary:")
    print("   - Total servers: 30")
    print("   - Regions: 3 (10 servers each)")
    print(f"   - Protocols: WireGuard ({len(wg_hosts)}), OpenVPN ({len(ovpn_hosts)})")
    print("   - Group variables: 7 files")
    print("   - Host variables: 4 example files")
    print()
    
    return True

if __name__ == "__main__":
    success = validate_inventory_structure()
    sys.exit(0 if success else 1)