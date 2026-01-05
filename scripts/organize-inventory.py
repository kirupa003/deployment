#!/usr/bin/env python3
"""
Inventory Organization and Server Grouping Script
Automatically organizes VPN servers into logical groups based on various criteria
"""

import json
import yaml
import sys
import os
import argparse
from typing import Dict, List, Any, Set
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InventoryOrganizer:
    def __init__(self, inventory_path: str = None, config_path: str = None):
        self.inventory_path = inventory_path or 'inventories/production'
        self.config_path = config_path or 'inventories/organization-config.yml'
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load organization configuration"""
        default_config = {
            'grouping_strategies': {
                'by_region': {
                    'enabled': True,
                    'prefix': '',
                    'mapping': {
                        'us-east-1': 'north_america',
                        'us-west-2': 'north_america',
                        'eu-west-1': 'europe',
                        'eu-central-1': 'europe',
                        'ap-southeast-1': 'asia_pacific',
                        'ap-northeast-1': 'asia_pacific'
                    }
                },
                'by_protocol': {
                    'enabled': True,
                    'prefix': '',
                    'suffix': '_servers'
                },
                'by_capacity': {
                    'enabled': True,
                    'prefix': 'capacity_',
                    'tiers': {
                        'small': {'min': 1, 'max': 50},
                        'medium': {'min': 51, 'max': 100},
                        'large': {'min': 101, 'max': 200},
                        'xlarge': {'min': 201, 'max': 500}
                    }
                },
                'by_provider': {
                    'enabled': True,
                    'prefix': '',
                    'suffix': '_servers'
                },
                'by_environment': {
                    'enabled': True,
                    'prefix': 'env_'
                },
                'by_server_type': {
                    'enabled': True,
                    'prefix': 'type_'
                }
            },
            'group_vars': {
                'apply_regional_vars': True,
                'apply_protocol_vars': True,
                'apply_capacity_vars': True
            },
            'optimization': {
                'remove_empty_groups': True,
                'merge_similar_groups': False,
                'sort_hosts': True
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
        """Load existing inventory"""
        if os.path.isfile(self.inventory_path):
            with open(self.inventory_path, 'r') as f:
                if self.inventory_path.endswith(('.yml', '.yaml')):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        else:
            # Create empty inventory structure
            return {
                '_meta': {'hostvars': {}},
                'all': {'children': []}
            }
    
    def extract_hosts_info(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract host information for organization"""
        hosts_info = []
        
        if '_meta' not in inventory or 'hostvars' not in inventory['_meta']:
            logger.warning("No hostvars found in inventory")
            return hosts_info
        
        hostvars = inventory['_meta']['hostvars']
        
        # Collect hosts from all groups
        all_hosts = set()
        for group_name, group_data in inventory.items():
            if group_name == '_meta':
                continue
            if isinstance(group_data, dict) and 'hosts' in group_data:
                all_hosts.update(group_data['hosts'])
        
        # Extract information for each host
        for hostname in all_hosts:
            host_vars = hostvars.get(hostname, {})
            
            host_info = {
                'hostname': hostname,
                'region': self.extract_region(host_vars),
                'protocols': self.extract_protocols(host_vars),
                'capacity': self.extract_capacity(host_vars),
                'provider': self.extract_provider(host_vars),
                'environment': self.extract_environment(host_vars),
                'server_type': self.extract_server_type(host_vars),
                'zone': host_vars.get('availability_zone', ''),
                'instance_type': host_vars.get('instance_type', ''),
                'tags': host_vars.get('cloud_tags', {}),
                'vars': host_vars
            }
            
            hosts_info.append(host_info)
        
        return hosts_info
    
    def extract_region(self, host_vars: Dict[str, Any]) -> str:
        """Extract region information from host vars"""
        # Try multiple possible region fields
        region_fields = ['server_region', 'region', 'aws_region', 'gcp_zone', 'azure_region']
        
        for field in region_fields:
            if field in host_vars:
                region = host_vars[field]
                # Map cloud regions to standard regions
                return self.config['grouping_strategies']['by_region']['mapping'].get(region, region)
        
        return 'unknown'
    
    def extract_protocols(self, host_vars: Dict[str, Any]) -> List[str]:
        """Extract VPN protocols from host vars"""
        protocols = host_vars.get('server_protocols', [])
        
        if isinstance(protocols, str):
            return [protocols]
        elif isinstance(protocols, list):
            return protocols
        else:
            return ['wireguard']  # Default protocol
    
    def extract_capacity(self, host_vars: Dict[str, Any]) -> int:
        """Extract server capacity from host vars"""
        capacity = host_vars.get('server_capacity', 100)
        try:
            return int(capacity)
        except (ValueError, TypeError):
            return 100
    
    def extract_provider(self, host_vars: Dict[str, Any]) -> str:
        """Extract cloud provider from host vars"""
        provider_fields = ['cloud_provider', 'provider', 'aws_provider', 'gcp_provider']
        
        for field in provider_fields:
            if field in host_vars:
                return host_vars[field]
        
        # Try to infer from instance type or other fields
        instance_type = host_vars.get('instance_type', '')
        if instance_type.startswith(('t2.', 't3.', 'm5.', 'c5.')):
            return 'aws'
        elif instance_type.startswith(('n1-', 'n2-', 'e2-')):
            return 'gcp'
        elif instance_type.startswith(('Standard_', 'Basic_')):
            return 'azure'
        
        return 'unknown'
    
    def extract_environment(self, host_vars: Dict[str, Any]) -> str:
        """Extract environment from host vars or tags"""
        # Check direct environment field
        if 'environment' in host_vars:
            return host_vars['environment']
        
        # Check cloud tags
        tags = host_vars.get('cloud_tags', {})
        env_fields = ['Environment', 'environment', 'Env', 'env']
        
        for field in env_fields:
            if field in tags:
                return tags[field].lower()
        
        return 'production'  # Default environment
    
    def extract_server_type(self, host_vars: Dict[str, Any]) -> str:
        """Extract server type from host vars"""
        server_type = host_vars.get('server_type', 'standard')
        
        # Infer from instance type if not explicitly set
        if server_type == 'standard':
            instance_type = host_vars.get('instance_type', '')
            if 'large' in instance_type or 'xlarge' in instance_type:
                return 'high_performance'
            elif 'small' in instance_type or 'micro' in instance_type:
                return 'basic'
        
        return server_type
    
    def create_organized_inventory(self, hosts_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create organized inventory with proper grouping"""
        inventory = {
            '_meta': {'hostvars': {}},
            'all': {'children': []}
        }
        
        # Initialize base groups
        base_groups = ['vpn_servers']
        for group in base_groups:
            inventory[group] = {'hosts': [], 'children': []}
        
        # Group hosts by various strategies
        groups_created = set(base_groups)
        
        for host_info in hosts_info:
            hostname = host_info['hostname']
            
            # Add to base group
            inventory['vpn_servers']['hosts'].append(hostname)
            
            # Store host vars
            inventory['_meta']['hostvars'][hostname] = host_info['vars']
            
            # Apply grouping strategies
            self.apply_regional_grouping(inventory, host_info, groups_created)
            self.apply_protocol_grouping(inventory, host_info, groups_created)
            self.apply_capacity_grouping(inventory, host_info, groups_created)
            self.apply_provider_grouping(inventory, host_info, groups_created)
            self.apply_environment_grouping(inventory, host_info, groups_created)
            self.apply_server_type_grouping(inventory, host_info, groups_created)
        
        # Apply group variables
        self.apply_group_variables(inventory)
        
        # Optimize inventory
        self.optimize_inventory(inventory)
        
        return inventory
    
    def apply_regional_grouping(self, inventory: Dict[str, Any], host_info: Dict[str, Any], 
                              groups_created: Set[str]) -> None:
        """Apply regional grouping strategy"""
        if not self.config['grouping_strategies']['by_region']['enabled']:
            return
        
        region = host_info['region']
        if region == 'unknown':
            return
        
        group_name = region
        
        if group_name not in groups_created:
            inventory[group_name] = {'hosts': [], 'vars': {}}
            groups_created.add(group_name)
        
        inventory[group_name]['hosts'].append(host_info['hostname'])
    
    def apply_protocol_grouping(self, inventory: Dict[str, Any], host_info: Dict[str, Any],
                               groups_created: Set[str]) -> None:
        """Apply protocol-based grouping strategy"""
        if not self.config['grouping_strategies']['by_protocol']['enabled']:
            return
        
        config = self.config['grouping_strategies']['by_protocol']
        
        for protocol in host_info['protocols']:
            group_name = f"{config.get('prefix', '')}{protocol}{config.get('suffix', '_servers')}"
            
            if group_name not in groups_created:
                inventory[group_name] = {'hosts': [], 'vars': {}}
                groups_created.add(group_name)
            
            inventory[group_name]['hosts'].append(host_info['hostname'])
    
    def apply_capacity_grouping(self, inventory: Dict[str, Any], host_info: Dict[str, Any],
                               groups_created: Set[str]) -> None:
        """Apply capacity-based grouping strategy"""
        if not self.config['grouping_strategies']['by_capacity']['enabled']:
            return
        
        config = self.config['grouping_strategies']['by_capacity']
        capacity = host_info['capacity']
        
        # Determine capacity tier
        tier = 'unknown'
        for tier_name, tier_config in config['tiers'].items():
            if tier_config['min'] <= capacity <= tier_config['max']:
                tier = tier_name
                break
        
        if tier != 'unknown':
            group_name = f"{config.get('prefix', 'capacity_')}{tier}"
            
            if group_name not in groups_created:
                inventory[group_name] = {'hosts': [], 'vars': {}}
                groups_created.add(group_name)
            
            inventory[group_name]['hosts'].append(host_info['hostname'])
    
    def apply_provider_grouping(self, inventory: Dict[str, Any], host_info: Dict[str, Any],
                               groups_created: Set[str]) -> None:
        """Apply cloud provider grouping strategy"""
        if not self.config['grouping_strategies']['by_provider']['enabled']:
            return
        
        provider = host_info['provider']
        if provider == 'unknown':
            return
        
        config = self.config['grouping_strategies']['by_provider']
        group_name = f"{config.get('prefix', '')}{provider}{config.get('suffix', '_servers')}"
        
        if group_name not in groups_created:
            inventory[group_name] = {'hosts': [], 'vars': {}}
            groups_created.add(group_name)
        
        inventory[group_name]['hosts'].append(host_info['hostname'])
    
    def apply_environment_grouping(self, inventory: Dict[str, Any], host_info: Dict[str, Any],
                                  groups_created: Set[str]) -> None:
        """Apply environment-based grouping strategy"""
        if not self.config['grouping_strategies']['by_environment']['enabled']:
            return
        
        environment = host_info['environment']
        config = self.config['grouping_strategies']['by_environment']
        group_name = f"{config.get('prefix', 'env_')}{environment}"
        
        if group_name not in groups_created:
            inventory[group_name] = {'hosts': [], 'vars': {}}
            groups_created.add(group_name)
        
        inventory[group_name]['hosts'].append(host_info['hostname'])
    
    def apply_server_type_grouping(self, inventory: Dict[str, Any], host_info: Dict[str, Any],
                                  groups_created: Set[str]) -> None:
        """Apply server type grouping strategy"""
        if not self.config['grouping_strategies']['by_server_type']['enabled']:
            return
        
        server_type = host_info['server_type']
        config = self.config['grouping_strategies']['by_server_type']
        group_name = f"{config.get('prefix', 'type_')}{server_type}"
        
        if group_name not in groups_created:
            inventory[group_name] = {'hosts': [], 'vars': {}}
            groups_created.add(group_name)
        
        inventory[group_name]['hosts'].append(host_info['hostname'])
    
    def apply_group_variables(self, inventory: Dict[str, Any]) -> None:
        """Apply appropriate variables to groups"""
        
        # Regional variables
        if self.config['group_vars']['apply_regional_vars']:
            regional_vars = {
                'europe': {
                    'ntp_servers': ['0.europe.pool.ntp.org', '1.europe.pool.ntp.org'],
                    'dns_servers': ['1.1.1.1', '8.8.8.8'],
                    'timezone': 'Europe/London'
                },
                'north_america': {
                    'ntp_servers': ['0.north-america.pool.ntp.org', '1.north-america.pool.ntp.org'],
                    'dns_servers': ['1.1.1.1', '8.8.8.8'],
                    'timezone': 'America/New_York'
                },
                'asia_pacific': {
                    'ntp_servers': ['0.asia.pool.ntp.org', '1.asia.pool.ntp.org'],
                    'dns_servers': ['1.1.1.1', '8.8.8.8'],
                    'timezone': 'Asia/Singapore'
                }
            }
            
            for region, vars_dict in regional_vars.items():
                if region in inventory:
                    inventory[region]['vars'].update(vars_dict)
        
        # Protocol variables
        if self.config['group_vars']['apply_protocol_vars']:
            protocol_vars = {
                'wireguard_servers': {
                    'wireguard_port': 51820,
                    'wireguard_dashboard_port': 10086,
                    'wireguard_interface': 'wg0'
                },
                'openvpn_servers': {
                    'openvpn_port': 1194,
                    'openvpn_protocol': 'udp',
                    'openvpn_cipher': 'AES-256-GCM'
                },
                'amneziawg_servers': {
                    'amneziawg_port': 51821,
                    'amneziawg_interface': 'awg0'
                }
            }
            
            for group, vars_dict in protocol_vars.items():
                if group in inventory:
                    inventory[group]['vars'].update(vars_dict)
    
    def optimize_inventory(self, inventory: Dict[str, Any]) -> None:
        """Optimize inventory structure"""
        
        # Remove empty groups
        if self.config['optimization']['remove_empty_groups']:
            empty_groups = []
            for group_name, group_data in inventory.items():
                if group_name == '_meta':
                    continue
                if isinstance(group_data, dict) and 'hosts' in group_data:
                    if not group_data['hosts']:
                        empty_groups.append(group_name)
            
            for group in empty_groups:
                del inventory[group]
                logger.info(f"Removed empty group: {group}")
        
        # Sort hosts in groups
        if self.config['optimization']['sort_hosts']:
            for group_name, group_data in inventory.items():
                if group_name == '_meta':
                    continue
                if isinstance(group_data, dict) and 'hosts' in group_data:
                    group_data['hosts'].sort()
    
    def save_inventory(self, inventory: Dict[str, Any], output_path: str) -> None:
        """Save organized inventory to file"""
        
        if output_path.endswith(('.yml', '.yaml')):
            with open(output_path, 'w') as f:
                yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)
        else:
            with open(output_path, 'w') as f:
                json.dump(inventory, f, indent=2, sort_keys=False)
        
        logger.info(f"Organized inventory saved to: {output_path}")
    
    def organize_inventory(self, output_path: str = None) -> Dict[str, Any]:
        """Main method to organize inventory"""
        
        logger.info(f"Loading inventory from: {self.inventory_path}")
        original_inventory = self.load_inventory()
        
        logger.info("Extracting host information...")
        hosts_info = self.extract_hosts_info(original_inventory)
        
        if not hosts_info:
            logger.warning("No hosts found in inventory")
            return original_inventory
        
        logger.info(f"Organizing {len(hosts_info)} hosts...")
        organized_inventory = self.create_organized_inventory(hosts_info)
        
        if output_path:
            self.save_inventory(organized_inventory, output_path)
        
        # Log organization summary
        group_count = len([g for g in organized_inventory.keys() if g != '_meta'])
        logger.info(f"Created {group_count} groups for {len(hosts_info)} hosts")
        
        return organized_inventory

def main():
    parser = argparse.ArgumentParser(description='VPN Infrastructure Inventory Organizer')
    parser.add_argument('--inventory', '-i', help='Path to input inventory file')
    parser.add_argument('--config', '-c', help='Path to organization config file')
    parser.add_argument('--output', '-o', help='Path to output organized inventory')
    parser.add_argument('--format', choices=['json', 'yaml'], default='yaml',
                       help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine output path
    output_path = args.output
    if not output_path:
        base_path = args.inventory or 'inventories/production'
        if args.format == 'yaml':
            output_path = f"{base_path}-organized.yml"
        else:
            output_path = f"{base_path}-organized.json"
    
    organizer = InventoryOrganizer(args.inventory, args.config)
    organized_inventory = organizer.organize_inventory(output_path)
    
    print(f"Inventory organization completed. Output saved to: {output_path}")

if __name__ == '__main__':
    main()