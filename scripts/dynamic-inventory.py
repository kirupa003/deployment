#!/usr/bin/env python3
"""
Dynamic Inventory Script for VPN Infrastructure
Supports multiple cloud providers and generates Ansible inventory
"""

import json
import sys
import argparse
import os
import boto3
import yaml
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VPNDynamicInventory:
    def __init__(self):
        self.inventory = {
            '_meta': {
                'hostvars': {}
            }
        }
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        config_file = os.environ.get('VPN_INVENTORY_CONFIG', 'inventories/dynamic-config.yml')
        
        default_config = {
            'providers': {
                'aws': {
                    'enabled': True,
                    'regions': ['us-east-1', 'eu-west-1', 'ap-southeast-1'],
                    'tag_filters': {
                        'VPN-Infrastructure': 'true',
                        'Environment': 'production'
                    }
                },
                'gcp': {
                    'enabled': False,
                    'project_id': '',
                    'zones': []
                },
                'azure': {
                    'enabled': False,
                    'subscription_id': '',
                    'resource_groups': []
                },
                'hetzner': {
                    'enabled': False,
                    'api_token': ''
                }
            },
            'grouping': {
                'by_region': True,
                'by_protocol': True,
                'by_capacity': True,
                'by_provider': True
            },
            'host_vars': {
                'ansible_user': 'ubuntu',
                'ansible_ssh_private_key_file': '~/.ssh/vpn-infrastructure',
                'ansible_ssh_common_args': '-o StrictHostKeyChecking=no'
            }
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            return default_config
    
    def get_aws_instances(self) -> List[Dict[str, Any]]:
        """Fetch VPN instances from AWS"""
        instances = []
        
        if not self.config['providers']['aws']['enabled']:
            return instances
            
        try:
            for region in self.config['providers']['aws']['regions']:
                ec2 = boto3.client('ec2', region_name=region)
                
                # Build filter from tag configuration
                filters = []
                for key, value in self.config['providers']['aws']['tag_filters'].items():
                    filters.append({
                        'Name': f'tag:{key}',
                        'Values': [value]
                    })
                
                filters.append({
                    'Name': 'instance-state-name',
                    'Values': ['running']
                })
                
                response = ec2.describe_instances(Filters=filters)
                
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        instance_data = self.parse_aws_instance(instance, region)
                        if instance_data:
                            instances.append(instance_data)
                            
        except Exception as e:
            logger.error(f"Error fetching AWS instances: {e}")
            
        return instances
    
    def parse_aws_instance(self, instance: Dict[str, Any], region: str) -> Dict[str, Any]:
        """Parse AWS instance data into inventory format"""
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        
        # Extract VPN-specific information from tags
        protocols = tags.get('VPN-Protocols', 'wireguard').split(',')
        capacity = int(tags.get('VPN-Capacity', '100'))
        server_type = tags.get('VPN-Type', 'standard')
        
        return {
            'hostname': tags.get('Name', instance['InstanceId']),
            'ansible_host': instance.get('PublicIpAddress', instance.get('PrivateIpAddress')),
            'instance_id': instance['InstanceId'],
            'provider': 'aws',
            'region': region,
            'zone': instance['Placement']['AvailabilityZone'],
            'instance_type': instance['InstanceType'],
            'protocols': protocols,
            'capacity': capacity,
            'server_type': server_type,
            'private_ip': instance.get('PrivateIpAddress'),
            'public_ip': instance.get('PublicIpAddress'),
            'vpc_id': instance.get('VpcId'),
            'subnet_id': instance.get('SubnetId'),
            'security_groups': [sg['GroupId'] for sg in instance.get('SecurityGroups', [])],
            'tags': tags,
            'launch_time': instance['LaunchTime'].isoformat() if 'LaunchTime' in instance else None
        }
    
    def get_gcp_instances(self) -> List[Dict[str, Any]]:
        """Fetch VPN instances from Google Cloud Platform"""
        instances = []
        
        if not self.config['providers']['gcp']['enabled']:
            return instances
            
        # TODO: Implement GCP integration
        logger.info("GCP integration not yet implemented")
        return instances
    
    def get_azure_instances(self) -> List[Dict[str, Any]]:
        """Fetch VPN instances from Microsoft Azure"""
        instances = []
        
        if not self.config['providers']['azure']['enabled']:
            return instances
            
        # TODO: Implement Azure integration
        logger.info("Azure integration not yet implemented")
        return instances
    
    def get_hetzner_instances(self) -> List[Dict[str, Any]]:
        """Fetch VPN instances from Hetzner Cloud"""
        instances = []
        
        if not self.config['providers']['hetzner']['enabled']:
            return instances
            
        # TODO: Implement Hetzner integration
        logger.info("Hetzner integration not yet implemented")
        return instances
    
    def create_groups(self, instances: List[Dict[str, Any]]) -> None:
        """Create inventory groups based on instance attributes"""
        
        # Initialize base groups
        base_groups = [
            'vpn_servers',
            'wireguard_servers',
            'openvpn_servers',
            'amneziawg_servers'
        ]
        
        for group in base_groups:
            self.inventory[group] = {'hosts': [], 'vars': {}}
        
        # Group by various attributes
        for instance in instances:
            hostname = instance['hostname']
            
            # Add to base VPN servers group
            self.inventory['vpn_servers']['hosts'].append(hostname)
            
            # Group by protocols
            for protocol in instance['protocols']:
                group_name = f"{protocol}_servers"
                if group_name not in self.inventory:
                    self.inventory[group_name] = {'hosts': [], 'vars': {}}
                self.inventory[group_name]['hosts'].append(hostname)
            
            # Group by region
            if self.config['grouping']['by_region']:
                region_group = self.normalize_region_name(instance['region'])
                if region_group not in self.inventory:
                    self.inventory[region_group] = {'hosts': [], 'vars': {}}
                self.inventory[region_group]['hosts'].append(hostname)
            
            # Group by provider
            if self.config['grouping']['by_provider']:
                provider_group = f"{instance['provider']}_servers"
                if provider_group not in self.inventory:
                    self.inventory[provider_group] = {'hosts': [], 'vars': {}}
                self.inventory[provider_group]['hosts'].append(hostname)
            
            # Group by capacity tier
            if self.config['grouping']['by_capacity']:
                capacity_tier = self.get_capacity_tier(instance['capacity'])
                capacity_group = f"capacity_{capacity_tier}"
                if capacity_group not in self.inventory:
                    self.inventory[capacity_group] = {'hosts': [], 'vars': {}}
                self.inventory[capacity_group]['hosts'].append(hostname)
            
            # Group by server type
            type_group = f"type_{instance['server_type']}"
            if type_group not in self.inventory:
                self.inventory[type_group] = {'hosts': [], 'vars': {}}
            self.inventory[type_group]['hosts'].append(hostname)
    
    def normalize_region_name(self, region: str) -> str:
        """Normalize region names to standard group names"""
        region_mapping = {
            'us-east-1': 'north_america',
            'us-west-1': 'north_america',
            'us-west-2': 'north_america',
            'ca-central-1': 'north_america',
            'eu-west-1': 'europe',
            'eu-west-2': 'europe',
            'eu-central-1': 'europe',
            'eu-north-1': 'europe',
            'ap-southeast-1': 'asia_pacific',
            'ap-southeast-2': 'asia_pacific',
            'ap-northeast-1': 'asia_pacific',
            'ap-south-1': 'asia_pacific'
        }
        
        return region_mapping.get(region, region.replace('-', '_'))
    
    def get_capacity_tier(self, capacity: int) -> str:
        """Determine capacity tier based on connection limit"""
        if capacity <= 50:
            return 'small'
        elif capacity <= 100:
            return 'medium'
        elif capacity <= 200:
            return 'large'
        else:
            return 'xlarge'
    
    def set_host_vars(self, instances: List[Dict[str, Any]]) -> None:
        """Set host-specific variables"""
        for instance in instances:
            hostname = instance['hostname']
            
            # Base host vars from config
            host_vars = self.config['host_vars'].copy()
            
            # Instance-specific vars
            host_vars.update({
                'server_region': self.normalize_region_name(instance['region']),
                'server_protocols': instance['protocols'],
                'server_capacity': instance['capacity'],
                'server_type': instance['server_type'],
                'cloud_provider': instance['provider'],
                'instance_id': instance['instance_id'],
                'instance_type': instance.get('instance_type'),
                'private_ip': instance.get('private_ip'),
                'public_ip': instance.get('public_ip'),
                'availability_zone': instance.get('zone'),
                'vpc_id': instance.get('vpc_id'),
                'subnet_id': instance.get('subnet_id'),
                'security_groups': instance.get('security_groups', []),
                'launch_time': instance.get('launch_time'),
                'cloud_tags': instance.get('tags', {})
            })
            
            self.inventory['_meta']['hostvars'][hostname] = host_vars
    
    def add_group_vars(self) -> None:
        """Add group-specific variables"""
        
        # VPN servers group vars
        self.inventory['vpn_servers']['vars'] = {
            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null',
            'vpn_infrastructure': True,
            'monitoring_enabled': True,
            'security_hardening': True
        }
        
        # Protocol-specific vars
        if 'wireguard_servers' in self.inventory:
            self.inventory['wireguard_servers']['vars'] = {
                'wireguard_port': 51820,
                'wireguard_dashboard_port': 10086,
                'wireguard_interface': 'wg0'
            }
        
        if 'openvpn_servers' in self.inventory:
            self.inventory['openvpn_servers']['vars'] = {
                'openvpn_port': 1194,
                'openvpn_protocol': 'udp',
                'openvpn_cipher': 'AES-256-GCM'
            }
        
        # Regional vars
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
            if region in self.inventory:
                self.inventory[region]['vars'] = vars_dict
    
    def generate_inventory(self) -> Dict[str, Any]:
        """Generate complete dynamic inventory"""
        
        # Collect instances from all providers
        all_instances = []
        all_instances.extend(self.get_aws_instances())
        all_instances.extend(self.get_gcp_instances())
        all_instances.extend(self.get_azure_instances())
        all_instances.extend(self.get_hetzner_instances())
        
        if not all_instances:
            logger.warning("No VPN instances found across all providers")
            return self.inventory
        
        # Create groups and set variables
        self.create_groups(all_instances)
        self.set_host_vars(all_instances)
        self.add_group_vars()
        
        logger.info(f"Generated inventory with {len(all_instances)} hosts across {len(self.inventory) - 1} groups")
        
        return self.inventory
    
    def list_inventory(self) -> str:
        """Return inventory as JSON string"""
        return json.dumps(self.generate_inventory(), indent=2)
    
    def get_host(self, hostname: str) -> str:
        """Return host variables as JSON string"""
        inventory = self.generate_inventory()
        host_vars = inventory['_meta']['hostvars'].get(hostname, {})
        return json.dumps(host_vars, indent=2)

def main():
    parser = argparse.ArgumentParser(description='VPN Infrastructure Dynamic Inventory')
    parser.add_argument('--list', action='store_true', help='List all hosts')
    parser.add_argument('--host', help='Get variables for specific host')
    
    args = parser.parse_args()
    
    inventory = VPNDynamicInventory()
    
    if args.list:
        print(inventory.list_inventory())
    elif args.host:
        print(inventory.get_host(args.host))
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()