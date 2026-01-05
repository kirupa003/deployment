# VPN Infrastructure Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying and managing the VPN Infrastructure DevOps Controller system. The system supports automated deployment of 30 VPN servers across 3 regions using Ansible automation.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration Management](#configuration-management)
4. [Deployment Procedures](#deployment-procedures)
5. [Monitoring Setup](#monitoring-setup)
6. [Security Configuration](#security-configuration)
7. [Maintenance Operations](#maintenance-operations)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Control Node:** Linux system with Ansible 2.12+
- **Target Servers:** Ubuntu 20.04+ or Debian 11+ (30 servers across 3 regions)
- **Network:** SSH access to all target servers
- **Storage:** Minimum 50GB for backups and logs

### Required Software

```bash
# Install Ansible and dependencies
sudo apt update
sudo apt install -y ansible python3-pip git
pip3 install jinja2 pyyaml netaddr

# Install additional tools
sudo apt install -y jq curl wget unzip
```

### Access Requirements

- SSH key-based authentication to all servers
- Sudo privileges on target servers
- Internet access for package downloads
- DNS resolution for all server hostnames

## Initial Setup

### 1. Clone and Configure Repository

```bash
# Clone the repository
git clone <repository-url>
cd vpn-infrastructure-deployment

# Set up vault password
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass

# Initialize SSH keys
./scripts/ssh-key-setup.sh
```

### 2. Configure Inventory

```bash
# Edit production inventory
vim inventories/production

# Configure group variables
vim inventories/group_vars/all.yml
vim inventories/group_vars/vpn_servers.yml

# Configure host-specific variables
vim inventories/host_vars/server1.example.com.yml
```

### 3. Validate Configuration

```bash
# Validate inventory and configuration
./scripts/validate-inventory.py
./scripts/validate-configuration.py

# Test connectivity
ansible all -m ping
```

## Configuration Management

### Environment Configuration

The system uses Jinja2 templates for environment-specific configurations:

```bash
# Generate configurations from templates
ansible-playbook playbooks/generate-configurations.yml \
  -e environment_name=production \
  -e domain_name=vpn.example.com

# Validate generated configurations
./scripts/validate-configuration.py --path generated-configs/
```

### Variable Management

Configuration variables are organized hierarchically:

1. **Global Variables:** `inventories/group_vars/all.yml`
2. **Group Variables:** `inventories/group_vars/[group].yml`
3. **Host Variables:** `inventories/host_vars/[hostname].yml`
4. **Environment Templates:** `inventories/templates/`

### Configuration Backup

```bash
# Create configuration backup
./scripts/backup-configuration.sh backup

# List available backups
./scripts/backup-configuration.sh list

# Restore from backup
./scripts/backup-configuration.sh restore config_backup_20240105_143022.tar.gz
```

## Deployment Procedures

### Full Infrastructure Deployment

```bash
# Deploy complete VPN infrastructure
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --limit vpn_servers \
  --extra-vars "batch_size=10"
```

### Service-Specific Deployments

#### WireGuard with Dashboard

```bash
# Deploy WireGuard servers with web dashboard
ansible-playbook playbooks/wireguard-dashboard.yml \
  --limit wireguard_servers
```

#### OpenVPN Deployment

```bash
# Deploy OpenVPN servers with PKI
ansible-playbook playbooks/openvpn-deployment.yml \
  --limit openvpn_servers
```

#### CoreDNS Deployment

```bash
# Deploy DNS service with ad-blocking
ansible-playbook playbooks/deploy-coredns.yml \
  --limit vpn_servers
```

### Regional Deployments

```bash
# Deploy to specific region
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --limit europe

# Deploy with rolling updates
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --limit vpn_servers \
  --extra-vars "serial=5"
```

## Monitoring Setup

### Metrics Collection

```bash
# Deploy monitoring stack
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --tags monitoring \
  --limit vpn_servers

# Verify monitoring agents
ansible vpn_servers -m service -a "name=node_exporter state=started"
ansible wireguard_servers -m service -a "name=wg_exporter state=started"
```

### Log Shipping

```bash
# Configure log shipping
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --tags logging \
  --limit vpn_servers

# Check log shipping status
ansible vpn_servers -m service -a "name=promtail state=started"
```

### Dashboard Access

- **Grafana:** `https://grafana.vpn.example.com`
- **WireGuard Dashboard:** `https://server:10086`
- **Prometheus:** `https://prometheus.vpn.example.com`

## Security Configuration

### SSH Hardening

```bash
# Apply SSH security hardening
ansible-playbook playbooks/security-hardening.yml \
  --tags ssh \
  --limit vpn_servers
```

### Firewall Configuration

```bash
# Configure UFW firewall
ansible-playbook playbooks/security-hardening.yml \
  --tags firewall \
  --limit vpn_servers

# Verify firewall status
ansible vpn_servers -m shell -a "ufw status verbose"
```

### Security Monitoring

```bash
# Deploy CrowdSec and Fail2Ban
ansible-playbook playbooks/security-hardening.yml \
  --tags security_monitoring \
  --limit vpn_servers

# Check security services
ansible vpn_servers -m service -a "name=crowdsec state=started"
ansible vpn_servers -m service -a "name=fail2ban state=started"
```

## Maintenance Operations

### Health Checks

```bash
# Run comprehensive health check
ansible-playbook playbooks/health-check.yml

# Check specific services
ansible-playbook playbooks/server-health-validation.yml \
  --limit europe
```

### Package Updates

```bash
# Update packages with rolling deployment
ansible-playbook playbooks/upgrade-packages.yml \
  --extra-vars "batch_size=5 reboot_required=true"

# Security updates only
ansible-playbook playbooks/upgrade-packages.yml \
  --extra-vars "security_only=true"
```

### Certificate Management

```bash
# Rotate certificates
ansible-playbook playbooks/certificate-rotation.yml \
  --limit openvpn_servers

# Check certificate expiry
ansible-playbook playbooks/health-check.yml \
  --tags certificates
```

### Backup Operations

```bash
# Create infrastructure backup
ansible-playbook playbooks/backup-disaster-recovery.yml \
  --tags backup

# Restore from backup
ansible-playbook playbooks/backup-disaster-recovery.yml \
  --tags restore \
  --extra-vars "backup_date=2024-01-05"
```

## Troubleshooting

### Common Issues

#### SSH Connection Problems

```bash
# Test SSH connectivity
ansible all -m ping -vvv

# Check SSH configuration
ansible-playbook playbooks/health-check.yml --tags ssh

# Reset SSH keys
./scripts/bulk-ssh-bootstrap.sh
```

#### Service Failures

```bash
# Check service status
ansible vpn_servers -m service -a "name=wireguard state=started"

# View service logs
ansible vpn_servers -m shell -a "journalctl -u wireguard -n 50"

# Restart services
ansible vpn_servers -m service -a "name=wireguard state=restarted"
```

#### Network Connectivity

```bash
# Test VPN connectivity
ansible-playbook playbooks/server-health-validation.yml \
  --tags network

# Check firewall rules
ansible vpn_servers -m shell -a "ufw status numbered"

# Verify DNS resolution
ansible vpn_servers -m shell -a "nslookup google.com"
```

### Emergency Procedures

#### Emergency IP Blocking

```bash
# Block malicious IPs across all servers
ansible-playbook playbooks/emergency-block.yml \
  --extra-vars "block_ips=['1.2.3.4','5.6.7.8']"
```

#### Security Incident Response

```bash
# Run security audit
ansible-playbook playbooks/security-audit.yml

# Emergency security response
ansible-playbook playbooks/emergency-security-response.yml
```

#### Server Decommissioning

```bash
# Safely decommission server
ansible-playbook playbooks/server-decommissioning.yml \
  --limit server-to-remove.example.com \
  --extra-vars "drain_connections=true"
```

### Log Analysis

#### Common Log Locations

- **System Logs:** `/var/log/syslog`
- **VPN Logs:** `/var/log/wireguard/`, `/var/log/openvpn/`
- **Security Logs:** `/var/log/crowdsec/`, `/var/log/fail2ban.log`
- **DNS Logs:** `/var/log/coredns/`

#### Log Analysis Commands

```bash
# Check VPN connection logs
ansible vpn_servers -m shell -a "tail -f /var/log/wireguard/wg0.log"

# Monitor security events
ansible vpn_servers -m shell -a "tail -f /var/log/crowdsec/crowdsec.log"

# Analyze DNS queries
ansible vpn_servers -m shell -a "tail -f /var/log/coredns/query.log"
```

## Performance Optimization

### System Tuning

```bash
# Apply performance optimizations
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --tags performance \
  --limit vpn_servers
```

### Monitoring Performance

```bash
# Check system performance
ansible vpn_servers -m shell -a "top -bn1 | head -20"

# Monitor network usage
ansible vpn_servers -m shell -a "iftop -t -s 10"

# Check disk usage
ansible vpn_servers -m shell -a "df -h"
```

## Best Practices

### Deployment Best Practices

1. **Always validate configurations before deployment**
2. **Use rolling deployments for production updates**
3. **Create backups before major changes**
4. **Test in staging environment first**
5. **Monitor deployment progress and logs**

### Security Best Practices

1. **Regularly rotate SSH keys and certificates**
2. **Keep systems updated with security patches**
3. **Monitor security logs and alerts**
4. **Use strong passwords and encryption**
5. **Implement network segmentation**

### Operational Best Practices

1. **Automate routine maintenance tasks**
2. **Document all configuration changes**
3. **Maintain comprehensive monitoring**
4. **Regular backup and disaster recovery testing**
5. **Keep runbooks updated and accessible**

## Support and Resources

### Documentation

- [Troubleshooting Guide](troubleshooting-guide.md)
- [Security Runbook](security-runbook.md)
- [Monitoring Guide](monitoring-guide.md)
- [API Documentation](api-documentation.md)

### Emergency Contacts

- **Primary On-Call:** [Contact Information]
- **Secondary On-Call:** [Contact Information]
- **Security Team:** [Contact Information]
- **Infrastructure Team:** [Contact Information]

### Useful Commands Reference

```bash
# Quick status check
ansible all -m ping

# Service status
ansible vpn_servers -m service -a "name=wireguard"

# System information
ansible vpn_servers -m setup -a "filter=ansible_distribution*"

# Disk space
ansible vpn_servers -m shell -a "df -h"

# Memory usage
ansible vpn_servers -m shell -a "free -h"
```