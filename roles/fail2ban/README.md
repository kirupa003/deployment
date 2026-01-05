# Fail2Ban Role

This Ansible role installs and configures Fail2Ban intrusion prevention system for VPN servers with custom jails for SSH, OpenVPN, and WireGuard services.

## Features

- **SSH Protection**: Enhanced SSH jail with aggressive filtering
- **OpenVPN Protection**: Custom OpenVPN jail with TLS error detection
- **WireGuard Protection**: Custom WireGuard jail for handshake failures
- **Recidive Jail**: Catches repeat offenders across all jails
- **CrowdSec Integration**: Optional integration with CrowdSec
- **Email Notifications**: Configurable email alerts for bans
- **Logging**: Comprehensive logging with logrotate integration

## Requirements

- Ubuntu 20.04+ or Debian 11+
- Ansible 2.9+
- systemd-based system

## Role Variables

### Service Configuration
- `fail2ban_enabled`: Enable/disable Fail2Ban (default: `true`)
- `fail2ban_service_state`: Service state (default: `started`)
- `fail2ban_service_enabled`: Enable at boot (default: `true`)

### Global Settings
- `fail2ban_bantime`: Default ban time in seconds (default: `3600`)
- `fail2ban_findtime`: Time window for failures (default: `600`)
- `fail2ban_maxretry`: Maximum retry attempts (default: `5`)
- `fail2ban_backend`: Log backend (default: `systemd`)

### Jail Configuration
- `fail2ban_ssh_enabled`: Enable SSH jail (default: `true`)
- `fail2ban_openvpn_enabled`: Enable OpenVPN jail (default: `true`)
- `fail2ban_wireguard_enabled`: Enable WireGuard jail (default: `true`)
- `fail2ban_recidive_enabled`: Enable recidive jail (default: `true`)

### Notification Settings
- `fail2ban_destemail`: Destination email for alerts
- `fail2ban_sender`: Sender email address
- `fail2ban_mta`: Mail transfer agent (default: `sendmail`)

## Example Playbook

```yaml
- hosts: vpn_servers
  become: true
  roles:
    - role: fail2ban
      vars:
        fail2ban_destemail: admin@example.com
        fail2ban_ssh_maxretry: 3
        fail2ban_ssh_bantime: 7200
        fail2ban_wireguard_port: "51820"
        fail2ban_openvpn_port: "1194"
```

## Custom Filters

### WireGuard Filter
Detects:
- Invalid handshake initiations
- Unallowed source IPs
- Invalid MAC addresses
- Packet authentication failures

### OpenVPN Enhanced Filter
Detects:
- TLS handshake failures
- Certificate verification errors
- HMAC authentication failures
- Bad packet lengths
- Connection timeouts

### SSH Aggressive Filter
Enhanced SSH protection with additional patterns for:
- Protocol version attacks
- Key exchange failures
- Authentication flooding
- Connection abuse

## Integration

### CrowdSec Integration
When `crowdsec_enabled` is true, Fail2Ban will send decisions to CrowdSec API.

### UFW Integration
Works seamlessly with UFW firewall rules.

## Monitoring

The role includes validation tasks that verify:
- Service status and connectivity
- Active jails configuration
- Configuration syntax
- Log file accessibility

## Security Considerations

- Uses systemd backend for better performance
- Implements rate limiting for SSH
- Configures proper log rotation
- Sets secure file permissions
- Provides email notifications for security events

## License

MIT

## Author Information

VPN Infrastructure Team