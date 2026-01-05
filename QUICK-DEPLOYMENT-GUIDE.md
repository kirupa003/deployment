# Quick Deployment Guide - VPN Infrastructure

**🚀 Ready to deploy 30 VPN servers across 3 regions TODAY!**

This consolidated infrastructure combines the best of both `planet-proxy-devops-controller` and `the-deployment` projects for immediate production deployment.

## ⚡ Pre-Deployment Checklist (5 minutes)

### 1. Prerequisites Check
```bash
# Verify Ansible installation
ansible --version  # Should be 2.12+

# Check Python dependencies
python3 -c "import jinja2, yaml, netaddr; print('Dependencies OK')"

# Verify SSH key exists
ls -la ~/.ssh/ansible_ed25519*
```

### 2. Server Access Validation
```bash
# Test connectivity to all servers
cd the-deployment
ansible all -m ping

# If SSH keys need setup:
./scripts/ssh-key-setup.sh
./scripts/bulk-ssh-bootstrap.sh
```

### 3. Install Required Collections
```bash
# Install all required Ansible collections and roles
ansible-galaxy install -r requirements.yml
```

## 🎯 Immediate Deployment (30 minutes)

### Step 1: Configure Your Servers (5 minutes)
Edit the inventory file with your actual server IPs:
```bash
vim inventories/production/hosts.yml
```

**Replace the example IPs with your actual server IPs:**
- Europe: 12 servers (185.199.108.153 → your-eu-ips)
- North America: 10 servers (192.241.128.100 → your-na-ips)  
- Asia Pacific: 8 servers (203.175.10.200 → your-ap-ips)

### Step 2: Initialize Secrets (5 minutes)
```bash
# Initialize vault password
./scripts/init-vault.sh

# Generate WireGuard keys for all servers
./scripts/generate-wireguard-keys.sh

# Generate OpenVPN PKI
./scripts/generate-openvpn-pki.sh
```

### Step 3: Deploy Infrastructure (20 minutes)
Choose your deployment strategy:

#### Option A: Full Multi-Protocol Deployment (Recommended)
```bash
# Deploy everything to all servers
ansible-playbook playbooks/multi-protocol-deployment.yml
```

#### Option B: Service-Specific Deployment
```bash
# WireGuard with Dashboard only
ansible-playbook playbooks/deploy/wireguard-dashboard.yml

# OpenVPN only
ansible-playbook playbooks/openvpn-deployment.yml

# DNS and monitoring
ansible-playbook playbooks/deploy-coredns.yml
```

#### Option C: Regional Deployment
```bash
# Deploy to Europe first
ansible-playbook playbooks/multi-protocol-deployment.yml --limit europe

# Then North America
ansible-playbook playbooks/multi-protocol-deployment.yml --limit north_america

# Finally Asia Pacific
ansible-playbook playbooks/multi-protocol-deployment.yml --limit asia_pacific
```

## 🔍 Post-Deployment Validation (10 minutes)

### 1. Health Check
```bash
# Comprehensive health check
ansible-playbook playbooks/health-check.yml

# Service status validation
ansible-playbook playbooks/server-health-validation.yml
```

### 2. Access Your Services

#### WireGuard Dashboard
- **URL**: `http://<server-ip>:10086`
- **Username**: `admin`
- **Password**: Check vault file

#### Monitoring
- **Node Exporter**: `http://<server-ip>:9100/metrics`
- **WireGuard Exporter**: `http://<server-ip>:9586/metrics`
- **OpenVPN Exporter**: `http://<server-ip>:9176/metrics`

### 3. Test VPN Connections
```bash
# Generate client configs
ansible-playbook playbooks/configure/generate-client-configs.yml

# Test connectivity
ansible vpn_servers -m shell -a "wg show"
ansible openvpn_servers -m shell -a "systemctl status openvpn@server"
```

## 🛠️ Daily Operations

### Health Monitoring
```bash
# Daily health check
ansible-playbook playbooks/health-check.yml

# Security updates
ansible-playbook playbooks/upgrade-packages.yml --extra-vars "security_only=true"
```

### Client Management
```bash
# Add new WireGuard client
ansible-playbook playbooks/configure/add-wireguard-client.yml -e "client_name=new-user"

# Generate OpenVPN client certificate
ansible-playbook playbooks/configure/generate-openvpn-client.yml -e "client_name=new-user"
```

### Maintenance
```bash
# Rotate WireGuard keys
ansible-playbook playbooks/configure/rotate-keys.yml

# Certificate renewal
ansible-playbook playbooks/certificate-rotation.yml

# Backup configurations
./scripts/backup-configuration.sh backup
```

## 🚨 Emergency Procedures

### Block Malicious IP
```bash
ansible-playbook playbooks/emergency-block.yml -e "block_ip=1.2.3.4"
```

### Security Incident Response
```bash
ansible-playbook playbooks/emergency-security-response.yml
```

### Server Recovery
```bash
# If a server goes down
ansible-playbook playbooks/server-health-validation.yml --limit failed-server
ansible-playbook playbooks/multi-protocol-deployment.yml --limit failed-server
```

## 📊 What You Get

### VPN Services Deployed
- ✅ **WireGuard** with web dashboard (port 10086)
- ✅ **OpenVPN** with PKI management (ports 1194/443)
- ✅ **AmneziaWG** for censorship circumvention (port 51821)
- ✅ **CoreDNS** with ad-blocking (port 53)

### Security Stack
- ✅ **SSH Hardening** with key-only authentication
- ✅ **UFW Firewall** with production rules
- ✅ **Fail2Ban** for intrusion prevention
- ✅ **CrowdSec** for collaborative threat intelligence

### Monitoring & Observability
- ✅ **Node Exporter** for system metrics (port 9100)
- ✅ **WireGuard Exporter** for VPN metrics (port 9586)
- ✅ **OpenVPN Exporter** for OpenVPN metrics (port 9176)
- ✅ **Promtail** for log shipping
- ✅ **Fluent Bit** for DNS analytics

### Infrastructure Management
- ✅ **Automated backups** and configuration management
- ✅ **Health monitoring** and validation
- ✅ **Certificate rotation** automation
- ✅ **Multi-region deployment** support

## 🔧 Customization

### Modify Server Configuration
Edit group variables:
```bash
vim inventories/production/group_vars/all.yml
vim inventories/production/group_vars/vpn_servers.yml
vim inventories/production/group_vars/wireguard_servers.yml
```

### Regional Settings
```bash
vim inventories/production/group_vars/europe.yml
vim inventories/production/group_vars/north_america.yml
vim inventories/production/group_vars/asia_pacific.yml
```

### Add New Servers
1. Add to `inventories/production/hosts.yml`
2. Generate keys: `./scripts/generate-wireguard-keys.sh`
3. Deploy: `ansible-playbook playbooks/multi-protocol-deployment.yml --limit new-server`

## 📞 Support

### Troubleshooting
- Check logs: `tail -f logs/ansible.log`
- Service status: `ansible vpn_servers -m service -a "name=wireguard"`
- System info: `ansible all -m setup`

### Documentation
- **Architecture**: `docs/ARCHITECTURE.md`
- **Security**: `docs/SECRETS.md`
- **SSH Management**: `docs/SSH-KEY-MANAGEMENT.md`
- **Troubleshooting**: `docs/troubleshooting-guide.md`

---

**🎉 Your production VPN infrastructure is ready! Deploy with confidence.**