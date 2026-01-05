# VPN Infrastructure Security Implementation

This directory contains comprehensive security playbooks for the VPN infrastructure deployment, implementing all security requirements as specified in the design document.

## Security Components

### 1. SSH Hardening (Requirement 3.1)
- **Role**: `ssh_hardening`
- **Purpose**: Implement secure SSH configuration with key-only authentication
- **Features**:
  - Root login disabled
  - Password authentication disabled
  - Strong cryptographic algorithms
  - Connection rate limiting
  - Security banner
  - Host key hardening

### 2. UFW Firewall (Requirement 3.2)
- **Role**: `ufw`
- **Purpose**: Deploy deny-by-default firewall policy
- **Features**:
  - Deny-by-default incoming policy
  - Allow outgoing traffic
  - Service-specific rules for VPN protocols
  - Rate limiting for SSH
  - Monitoring port access control

### 3. Threat Protection (Requirement 3.3)
- **Roles**: `fail2ban`, `crowdsec`
- **Purpose**: Collaborative security and brute force protection
- **Features**:
  - Fail2Ban jails for SSH, OpenVPN, WireGuard
  - CrowdSec collaborative threat intelligence
  - Centralized LAPI for decision sharing
  - Automatic IP blocking and reputation management
  - Integration with firewall systems

## Playbooks

### security-hardening.yml
**Purpose**: Complete security deployment across all VPN servers

**Usage**:
```bash
# Deploy security to all servers
ansible-playbook -i inventories/production playbooks/security-hardening.yml

# Deploy to specific region
ansible-playbook -i inventories/production playbooks/security-hardening.yml --limit europe

# Deploy with custom batch size
ansible-playbook -i inventories/production playbooks/security-hardening.yml -e batch_size=5
```

**Features**:
- Deploys all security roles in correct order
- Validates system requirements
- Generates deployment reports
- Comprehensive post-deployment validation

### emergency-security-response.yml
**Purpose**: Emergency security actions (Requirement 4.3 - 5 minute response time)

**Usage**:
```bash
# Block specific IP addresses
ansible-playbook -i inventories/production playbooks/emergency-security-response.yml \
  -e emergency_action=block_ip \
  -e emergency_block_ips='["1.2.3.4","5.6.7.8"]'

# Emergency lockdown mode
ansible-playbook -i inventories/production playbooks/emergency-security-response.yml \
  -e emergency_action=lockdown

# Unblock IP addresses
ansible-playbook -i inventories/production playbooks/emergency-security-response.yml \
  -e emergency_action=unblock_ip \
  -e emergency_unblock_ips='["1.2.3.4"]'
```

**Emergency Actions**:
- `block_ip`: Block specific IP addresses
- `block_country`: Block traffic from countries
- `lockdown`: Emergency lockdown mode
- `unblock_ip`: Remove IP blocks

### security-validation.yml
**Purpose**: Comprehensive security compliance validation

**Usage**:
```bash
# Full security validation
ansible-playbook -i inventories/production playbooks/security-validation.yml

# Quick validation (skip detailed checks)
ansible-playbook -i inventories/production playbooks/security-validation.yml --tags summary
```

**Validation Areas**:
- SSH hardening compliance
- UFW firewall configuration
- Fail2Ban jail status
- CrowdSec service health
- Security update configuration
- Network security parameters

## Security Requirements Compliance

### Requirement 3.1 - SSH Hardening
- ✅ Key-only authentication enforced
- ✅ Root login disabled
- ✅ Strong cryptographic algorithms
- ✅ Connection rate limiting
- ✅ Security banner implementation

### Requirement 3.2 - UFW Firewall
- ✅ Deny-by-default policy
- ✅ Service-specific allow rules
- ✅ Rate limiting enabled
- ✅ Monitoring access control

### Requirement 3.3 - Threat Protection
- ✅ CrowdSec collaborative security
- ✅ Fail2Ban brute force protection
- ✅ Centralized decision sharing
- ✅ Automatic threat response

### Requirement 3.5 - Security Updates
- ✅ Automatic security update configuration
- ✅ Package update validation
- ✅ Security patch management

