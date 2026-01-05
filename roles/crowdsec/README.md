# CrowdSec Ansible Role

This Ansible role deploys and configures CrowdSec collaborative security platform with centralized Local API (LAPI) for decision sharing across VPN infrastructure servers.

## Features

- **Complete CrowdSec Installation**: Automated installation of CrowdSec agent and firewall bouncer
- **Centralized LAPI**: Local API configuration for decision sharing across all servers
- **VPN-Specific Protection**: Pre-configured scenarios for SSH, VPN (WireGuard, OpenVPN), and web services
- **Firewall Integration**: Automatic iptables and UFW integration with custom chain management
- **Threat Intelligence**: Automatic blocklist updates and community threat feeds
- **Monitoring Integration**: Prometheus metrics export and decision monitoring
- **Notification Support**: Slack and email notifications for security events

## Requirements

- Ubuntu 20.04+ or Debian 11+
- Ansible 2.9+
- Root or sudo access
- Internet connectivity for package installation and threat intelligence updates

## Role Variables

### Core Configuration

```yaml
# CrowdSec version and basic settings
crowdsec_version: "1.6.0"
crowdsec_user: "crowdsec"
crowdsec_group: "crowdsec"

# LAPI Configuration
crowdsec_lapi_enabled: true
crowdsec_lapi_host: "0.0.0.0"
crowdsec_lapi_port: 8080

# Database Configuration
crowdsec_db_type: "sqlite"
crowdsec_db_path: "/var/lib/crowdsec/data/crowdsec.db"
```

### Security Scenarios

```yaml
# Pre-configured scenarios for VPN infrastructure
crowdsec_scenarios:
  - crowdsecurity/ssh-bf
  - crowdsecurity/ssh-slow-bf
  - crowdsecurity/http-bf
  - crowdsecurity/vpn-bf
  - crowdsecurity/openvpn-bf
  - crowdsecurity/wireguard-bf
```

### Firewall Integration

```yaml
# Firewall settings
crowdsec_firewall_integration: true
crowdsec_iptables_chain: "CROWDSEC"
crowdsec_ban_duration: "4h"
crowdsec_ufw_integration: true
```

### Notifications

```yaml
# Slack notifications
crowdsec_notifications:
  slack:
    enabled: false
    webhook_url: ""
    channel: "#security-alerts"
  email:
    enabled: false
    smtp_host: ""
    smtp_port: 587
    from_email: ""
    to_emails: []
```

## Usage

### Basic Deployment

```yaml
- hosts: vpn_servers
  become: true
  roles:
    - role: crowdsec
      vars:
        crowdsec_lapi_enabled: true
        crowdsec_firewall_integration: true
```

### With Notifications

```yaml
- hosts: vpn_servers
  become: true
  roles:
    - role: crowdsec
      vars:
        crowdsec_notifications:
          slack:
            enabled: true
            webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
            channel: "#security-alerts"
```

### Centralized LAPI Setup

For centralized decision sharing, configure one server as the LAPI hub:

```yaml
# LAPI Hub Server
- hosts: lapi_hub
  become: true
  roles:
    - role: crowdsec
      vars:
        crowdsec_lapi_enabled: true
        crowdsec_lapi_host: "0.0.0.0"
        crowdsec_central_api_enabled: true

# Agent Servers
- hosts: vpn_agents
  become: true
  roles:
    - role: crowdsec
      vars:
        crowdsec_lapi_enabled: false
        crowdsec_lapi_url: "http://{{ hostvars[groups['lapi_hub'][0]]['ansible_default_ipv4']['address'] }}:8080"
```

## Management Commands

The role installs management scripts for operational tasks:

```bash
# Firewall management
/usr/local/bin/crowdsec-firewall-manager.sh status
/usr/local/bin/crowdsec-firewall-manager.sh decisions
/usr/local/bin/crowdsec-firewall-manager.sh test

# CrowdSec CLI commands
cscli decisions list
cscli scenarios list
cscli bouncers list
cscli machines list
```

## Monitoring

The role provides Prometheus metrics at `http://server:6060/metrics` and creates textfile collector metrics for:

- Active decisions count
- Unique banned IPs
- LAPI health status
- Bouncer service status
- Installed scenarios count

## File Structure

```
roles/crowdsec/
├── defaults/main.yml          # Default variables
├── handlers/main.yml          # Service handlers
├── meta/main.yml             # Role metadata
├── tasks/
│   ├── main.yml              # Main task orchestration
│   ├── system.yml            # System preparation
│   ├── install.yml           # Package installation
│   ├── configure.yml         # Configuration management
│   ├── lapi.yml              # LAPI setup
│   ├── bouncers.yml          # Bouncer configuration
│   ├── firewall.yml          # Firewall integration
│   ├── service.yml           # Service management
│   └── validate.yml          # Installation validation
├── templates/
│   ├── config.yaml.j2        # Main CrowdSec config
│   ├── acquis.yaml.j2        # Log acquisition config
│   ├── profiles.yaml.j2      # Decision profiles
│   ├── notifications.yaml.j2 # Notification config
│   └── *.sh.j2              # Management scripts
└── vars/main.yml             # Role-specific variables
```

## Security Considerations

- API keys are automatically generated and stored securely
- Whitelist configuration includes local networks by default
- Firewall rules are applied with deny-by-default policy
- All sensitive configuration files have restricted permissions
- Regular security updates are enabled by default

## Troubleshooting

### Check Service Status
```bash
systemctl status crowdsec
systemctl status crowdsec-firewall-bouncer
```

### Validate Configuration
```bash
cscli config show
/usr/local/bin/crowdsec-firewall-manager.sh test
```

### View Logs
```bash
tail -f /var/log/crowdsec/crowdsec.log
tail -f /var/log/crowdsec/firewall-manager.log
```

### Reset Firewall Rules
```bash
/usr/local/bin/crowdsec-firewall-manager.sh restart
```

## Integration with VPN Infrastructure

This role is designed to integrate with the VPN infrastructure deployment:

- Monitors VPN service logs (WireGuard, OpenVPN, AmneziaWG)
- Protects SSH access to VPN servers
- Integrates with existing monitoring stack (Prometheus, Grafana)
- Shares threat intelligence across all VPN servers
- Provides automated incident response capabilities

## License

MIT

## Author Information

VPN Infrastructure Team - Part of the VPN Infrastructure DevOps Controller project.