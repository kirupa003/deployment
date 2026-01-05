#!/usr/bin/env python3
"""
Automated Documentation Generator for VPN Infrastructure
Generates documentation from Ansible metadata, playbooks, and roles
"""

import os
import sys
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentationGenerator:
    """Generates comprehensive documentation from Ansible metadata"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.docs_path = self.base_path / "docs"
        self.roles_path = self.base_path / "roles"
        self.playbooks_path = self.base_path / "playbooks"
        self.inventories_path = self.base_path / "inventories"
        
        # Ensure docs directory exists
        self.docs_path.mkdir(exist_ok=True)
        
    def generate_all_documentation(self):
        """Generate all documentation types"""
        logger.info("Starting comprehensive documentation generation...")
        
        # Generate role documentation
        self.generate_role_documentation()
        
        # Generate playbook documentation
        self.generate_playbook_documentation()
        
        # Generate inventory documentation
        self.generate_inventory_documentation()
        
        # Generate API documentation
        self.generate_api_documentation()
        
        # Generate architecture documentation
        self.generate_architecture_documentation()
        
        # Generate index page
        self.generate_index_documentation()
        
        logger.info("Documentation generation completed successfully!")
    
    def generate_role_documentation(self):
        """Generate documentation for all Ansible roles"""
        logger.info("Generating role documentation...")
        
        roles_doc_path = self.docs_path / "roles"
        roles_doc_path.mkdir(exist_ok=True)
        
        if not self.roles_path.exists():
            logger.warning("Roles directory not found")
            return
        
        roles_index = []
        
        for role_dir in self.roles_path.iterdir():
            if not role_dir.is_dir():
                continue
                
            role_name = role_dir.name
            logger.info(f"Processing role: {role_name}")
            
            role_info = self._extract_role_info(role_dir)
            roles_index.append(role_info)
            
            # Generate individual role documentation
            self._generate_individual_role_doc(role_info, roles_doc_path)
        
        # Generate roles index
        self._generate_roles_index(roles_index, roles_doc_path)
    
    def _extract_role_info(self, role_dir: Path) -> Dict[str, Any]:
        """Extract information from a role directory"""
        role_name = role_dir.name
        role_info = {
            'name': role_name,
            'path': str(role_dir),
            'description': '',
            'author': '',
            'version': '',
            'dependencies': [],
            'variables': {},
            'tasks': [],
            'handlers': [],
            'templates': [],
            'files': []
        }
        
        # Extract meta information
        meta_file = role_dir / "meta" / "main.yml"
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    meta_data = yaml.safe_load(f) or {}
                
                galaxy_info = meta_data.get('galaxy_info', {})
                role_info['description'] = galaxy_info.get('description', '')
                role_info['author'] = galaxy_info.get('author', '')
                role_info['version'] = galaxy_info.get('version', '')
                role_info['dependencies'] = meta_data.get('dependencies', [])
                
            except Exception as e:
                logger.warning(f"Error reading meta for {role_name}: {e}")
        
        # Extract default variables
        defaults_file = role_dir / "defaults" / "main.yml"
        if defaults_file.exists():
            try:
                with open(defaults_file, 'r') as f:
                    defaults_data = yaml.safe_load(f) or {}
                role_info['variables'] = defaults_data
            except Exception as e:
                logger.warning(f"Error reading defaults for {role_name}: {e}")
        
        # Extract tasks information
        tasks_dir = role_dir / "tasks"
        if tasks_dir.exists():
            for task_file in tasks_dir.glob("*.yml"):
                try:
                    with open(task_file, 'r') as f:
                        tasks_data = yaml.safe_load(f) or []
                    
                    if isinstance(tasks_data, list):
                        for task in tasks_data:
                            if isinstance(task, dict) and 'name' in task:
                                role_info['tasks'].append({
                                    'name': task['name'],
                                    'file': task_file.name,
                                    'tags': task.get('tags', [])
                                })
                except Exception as e:
                    logger.warning(f"Error reading tasks from {task_file}: {e}")
        
        # Extract handlers information
        handlers_file = role_dir / "handlers" / "main.yml"
        if handlers_file.exists():
            try:
                with open(handlers_file, 'r') as f:
                    handlers_data = yaml.safe_load(f) or []
                
                if isinstance(handlers_data, list):
                    for handler in handlers_data:
                        if isinstance(handler, dict) and 'name' in handler:
                            role_info['handlers'].append(handler['name'])
            except Exception as e:
                logger.warning(f"Error reading handlers for {role_name}: {e}")
        
        # List templates
        templates_dir = role_dir / "templates"
        if templates_dir.exists():
            role_info['templates'] = [f.name for f in templates_dir.glob("*") if f.is_file()]
        
        # List files
        files_dir = role_dir / "files"
        if files_dir.exists():
            role_info['files'] = [f.name for f in files_dir.glob("*") if f.is_file()]
        
        return role_info
    
    def _generate_individual_role_doc(self, role_info: Dict[str, Any], output_dir: Path):
        """Generate documentation for an individual role"""
        role_name = role_info['name']
        doc_file = output_dir / f"{role_name}.md"
        
        content = f"""# Role: {role_name}

## Overview

**Description:** {role_info['description'] or 'No description available'}  
**Author:** {role_info['author'] or 'Unknown'}  
**Version:** {role_info['version'] or 'Unknown'}  

## Dependencies

