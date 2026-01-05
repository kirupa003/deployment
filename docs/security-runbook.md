# VPN Infrastructure Security Runbook

## Overview

This security runbook provides comprehensive procedures for maintaining, monitoring, and responding to security incidents in the VPN Infrastructure DevOps Controller system. It covers preventive measures, incident response, and recovery procedures.

## Table of Contents

1. [Security Architecture Overview](#security-architecture-overview)
2. [Preventive Security Measures](#preventive-security-measures)
3. [Security Monitoring](#security-monitoring)
4. [Incident Response Procedures](#incident-response-procedures)
5. [Threat Detection and Analysis](#threat-detection-and-analysis)
6. [Access Control Management](#access-control-management)
7. [Certificate and Key Management](#certificate-and-key-management)
8. [Security Auditing](#security-auditing)
9. [Compliance and Reporting](#compliance-and-reporting)
10. [Emergency Response](#emergency-response)

## Security Architecture Overview

### Defense in Depth Strategy

The VPN infrastructure implements multiple security layers:

1. **Network Security:** Firewalls, network segmentation, DDoS protection
2. **Host Security:** SSH hardening, system updates, endpoint protection
3. **Application Security:** VPN protocol security, certificate management
4. **Data Security:** Encryption at rest and in transit, secure key storage
5. **Monitoring Security:** Real-time threat detection, log analysis, alerting

### Security Components

- **CrowdSec:** Collaborative threat intelligence and IP reputation
- **Fail2Ban:** Brute force protection and intrusion prevention
- **UFW Firewall:** Network access control and traffic filtering
- **SSH Hardening:** Secure remote access configuration
- **Certificate Management:** PKI and key rotation automation
- **Vault Integration:** Secure secrets management

## Preventive Security Measures

### 1. System Hardening

#### SSH Security Configuration

```bash
# Apply SSH hardening across all servers
ansible-playbook playbooks/security-hardening.yml --tags ssh

# Verify SSH configuration
ansible vpn_servers -m shell -a "sshd -T | grep -E 'passwordauthentication|permitrootlogin|pubkeyauthentication'"

# Check SSH key strength
ansible vpn_servers -m shell -a "ssh-keygen -l -f /etc/ssh/ssh_host_rsa_key.pub"
```

#### Firewall Configuration

```bash
# Deploy firewall rules
ansible-playbook playbooks/security-hardening.yml --tags firewall

# Verify firewall status
ansible vpn_servers -m shell -a "ufw status verbose"

# Check active connections
ansible vpn_servers -m shell -a "ss -tulnp"
```

#### System Updates

```bash
# Apply security updates
ansible-playbook playbooks/upgrade-packages.yml --extra-vars "security_only=true"

# Check for available updates
ansible vpn_servers -m shell -a "apt list --upgradable"

# Verify system integrity
ansible vpn_servers -m shell -a "debsums -c"
```

### 2. Access Control

#### User Management

```bash
# Review user accounts
ansible vpn_servers -m shell -a "cut -d: -f1,3,4,6,7 /etc/passwd | grep -E ':[0-9]{4}:'"

# Check sudo privileges
ansible vpn_servers -m shell -a "grep -r '' /etc/sudoers.d/"

# Audit login history
ansible vpn_servers -m shell -a "last -n 20"
```

#### SSH Key Management

```bash
# Rotate SSH keys quarterly
./scripts/ssh-key-setup.sh --rotate

# Audit authorized keys
ansible vpn_servers -m shell -a "find /home -name authorized_keys -exec wc -l {} \;"

# Remove unused keys
ansible vpn_servers -m shell -a "find /home -name authorized_keys -mtime +90"
```

### 3. Network Security

#### Port Security

```bash
# Scan for open ports
ansible vpn_servers -m shell -a "nmap -sT localhost"

# Check listening services
ansible vpn_servers -m shell -a "netstat -tlnp"

# Verify service bindings
ansible vpn_servers -m shell -a "ss -tlnp | grep -E ':22|:51820|:1194|:53'"
```

#### Network Monitoring

```bash
# Monitor network connections
ansible vpn_servers -m shell -a "netstat -an | grep ESTABLISHED | wc -l"

# Check for suspicious connections
ansible vpn_servers -m shell -a "ss -tuln | grep -v -E '127.0.0.1|::1'"

# Monitor bandwidth usage
ansible vpn_servers -m shell -a "vnstat -i eth0 --json"
```

## Security Monitoring

### 1. Real-time Threat Detection

#### CrowdSec Monitoring

```bash
# Check CrowdSec status
ansible vpn_servers -m shell -a "cscli metrics"

# Review active decisions
ansible vpn_servers -m shell -a "cscli decisions list"

# Check threat intelligence feeds
ansible vpn_servers -m shell -a "cscli collections list"

# Monitor CrowdSec alerts
ansible vpn_servers -m shell -a "cscli alerts list --limit 10"
```

#### Fail2Ban Monitoring

```bash
# Check Fail2Ban status
ansible vpn_servers -m shell -a "fail2ban-client status"

# Review banned IPs
ansible vpn_servers -m shell -a "fail2ban-client status sshd"

# Check jail statistics
ansible vpn_servers -m shell -a "fail2ban-client status | grep 'Jail list'"

# Monitor Fail2Ban logs
ansible vpn_servers -m shell -a "tail -20 /var/log/fail2ban.log"
```

### 2. Log Analysis

#### Security Log Review

```bash
# Check authentication logs
ansible vpn_servers -m shell -a "grep 'authentication failure' /var/log/auth.log | tail -10"

# Monitor sudo usage
ansible vpn_servers -m shell -a "grep 'sudo:' /var/log/auth.log | tail -10"

# Check for privilege escalation attempts
ansible vpn_servers -m shell -a "grep -i 'su:' /var/log/auth.log | tail -10"

# Review system logs for anomalies
ansible vpn_servers -m shell -a "journalctl --since '1 hour ago' | grep -i -E 'error|fail|attack|intrusion'"
```

#### VPN Security Logs

```bash
# Monitor WireGuard connections
ansible wireguard_servers -m shell -a "journalctl -u wg-quick@wg0 --since '1 hour ago'"

# Check OpenVPN authentication
ansible openvpn_servers -m shell -a "grep 'TLS Auth Error' /var/log/openvpn/server.log"

# Review DNS query logs for suspicious activity
ansible vpn_servers -m shell -a "tail -100 /var/log/coredns/query.log | grep -E 'malware|phishing|suspicious'"
```

### 3. Automated Security Scanning

#### Vulnerability Scanning

```bash
# Run security audit
ansible-playbook playbooks/security-audit.yml

# Check for rootkits
ansible vpn_servers -m shell -a "rkhunter --check --sk"

# Scan for malware
ansible vpn_servers -m shell -a "clamscan -r /home /tmp --infected --remove"

# Check file integrity
ansible vpn_servers -m shell -a "aide --check"
```

## Incident Response Procedures

### 1. Incident Classification

#### Severity Levels

- **Critical (P1):** Active attack, data breach, service unavailable
- **High (P2):** Security vulnerability, unauthorized access attempt
- **Medium (P3):** Policy violation, suspicious activity
- **Low (P4):** Security awareness, minor configuration issue

### 2. Immediate Response Actions

#### For Critical Incidents (P1)

```bash
# 1. Isolate affected systems
ansible-playbook playbooks/emergency-security-response.yml \
  --limit affected_servers \
  --extra-vars "isolate_server=true"

# 2. Block malicious IPs
ansible-playbook playbooks/emergency-block.yml \
  --extra-vars "block_ips=['malicious_ip'] block_reason='security_incident'"

# 3. Preserve evidence
ansible affected_servers -m shell -a "dd if=/dev/sda of=/tmp/disk_image.dd bs=1M"

# 4. Notify security team
# Send alert to security@company.com with incident details
```

#### For High Incidents (P2)

```bash
# 1. Increase monitoring
ansible-playbook playbooks/security-hardening.yml --tags monitoring

# 2. Review access logs
ansible vpn_servers -m shell -a "grep 'Failed password' /var/log/auth.log | tail -50"

# 3. Check for indicators of compromise
ansible vpn_servers -m shell -a "find / -name '*.suspicious' -o -name '.hidden*' 2>/dev/null"

# 4. Update security rules
ansible-playbook playbooks/security-hardening.yml --tags rules_update
```

### 3. Investigation Procedures

#### Evidence Collection

```bash
# Collect system information
ansible affected_servers -m setup > /tmp/system_info_$(date +%Y%m%d_%H%M%S).json

# Capture network state
ansible affected_servers -m shell -a "netstat -an > /tmp/network_state_$(hostname)_$(date +%Y%m%d_%H%M%S).txt"

# Collect process information
ansible affected_servers -m shell -a "ps auxf > /tmp/process_list_$(hostname)_$(date +%Y%m%d_%H%M%S).txt"

# Capture memory dump (if needed)
ansible affected_servers -m shell -a "cat /proc/kcore > /tmp/memory_dump_$(hostname)_$(date +%Y%m%d_%H%M%S).dump"
```

#### Log Analysis

```bash
# Extract relevant logs
ansible affected_servers -m shell -a "journalctl --since '24 hours ago' > /tmp/system_logs_$(hostname)_$(date +%Y%m%d_%H%M%S).log"

# Analyze authentication attempts
ansible affected_servers -m shell -a "grep -E 'sshd|sudo|su' /var/log/auth.log > /tmp/auth_analysis_$(hostname)_$(date +%Y%m%d_%H%M%S).log"

# Check for file modifications
ansible affected_servers -m shell -a "find /etc /usr/bin /usr/sbin -type f -mtime -1 > /tmp/recent_changes_$(hostname)_$(date +%Y%m%d_%H%M%S).txt"
```

## Threat Detection and Analysis

### 1. Behavioral Analysis

#### Unusual Activity Detection

```bash
# Monitor connection patterns
ansible vpn_servers -m shell -a "ss -tuln | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -nr"

# Check for unusual processes
ansible vpn_servers -m shell -a "ps aux | awk '{print \$11}' | sort | uniq -c | sort -nr | head -20"

# Monitor file access patterns
ansible vpn_servers -m shell -a "lsof | grep -E '/tmp|/var/tmp' | head -20"

# Check for unusual network traffic
ansible vpn_servers -m shell -a "iftop -t -s 10 -n"
```

#### Anomaly Detection

```bash
# Check for unusual login times
ansible vpn_servers -m shell -a "last | grep -E '(0[0-6]|2[2-3]):[0-9]{2}'"

# Monitor resource usage anomalies
ansible vpn_servers -m shell -a "top -bn1 | grep -E 'Cpu|Mem|Load'"

# Check for unusual file sizes
ansible vpn_servers -m shell -a "find /var/log -size +100M -ls"

# Monitor disk usage spikes
ansible vpn_servers -m shell -a "df -h | awk '\$5 > 90 {print \$0}'"
```

### 2. Threat Intelligence Integration

#### IP Reputation Checking

```bash
# Check IPs against threat feeds
ansible vpn_servers -m shell -a "cscli decisions list --type ban"

# Verify IP geolocation
ansible vpn_servers -m shell -a "geoiplookup \$(ss -tuln | grep :22 | awk '{print \$5}' | cut -d: -f1 | head -5)"

# Check for known malicious domains
ansible vpn_servers -m shell -a "grep -f /etc/coredns/blocklist.txt /var/log/coredns/query.log"
```

## Access Control Management

### 1. User Access Review

#### Quarterly Access Audit

```bash
# Review all user accounts
ansible vpn_servers -m shell -a "getent passwd | awk -F: '\$3 >= 1000 {print \$1,\$3,\$5}'"

# Check last login times
ansible vpn_servers -m shell -a "lastlog | grep -v 'Never logged in'"

# Review sudo access
ansible vpn_servers -m shell -a "grep -r '' /etc/sudoers.d/ | grep -v '#'"

# Check group memberships
ansible vpn_servers -m shell -a "getent group | grep -E 'sudo|admin|wheel'"
```

#### VPN User Management

```bash
# List active WireGuard peers
ansible wireguard_servers -m shell -a "wg show wg0 peers"

# Check OpenVPN client certificates
ansible openvpn_servers -m shell -a "ls -la /etc/openvpn/pki/issued/"

# Review client connection logs
ansible vpn_servers -m shell -a "grep 'peer' /var/log/wireguard/wg0.log | tail -20"

# Audit client bandwidth usage
ansible vpn_servers -m shell -a "wg show wg0 transfer"
```

### 2. Privilege Management

#### Least Privilege Enforcement

```bash
# Review file permissions
ansible vpn_servers -m shell -a "find /etc -perm -002 -type f -ls"

# Check SUID/SGID files
ansible vpn_servers -m shell -a "find / -perm -4000 -o -perm -2000 -type f 2>/dev/null"

# Audit cron jobs
ansible vpn_servers -m shell -a "crontab -l; ls -la /etc/cron.*/"

# Review service permissions
ansible vpn_servers -m shell -a "systemctl list-units --type=service --state=running | grep -v '@'"
```

## Certificate and Key Management

### 1. Certificate Lifecycle Management

#### Certificate Monitoring

```bash
# Check certificate expiry dates
ansible openvpn_servers -m shell -a "find /etc/openvpn/pki -name '*.crt' -exec openssl x509 -in {} -enddate -noout -subject \;"

# Monitor certificate usage
ansible vpn_servers -m shell -a "openssl x509 -in /etc/ssl/certs/server.crt -text -noout | grep -A2 'Validity'"

# Check certificate revocation lists
ansible openvpn_servers -m shell -a "openssl crl -in /etc/openvpn/pki/crl.pem -text -noout"
```

#### Key Rotation Procedures

```bash
# Rotate WireGuard keys (monthly)
ansible-playbook playbooks/certificate-rotation.yml --tags wireguard_keys

# Rotate OpenVPN certificates (annually)
ansible-playbook playbooks/certificate-rotation.yml --tags openvpn_certs

# Rotate SSH host keys (quarterly)
ansible-playbook playbooks/certificate-rotation.yml --tags ssh_keys

# Update CA certificates
ansible vpn_servers -m shell -a "update-ca-certificates"
```

### 2. Secure Key Storage

#### Vault Integration

```bash
# Check Vault connectivity
ansible localhost -m uri -a "url=https://vault.company.com/v1/sys/health"

# Rotate Vault tokens
ansible-vault rekey inventories/group_vars/vault.yml

# Backup encryption keys
./scripts/backup-configuration.sh backup --include-keys

# Test key recovery procedures
ansible-playbook playbooks/backup-disaster-recovery.yml --tags key_recovery --check
```

## Security Auditing

### 1. Compliance Auditing

#### Security Configuration Audit

```bash
# Run comprehensive security audit
ansible-playbook playbooks/security-audit.yml

# Check compliance with security baseline
ansible vpn_servers -m shell -a "lynis audit system --quick"

# Verify security controls
ansible-playbook playbooks/security-validation.yml

# Generate compliance report
ansible-playbook playbooks/security-audit.yml --tags compliance_report
```

#### Access Control Audit

```bash
# Audit user permissions
ansible vpn_servers -m shell -a "find /home -type f -perm -o+w -ls"

# Check file ownership
ansible vpn_servers -m shell -a "find /etc -not -user root -ls"

# Review network access controls
ansible vpn_servers -m shell -a "iptables -L -n | grep -E 'ACCEPT|DROP|REJECT'"

# Audit service configurations
ansible vpn_servers -m shell -a "systemctl show --property=User,Group wireguard openvpn"
```

### 2. Vulnerability Assessment

#### Regular Vulnerability Scans

```bash
# Run vulnerability scanner
ansible vpn_servers -m shell -a "nmap --script vuln localhost"

# Check for known vulnerabilities
ansible vpn_servers -m shell -a "apt list --installed | grep -f /tmp/vulnerable_packages.txt"

# Scan for configuration issues
ansible vpn_servers -m shell -a "chkrootkit"

# Check for weak passwords
ansible vpn_servers -m shell -a "john --test"
```

## Emergency Response

### 1. Incident Escalation

#### Emergency Contacts

- **Security Team Lead:** [Phone/Email]
- **CISO:** [Phone/Email]
- **Legal Team:** [Phone/Email]
- **External IR Firm:** [Phone/Email]

#### Escalation Triggers

- Active data exfiltration
- Ransomware detection
- Privilege escalation
- Multiple system compromise

### 2. Emergency Procedures

#### Immediate Containment

```bash
# Emergency shutdown of affected services
ansible affected_servers -m service -a "name=wireguard state=stopped"
ansible affected_servers -m service -a "name=openvpn state=stopped"

# Network isolation
ansible affected_servers -m shell -a "iptables -P INPUT DROP; iptables -P OUTPUT DROP"

# Preserve evidence
ansible affected_servers -m shell -a "mount -o remount,ro /"

# Notify stakeholders
# Execute communication plan
```

#### Recovery Procedures

```bash
# Restore from clean backups
ansible-playbook playbooks/backup-disaster-recovery.yml --tags restore

# Rebuild compromised systems
ansible-playbook playbooks/server-provisioning.yml --limit compromised_servers

# Restore services gradually
ansible-playbook playbooks/multi-protocol-deployment.yml --limit recovered_servers

# Verify system integrity
ansible-playbook playbooks/security-validation.yml --limit recovered_servers
```

## Security Metrics and KPIs

### Key Security Indicators

- **Mean Time to Detection (MTTD):** < 15 minutes
- **Mean Time to Response (MTTR):** < 30 minutes
- **False Positive Rate:** < 5%
- **Security Patch Compliance:** > 95%
- **Certificate Expiry Monitoring:** 30-day advance notice

### Monitoring Dashboard

- Failed authentication attempts
- Blocked IP addresses
- Certificate expiry timeline
- Security patch status
- Vulnerability scan results

## Compliance and Reporting

### Regular Security Reports

- **Daily:** Security event summary
- **Weekly:** Threat intelligence report
- **Monthly:** Security metrics dashboard
- **Quarterly:** Compliance audit report
- **Annually:** Security posture assessment

### Documentation Requirements

- Incident response logs
- Security configuration changes
- Access control modifications
- Certificate management activities
- Compliance audit results