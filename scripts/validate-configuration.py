#!/usr/bin/env python3
"""
Configuration Validation Script for VPN Infrastructure
Validates Ansible configuration files, templates, and variable consistency
"""

import os
import sys
import yaml
import json
import argparse
import ipaddress
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re
from jinja2 import Environment, FileSystemLoader, TemplateError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigurationValidator:
    """Validates VPN infrastructure configuration files"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.errors = []
        self.warnings = []
        self.inventory_path = self.base_path / "inventories"
        self.roles_path = self.base_path / "roles"
        self.playbooks_path = self.base_path / "playbooks"
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        logger.info("Starting comprehensive configuration validation...")
        
        # Validate YAML syntax
        self.validate_yaml_files()
        
        # Validate inventory structure
        self.validate_inventory_structure()
        
        # Validate variable consistency
        self.validate_variable_consistency()
        
        # Validate network configurations
        self.validate_network_configs()
        
        # Validate template syntax
        self.validate_template_syntax()
        
        # Validate role dependencies
        self.validate_role_dependencies()
        
        # Validate security configurations
        self.validate_security_configs()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def validate_yaml_files(self):
        """Validate YAML syntax in all configuration files"""
        logger.info("Validating YAML syntax...")
        
        yaml_patterns = [
            "inventories/**/*.yml",
            "inventories/**/*.yaml", 
            "playbooks/**/*.yml",
            "playbooks/**/*.yaml",
            "roles/**/defaults/*.yml",
            "roles/**/vars/*.yml",
            "roles/**/meta/*.yml"
        ]
        
        for pattern in yaml_patterns:
            for yaml_file in self.base_path.glob(pattern):
                try:
                    with open(yaml_file, 'r') as f:
                        yaml.safe_load(f)
                    logger.debug(f"✓ Valid YAML: {yaml_file}")
                except yaml.YAMLError as e:
                    self.errors.append(f"Invalid YAML in {yaml_file}: {e}")
                except Exception as e:
                    self.errors.append(f"Error reading {yaml_file}: {e}")
    
    def validate_inventory_structure(self):
        """Validate inventory structure and required files"""
        logger.info("Validating inventory structure...")
        
        required_files = [
            "inventories/production",
            "inventories/group_vars/all.yml",
            "inventories/group_vars/vpn_servers.yml"
        ]
        
        for required_file in required_files:
            file_path = self.base_path / required_file
            if not file_path.exists():
                self.errors.append(f"Missing required file: {required_file}")
        
        # Validate inventory file format
        inventory_file = self.base_path / "inventories/production"
        if inventory_file.exists():
            try:
                with open(inventory_file, 'r') as f:
                    content = f.read()
                    
                # Check for required groups
                required_groups = ['vpn_servers', 'wireguard_servers', 'openvpn_servers']
                for group in required_groups:
                    if f"[{group}]" not in content:
                        self.warnings.append(f"Missing inventory group: {group}")
                        
            except Exception as e:
                self.errors.append(f"Error reading inventory file: {e}")
    
    def validate_variable_consistency(self):
        """Validate variable consistency across group_vars and host_vars"""
        logger.info("Validating variable consistency...")
        
        # Load all group variables
        group_vars = {}
        group_vars_path = self.inventory_path / "group_vars"
        
        if group_vars_path.exists():
            for var_file in group_vars_path.glob("*.yml"):
                try:
                    with open(var_file, 'r') as f:
                        vars_data = yaml.safe_load(f) or {}
                        group_vars[var_file.stem] = vars_data
                except Exception as e:
                    self.errors.append(f"Error loading group vars {var_file}: {e}")
        
        # Validate required variables
        required_vars = {
            'all': ['ansible_user', 'ssh_port', 'timezone'],
            'vpn_servers': ['max_concurrent_connections', 'dns_servers'],
            'wireguard_servers': ['wireguard_port'],
            'openvpn_servers': ['openvpn_port_udp', 'openvpn_port_tcp']
        }
        
        for group, vars_list in required_vars.items():
            if group in group_vars:
                for var in vars_list:
                    if var not in group_vars[group]:
                        self.warnings.append(f"Missing variable '{var}' in group '{group}'")
    
    def validate_network_configs(self):
        """Validate network configuration consistency"""
        logger.info("Validating network configurations...")
        
        # Load network configurations
        try:
            with open(self.inventory_path / "group_vars/vpn_servers.yml", 'r') as f:
                vpn_config = yaml.safe_load(f) or {}
        except:
            return
        
        # Validate DNS servers
        dns_servers = vpn_config.get('dns_servers', [])
        for dns_server in dns_servers:
            try:
                ipaddress.ip_address(dns_server)
            except ValueError:
                self.errors.append(f"Invalid DNS server IP: {dns_server}")
        
        # Validate port ranges
        port_configs = [
            ('wireguard_port', 1024, 65535),
            ('openvpn_port_udp', 1024, 65535),
            ('openvpn_port_tcp', 1024, 65535),
            ('coredns_port', 1, 65535),
            ('node_exporter_port', 1024, 65535)
        ]
        
        for port_var, min_port, max_port in port_configs:
            if port_var in vpn_config:
                port = vpn_config[port_var]
                if not isinstance(port, int) or port < min_port or port > max_port:
                    self.errors.append(f"Invalid port {port_var}: {port} (must be {min_port}-{max_port})")
    
    def validate_template_syntax(self):
        """Validate Jinja2 template syntax"""
        logger.info("Validating template syntax...")
        
        template_paths = [
            self.inventory_path / "templates",
            self.roles_path
        ]
        
        for template_path in template_paths:
            if not template_path.exists():
                continue
                
            for template_file in template_path.rglob("*.j2"):
                try:
                    # Load template directory
                    template_dir = template_file.parent
                    env = Environment(loader=FileSystemLoader(str(template_dir)))
                    
                    # Parse template
                    template = env.get_template(template_file.name)
                    
                    # Basic syntax validation (without rendering)
                    template.environment.parse(template.source)
                    logger.debug(f"✓ Valid template: {template_file}")
                    
                except TemplateError as e:
                    self.errors.append(f"Template syntax error in {template_file}: {e}")
                except Exception as e:
                    self.errors.append(f"Error validating template {template_file}: {e}")
    
    def validate_role_dependencies(self):
        """Validate role dependencies and meta information"""
        logger.info("Validating role dependencies...")
        
        if not self.roles_path.exists():
            return
        
        for role_dir in self.roles_path.iterdir():
            if not role_dir.is_dir():
                continue
                
            meta_file = role_dir / "meta" / "main.yml"
            if meta_file.exists():
                try:
                    with open(meta_file, 'r') as f:
                        meta_data = yaml.safe_load(f) or {}
                    
                    # Validate dependencies
                    dependencies = meta_data.get('dependencies', [])
                    for dep in dependencies:
                        if isinstance(dep, dict):
                            dep_name = dep.get('name') or dep.get('role')
                        else:
                            dep_name = dep
                        
                        if dep_name:
                            dep_path = self.roles_path / dep_name
                            if not dep_path.exists():
                                self.warnings.append(f"Role dependency not found: {dep_name} (required by {role_dir.name})")
                                
                except Exception as e:
                    self.errors.append(f"Error validating role meta {role_dir.name}: {e}")
    
    def validate_security_configs(self):
        """Validate security-related configurations"""
        logger.info("Validating security configurations...")
        
        # Check for vault password file
        vault_pass_file = self.base_path / ".vault_pass"
        if not vault_pass_file.exists():
            self.warnings.append("Vault password file (.vault_pass) not found")
        
        # Validate SSH configuration
        try:
            with open(self.inventory_path / "group_vars/all.yml", 'r') as f:
                all_vars = yaml.safe_load(f) or {}
            
            # Check SSH security settings
            ssh_port = all_vars.get('ssh_port', 22)
            if ssh_port == 22:
                self.warnings.append("SSH running on default port 22 - consider changing for security")
            
            # Check for SSH key configuration
            if 'ansible_ssh_private_key_file' not in all_vars:
                self.warnings.append("SSH private key file not configured")
            
            # Check firewall policy
            firewall_policy = all_vars.get('ufw_default_policy', {})
            if firewall_policy.get('incoming') != 'deny':
                self.warnings.append("Firewall default incoming policy should be 'deny'")
                
        except Exception as e:
            self.errors.append(f"Error validating security configs: {e}")
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("CONFIGURATION VALIDATION RESULTS")
        print("="*60)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All configuration validations passed!")
        elif not self.errors:
            print(f"\n✅ No errors found, but {len(self.warnings)} warnings to review")
        else:
            print(f"\n❌ Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings")
        
        print("="*60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Validate VPN infrastructure configuration")
    parser.add_argument("--path", "-p", default=".", help="Base path to validate (default: current directory)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = ConfigurationValidator(args.path)
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()