"""
        
        if role_info['dependencies']:
            for dep in role_info['dependencies']:
                if isinstance(dep, dict):
                    dep_name = dep.get('name') or dep.get('role', 'Unknown')
                    content += f"- `{dep_name}`\n"
                else:
                    content += f"- `{dep}`\n"
        else:
            content += "No dependencies\n"
        
        content += "\n## Variables\n\n"
        
        if role_info['variables']:
            content += "| Variable | Default Value | Description |\n"
            content += "|----------|---------------|-------------|\n"
            
            for var_name, var_value in role_info['variables'].items():
                # Handle complex values
                if isinstance(var_value, (dict, list)):
                    var_display = f"`{yaml.dump(var_value, default_flow_style=True).strip()}`"
                else:
                    var_display = f"`{var_value}`"
                
                content += f"| `{var_name}` | {var_display} | |\n"
        else:
            content += "No configurable variables\n"
        
        content += "\n## Tasks\n\n"
        
        if role_info['tasks']:
            current_file = None
            for task in role_info['tasks']:
                if task['file'] != current_file:
                    current_file = task['file']
                    content += f"\n### {current_file}\n\n"
                
                tags_str = f" `{', '.join(task['tags'])}`" if task['tags'] else ""
                content += f"- **{task['name']}**{tags_str}\n"
        else:
            content += "No tasks defined\n"
        
        content += "\n## Handlers\n\n"
        
        if role_info['handlers']:
            for handler in role_info['handlers']:
                content += f"- {handler}\n"
        else:
            content += "No handlers defined\n"
        
        content += "\n## Templates\n\n"
        
        if role_info['templates']:
            for template in role_info['templates']:
                content += f"- `{template}`\n"
        else:
            content += "No templates\n"
        
        content += "\n## Files\n\n"
        
        if role_info['files']:
            for file_name in role_info['files']:
                content += f"- `{file_name}`\n"
        else:
            content += "No static files\n"
        
        content += f"""
## Usage

```yaml
- name: Apply {role_name} role
  hosts: target_servers
  roles:
    - {role_name}
```

## Tags

Common tags for this role:

```bash
# Run specific parts of the role
ansible-playbook playbook.yml --tags "tag_name"
```

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(doc_file, 'w') as f:
            f.write(content)
        
        logger.info(f"Generated documentation for role: {role_name}")
    
    def _generate_roles_index(self, roles_info: List[Dict[str, Any]], output_dir: Path):
        """Generate index page for all roles"""
        index_file = output_dir / "README.md"
        
        content = f"""# Ansible Roles Documentation

This directory contains documentation for all Ansible roles in the VPN Infrastructure project.

## Available Roles

| Role | Description | Dependencies |
|------|-------------|--------------|
"""
        
        for role in sorted(roles_info, key=lambda x: x['name']):
            deps_count = len(role['dependencies'])
            deps_str = f"{deps_count} dependencies" if deps_count > 0 else "No dependencies"
            
            content += f"| [{role['name']}]({role['name']}.md) | {role['description'][:50]}{'...' if len(role['description']) > 50 else ''} | {deps_str} |\n"
        
        content += f"""

## Role Categories

### VPN Services
- [wireguard](wireguard.md) - WireGuard VPN server with dashboard
- [openvpn](openvpn.md) - OpenVPN server with PKI management
- [amneziawg](amneziawg.md) - AmneziaWG obfuscated VPN

### Security
- [crowdsec](crowdsec.md) - Collaborative security and threat intelligence
- [fail2ban](fail2ban.md) - Intrusion prevention and brute force protection
- [ufw](ufw.md) - Uncomplicated Firewall configuration
- [ssh_hardening](ssh_hardening.md) - SSH security hardening

### Monitoring
- [node_exporter](node_exporter.md) - System metrics collection
- [wg_exporter](wg_exporter.md) - WireGuard metrics collection
- [promtail](promtail.md) - Log shipping to Loki
- [fluent_bit](fluent_bit.md) - Log processing and forwarding
- [monitoring](monitoring.md) - Grafana dashboards and alerting

### DNS and Network
- [coredns](coredns.md) - DNS server with ad-blocking

## Usage Examples

### Deploy VPN Server with Monitoring
```yaml
- hosts: vpn_servers
  roles:
    - ufw
    - ssh_hardening
    - wireguard
    - node_exporter
    - wg_exporter
    - promtail
    - crowdsec
    - fail2ban
```

### Security Hardening Only
```yaml
- hosts: all_servers
  roles:
    - ufw
    - ssh_hardening
    - fail2ban
    - crowdsec
```

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(index_file, 'w') as f:
            f.write(content)
    
    def generate_playbook_documentation(self):
        """Generate documentation for all playbooks"""
        logger.info("Generating playbook documentation...")
        
        playbooks_doc_path = self.docs_path / "playbooks"
        playbooks_doc_path.mkdir(exist_ok=True)
        
        if not self.playbooks_path.exists():
            logger.warning("Playbooks directory not found")
            return
        
        playbooks_info = []
        
        for playbook_file in self.playbooks_path.glob("*.yml"):
            logger.info(f"Processing playbook: {playbook_file.name}")
            
            playbook_info = self._extract_playbook_info(playbook_file)
            playbooks_info.append(playbook_info)
        
        # Generate playbooks index
        self._generate_playbooks_index(playbooks_info, playbooks_doc_path)
    
    def _extract_playbook_info(self, playbook_file: Path) -> Dict[str, Any]:
        """Extract information from a playbook file"""
        playbook_info = {
            'name': playbook_file.stem,
            'file': playbook_file.name,
            'description': '',
            'hosts': [],
            'roles': [],
            'tasks': [],
            'variables': {},
            'tags': set()
        }
        
        try:
            with open(playbook_file, 'r') as f:
                content = f.read()
                
            # Extract description from comments
            description_match = re.search(r'^#\s*(.+)', content, re.MULTILINE)
            if description_match:
                playbook_info['description'] = description_match.group(1).strip()
            
            # Parse YAML content
            playbook_data = yaml.safe_load(content)
            
            if isinstance(playbook_data, list):
                for play in playbook_data:
                    if isinstance(play, dict):
                        # Extract hosts
                        hosts = play.get('hosts', '')
                        if hosts and hosts not in playbook_info['hosts']:
                            playbook_info['hosts'].append(hosts)
                        
                        # Extract roles
                        roles = play.get('roles', [])
                        for role in roles:
                            if isinstance(role, dict):
                                role_name = role.get('name') or role.get('role', 'unknown')
                            else:
                                role_name = role
                            
                            if role_name not in playbook_info['roles']:
                                playbook_info['roles'].append(role_name)
                        
                        # Extract tasks
                        tasks = play.get('tasks', [])
                        for task in tasks:
                            if isinstance(task, dict) and 'name' in task:
                                task_info = {
                                    'name': task['name'],
                                    'tags': task.get('tags', [])
                                }
                                playbook_info['tasks'].append(task_info)
                                
                                # Collect tags
                                for tag in task.get('tags', []):
                                    playbook_info['tags'].add(tag)
                        
                        # Extract variables
                        vars_data = play.get('vars', {})
                        playbook_info['variables'].update(vars_data)
                        
        except Exception as e:
            logger.warning(f"Error parsing playbook {playbook_file}: {e}")
        
        playbook_info['tags'] = list(playbook_info['tags'])
        return playbook_info
    
    def _generate_playbooks_index(self, playbooks_info: List[Dict[str, Any]], output_dir: Path):
        """Generate index page for all playbooks"""
        index_file = output_dir / "README.md"
        
        content = f"""# Ansible Playbooks Documentation

