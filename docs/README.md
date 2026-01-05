# VPN Infrastructure Documentation

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

**Last Updated:** 2026-01-05 16:24:16  
**Generated By:** Automated Documentation Generator  
**Version:** 1.0.0