## Configuration Variables

### Global Security Settings
```yaml
# Security deployment mode
security_deployment_mode: "production"
security_validation_enabled: true

# Emergency response configuration
emergency_batch_size: "100%"
response_timeout: 300  # 5 minutes
emergency_notification_email: "security@example.com"
```

### SSH Hardening Variables
```yaml
ssh_permit_root_login: "no"
ssh_password_authentication: "no"
ssh_max_auth_tries: 3
ssh_client_alive_interval: 300
```

### UFW Firewall Variables
```yaml
ufw_default_input_policy: deny
ufw_default_output_policy: allow
ufw_rate_limit_enabled: true
ufw_ssh_rule: allow
```

### Fail2Ban Variables
```yaml
fail2ban_ssh_maxretry: 3
fail2ban_ssh_bantime: 7200  # 2 hours
fail2ban_openvpn_enabled: true
fail2ban_wireguard_enabled: true
```

### CrowdSec Variables
```yaml
crowdsec_lapi_enabled: true  # Only on first server
crowdsec_central_api_enabled: true
crowdsec_firewall_integration: true
crowdsec_prometheus_enabled: true
```

## Monitoring and Alerting

### Security Metrics
- SSH authentication attempts
- Firewall rule hits
- Fail2Ban jail statistics
- CrowdSec decision counts
- Security update status

### Log Files
- `/var/log/security-deployment-*.log` - Deployment reports
- `/var/log/emergency-response-*.log` - Emergency action logs
- `/var/log/security-validation-*.log` - Validation reports
- `/var/log/emergency-security.log` - Emergency action audit trail

### Alert Conditions
- Failed SSH authentication attempts > threshold
- Emergency security actions executed
- Security service failures
- Firewall policy violations
- Security update failures

## Maintenance Procedures

### Daily Operations
1. Review security logs
2. Monitor CrowdSec decisions
3. Check Fail2Ban jail status
4. Validate firewall rules

### Weekly Operations
1. Run security validation playbook
2. Review emergency response logs
3. Update threat intelligence feeds
4. Security metrics analysis

### Monthly Operations
1. Security configuration review
2. Update security policies
3. Test emergency response procedures
4. Security training updates

### Quarterly Operations
1. SSH key rotation
2. Certificate renewal
3. Security audit
4. Penetration testing

## Troubleshooting

### Common Issues

#### SSH Access Problems
```bash
# Check SSH configuration
sudo sshd -t

# Review SSH logs
sudo journalctl -u ssh -f

# Temporary password access (emergency only)
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

#### UFW Firewall Issues
```bash
# Check UFW status
sudo ufw status verbose

# Reset UFW (emergency only)
sudo ufw --force reset

# Reload UFW rules
sudo ufw reload
```

#### Fail2Ban Problems
```bash
# Check jail status
sudo fail2ban-client status

# Unban IP address
sudo fail2ban-client set sshd unbanip 1.2.3.4

# Restart Fail2Ban
sudo systemctl restart fail2ban
```

#### CrowdSec Issues
```bash
# Check CrowdSec status
sudo cscli metrics

# Test LAPI connectivity
curl http://localhost:8080/v1/heartbeat

# Restart CrowdSec
sudo systemctl restart crowdsec
```

## Security Best Practices

1. **Regular Updates**: Keep all security components updated
2. **Monitoring**: Continuously monitor security metrics and logs
3. **Testing**: Regularly test emergency response procedures
4. **Documentation**: Maintain up-to-date security documentation
5. **Training**: Ensure team is trained on security procedures
6. **Backup**: Maintain secure backups of security configurations
7. **Audit**: Regular security audits and compliance checks

## Emergency Contacts

- **Security Team**: security@example.com
- **Operations Team**: ops@example.com
- **Emergency Hotline**: +1-XXX-XXX-XXXX

## Compliance and Audit

This security implementation meets the following compliance requirements:
- VPN Infrastructure Security Requirements 3.1, 3.2, 3.3, 3.5
- Emergency Response Requirement 4.3 (5-minute response time)
- Automated Operations Requirements 4.1, 4.2

All security actions are logged and auditable for compliance purposes.