This directory contains documentation for all Ansible playbooks in the VPN Infrastructure project.

## Available Playbooks

| Playbook | Description | Target Hosts |
|----------|-------------|--------------|
"""
        
        for playbook in sorted(playbooks_info, key=lambda x: x['name']):
            hosts_str = ', '.join(playbook['hosts']) if playbook['hosts'] else 'Various'
            desc = playbook['description'][:60] + '...' if len(playbook['description']) > 60 else playbook['description']
            
            content += f"| `{playbook['file']}` | {desc} | {hosts_str} |\n"
        
        content += """

## Playbook Categories

### Deployment Playbooks
- `multi-protocol-deployment.yml` - Complete VPN infrastructure deployment
- `wireguard-dashboard.yml` - WireGuard server with web dashboard
- `openvpn-deployment.yml` - OpenVPN server deployment
- `deploy-coredns.yml` - DNS server deployment

### Maintenance Playbooks
- `health-check.yml` - Comprehensive system health validation
- `upgrade-packages.yml` - System package updates
- `certificate-rotation.yml` - Certificate and key rotation
- `backup-disaster-recovery.yml` - Backup and recovery operations

### Security Playbooks
- `security-hardening.yml` - System security hardening
- `security-audit.yml` - Security compliance audit
- `emergency-block.yml` - Emergency IP blocking
- `emergency-security-response.yml` - Security incident response

### Server Management
- `server-provisioning.yml` - New server setup
- `server-decommissioning.yml` - Server removal procedures
- `server-health-validation.yml` - Server health checks

## Usage Examples

### Full Infrastructure Deployment
```bash
ansible-playbook playbooks/multi-protocol-deployment.yml \\
  --limit vpn_servers \\
  --extra-vars "batch_size=10"
```

### Regional Deployment
```bash
ansible-playbook playbooks/wireguard-dashboard.yml \\
  --limit europe
```

### Maintenance Operations
```bash
# Health check
ansible-playbook playbooks/health-check.yml

# Package updates
ansible-playbook playbooks/upgrade-packages.yml \\
  --extra-vars "security_only=true"

# Certificate rotation
ansible-playbook playbooks/certificate-rotation.yml \\
  --limit openvpn_servers
```

### Emergency Procedures
```bash
# Emergency IP blocking
ansible-playbook playbooks/emergency-block.yml \\
  --extra-vars "block_ips=['1.2.3.4','5.6.7.8']"

# Security incident response
ansible-playbook playbooks/emergency-security-response.yml \\
  --limit affected_servers
```

## Common Tags

Use tags to run specific parts of playbooks:

