# Runbook: VPN Server Down

## Alert
**VPNServerDown** - Server has been unreachable for more than 2 minutes.

## Severity
**Critical** - Immediate action required.

## Impact
- VPN clients connected to this server will be disconnected
- Clients may fail over to other servers (if client configured)
- Reduced capacity in the affected region

## Quick Diagnosis

### 1. Check Server Status via Cloud Provider
```bash
# AWS
aws ec2 describe-instance-status --instance-ids <instance-id>

# GCP
gcloud compute instances describe <instance-name> --zone=<zone>

# DigitalOcean
doctl compute droplet get <droplet-id>
```

### 2. Check from Control Plane
```bash
# Ping test
ping -c 5 <server-ip>

# SSH test
ssh -o ConnectTimeout=5 ansible@<server-ip> "uptime"

# Run quick health check
ansible-playbook playbooks/maintenance/health-check.yml \
  --limit <hostname> -v
```

### 3. Check Metrics
- Open Grafana: `https://grafana.example.com`
- Dashboard: VPN Infrastructure Overview
- Look for recent metrics dropout

## Resolution Steps

### Scenario A: Server Unreachable (Network Issue)

1. **Check cloud provider status page**
2. **Verify security groups/firewall**
   ```bash
   # AWS
   aws ec2 describe-security-groups --group-ids <sg-id>
   ```
3. **Check if IP changed** (common with some providers)
4. **Reboot via cloud console** if no network access

### Scenario B: Server Reachable but Services Down

1. **SSH into server**
   ```bash
   ssh ansible@<server-ip>
   ```

2. **Check VPN service**
   ```bash
   # WireGuard
   sudo systemctl status wg-quick@wg0
   sudo wg show

   # Docker Dashboard
   sudo docker ps
   sudo docker logs wg-dashboard
   ```

3. **Restart services**
   ```bash
   # WireGuard
   sudo systemctl restart wg-quick@wg0

   # Docker
   cd /opt/wg-dashboard && sudo docker compose restart
   ```

4. **Check logs**
   ```bash
   sudo journalctl -u wg-quick@wg0 -n 50
   sudo dmesg | tail -50
   ```

### Scenario C: High Load / Resource Exhaustion

1. **Check resources**
   ```bash
   top -bn1 | head -20
   free -h
   df -h
   ```

2. **Identify problematic process**
   ```bash
   ps aux --sort=-%mem | head -10
   ps aux --sort=-%cpu | head -10
   ```

3. **Clear if disk full**
   ```bash
   sudo journalctl --vacuum-size=100M
   sudo apt clean
   ```

### Scenario D: Server Compromised

1. **Isolate immediately**
   - Remove from load balancer
   - Block all inbound traffic except your IP

2. **Preserve evidence**
   ```bash
   # Snapshot the disk
   # Export logs
   ```

3. **Deploy replacement**
   ```bash
   ansible-playbook playbooks/deploy/wireguard-dashboard.yml \
     --limit <new-server>
   ```

4. **Decommission old server**

## Post-Incident

1. **Update inventory** if server replaced
2. **Run health check** to confirm resolution
   ```bash
   ansible-playbook playbooks/maintenance/health-check.yml \
     --limit <hostname>
   ```
3. **Document incident** in incident log
4. **Update monitoring** if new failure mode discovered

## Escalation

| Time | Action |
|------|--------|
| 0-5 min | On-call engineer investigates |
| 5-15 min | Attempt restart/recovery |
| 15-30 min | Escalate to senior engineer |
| 30+ min | Consider replacement server |

## Contacts

- **On-Call**: Check PagerDuty schedule
- **Cloud Provider Support**: [AWS/GCP/DO support portal]
- **Senior Engineer**: @senior-oncall in Slack
