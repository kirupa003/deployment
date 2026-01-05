# VPN Infrastructure DevOps Controller - Production Ready

**🚀 Enterprise-grade Ansible automation for managing 30+ VPN servers across 3 geographic regions**

*Consolidated from planet-proxy-devops-controller and the-deployment for immediate production deployment*

[![Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen)](QUICK-DEPLOYMENT-GUIDE.md)
[![Servers](https://img.shields.io/badge/servers-30%2B-blue)](#inventory-structure)
[![Protocols](https://img.shields.io/badge/protocols-WireGuard%20%7C%20OpenVPN%20%7C%20AmneziaWG-orange)](#vpn-services)
[![Regions](https://img.shields.io/badge/regions-3%20continents-purple)](#multi-region-deployment)

## 🎯 Quick Start - Deploy Today!

**Ready to deploy? See the [QUICK DEPLOYMENT GUIDE](QUICK-DEPLOYMENT-GUIDE.md) for immediate deployment.**

### Prerequisites (2 minutes)
```bash
# Install Ansible and dependencies
pip install ansible jmespath netaddr

# Install collections and roles
ansible-galaxy install -r requirements.yml

# Verify SSH access
ansible all -m ping
```

### Deploy Infrastructure (30 minutes)
```bash
# 1. Configure your server IPs
vim inventories/production/hosts.yml

# 2. Initialize secrets and keys
./scripts/init-vault.sh
./scripts/generate-wireguard-keys.sh

# 3. Deploy everything
ansible-playbook playbooks/multi-protocol-deployment.yml
```

**🎉 That's it! Your production VPN infrastructure is ready.**

## 📋 What This Deploys - Production Ready Stack

### 🔐 VPN Services (Multi-Protocol Support)
- **WireGuard** with Docker-based web dashboard (port 10086)
- **OpenVPN** with full PKI certificate management (ports 1194/443)
- **AmneziaWG** for censorship circumvention (port 51821)
- **CoreDNS** with ad-blocking and DNS analytics (port 53)

### 🛡️ Enterprise Security Stack
- **SSH Hardening** with key-only authentication and fail2ban
- **UFW Firewall** with production-grade security rules
- **CrowdSec** collaborative threat intelligence platform
- **Fail2Ban** intrusion prevention with VPN-specific jails
- **Cloudflare Tunnel** for zero-trust access (optional)

### 📊 Comprehensive Monitoring & Observability
- **Node Exporter** for system metrics (port 9100)
- **WireGuard Exporter** for VPN connection metrics (port 9586)
- **OpenVPN Exporter** for OpenVPN statistics (port 9176)
- **DNS Analytics** for query monitoring and analysis
- **Promtail** for centralized log shipping to Loki
- **Fluent Bit** for DNS query analytics
- **Grafana Dashboards** for visualization (imported from monitoring/)

### 🏗️ Infrastructure Management
- **Multi-Region Deployment** across Europe, North America, Asia Pacific
- **Automated Backups** with S3 integration and retention policies
- **Health Monitoring** with comprehensive validation playbooks
- **Certificate Rotation** automation for OpenVPN and system certificates
- **GitOps Integration** with drift detection and remediation
- **Secrets Management** with Ansible Vault and HashiCorp Vault support

## 🏗️ Consolidated Architecture - Production Grade

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONTROL PLANE (Enhanced)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Ansible       │  │   Monitoring    │  │   Security      │     │
│  │   Controller    │  │   Stack         │  │   Management    │     │
│  │   + Vault       │  │   + Analytics   │  │   + Zero Trust  │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        EDGE LAYER (30+ Servers)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   EUROPE (12)   │  │ NORTH AMERICA   │  │ ASIA PACIFIC    │     │
│  │                 │  │     (10)        │  │     (8)         │     │
│  │ • WireGuard     │  │ • WireGuard     │  │ • WireGuard     │     │
│  │ • OpenVPN       │  │ • OpenVPN       │  │ • OpenVPN       │     │
│  │ • AmneziaWG     │  │ • AmneziaWG     │  │ • AmneziaWG     │     │
│  │ • Dashboard     │  │ • Dashboard     │  │ • Dashboard     │     │
│  │ • CoreDNS       │  │ • CoreDNS       │  │ • CoreDNS       │     │
│  │ • Monitoring    │  │ • Monitoring    │  │ • Monitoring    │     │
│  │ • Security      │  │ • Security      │  │ • Security      │     │
│  │ • Analytics     │  │ • Analytics     │  │ • Analytics     │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### 🔧 Enhanced Role Library (20+ Production Roles)
```
roles/
├── Core Infrastructure
│   ├── common/              # Base system configuration
│   ├── hardening/           # Security hardening (enhanced)
│   ├── ssh_hardening/       # SSH security configuration
│   └── ufw/                 # Firewall management
├── VPN Protocols
│   ├── wireguard/           # WireGuard VPN server
│   ├── wg_dashboard/        # Docker-based WireGuard UI
│   ├── openvpn/             # OpenVPN with PKI
│   └── amneziawg/           # Obfuscated WireGuard
├── Security & Monitoring
│   ├── fail2ban/            # Intrusion prevention
│   ├── crowdsec/            # Collaborative security
│   ├── cloudflare_tunnel/   # Zero-trust access
│   ├── node_exporter/       # System metrics
│   ├── wg_exporter/         # WireGuard metrics
│   ├── openvpn_exporter/    # OpenVPN metrics
│   └── dns_analytics/       # DNS monitoring
├── Infrastructure Services
│   ├── coredns/             # DNS with ad-blocking
│   ├── promtail/            # Log shipping
│   ├── fluent_bit/          # Log processing
│   ├── vpn_config_api/      # Configuration API
│   └── vpn_config_db/       # Configuration database
└── Monitoring
    └── monitoring/          # Centralized monitoring
```

## 🚀 Production Deployment Options

### Option 1: Full Multi-Protocol Deployment (Recommended)
```bash
# Deploy everything to all 30 servers
ansible-playbook playbooks/multi-protocol-deployment.yml

# With custom batch size for controlled rollout
ansible-playbook playbooks/multi-protocol-deployment.yml -e "batch_size=5"
```

### Option 2: Service-Specific Deployments
```bash
# WireGuard with Dashboard (Docker-based)
ansible-playbook playbooks/deploy/wireguard-dashboard.yml

# OpenVPN with PKI management
ansible-playbook playbooks/openvpn-deployment.yml

# DNS and monitoring services
ansible-playbook playbooks/deploy-coredns.yml
```

### Option 3: Regional Deployments
```bash
# Deploy to Europe (12 servers)
ansible-playbook playbooks/multi-protocol-deployment.yml --limit europe

# Deploy to North America (10 servers)
ansible-playbook playbooks/multi-protocol-deployment.yml --limit north_america

# Deploy to Asia Pacific (8 servers)
ansible-playbook playbooks/multi-protocol-deployment.yml --limit asia_pacific
```

### Option 4: Protocol-Specific Deployments
```bash
# WireGuard servers only
ansible-playbook playbooks/multi-protocol-deployment.yml --limit wireguard_servers

# OpenVPN servers only
ansible-playbook playbooks/multi-protocol-deployment.yml --limit openvpn_servers

# AmneziaWG servers only
ansible-playbook playbooks/multi-protocol-deployment.yml --limit amneziawg_servers
```

## 📊 Multi-Region Inventory Structure

### Production Inventory (30 Servers)
```yaml
# inventories/production/hosts.yml
all:
  children:
    vpn_servers:
      children:
        europe:          # 12 servers
          hosts:
            eu-wg-001: { ansible_host: "185.199.108.153", protocols: [wireguard, amneziawg] }
            eu-wg-002: { ansible_host: "185.199.109.154", protocols: [wireguard, openvpn] }
            # ... 10 more EU servers
        north_america:   # 10 servers  
          hosts:
            na-wg-001: { ansible_host: "192.241.128.100", protocols: [wireguard, amneziawg] }
            na-wg-002: { ansible_host: "192.241.129.101", protocols: [wireguard, openvpn] }
            # ... 8 more NA servers
        asia_pacific:    # 8 servers
          hosts:
            ap-wg-001: { ansible_host: "203.175.10.200", protocols: [wireguard, amneziawg] }
            ap-wg-002: { ansible_host: "203.175.11.201", protocols: [wireguard, openvpn] }
            # ... 6 more AP servers
```

### Protocol Distribution
| Region | WireGuard | OpenVPN | AmneziaWG | Total |
|--------|-----------|---------|-----------|-------|
| Europe | 8 servers | 7 servers | 5 servers | 12 |
| North America | 6 servers | 6 servers | 4 servers | 10 |
| Asia Pacific | 6 servers | 4 servers | 4 servers | 8 |
| **Total** | **20** | **17** | **13** | **30** |

## 📊 Management Commands

### Daily Operations

```bash
# Health check
ansible-playbook playbooks/health-check.yml

# Package updates
ansible-playbook playbooks/upgrade-packages.yml \
  --extra-vars "security_only=true"

# Configuration backup
./scripts/backup-configuration.sh backup
```

### Maintenance Operations

```bash
# Certificate rotation
ansible-playbook playbooks/certificate-rotation.yml

# Security hardening
ansible-playbook playbooks/security-hardening.yml

# Drift detection
./scripts/drift-detection.py --auto-detect
```

### Emergency Procedures

```bash
# Emergency IP blocking
ansible-playbook playbooks/emergency-block.yml \
  --extra-vars "block_ips=['1.2.3.4','5.6.7.8']"

# Security incident response
ansible-playbook playbooks/emergency-security-response.yml

# Server decommissioning
ansible-playbook playbooks/server-decommissioning.yml \
  --limit server-to-remove.example.com
```

## 🔧 Configuration Management

### Inventory Structure
```
inventories/
├── production              # Main inventory file
├── group_vars/            # Group-specific variables
│   ├── all.yml           # Global settings
│   ├── vpn_servers.yml   # VPN server config
│   ├── europe.yml        # Europe region config
│   └── ...
├── host_vars/            # Host-specific variables
└── templates/            # Configuration templates
```

### Variable Hierarchy
1. Global variables (`group_vars/all.yml`)
2. Group variables (`group_vars/[group].yml`)
3. Host variables (`host_vars/[hostname].yml`)
4. Playbook variables
5. Command-line extra variables

### Configuration Templates
```bash
# Generate configurations from templates
ansible-playbook playbooks/generate-configurations.yml \
  -e environment_name=production \
  -e domain_name=vpn.example.com
```

## 🔐 Security Features

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

## 📈 Monitoring & Alerting

### Dashboards
- **VPN Infrastructure Overview** - High-level system status
- **Server Health & Performance** - Individual server metrics
- **VPN Service Metrics** - Protocol-specific metrics
- **Security Events** - Security monitoring and alerts
- **DNS Analytics** - DNS query analysis

### Key Metrics
- System health (CPU, memory, disk)
- VPN metrics (connections, bandwidth)
- Security events (failed logins, blocked IPs)
- Service availability (uptime, response times)

### Access Dashboards
- **Grafana:** `https://grafana.vpn.example.com`
- **WireGuard Dashboard:** `https://server:10086`

## 🚨 Troubleshooting

### Common Issues

#### SSH Connection Problems
```bash
# Test connectivity
ansible all -m ping -vvv

# Reset SSH keys
./scripts/bulk-ssh-bootstrap.sh
```

#### Service Failures
```bash
# Check service status
ansible vpn_servers -m service -a "name=wireguard"

# View logs
ansible vpn_servers -m shell -a "journalctl -u wireguard -n 50"
```

#### Configuration Issues
```bash
# Validate configuration
./scripts/validate-configuration.py

# Check for drift
./scripts/drift-detection.py
```

### Emergency Contacts
- **Primary On-Call:** [Your Contact]
- **Security Team:** [Security Contact]
- **Infrastructure Team:** [Infrastructure Contact]

## 📚 Documentation

### Complete Documentation
- **[Deployment Guide](docs/deployment-guide.md)** - Detailed deployment procedures
- **[Troubleshooting Guide](docs/troubleshooting-guide.md)** - Problem resolution
- **[Security Runbook](docs/security-runbook.md)** - Security operations
- **[API Documentation](docs/api-documentation.md)** - API reference
- **[Architecture Overview](docs/architecture-overview.md)** - System design

### Quick References
- **[Roles Documentation](docs/roles/README.md)** - Ansible roles reference
- **[Playbooks Documentation](docs/playbooks/README.md)** - Playbook usage
- **[Inventory Structure](docs/inventory-structure.md)** - Inventory organization

## 🔄 CI/CD Integration

### GitHub Actions Pipeline
- **Validation:** Configuration and syntax validation
- **Testing:** Automated deployment testing
- **Staging:** Deployment to staging environment
- **Production:** Controlled production deployment
- **Monitoring:** Health checks and drift detection

### GitOps Workflow
```bash
# Sync from Git repository
ansible-playbook playbooks/gitops-sync.yml

# Detect configuration drift
./scripts/drift-detection.py --auto-detect --auto-remediate
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch
3. Make changes and test
4. Run validation: `./scripts/validate-configuration.py`
5. Submit pull request

### Testing
```bash
# Validate changes
./scripts/validate-configuration.py

# Test in staging
ansible-playbook playbooks/multi-protocol-deployment.yml \
  --inventory inventories/staging \
  --check
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help
1. Check the [troubleshooting guide](docs/troubleshooting-guide.md)
2. Review [documentation](docs/README.md)
3. Open an issue on GitHub
4. Contact the operations team

### Useful Commands Reference
```bash
# Quick status check
ansible all -m ping

# Service status
ansible vpn_servers -m service -a "name=wireguard"

# System information
ansible vpn_servers -m setup -a "filter=ansible_distribution*"

# Resource usage
ansible vpn_servers -m shell -a "top -bn1 | head -5; free -h; df -h /"
```

---

**🎯 Ready to deploy your VPN infrastructure? Start with the [Quick Start](#-quick-start) guide above!**