- `--tags setup` - Initial setup tasks
- `--tags configure` - Configuration tasks
- `--tags security` - Security-related tasks
- `--tags monitoring` - Monitoring setup
- `--tags backup` - Backup operations
- `--tags validate` - Validation and testing

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(index_file, 'w') as f:
            f.write(content)
    
    def generate_inventory_documentation(self):
        """Generate documentation for inventory structure"""
        logger.info("Generating inventory documentation...")
        
        inventory_doc_file = self.docs_path / "inventory-structure.md"
        
        content = f"""# Inventory Structure Documentation

## Overview

The VPN Infrastructure uses a hierarchical inventory structure to manage 30 VPN servers across 3 geographic regions.

## Directory Structure

```
inventories/
├── production                    # Main inventory file
├── group_vars/                   # Group-specific variables
│   ├── all.yml                  # Global variables
│   ├── vpn_servers.yml          # VPN server common config
│   ├── wireguard_servers.yml    # WireGuard-specific config
│   ├── openvpn_servers.yml      # OpenVPN-specific config
│   ├── europe.yml               # Europe region config
│   ├── north_america.yml        # North America region config
│   └── asia_pacific.yml         # Asia Pacific region config
├── host_vars/                   # Host-specific variables
│   ├── eu-vpn-wg-01.example.com.yml
│   ├── na-vpn-wg-01.example.com.yml
│   └── ap-vpn-wg-01.example.com.yml
└── templates/                   # Configuration templates
    ├── environment.yml.j2       # Environment template
    └── server.yml.j2           # Server template
```

## Inventory Groups

### Primary Groups

- **`vpn_servers`** - All VPN servers (30 total)
- **`wireguard_servers`** - Servers running WireGuard
- **`openvpn_servers`** - Servers running OpenVPN
- **`amneziawg_servers`** - Servers running AmneziaWG

### Regional Groups

- **`europe`** - European servers (10 servers)
- **`north_america`** - North American servers (10 servers)
- **`asia_pacific`** - Asia Pacific servers (10 servers)

### Service Groups

- **`monitoring_targets`** - Servers with monitoring enabled
- **`dns_servers`** - Servers running CoreDNS
- **`security_hardened`** - Servers with security hardening

## Variable Hierarchy

Variables are applied in the following order (later overrides earlier):

1. **Global variables** (`group_vars/all.yml`)
2. **Group variables** (`group_vars/[group].yml`)
3. **Host variables** (`host_vars/[hostname].yml`)
4. **Playbook variables**
5. **Command-line extra variables**

## Configuration Management

### Environment-Specific Configuration

Use templates to generate environment-specific configurations:

```bash
# Generate configurations
ansible-playbook playbooks/generate-configurations.yml \\
  -e environment_name=production \\
  -e domain_name=vpn.example.com
```

### Variable Validation

Validate inventory configuration:

```bash
# Validate inventory structure
./scripts/validate-inventory.py

# Validate configuration consistency
./scripts/validate-configuration.py
```

## Usage Examples

### Target Specific Groups

```bash
# Deploy to all VPN servers
ansible-playbook playbook.yml --limit vpn_servers

# Deploy to specific region
ansible-playbook playbook.yml --limit europe

# Deploy to specific protocol
ansible-playbook playbook.yml --limit wireguard_servers

# Deploy to specific server
ansible-playbook playbook.yml --limit eu-vpn-wg-01.example.com
```

### Combine Groups

```bash
# Deploy to WireGuard servers in Europe
ansible-playbook playbook.yml --limit "europe:&wireguard_servers"

# Deploy to all except one region
ansible-playbook playbook.yml --limit "vpn_servers:!asia_pacific"
```

### Rolling Deployments

```bash
# Deploy in batches
ansible-playbook playbook.yml \\
  --limit vpn_servers \\
  --extra-vars "serial=5"
```

## Best Practices

### Inventory Organization

1. **Group by function and location**
2. **Use descriptive hostnames**
3. **Maintain consistent naming conventions**
4. **Document variable purposes**
5. **Validate configurations regularly**

### Variable Management

1. **Use group_vars for common settings**
2. **Use host_vars for server-specific config**
3. **Encrypt sensitive data with Vault**
4. **Document variable dependencies**
5. **Use templates for complex configurations**

### Security Considerations

1. **Encrypt sensitive variables**
2. **Use separate inventories for environments**
3. **Limit access to production inventory**
4. **Regular inventory audits**
5. **Version control all changes**

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(inventory_doc_file, 'w') as f:
            f.write(content)
    
    def generate_api_documentation(self):
        """Generate API documentation"""
        logger.info("Generating API documentation...")
        
        api_doc_file = self.docs_path / "api-documentation.md"
        
        content = f"""# VPN Infrastructure API Documentation

## Overview

The VPN Infrastructure provides several APIs for management and monitoring:

1. **Ansible API** - Automation and configuration management
2. **WireGuard Dashboard API** - VPN user management
3. **Monitoring APIs** - Metrics and health endpoints
4. **Security APIs** - CrowdSec and security management

## Ansible API

### Inventory API

```bash
# List all hosts
ansible-inventory --list

# List hosts in specific group
ansible-inventory --list --limit vpn_servers

# Get host variables
ansible-inventory --host server.example.com
```

### Playbook Execution API

```bash
# Run playbook with API-like interface
ansible-playbook playbooks/health-check.yml \\
  --extra-vars '{{"target_hosts": "vpn_servers", "check_type": "full"}}'

# Get playbook information
ansible-playbook playbooks/health-check.yml --list-tasks
```

## WireGuard Dashboard API

### Base URL
```
https://server.example.com:10086/api
```

### Authentication
```bash
# Login to get session token
curl -X POST https://server.example.com:10086/api/login \\
  -H "Content-Type: application/json" \\
  -d '{{"username": "admin", "password": "password"}}'
```

### Endpoints

#### Get Server Status
```bash
GET /api/server/status
```

Response:
```json
{{
  "status": "running",
  "peers": 25,
  "interface": "wg0",
  "listen_port": 51820,
  "public_key": "...",
  "bandwidth": {{
    "rx": 1024000,
    "tx": 2048000
  }}
}}
```

#### List Peers
```bash
GET /api/peers
```

