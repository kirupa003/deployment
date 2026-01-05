# VPN Infrastructure Troubleshooting Guide

## Overview

This guide provides systematic troubleshooting procedures for common issues in the VPN Infrastructure DevOps Controller system. Follow the diagnostic steps in order and escalate to the next level if issues persist.

## Table of Contents

1. [General Troubleshooting Approach](#general-troubleshooting-approach)
2. [SSH and Connectivity Issues](#ssh-and-connectivity-issues)
3. [VPN Service Problems](#vpn-service-problems)
4. [Monitoring and Logging Issues](#monitoring-and-logging-issues)
5. [Security-Related Problems](#security-related-problems)
6. [Performance Issues](#performance-issues)
7. [Certificate and PKI Problems](#certificate-and-pki-problems)
8. [Network Configuration Issues](#network-configuration-issues)
9. [Emergency Procedures](#emergency-procedures)

## General Troubleshooting Approach

### 1. Initial Assessment

```bash
# Check overall system status
ansible all -m ping

# Verify Ansible configuration
ansible-config dump --only-changed

# Check inventory
ansible-inventory --list

# Validate configuration
./scripts/validate-configuration.py
```

### 2. Gather System Information

```bash
# System information
ansible vpn_servers -m setup -a "filter=ansible_distribution*"

# Service status overview
ansible vpn_servers -m shell -a "systemctl status wireguard openvpn crowdsec fail2ban"

# Resource usage
ansible vpn_servers -m shell -a "top -bn1 | head -10"
ansible vpn_servers -m shell -a "df -h"
ansible vpn_servers -m shell -a "free -h"
```

### 3. Check Logs

```bash
# System logs
ansible vpn_servers -m shell -a "journalctl -n 50 --no-pager"

# Service-specific logs
ansible vpn_servers -m shell -a "journalctl -u wireguard -n 20 --no-pager"
ansible vpn_servers -m shell -a "journalctl -u openvpn -n 20 --no-pager"
```

## SSH and Connectivity Issues

### Problem: Cannot Connect to Servers

#### Symptoms
- `ansible all -m ping` fails
- SSH timeouts or connection refused
- Authentication failures

#### Diagnostic Steps

```bash
# Test direct SSH connection
ssh -v ansible@server.example.com

# Check SSH service on target
ansible server.example.com -m shell -a "systemctl status ssh" -u root --ask-pass

# Verify SSH configuration
ansible server.example.com -m shell -a "sshd -T" -u root --ask-pass

# Check network connectivity
ping server.example.com
telnet server.example.com 22
```

#### Solutions

1. **SSH Service Down**
   ```bash
   # Restart SSH service (requires console access)
   sudo systemctl restart ssh
   sudo systemctl enable ssh
   ```

2. **Firewall Blocking SSH**
   ```bash
   # Check firewall rules
   sudo ufw status
   
   # Allow SSH (emergency access needed)
   sudo ufw allow 22/tcp
   ```

3. **SSH Key Issues**
   ```bash
   # Regenerate SSH keys
   ./scripts/ssh-key-setup.sh
   
   # Bootstrap SSH access
   ./scripts/bulk-ssh-bootstrap.sh
   ```

4. **SSH Configuration Problems**
   ```bash
   # Reset SSH configuration
   ansible-playbook playbooks/security-hardening.yml --tags ssh --limit problematic_server
   ```

### Problem: Intermittent SSH Failures

#### Symptoms
- Some servers respond, others don't
- Random connection timeouts
- Inconsistent authentication

#### Diagnostic Steps

```bash
# Test connectivity to all servers
for server in $(ansible vpn_servers --list-hosts | grep -v hosts); do
  echo "Testing $server:"
  ssh -o ConnectTimeout=5 ansible@$server "echo OK" || echo "FAILED"
done

# Check SSH connection limits
ansible vpn_servers -m shell -a "grep -E 'MaxStartups|MaxSessions' /etc/ssh/sshd_config"

# Monitor SSH logs
ansible vpn_servers -m shell -a "tail -f /var/log/auth.log" --background
```

#### Solutions

1. **Increase SSH Connection Limits**
   ```bash
   # Update SSH configuration
   ansible vpn_servers -m lineinfile -a "path=/etc/ssh/sshd_config line='MaxStartups 30:30:100' regexp='^MaxStartups'"
   ansible vpn_servers -m service -a "name=ssh state=restarted"
   ```

2. **Optimize Ansible SSH Settings**
   ```bash
   # Update ansible.cfg
   [ssh_connection]
   ssh_args = -C -o ControlMaster=auto -o ControlPersist=300s
   pipelining = True
   retries = 3
   ```

## VPN Service Problems

### Problem: WireGuard Service Not Starting

#### Symptoms
- `systemctl status wg-quick@wg0` shows failed
- No WireGuard interface visible in `ip addr`
- Clients cannot connect

#### Diagnostic Steps

```bash
# Check WireGuard service status
ansible wireguard_servers -m shell -a "systemctl status wg-quick@wg0"

# Check WireGuard configuration
ansible wireguard_servers -m shell -a "wg-quick strip /etc/wireguard/wg0.conf"

# Test configuration syntax
ansible wireguard_servers -m shell -a "wg-quick up /etc/wireguard/wg0.conf --dry-run"

# Check kernel module
ansible wireguard_servers -m shell -a "lsmod | grep wireguard"
```

#### Solutions

1. **Configuration Syntax Error**
   ```bash
   # Validate and fix configuration
   ansible-playbook playbooks/wireguard-dashboard.yml --tags configure --limit problematic_server
   
   # Check configuration file
   ansible wireguard_servers -m shell -a "cat /etc/wireguard/wg0.conf"
   ```

2. **Missing Kernel Module**
   ```bash
   # Install WireGuard kernel module
   ansible wireguard_servers -m apt -a "name=wireguard state=present"
   ansible wireguard_servers -m shell -a "modprobe wireguard"
   ```

3. **Port Conflict**
   ```bash
   # Check port usage
   ansible wireguard_servers -m shell -a "netstat -ulnp | grep :51820"
   
   # Change WireGuard port if needed
   ansible-playbook playbooks/wireguard-dashboard.yml --extra-vars "wireguard_port=51821"
   ```

### Problem: OpenVPN Certificate Issues

#### Symptoms
- OpenVPN service fails to start
- Certificate validation errors
- Client authentication failures

#### Diagnostic Steps

```bash
# Check OpenVPN service
ansible openvpn_servers -m shell -a "systemctl status openvpn@server"

# Verify certificates
ansible openvpn_servers -m shell -a "openssl x509 -in /etc/openvpn/pki/ca.crt -text -noout"
ansible openvpn_servers -m shell -a "openssl x509 -in /etc/openvpn/pki/issued/server.crt -text -noout"

# Check certificate expiry
ansible openvpn_servers -m shell -a "openssl x509 -in /etc/openvpn/pki/ca.crt -enddate -noout"
```

#### Solutions

1. **Regenerate Certificates**
   ```bash
   # Regenerate PKI
   ansible-playbook playbooks/openvpn-deployment.yml --tags pki --limit problematic_server
   ```

2. **Fix Certificate Permissions**
   ```bash
   # Fix certificate permissions
   ansible openvpn_servers -m file -a "path=/etc/openvpn/pki owner=root group=root mode=0600 recurse=yes"
   ```

## Monitoring and Logging Issues

### Problem: Metrics Not Being Collected

#### Symptoms
- Grafana dashboards show no data
- Prometheus targets down
- Missing metrics from exporters

#### Diagnostic Steps

```bash
# Check exporter services
ansible vpn_servers -m service -a "name=node_exporter"
ansible wireguard_servers -m service -a "name=wg_exporter"

# Test exporter endpoints
ansible vpn_servers -m uri -a "url=http://localhost:9100/metrics"
ansible wireguard_servers -m uri -a "url=http://localhost:9586/metrics"

# Check firewall rules for metrics ports
ansible vpn_servers -m shell -a "ufw status | grep -E '9100|9586'"
```

#### Solutions

1. **Restart Monitoring Services**
   ```bash
   # Restart exporters
   ansible vpn_servers -m service -a "name=node_exporter state=restarted"
   ansible wireguard_servers -m service -a "name=wg_exporter state=restarted"
   ```

2. **Fix Firewall Rules**
   ```bash
   # Allow metrics ports
   ansible vpn_servers -m ufw -a "rule=allow port=9100 proto=tcp"
   ansible wireguard_servers -m ufw -a "rule=allow port=9586 proto=tcp"
   ```

### Problem: Log Shipping Failures

#### Symptoms
- Logs not appearing in Loki/Grafana
- Promtail service errors
- Log files growing without rotation

#### Diagnostic Steps

```bash
# Check Promtail service
ansible vpn_servers -m service -a "name=promtail"

# Check Promtail configuration
ansible vpn_servers -m shell -a "promtail -config.file=/etc/promtail/config.yml -dry-run"

# Test Loki connectivity
ansible vpn_servers -m uri -a "url=http://loki.monitoring.svc.cluster.local:3100/ready"
```

#### Solutions

1. **Restart Log Shipping**
   ```bash
   # Restart Promtail
   ansible vpn_servers -m service -a "name=promtail state=restarted"
   
   # Check Promtail logs
   ansible vpn_servers -m shell -a "journalctl -u promtail -n 20"
   ```

2. **Fix Log Rotation**
   ```bash
   # Force log rotation
   ansible vpn_servers -m shell -a "logrotate -f /etc/logrotate.d/vpn-logs"
   ```

## Security-Related Problems

### Problem: CrowdSec Not Blocking IPs

#### Symptoms
- Known malicious IPs not blocked
- CrowdSec decisions not being applied
- Firewall bouncer not working

#### Diagnostic Steps

```bash
# Check CrowdSec service
ansible vpn_servers -m service -a "name=crowdsec"

# Check CrowdSec decisions
ansible vpn_servers -m shell -a "cscli decisions list"

# Check firewall bouncer
ansible vpn_servers -m service -a "name=crowdsec-firewall-bouncer"

# Test CrowdSec API
ansible vpn_servers -m shell -a "cscli lapi status"
```

#### Solutions

1. **Restart CrowdSec Services**
   ```bash
   # Restart CrowdSec and bouncer
   ansible vpn_servers -m service -a "name=crowdsec state=restarted"
   ansible vpn_servers -m service -a "name=crowdsec-firewall-bouncer state=restarted"
   ```

2. **Update CrowdSec Configuration**
   ```bash
   # Redeploy CrowdSec configuration
   ansible-playbook playbooks/security-hardening.yml --tags crowdsec
   ```

### Problem: Fail2Ban Not Working

#### Symptoms
- Brute force attacks not being blocked
- Fail2Ban jails not active
- No banned IPs in fail2ban-client

#### Diagnostic Steps

```bash
# Check Fail2Ban status
ansible vpn_servers -m shell -a "fail2ban-client status"

# Check jail status
ansible vpn_servers -m shell -a "fail2ban-client status sshd"

# Check Fail2Ban logs
ansible vpn_servers -m shell -a "tail -20 /var/log/fail2ban.log"
```

#### Solutions

1. **Restart Fail2Ban**
   ```bash
   # Restart Fail2Ban service
   ansible vpn_servers -m service -a "name=fail2ban state=restarted"
   ```

2. **Fix Jail Configuration**
   ```bash
   # Redeploy Fail2Ban configuration
   ansible-playbook playbooks/security-hardening.yml --tags fail2ban
   ```

## Performance Issues

### Problem: High CPU Usage

#### Symptoms
- Server response slow
- High load averages
- VPN connection drops

#### Diagnostic Steps

```bash
# Check CPU usage
ansible vpn_servers -m shell -a "top -bn1 | head -20"

# Check load average
ansible vpn_servers -m shell -a "uptime"

# Identify CPU-intensive processes
ansible vpn_servers -m shell -a "ps aux --sort=-%cpu | head -10"

# Check system resources
ansible vpn_servers -m shell -a "vmstat 1 5"
```

#### Solutions

1. **Optimize VPN Configuration**
   ```bash
   # Apply performance optimizations
   ansible-playbook playbooks/multi-protocol-deployment.yml --tags performance
   ```

2. **Scale Resources**
   ```bash
   # Check if more servers needed
   ansible vpn_servers -m shell -a "wg show wg0 | grep peer | wc -l"
   ```

### Problem: Memory Issues

#### Symptoms
- Out of memory errors
- Swap usage high
- Services being killed by OOM

#### Diagnostic Steps

```bash
# Check memory usage
ansible vpn_servers -m shell -a "free -h"

# Check swap usage
ansible vpn_servers -m shell -a "swapon --show"

# Check for OOM kills
ansible vpn_servers -m shell -a "dmesg | grep -i 'killed process'"
```

#### Solutions

1. **Optimize Memory Usage**
   ```bash
   # Restart memory-intensive services
   ansible vpn_servers -m service -a "name=wireguard state=restarted"
   
   # Clear system caches
   ansible vpn_servers -m shell -a "echo 3 > /proc/sys/vm/drop_caches"
   ```

## Certificate and PKI Problems

### Problem: Certificate Expiry

#### Symptoms
- VPN clients cannot connect
- Certificate validation errors
- SSL/TLS handshake failures

#### Diagnostic Steps

```bash
# Check certificate expiry dates
ansible openvpn_servers -m shell -a "find /etc/openvpn/pki -name '*.crt' -exec openssl x509 -in {} -enddate -noout -subject \;"

# Check WireGuard key age
ansible wireguard_servers -m shell -a "stat /etc/wireguard/server_private.key"
```

#### Solutions

1. **Rotate Certificates**
   ```bash
   # Rotate OpenVPN certificates
   ansible-playbook playbooks/certificate-rotation.yml --limit openvpn_servers
   
   # Rotate WireGuard keys
   ansible-playbook playbooks/certificate-rotation.yml --limit wireguard_servers
   ```

## Network Configuration Issues

### Problem: DNS Resolution Failures

#### Symptoms
- Clients cannot resolve domains
- DNS queries timing out
- CoreDNS service issues

#### Diagnostic Steps

```bash
# Check CoreDNS service
ansible vpn_servers -m service -a "name=coredns"

# Test DNS resolution
ansible vpn_servers -m shell -a "nslookup google.com localhost"

# Check DNS configuration
ansible vpn_servers -m shell -a "cat /etc/coredns/Corefile"
```

#### Solutions

1. **Restart DNS Service**
   ```bash
   # Restart CoreDNS
   ansible vpn_servers -m service -a "name=coredns state=restarted"
   ```

2. **Fix DNS Configuration**
   ```bash
   # Redeploy CoreDNS
   ansible-playbook playbooks/deploy-coredns.yml
   ```

## Emergency Procedures

### Emergency Server Isolation

```bash
# Isolate compromised server
ansible-playbook playbooks/emergency-security-response.yml \
  --limit compromised-server.example.com \
  --extra-vars "isolate_server=true"
```

### Emergency IP Blocking

```bash
# Block malicious IPs immediately
ansible-playbook playbooks/emergency-block.yml \
  --extra-vars "block_ips=['1.2.3.4','5.6.7.8'] block_reason='security_incident'"
```

### Service Recovery

```bash
# Emergency service restart
ansible vpn_servers -m service -a "name=wireguard state=restarted"
ansible vpn_servers -m service -a "name=openvpn state=restarted"

# Full system recovery
ansible-playbook playbooks/backup-disaster-recovery.yml --tags restore
```

### Rollback Procedures

```bash
# Rollback to previous configuration
./scripts/backup-configuration.sh restore config_backup_20240105_143022.tar.gz

# Rollback specific service
ansible-playbook playbooks/tasks/server-rollback.yml \
  --limit affected_servers \
  --extra-vars "rollback_service=wireguard"
```

## Escalation Procedures

### Level 1: Self-Service
- Check this troubleshooting guide
- Run automated diagnostics
- Attempt basic remediation

### Level 2: Team Support
- Contact team lead or senior engineer
- Provide diagnostic output and logs
- Implement guided solutions

### Level 3: Emergency Response
- Contact on-call engineer
- Escalate to security team if needed
- Implement emergency procedures

### Contact Information

- **Primary On-Call:** [Phone/Email]
- **Secondary On-Call:** [Phone/Email]
- **Security Team:** [Phone/Email]
- **Infrastructure Team:** [Phone/Email]

## Useful Commands Reference

```bash
# Quick health check
ansible all -m ping

# Service status check
ansible vpn_servers -m shell -a "systemctl is-active wireguard openvpn crowdsec"

# Resource usage
ansible vpn_servers -m shell -a "top -bn1 | head -5; free -h; df -h /"

# Network connectivity
ansible vpn_servers -m shell -a "ss -tulnp | grep -E ':22|:51820|:1194'"

# Log analysis
ansible vpn_servers -m shell -a "journalctl --since '1 hour ago' --no-pager | tail -20"
```