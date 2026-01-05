# Runbook: Security Incident Response

## Overview
This runbook covers response procedures for security incidents affecting the VPN infrastructure.

## Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| P1 - Critical | Active breach, data exfiltration | Immediate |
| P2 - High | Attempted breach, suspicious activity | < 15 min |
| P3 - Medium | Anomalous patterns, policy violations | < 1 hour |
| P4 - Low | Informational, hardening opportunities | < 24 hours |

## Immediate Actions (All Incidents)

### 1. Assess and Contain

```bash
# Check active connections
ansible all -i inventories/production/hosts.yml \
  -m shell -a "ss -tnp | grep -E ':22|:51820'" --limit <affected-hosts>

# Check for unauthorized access
ansible all -i inventories/production/hosts.yml \
  -m shell -a "last -20" --limit <affected-hosts>
```

### 2. Emergency IP Block (if attacker identified)

```bash
# Block across all servers
ansible-playbook playbooks/security/emergency-block.yml \
  -e "block_ip=<attacker-ip>" \
  -e "auto_confirm=true"

# Verify block
ansible all -m shell -a "cscli decisions list --ip <attacker-ip>"
```

### 3. Preserve Evidence

```bash
# Create forensic snapshot
ssh ansible@<server> "sudo tar -czf /tmp/forensics-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/log \
  /etc/wireguard \
  /etc/crowdsec"

# Download evidence
scp ansible@<server>:/tmp/forensics-*.tar.gz ./evidence/
```

## Specific Scenarios

### Scenario: Brute Force Attack

**Indicators:**
- CrowdSec alerts
- Fail2Ban ban spike
- High authentication failures in logs

**Response:**
```bash
# 1. Check current bans
ansible <server> -m shell -a "fail2ban-client status sshd"
ansible <server> -m shell -a "cscli decisions list"

# 2. Increase ban duration temporarily
ansible <server> -m shell -a "cscli decisions add --ip <ip> --duration 720h --reason 'Brute force'"

# 3. Review and block at network level if persistent
# Update cloud security group to block IP range
```

### Scenario: Compromised Server

**Indicators:**
- Unauthorized processes
- Modified system files
- Unexpected outbound connections

**Response:**

1. **Isolate immediately**
   ```bash
   # Cloud console: Remove from all security groups except management
   # Or block all traffic
   ansible <server> -m shell -a "iptables -P INPUT DROP; iptables -P OUTPUT DROP; iptables -A INPUT -s <your-ip> -j ACCEPT; iptables -A OUTPUT -d <your-ip> -j ACCEPT"
   ```

2. **Assess scope**
   ```bash
   # Check for persistence
   ssh ansible@<server> "
     crontab -l
     ls -la /etc/cron.*
     systemctl list-unit-files | grep enabled
     cat /etc/passwd | grep -v nologin
     find /tmp -type f -executable
   "
   ```

3. **Check lateral movement**
   ```bash
   # Verify no connections to other VPN servers
   ansible all -m shell -a "ss -tn | grep <compromised-ip>"

   # Check for stolen credentials usage
   ansible all -m shell -a "grep <compromised-ip> /var/log/auth.log"
   ```

4. **Rebuild server**
   ```bash
   # Do NOT try to clean - rebuild fresh
   ansible-playbook playbooks/deploy/wireguard-dashboard.yml \
     --limit <new-replacement-server>
   ```

5. **Rotate all secrets**
   ```bash
   ./scripts/generate-wireguard-keys.sh
   ansible-playbook playbooks/configure/rotate-keys.yml
   ```

### Scenario: DDoS Attack

**Indicators:**
- Bandwidth saturation
- High packet rates
- Server unresponsive

**Response:**

1. **Enable cloud DDoS protection**
   - AWS Shield
   - Cloudflare Spectrum
   - GCP Cloud Armor

2. **Rate limit at firewall**
   ```bash
   ansible <server> -m shell -a "
     iptables -A INPUT -p udp --dport 51820 -m limit --limit 100/s --limit-burst 200 -j ACCEPT
     iptables -A INPUT -p udp --dport 51820 -j DROP
   "
   ```

3. **Null route attack sources**
   ```bash
   ansible <server> -m shell -a "ip route add blackhole <attacker-cidr>"
   ```

### Scenario: Credential Leak

**Indicators:**
- Secrets found in logs/repos
- Unauthorized access using valid credentials

**Response:**

1. **Identify leaked credentials**
2. **Rotate immediately**
   ```bash
   # Regenerate vault password
   ./scripts/init-vault.sh  # Creates new password

   # Re-encrypt all vault files
   find . -name "vault.yml" -exec ansible-vault rekey {} \;

   # Rotate WireGuard keys
   ./scripts/generate-wireguard-keys.sh
   ansible-playbook playbooks/configure/rotate-keys.yml --limit all

   # Rotate dashboard passwords
   ansible-vault edit inventories/production/group_vars/all/vault.yml
   ```

3. **Revoke old credentials in Vault**
   ```bash
   vault token revoke <old-token>
   vault lease revoke -prefix vpn/
   ```

4. **Audit access logs**

## Post-Incident

### Documentation Required

- [ ] Timeline of events
- [ ] Systems affected
- [ ] Attack vector identified
- [ ] Data impacted (if any)
- [ ] Actions taken
- [ ] Root cause
- [ ] Remediation steps
- [ ] Lessons learned

### Follow-up Actions

1. **Conduct post-mortem** within 48 hours
2. **Update runbooks** with new scenarios
3. **Improve monitoring** for detected blind spots
4. **Security audit** of similar systems
5. **Report** to stakeholders as required

## Emergency Contacts

| Role | Contact |
|------|---------|
| Security Lead | @security-lead |
| On-Call Engineer | PagerDuty |
| Cloud Provider | Support portal |
| Legal (if data breach) | legal@company.com |