Response:
```json
{{
  "peers": [
    {{
      "id": "peer1",
      "name": "client1",
      "public_key": "...",
      "allowed_ips": ["10.8.0.2/32"],
      "endpoint": "1.2.3.4:12345",
      "latest_handshake": "2024-01-05T10:30:00Z",
      "transfer": {{
        "rx": 1024,
        "tx": 2048
      }}
    }}
  ]
}}
```

#### Add Peer
```bash
POST /api/peers
Content-Type: application/json

{{
  "name": "new_client",
  "allowed_ips": ["10.8.0.10/32"],
  "dns": ["10.8.0.1"]
}}
```

#### Remove Peer
```bash
DELETE /api/peers/{{peer_id}}
```

## Monitoring APIs

### Node Exporter (Port 9100)

#### System Metrics
```bash
# Get all metrics
curl http://server.example.com:9100/metrics

# CPU usage
curl -s http://server.example.com:9100/metrics | grep node_cpu_seconds_total

# Memory usage
curl -s http://server.example.com:9100/metrics | grep node_memory_MemAvailable_bytes
```

### WireGuard Exporter (Port 9586)

#### VPN Metrics
```bash
# Get WireGuard metrics
curl http://server.example.com:9586/metrics

# Peer count
curl -s http://server.example.com:9586/metrics | grep wireguard_peers

# Bandwidth usage
curl -s http://server.example.com:9586/metrics | grep wireguard_peer_receive_bytes_total
```

### Promtail (Port 9080)

#### Log Shipping Status
```bash
# Get Promtail metrics
curl http://server.example.com:9080/metrics

# Check targets
curl http://server.example.com:9080/targets
```

## Security APIs

### CrowdSec API

#### Local API (LAPI)
```bash
# Get decisions
curl -H "X-Api-Key: your-api-key" \\
  http://server.example.com:8080/v1/decisions

# Add decision
curl -X POST -H "X-Api-Key: your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{{"decisions": [{{"value": "1.2.3.4", "type": "ban", "duration": "4h"}}]}}' \\
  http://server.example.com:8080/v1/decisions
```

#### Metrics API
```bash
# Get CrowdSec metrics
curl http://server.example.com:6060/metrics
```

### Fail2Ban Status

```bash
# Get jail status (via SSH)
ssh server.example.com "fail2ban-client status"

# Get banned IPs
ssh server.example.com "fail2ban-client status sshd"
```

## Health Check APIs

### Ansible Health Checks

```bash
# Quick connectivity check
ansible all -m ping

# Service status check
ansible vpn_servers -m service -a "name=wireguard"

# System information
ansible vpn_servers -m setup -a "filter=ansible_distribution*"
```

### Custom Health Endpoints

#### Server Health
```bash
# Run health check playbook
ansible-playbook playbooks/health-check.yml \\
  --extra-vars "output_format=json" \\
  --limit server.example.com
```

#### Service Validation
```bash
# Validate specific services
ansible-playbook playbooks/server-health-validation.yml \\
  --tags network,vpn \\
  --limit server.example.com
```

## Automation APIs

### Configuration Management

```bash
# Generate configurations
ansible-playbook playbooks/generate-configurations.yml \\
  --extra-vars "environment=production"

# Validate configurations
./scripts/validate-configuration.py --path generated-configs/

# Apply configurations
ansible-playbook playbooks/multi-protocol-deployment.yml \\
  --limit target_servers
```

### Backup and Recovery

```bash
# Create backup
./scripts/backup-configuration.sh backup

# List backups
./scripts/backup-configuration.sh list

# Restore backup
./scripts/backup-configuration.sh restore backup_file.tar.gz
```

## Error Handling

### Common HTTP Status Codes

- **200 OK** - Request successful
- **400 Bad Request** - Invalid request parameters
- **401 Unauthorized** - Authentication required
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

### Error Response Format

```json
{{
  "error": {{
    "code": "INVALID_PARAMETER",
    "message": "Invalid peer configuration",
    "details": {{
      "field": "allowed_ips",
      "reason": "Invalid IP address format"
    }}
  }}
}}
```

## Rate Limiting

### API Limits

- **WireGuard Dashboard:** 100 requests/minute per IP
- **Monitoring APIs:** 1000 requests/minute per IP
- **CrowdSec API:** 500 requests/minute per API key

### Ansible Execution

- **Concurrent forks:** 30 (configurable in ansible.cfg)
- **Serial execution:** Configurable per playbook
- **Timeout settings:** 60 seconds default

## Authentication and Security

### API Keys

- **CrowdSec:** API key authentication
- **WireGuard Dashboard:** Session-based authentication
- **Monitoring:** IP-based access control

### SSL/TLS

All APIs support HTTPS with valid certificates:

```bash
# Verify SSL certificate
openssl s_client -connect server.example.com:10086 -servername server.example.com
```

### Access Control

