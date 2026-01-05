#!/usr/bin/env python3
"""
Advanced Inventory Validation and Consistency Checking Script
Validates VPN infrastructure inventory for completeness, consistency, and compliance
"""

import json
import yaml
import sys
import os
import argparse
import ipaddress
import re
from typing import Dict, List, Any, Tuple, Set
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InventoryValidator:
    def __init__(self, inventory_path: str = None, config_path: str = None):
        self.inventory_path = inventory_path or 'inventories/production'
        self.config_path = config_path or 'inventories/validation-config.yml'
        self.validation_results = {
            'passed': [],
            'warnings': [],
            'errors': [],
            'critical': []
        }
        self.config = self.load_validation_config()
        
    def load_validation_config(self) -> Dict[str, Any]:
        """Load validation configuration"""
        default_config = {
            'required_groups': [
                'vpn_servers',
                'wireguard_servers',
                'openvpn_servers',
                'europe',
                'north_america',
                'asia_pacific'
            ],
            'required_host_vars': [
                'ansible_host',
                'server_region',
                'server_protocols',
                'server_capacity'
            ],
            'capacity_limits': {
                'min': 10,
                'max': 1000,
                'recommended_max': 500
            },
            'ip_ranges': {
                'allowed_public': [
                    '0.0.0.0/0'  # Allow all public IPs by default
                ],
                'allowed_private': [
                    '10.0.0.0/8',
                    '172.16.0.0/12',
                    '192.168.0.0/16'
                ]
            },
            'protocols': {
                'supported': ['wireguard', 'openvpn', 'amneziawg'],
                'required': ['wireguard']
            },
            'regions': {
                'supported': ['europe', 'north_america', 'asia_pacific', 'south_america'],
                'required': ['europe', 'north_america', 'asia_pacific']
            },
            'naming_conventions': {
                'hostname_pattern': r'^[a-z0-9-]+\.(example\.com|vpn\.local)$',
                'group_pattern': r'^[a-z_]+$'
            },
            'security_requirements': {
                'ssh_key_required': True,
                'firewall_required': True,
                'monitoring_required': True
            }
        }
        
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            return default_config
    
    def load_inventory(self) -> Dict[str, Any]:
        """Load inventory from file or dynamic script"""
        if os.path.isfile(self.inventory_path):
            # Static inventory file
            with open(self.inventory_path, 'r') as f:
                if self.inventory_path.endswith('.yml') or self.inventory_path.endswith('.yaml'):
                    return yaml.safe_load(f)
                else:
                    # Assume INI format, convert to dict
                    return self.parse_ini_inventory(f.read())
        elif os.path.isfile(f"{self.inventory_path}.py"):
            # Dynamic inventory script
            import subprocess
            result = subprocess.run([f"{self.inventory_path}.py", "--list"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                raise Exception(f"Dynamic inventory script failed: {result.stderr}")
        else:
            raise FileNotFoundError(f"Inventory not found: {self.inventory_path}")
    
    def parse_ini_inventory(self, content: str) -> Dict[str, Any]:
        """Parse INI format inventory into dict format"""
        inventory = {'_meta': {'hostvars': {}}}
        current_group = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                current_group = line[1:-1]
                if ':vars' not in current_group and ':children' not in current_group:
                    inventory[current_group] = {'hosts': []}
            elif current_group and '=' in line:
                # Variable assignment
                key, value = line.split('=', 1)
                # Handle group vars or host vars
                pass  # Simplified for now
            elif current_group and line:
                # Host entry
                hostname = line.split()[0]
                inventory[current_group]['hosts'].append(hostname)
        
        return inventory
    
    def validate_inventory_structure(self, inventory: Dict[str, Any]) -> None:
        """Validate basic inventory structure"""
        
        # Check for required groups
        for group in self.config['required_groups']:
            if group not in inventory:
                self.validation_results['errors'].append(
                    f"Required group '{group}' not found in inventory"
                )
            else:
                self.validation_results['passed'].append(
                    f"Required group '{group}' found"
                )
        
        # Check for _meta section
        if '_meta' not in inventory:
            self.validation_results['errors'].append("Missing '_meta' section in inventory")
        elif 'hostvars' not in inventory['_meta']:
            self.validation_results['errors'].append("Missing 'hostvars' in _meta section")
        else:
            self.validation_results['passed'].append("Inventory structure is valid")
    
    def validate_hosts(self, inventory: Dict[str, Any]) -> None:
        """Validate individual hosts"""
        
        if '_meta' not in inventory or 'hostvars' not in inventory['_meta']:
            self.validation_results['critical'].append("Cannot validate hosts: missing hostvars")
            return
        
        hostvars = inventory['_meta']['hostvars']
        all_hosts = set()
        
        # Collect all hosts from groups
        for group_name, group_data in inventory.items():
            if group_name == '_meta':
                continue
            if isinstance(group_data, dict) and 'hosts' in group_data:
                all_hosts.update(group_data['hosts'])
        
        # Validate each host
        for hostname in all_hosts:
            self.validate_single_host(hostname, hostvars.get(hostname, {}))
        
        # Check for orphaned hostvars
        hostvar_hosts = set(hostvars.keys())
        orphaned = hostvar_hosts - all_hosts
        if orphaned:
            self.validation_results['warnings'].append(
                f"Orphaned host variables found for: {', '.join(orphaned)}"
            )
    
    def validate_single_host(self, hostname: str, host_vars: Dict[str, Any]) -> None:
        """Validate a single host configuration"""
        
        # Check hostname format
        if not re.match(self.config['naming_conventions']['hostname_pattern'], hostname):
            self.validation_results['warnings'].append(
                f"Host '{hostname}' doesn't match naming convention"
            )
        
        # Check required host variables
        for var in self.config['required_host_vars']:
            if var not in host_vars:
                self.validation_results['errors'].append(
                    f"Host '{hostname}' missing required variable '{var}'"
                )
        
        # Validate IP addresses
        if 'ansible_host' in host_vars:
            self.validate_ip_address(hostname, host_vars['ansible_host'])
        
        # Validate capacity
        if 'server_capacity' in host_vars:
            self.validate_capacity(hostname, host_vars['server_capacity'])
        
        # Validate protocols
        if 'server_protocols' in host_vars:
            self.validate_protocols(hostname, host_vars['server_protocols'])
        
        # Validate region
        if 'server_region' in host_vars:
            self.validate_region(hostname, host_vars['server_region'])
        
        # Check security requirements
        self.validate_security_config(hostname, host_vars)
    
    def validate_ip_address(self, hostname: str, ip_addr: str) -> None:
        """Validate IP address format and ranges"""
        try:
            ip = ipaddress.ip_address(ip_addr)
            
            # Check if IP is in allowed ranges
            if ip.is_private:
                allowed = any(ip in ipaddress.ip_network(net) 
                            for net in self.config['ip_ranges']['allowed_private'])
                if not allowed:
                    self.validation_results['warnings'].append(
                        f"Host '{hostname}' has private IP outside allowed ranges: {ip_addr}"
                    )
            else:
                # Public IP validation could be added here
                self.validation_results['passed'].append(
                    f"Host '{hostname}' has valid public IP: {ip_addr}"
                )
                
        except ValueError:
            self.validation_results['errors'].append(
                f"Host '{hostname}' has invalid IP address: {ip_addr}"
            )
    
    def validate_capacity(self, hostname: str, capacity: Any) -> None:
        """Validate server capacity configuration"""
        try:
            cap = int(capacity)
            limits = self.config['capacity_limits']
            
            if cap < limits['min']:
                self.validation_results['errors'].append(
                    f"Host '{hostname}' capacity {cap} below minimum {limits['min']}"
                )
            elif cap > limits['max']:
                self.validation_results['errors'].append(
                    f"Host '{hostname}' capacity {cap} above maximum {limits['max']}"
                )
            elif cap > limits['recommended_max']:
                self.validation_results['warnings'].append(
                    f"Host '{hostname}' capacity {cap} above recommended maximum {limits['recommended_max']}"
                )
            else:
                self.validation_results['passed'].append(
                    f"Host '{hostname}' has valid capacity: {cap}"
                )
                
        except (ValueError, TypeError):
            self.validation_results['errors'].append(
                f"Host '{hostname}' has invalid capacity value: {capacity}"
            )
    
    def validate_protocols(self, hostname: str, protocols: Any) -> None:
        """Validate VPN protocols configuration"""
        if isinstance(protocols, str):
            protocols = [protocols]
        elif not isinstance(protocols, list):
            self.validation_results['errors'].append(
                f"Host '{hostname}' protocols must be string or list: {protocols}"
            )
            return
        
        supported = self.config['protocols']['supported']
        required = self.config['protocols']['required']
        
        # Check for unsupported protocols
        unsupported = set(protocols) - set(supported)
        if unsupported:
            self.validation_results['errors'].append(
                f"Host '{hostname}' has unsupported protocols: {', '.join(unsupported)}"
            )
        
        # Check for required protocols
        missing_required = set(required) - set(protocols)
        if missing_required:
            self.validation_results['warnings'].append(
                f"Host '{hostname}' missing recommended protocols: {', '.join(missing_required)}"
            )
        
        if not unsupported and not missing_required:
            self.validation_results['passed'].append(
                f"Host '{hostname}' has valid protocols: {', '.join(protocols)}"
            )
    
    def validate_region(self, hostname: str, region: str) -> None:
        """Validate region configuration"""
        supported = self.config['regions']['supported']
        
        if region not in supported:
            self.validation_results['errors'].append(
                f"Host '{hostname}' has unsupported region: {region}"
            )
        else:
            self.validation_results['passed'].append(
                f"Host '{hostname}' has valid region: {region}"
            )
    
    def validate_security_config(self, hostname: str, host_vars: Dict[str, Any]) -> None:
        """Validate security configuration"""
        security_req = self.config['security_requirements']
        
        # Check SSH key requirement
        if security_req['ssh_key_required']:
            ssh_key_vars = ['ansible_ssh_private_key_file', 'ansible_ssh_key_file']
            if not any(var in host_vars for var in ssh_key_vars):
                self.validation_results['warnings'].append(
                    f"Host '{hostname}' missing SSH key configuration"
                )
        
        # Check monitoring requirement
        if security_req['monitoring_required']:
            if not host_vars.get('monitoring_enabled', False):
                self.validation_results['warnings'].append(
                    f"Host '{hostname}' monitoring not enabled"
                )
    
    def validate_group_consistency(self, inventory: Dict[str, Any]) -> None:
        """Validate consistency across groups"""
        
        # Check for duplicate hosts across exclusive groups
        exclusive_groups = [
            ['wireguard_servers', 'openvpn_servers'],  # Can overlap
            ['europe', 'north_america', 'asia_pacific']  # Should not overlap
        ]
        
        for group_set in exclusive_groups:
            if group_set == ['wireguard_servers', 'openvpn_servers']:
                continue  # Allow protocol overlap
                
            hosts_in_groups = {}
            for group in group_set:
                if group in inventory and 'hosts' in inventory[group]:
                    hosts_in_groups[group] = set(inventory[group]['hosts'])
            
            # Check for overlaps in regional groups
            if len(hosts_in_groups) > 1:
                all_hosts = set()
                for group, hosts in hosts_in_groups.items():
                    overlaps = all_hosts & hosts
                    if overlaps:
                        self.validation_results['errors'].append(
                            f"Hosts in multiple exclusive groups: {', '.join(overlaps)}"
                        )
                    all_hosts.update(hosts)
    
    def validate_regional_distribution(self, inventory: Dict[str, Any]) -> None:
        """Validate regional distribution of servers"""
        regional_groups = ['europe', 'north_america', 'asia_pacific']
        region_counts = {}
        
        for region in regional_groups:
            if region in inventory and 'hosts' in inventory[region]:
                region_counts[region] = len(inventory[region]['hosts'])
            else:
                region_counts[region] = 0
        
        total_servers = sum(region_counts.values())
        if total_servers == 0:
            self.validation_results['critical'].append("No servers found in any region")
            return
        
        # Check for balanced distribution (within 50% of average)
        avg_per_region = total_servers / len(regional_groups)
        for region, count in region_counts.items():
            if count == 0:
                self.validation_results['warnings'].append(f"No servers in region: {region}")
            elif count < avg_per_region * 0.5:
                self.validation_results['warnings'].append(
                    f"Region '{region}' has low server count: {count} (avg: {avg_per_region:.1f})"
                )
            elif count > avg_per_region * 1.5:
                self.validation_results['warnings'].append(
                    f"Region '{region}' has high server count: {count} (avg: {avg_per_region:.1f})"
                )
    
    def validate_capacity_distribution(self, inventory: Dict[str, Any]) -> None:
        """Validate capacity distribution across servers"""
        if '_meta' not in inventory or 'hostvars' not in inventory['_meta']:
            return
        
        capacities = []
        for hostname, host_vars in inventory['_meta']['hostvars'].items():
            if 'server_capacity' in host_vars:
                try:
                    capacities.append(int(host_vars['server_capacity']))
                except (ValueError, TypeError):
                    continue
        
        if not capacities:
            self.validation_results['warnings'].append("No capacity information found")
            return
        
        total_capacity = sum(capacities)
        avg_capacity = total_capacity / len(capacities)
        
        self.validation_results['passed'].append(
            f"Total infrastructure capacity: {total_capacity} connections"
        )
        self.validation_results['passed'].append(
            f"Average server capacity: {avg_capacity:.1f} connections"
        )
        
        # Check for capacity outliers
        for i, capacity in enumerate(capacities):
            if capacity < avg_capacity * 0.3:
                self.validation_results['warnings'].append(
                    f"Server has very low capacity: {capacity} (avg: {avg_capacity:.1f})"
                )
            elif capacity > avg_capacity * 3:
                self.validation_results['warnings'].append(
                    f"Server has very high capacity: {capacity} (avg: {avg_capacity:.1f})"
                )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'inventory_path': self.inventory_path,
            'validation_summary': {
                'total_checks': sum(len(v) for v in self.validation_results.values()),
                'passed': len(self.validation_results['passed']),
                'warnings': len(self.validation_results['warnings']),
                'errors': len(self.validation_results['errors']),
                'critical': len(self.validation_results['critical'])
            },
            'results': self.validation_results,
            'status': self.get_overall_status()
        }
        
        return report
    
    def get_overall_status(self) -> str:
        """Determine overall validation status"""
        if self.validation_results['critical']:
            return 'CRITICAL'
        elif self.validation_results['errors']:
            return 'FAILED'
        elif self.validation_results['warnings']:
            return 'WARNING'
        else:
            return 'PASSED'
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete inventory validation"""
        try:
            logger.info(f"Loading inventory from: {self.inventory_path}")
            inventory = self.load_inventory()
            
            logger.info("Validating inventory structure...")
            self.validate_inventory_structure(inventory)
            
            logger.info("Validating hosts...")
            self.validate_hosts(inventory)
            
            logger.info("Validating group consistency...")
            self.validate_group_consistency(inventory)
            
            logger.info("Validating regional distribution...")
            self.validate_regional_distribution(inventory)
            
            logger.info("Validating capacity distribution...")
            self.validate_capacity_distribution(inventory)
            
            report = self.generate_report()
            logger.info(f"Validation completed with status: {report['status']}")
            
            return report
            
        except Exception as e:
            self.validation_results['critical'].append(f"Validation failed: {str(e)}")
            return self.generate_report()

def main():
    parser = argparse.ArgumentParser(description='VPN Infrastructure Inventory Validator')
    parser.add_argument('--inventory', '-i', help='Path to inventory file or script')
    parser.add_argument('--config', '-c', help='Path to validation config file')
    parser.add_argument('--output', '-o', help='Output file for validation report')
    parser.add_argument('--format', choices=['json', 'yaml', 'text'], default='text',
                       help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = InventoryValidator(args.inventory, args.config)
    report = validator.run_validation()
    
    # Format output
    if args.format == 'json':
        output = json.dumps(report, indent=2)
    elif args.format == 'yaml':
        output = yaml.dump(report, default_flow_style=False)
    else:  # text format
        output = format_text_report(report)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Validation report written to: {args.output}")
    else:
        print(output)
    
    # Exit with appropriate code
    status = report['status']
    if status == 'CRITICAL':
        sys.exit(2)
    elif status == 'FAILED':
        sys.exit(1)
    elif status == 'WARNING':
        sys.exit(0)  # Warnings don't fail the validation
    else:
        sys.exit(0)

def format_text_report(report: Dict[str, Any]) -> str:
    """Format validation report as human-readable text"""
    lines = []
    lines.append("VPN Infrastructure Inventory Validation Report")
    lines.append("=" * 50)
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append(f"Inventory: {report['inventory_path']}")
    lines.append(f"Status: {report['status']}")
    lines.append("")
    
    summary = report['validation_summary']
    lines.append("Summary:")
    lines.append(f"  Total Checks: {summary['total_checks']}")
    lines.append(f"  Passed: {summary['passed']}")
    lines.append(f"  Warnings: {summary['warnings']}")
    lines.append(f"  Errors: {summary['errors']}")
    lines.append(f"  Critical: {summary['critical']}")
    lines.append("")
    
    results = report['results']
    
    if results['critical']:
        lines.append("CRITICAL ISSUES:")
        for issue in results['critical']:
            lines.append(f"  ❌ {issue}")
        lines.append("")
    
    if results['errors']:
        lines.append("ERRORS:")
        for error in results['errors']:
            lines.append(f"  ❌ {error}")
        lines.append("")
    
    if results['warnings']:
        lines.append("WARNINGS:")
        for warning in results['warnings']:
            lines.append(f"  ⚠️  {warning}")
        lines.append("")
    
    if results['passed']:
        lines.append("PASSED CHECKS:")
        for passed in results['passed']:
            lines.append(f"  ✅ {passed}")
    
    return "\n".join(lines)

if __name__ == '__main__':
    main()