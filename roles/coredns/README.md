# CoreDNS Role

This Ansible role deploys CoreDNS with ad-blocking capabilities for VPN infrastructure. It provides DNS forwarding, caching, and comprehensive ad-blocking using multiple blocklist sources.

## Features

- **DNS Server**: High-performance DNS resolution with caching
- **Ad-blocking**: Multiple blocklist sources (AdGuard, Pi-hole, EasyList, Malware)
- **Analytics**: DNS query logging and metrics collection
- **Monitoring**: Prometheus metrics and health checks
- **Security**: Firewall configuration and secure service setup
- **Automation**: Automatic blocklist updates via systemd timer

## Requirements

- Ubuntu 20.04+ or Debian 11+
- Python 3.6+
- Systemd
- UFW firewall (for Ubuntu/Debian)

## Role Variables

### Basic Configuration

```yaml
coredns_version: "1.11.1"              # CoreDNS version to install
coredns_user: "coredns"                # System user for CoreDNS
coredns_group: "coredns"               # System group for CoreDNS
coredns_home: "/opt/coredns"           # CoreDNS installation directory
coredns_config_dir: "/etc/coredns"     # Configuration directory
coredns_data_dir: "/var/lib/coredns"   # Data directory
coredns_log_dir: "/var/log/coredns"    # Log directory
```

### Network Configuration

```yaml
coredns_listen_port: 53                # DNS port
coredns_listen_address: "0.0.0.0"      # Listen address
coredns_metrics_port: 9153             # Prometheus metrics port
coredns_health_port: 8080              # Health check port
```

### DNS Configuration

```yaml
coredns_upstream_resolvers:            # Upstream DNS resolvers
  - "1.1.1.1"
  - "1.0.0.1"
  - "8.8.8.8"
  - "8.8.4.4"

coredns_cache_ttl: 3600                # Cache TTL in seconds
coredns_cache_size: 10000              # Cache size (number of entries)
```

### Ad-blocking Configuration

```yaml
coredns_adblock_enabled: true          # Enable ad-blocking
coredns_adblock_lists:                 # Blocklist sources
  - name: "adguard"
    url: "https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/BaseFilter/sections/adservers.txt"
    format: "adguard"
  - name: "pihole"
    url: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    format: "hosts"

coredns_blocklist_update_cron: "0 2 * * *"  # Daily at 2 AM
```

### Monitoring Configuration

```yaml
coredns_query_logging: true            # Enable query logging
coredns_analytics_enabled: true       # Enable analytics
coredns_log_level: "info"              # Log level
coredns_log_format: "json"             # Log format
```

## Dependencies

This role requires the following Ansible collections:
- `community.general`
- `ansible.posix`

## Example Playbook

```yaml
---
- name: Deploy CoreDNS with ad-blocking
  hosts: vpn_servers
  become: yes
  
  vars:
    coredns_adblock_enabled: true
    coredns_query_logging: true
    coredns_analytics_enabled: true
    
  roles:
    - role: coredns
      tags: [coredns, dns]
```

## Usage

### Deploy CoreDNS

```bash
ansible-playbook -i inventories/production playbooks/deploy-coredns.yml
```

### Deploy to specific region

```bash
ansible-playbook -i inventories/production playbooks/deploy-coredns.yml --limit europe
```

### Update blocklists manually

```bash
ansible vpn_servers -i inventories/production -m command -a "/opt/coredns/update-blocklists.sh"
```

### Check CoreDNS status

```bash
ansible vpn_servers -i inventories/production -m systemd -a "name=coredns state=started"
```

## Testing

### Test DNS resolution

```bash
# Test good domain
dig @<server_ip> google.com

# Test blocked domain (should return 0.0.0.0 or NXDOMAIN)
dig @<server_ip> doubleclick.net
```

### Check metrics

```bash
curl http://<server_ip>:9153/metrics
```

### Check health

```bash
curl http://<server_ip>:8080/health
```

## File Structure

```
roles/coredns/
├── defaults/main.yml           # Default variables
├── handlers/main.yml           # Service handlers
├── meta/main.yml              # Role metadata
├── tasks/
│   ├── main.yml               # Main task orchestration
│   ├── system.yml             # System setup
│   ├── install.yml            # CoreDNS installation
│   ├── configure.yml          # Configuration management
│   ├── adblock.yml            # Ad-blocking setup
│   ├── firewall.yml           # Firewall configuration
│   ├── service.yml            # Service management
│   └── validate.yml           # Validation tests
└── templates/
    ├── Corefile.j2            # Main CoreDNS configuration
    ├── coredns.service.j2     # Systemd service file
    ├── coredns.env.j2         # Environment variables
    ├── update-blocklists.sh.j2 # Blocklist update script
    ├── process-blocklist.py.j2 # Blocklist processor
    ├── blocklist.db.j2        # Blocked domains zone
    ├── custom.db.j2           # Custom DNS records
    ├── analytics.conf.j2      # Analytics configuration
    ├── coredns.logrotate.j2   # Log rotation
    └── validation-report.txt.j2 # Validation report
```

## Ports

The role configures the following ports:

- **53/UDP, 53/TCP**: DNS service
- **8080/TCP**: Health check endpoint (internal networks only)
- **9153/TCP**: Prometheus metrics (internal networks only)

## Security

- CoreDNS runs as non-root user
- Firewall rules restrict metrics and health endpoints to internal networks
- Systemd security hardening enabled
- Log rotation configured
- Automatic security updates for blocklists

## Monitoring Integration

The role provides:

- Prometheus metrics on port 9153
- Health check endpoint on port 8080
- Structured JSON logging
- DNS query analytics
- Blocklist update monitoring

## Troubleshooting

### Check service status

```bash
systemctl status coredns
journalctl -u coredns -f
```

### Validate configuration

```bash
/opt/coredns/coredns -conf /etc/coredns/Corefile -validate
```

### Check blocklist updates

```bash
systemctl status coredns-blocklist-updater.timer
journalctl -u coredns-blocklist-updater -f
```

### View validation report

```bash
ls -la /var/log/coredns/validation-report-*.txt
```

## License

MIT

## Author Information

VPN Infrastructure Team