- **Firewall rules:** UFW controls API access
- **Network segmentation:** APIs bound to specific interfaces
- **Authentication:** Required for management APIs

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(api_doc_file, 'w') as f:
            f.write(content)
    
    def generate_architecture_documentation(self):
        """Generate architecture documentation"""
        logger.info("Generating architecture documentation...")
        
        arch_doc_file = self.docs_path / "architecture-overview.md"
        
        content = f"""# VPN Infrastructure Architecture Overview

## System Architecture

The VPN Infrastructure DevOps Controller implements a distributed architecture supporting 30 VPN servers across 3 geographic regions with centralized management and monitoring.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Ansible       │  │   Monitoring    │  │   Security      │ │
│  │   Controller    │  │   Stack         │  │   Management    │ │
│  │                 │  │                 │  │                 │ │
│  │ • Semaphore UI  │  │ • Grafana       │  │ • Vault         │ │
│  │ • AWX Platform  │  │ • Prometheus    │  │ • CrowdSec LAPI │ │
│  │ • Playbooks     │  │ • Loki          │  │ • Certificate   │ │
│  │ • Inventory     │  │ • AlertManager  │  │   Management    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Management & Monitoring
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EDGE LAYER                               │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   EUROPE (10)   │  │ NORTH AMERICA   │  │ ASIA PACIFIC    │ │
│  │                 │  │     (10)        │  │     (10)        │ │
│  │ • WireGuard     │  │ • WireGuard     │  │ • WireGuard     │ │
│  │ • OpenVPN       │  │ • OpenVPN       │  │ • OpenVPN       │ │
│  │ • AmneziaWG     │  │ • AmneziaWG     │  │ • AmneziaWG     │ │
│  │ • CoreDNS       │  │ • CoreDNS       │  │ • CoreDNS       │ │
│  │ • Monitoring    │  │ • Monitoring    │  │ • Monitoring    │ │
│  │ • Security      │  │ • Security      │  │ • Security      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Control Plane Components

#### 1. Ansible Controller
- **Semaphore UI:** Web-based playbook execution interface
- **AWX Platform:** Enterprise Ansible automation
- **Inventory Management:** Dynamic and static inventory sources
- **Playbook Library:** Comprehensive automation playbooks

#### 2. Monitoring Stack
- **Grafana:** Visualization and dashboarding
- **VictoriaMetrics:** Time-series metrics storage
- **Loki:** Log aggregation and querying
- **AlertManager:** Alert routing and notification

#### 3. Security Management
- **HashiCorp Vault:** Secrets management and encryption
- **CrowdSec LAPI:** Centralized threat intelligence
- **Certificate Authority:** PKI management for OpenVPN
- **Security Policies:** Centralized security configuration

### Edge Layer Components

#### VPN Services
- **WireGuard:** Modern, high-performance VPN protocol
- **OpenVPN:** Traditional VPN with certificate-based auth
- **AmneziaWG:** Obfuscated WireGuard for censorship circumvention
- **WireGuard Dashboard:** Web-based VPN management interface

#### Supporting Services
- **CoreDNS:** DNS resolution with ad-blocking
- **UFW Firewall:** Network access control
- **CrowdSec Agent:** Local threat detection
- **Fail2Ban:** Brute force protection

#### Monitoring Agents
- **node_exporter:** System metrics collection
- **wg_exporter:** WireGuard-specific metrics
- **promtail:** Log shipping to Loki
- **fluent-bit:** DNS log processing

## Network Architecture

### Regional Distribution

```
Internet
    │
    ├── Europe Region (10 servers)
    │   ├── eu-vpn-wg-01.example.com    (WireGuard + Dashboard)
    │   ├── eu-vpn-wg-02.example.com    (WireGuard)
    │   ├── eu-vpn-ovpn-01.example.com  (OpenVPN)
    │   └── ... (7 more servers)
    │
    ├── North America Region (10 servers)
    │   ├── na-vpn-wg-01.example.com    (WireGuard + Dashboard)
    │   ├── na-vpn-wg-02.example.com    (WireGuard)
    │   ├── na-vpn-ovpn-01.example.com  (OpenVPN)
    │   └── ... (7 more servers)
    │
    └── Asia Pacific Region (10 servers)
        ├── ap-vpn-wg-01.example.com    (WireGuard + Dashboard)
        ├── ap-vpn-wg-02.example.com    (WireGuard)
        ├── ap-vpn-ovpn-01.example.com  (OpenVPN)
        └── ... (7 more servers)
```

### Network Segmentation

#### Management Network
- **Purpose:** Ansible automation and monitoring
- **Access:** SSH (port 22), HTTPS management interfaces
- **Security:** SSH key authentication, firewall rules

#### VPN Client Network
- **WireGuard:** UDP port 51820
- **OpenVPN:** UDP port 1194, TCP port 443
- **AmneziaWG:** UDP port 51821
- **Security:** Protocol-specific encryption, client certificates

#### Monitoring Network
- **Metrics:** HTTP ports 9100, 9586, 9080
- **Logs:** Secure log shipping to central collectors
- **Security:** Internal network access, TLS encryption

## Data Flow Architecture

### Configuration Management Flow

```
1. Configuration Templates (Jinja2)
   ↓
2. Ansible Variable Processing
   ↓
3. Playbook Execution
   ↓
4. Server Configuration Deployment
   ↓
5. Service Validation and Health Checks
```

### Monitoring Data Flow

```
1. Metrics Collection (exporters)
   ↓
2. Metrics Storage (VictoriaMetrics)
   ↓
3. Visualization (Grafana)
   ↓
4. Alerting (AlertManager)
   ↓
5. Notification (Slack/Email)
```

### Log Processing Flow

```
1. Log Generation (services)
   ↓
2. Log Collection (promtail/fluent-bit)
   ↓
3. Log Aggregation (Loki/ClickHouse)
   ↓
4. Log Analysis (Grafana/Custom queries)
   ↓
5. Security Analysis (CrowdSec)
```

## Security Architecture

### Defense in Depth

#### Layer 1: Network Security
- **Firewall Rules:** UFW with deny-by-default policy
- **Network Segmentation:** Isolated management and client networks
- **DDoS Protection:** Rate limiting and connection throttling

#### Layer 2: Host Security
- **SSH Hardening:** Key-only authentication, custom ports
- **System Updates:** Automated security patch management
- **File Integrity:** Monitoring for unauthorized changes

#### Layer 3: Application Security
- **VPN Encryption:** Strong cryptographic protocols
- **Certificate Management:** Automated PKI with rotation
- **Access Control:** Role-based permissions

#### Layer 4: Data Security
- **Secrets Management:** HashiCorp Vault integration
- **Encryption at Rest:** Encrypted configuration storage
- **Secure Communication:** TLS for all management interfaces

#### Layer 5: Monitoring Security
- **Threat Detection:** CrowdSec collaborative intelligence
- **Intrusion Prevention:** Fail2Ban automated blocking
- **Security Auditing:** Comprehensive logging and analysis

## Scalability Architecture

### Horizontal Scaling

#### Server Scaling
- **Regional Expansion:** Add servers to existing regions
- **New Regions:** Deploy to additional geographic locations
- **Load Distribution:** Automatic client load balancing

#### Service Scaling
- **Protocol Support:** Multiple VPN protocols per server
- **Capacity Management:** Monitor and scale based on usage
- **Performance Optimization:** Kernel and network tuning

### Vertical Scaling

#### Resource Optimization
- **CPU Optimization:** Multi-core utilization
- **Memory Management:** Efficient memory allocation
- **Network Optimization:** High-throughput configurations

## High Availability Architecture

### Redundancy Strategies

#### Regional Redundancy
- **Multiple Servers:** 10 servers per region for redundancy
- **Protocol Diversity:** Multiple VPN protocols available
- **Failover Capability:** Automatic client failover

#### Service Redundancy
- **Monitoring:** Multiple monitoring agents per server
- **DNS:** Multiple DNS servers with failover
- **Security:** Distributed security enforcement

### Disaster Recovery

#### Backup Strategy
- **Configuration Backups:** Automated daily backups
- **Key Material Backup:** Secure key and certificate storage
- **Recovery Procedures:** Documented recovery processes

#### Recovery Time Objectives
- **RTO:** 4 hours for full region recovery
- **RPO:** 24 hours for configuration data
- **MTTR:** 30 minutes for individual server recovery

## Performance Architecture

### Optimization Strategies

#### Network Performance
- **TCP BBR:** Congestion control optimization
- **Kernel Tuning:** Network stack optimization
- **Hardware Acceleration:** Crypto acceleration where available

#### VPN Performance
- **Protocol Selection:** Optimal protocol for use case
- **Encryption Efficiency:** Balanced security and performance
- **Connection Pooling:** Efficient connection management

### Monitoring and Metrics

#### Key Performance Indicators
- **Throughput:** Bandwidth utilization per server
- **Latency:** Connection establishment time
- **Availability:** Service uptime percentage
- **Capacity:** Concurrent connection limits

## Technology Stack

### Infrastructure
- **Operating System:** Ubuntu 20.04+ / Debian 11+
- **Virtualization:** KVM/VMware/Cloud instances
- **Networking:** Linux networking stack with optimization

### Automation
- **Configuration Management:** Ansible 2.12+
- **Orchestration:** Ansible AWX/Semaphore
- **Version Control:** Git with GitOps workflows

### Monitoring
- **Metrics:** VictoriaMetrics, Prometheus exporters
- **Logging:** Loki, fluent-bit, promtail
- **Visualization:** Grafana dashboards
- **Alerting:** AlertManager with multiple channels

### Security
- **Secrets Management:** HashiCorp Vault
- **Threat Intelligence:** CrowdSec
- **Intrusion Prevention:** Fail2Ban
- **Firewall:** UFW (Uncomplicated Firewall)

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(arch_doc_file, 'w') as f:
            f.write(content)
    
    def generate_index_documentation(self):
        """Generate main documentation index"""
        logger.info("Generating documentation index...")
        
        index_file = self.docs_path / "README.md"
        
        content = f"""# VPN Infrastructure Documentation

Welcome to the comprehensive documentation for the VPN Infrastructure DevOps Controller system.

## Quick Start

1. **[Deployment Guide](deployment-guide.md)** - Complete deployment instructions
2. **[Troubleshooting Guide](troubleshooting-guide.md)** - Problem resolution procedures
3. **[Security Runbook](security-runbook.md)** - Security operations and incident response

## Documentation Structure

### 📋 Operations Guides
- **[Deployment Guide](deployment-guide.md)** - Step-by-step deployment procedures
- **[Troubleshooting Guide](troubleshooting-guide.md)** - Systematic problem resolution
- **[Security Runbook](security-runbook.md)** - Security operations and incident response

### 🏗️ Architecture Documentation
- **[Architecture Overview](architecture-overview.md)** - System architecture and design
- **[Inventory Structure](inventory-structure.md)** - Ansible inventory organization

### 🔧 Technical Reference
- **[API Documentation](api-documentation.md)** - API endpoints and usage
- **[Roles Documentation](roles/README.md)** - Ansible roles reference
- **[Playbooks Documentation](playbooks/README.md)** - Playbook usage guide

## System Overview

The VPN Infrastructure DevOps Controller manages **30 VPN servers** across **3 geographic regions**:

- **Europe:** 10 servers
- **North America:** 10 servers  
- **Asia Pacific:** 10 servers

### Supported VPN Protocols
- **WireGuard** - Modern, high-performance VPN
- **OpenVPN** - Traditional VPN with certificate authentication
- **AmneziaWG** - Obfuscated WireGuard for censorship circumvention

### Key Features
- ✅ **Automated Deployment** - Complete infrastructure automation
- ✅ **Multi-Protocol Support** - WireGuard, OpenVPN, AmneziaWG
- ✅ **Comprehensive Monitoring** - Grafana dashboards and alerting
- ✅ **Security Hardening** - CrowdSec, Fail2Ban, SSH hardening
- ✅ **DNS Services** - CoreDNS with ad-blocking
- ✅ **Certificate Management** - Automated PKI and key rotation
- ✅ **Backup & Recovery** - Automated backup and disaster recovery

## Quick Commands

### Health Checks
```bash
# Quick connectivity test
ansible all -m ping

# Comprehensive health check
ansible-playbook playbooks/health-check.yml

# Service status check
ansible vpn_servers -m service -a "name=wireguard"
```

### Deployment
```bash
# Full infrastructure deployment
ansible-playbook playbooks/multi-protocol-deployment.yml --limit vpn_servers

# WireGuard with dashboard
ansible-playbook playbooks/wireguard-dashboard.yml --limit wireguard_servers

# Regional deployment
ansible-playbook playbooks/multi-protocol-deployment.yml --limit europe
```

### Maintenance
```bash
# Package updates
ansible-playbook playbooks/upgrade-packages.yml --extra-vars "security_only=true"

# Certificate rotation
ansible-playbook playbooks/certificate-rotation.yml

# Configuration backup
./scripts/backup-configuration.sh backup
```

### Security
```bash
# Security hardening
ansible-playbook playbooks/security-hardening.yml

# Security audit
ansible-playbook playbooks/security-audit.yml

# Emergency IP blocking
ansible-playbook playbooks/emergency-block.yml --extra-vars "block_ips=['1.2.3.4']"
```

## Configuration Management

### Inventory Structure
```
inventories/
├── production              # Main inventory
├── group_vars/            # Group variables
├── host_vars/             # Host-specific variables
└── templates/             # Configuration templates
```

### Variable Hierarchy
1. Global variables (`group_vars/all.yml`)
2. Group variables (`group_vars/[group].yml`)
3. Host variables (`host_vars/[hostname].yml`)
4. Playbook variables
5. Command-line extra variables

### Configuration Validation
```bash
# Validate inventory
./scripts/validate-inventory.py

# Validate configuration
./scripts/validate-configuration.py

# Generate configurations
ansible-playbook playbooks/generate-configurations.yml
```

## Monitoring and Alerting

### Dashboards
- **VPN Infrastructure Overview** - High-level system status
- **Server Health & Performance** - Individual server metrics
- **VPN Service Metrics** - Protocol-specific metrics
- **Security Events** - Security monitoring and alerts
- **DNS Analytics** - DNS query analysis

### Key Metrics
- **System Health:** CPU, memory, disk usage
- **VPN Metrics:** Active connections, bandwidth usage
- **Security Events:** Failed logins, blocked IPs
- **Service Availability:** Uptime and response times

### Alerting Channels
- **Slack:** Real-time notifications
- **Email:** Detailed alert information
- **PagerDuty:** Critical incident escalation

## Security Features

### Multi-Layer Security
- **Network Security:** UFW firewall, network segmentation
- **Host Security:** SSH hardening, system updates
- **Application Security:** VPN encryption, certificate management
- **Monitoring Security:** CrowdSec, Fail2Ban, audit logging

### Threat Protection
- **CrowdSec:** Collaborative threat intelligence
- **Fail2Ban:** Brute force protection
- **IP Reputation:** Automatic malicious IP blocking
- **Security Auditing:** Regular compliance checks

## Support and Resources

### Getting Help
1. **Check Documentation** - Review relevant guides
2. **Run Diagnostics** - Use built-in troubleshooting tools
3. **Check Logs** - Examine system and service logs
4. **Contact Support** - Escalate to operations team

### Emergency Contacts
- **Primary On-Call:** [Contact Information]
- **Security Team:** [Contact Information]
- **Infrastructure Team:** [Contact Information]

### Useful Links
- **Grafana Dashboards:** `https://grafana.vpn.example.com`
- **WireGuard Dashboard:** `https://server:10086`
- **Repository:** `https://github.com/company/vpn-infrastructure`

## Contributing

### Documentation Updates
1. Update relevant documentation files
2. Run documentation generator: `./scripts/generate-documentation.py`
3. Validate changes: `./scripts/validate-configuration.py`
4. Submit pull request with documentation updates

### Best Practices
- Keep documentation current with code changes
- Include examples and use cases
- Document troubleshooting procedures
- Maintain security considerations

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Generated By:** Automated Documentation Generator  
**Version:** 1.0.0
"""
        
        with open(index_file, 'w') as f:
            f.write(content)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate VPN Infrastructure documentation")
    parser.add_argument("--path", "-p", default=".", help="Base path (default: current directory)")
    parser.add_argument("--type", "-t", choices=['all', 'roles', 'playbooks', 'inventory', 'api', 'architecture', 'index'], 
                       default='all', help="Documentation type to generate")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    generator = DocumentationGenerator(args.path)
    
    if args.type == 'all':
        generator.generate_all_documentation()
    elif args.type == 'roles':
        generator.generate_role_documentation()
    elif args.type == 'playbooks':
        generator.generate_playbook_documentation()
    elif args.type == 'inventory':
        generator.generate_inventory_documentation()
    elif args.type == 'api':
        generator.generate_api_documentation()
    elif args.type == 'architecture':
        generator.generate_architecture_documentation()
    elif args.type == 'index':
        generator.generate_index_documentation()

if __name__ == "__main__":
    main()