# UFW (Uncomplicated Firewall) Role

This Ansible role configures UFW firewall with deny-by-default policy and service-specific rules for VPN servers.

## Features

- **Deny-by-Default Policy**: Secure default configuration
- **VPN Service Rules**: Automatic rules for OpenVPN, WireGuard, AmneziaWG
- **SSH Hardening**: Rate limiting and access control
- **Monitoring Integration**: Rules for Prometheus exporters
- **Trusted Networks**: Whitelist configuration
- **Interface Rules**: VPN interface-specific rules
- **Application Profiles**: Support for UFW application profiles

## Requirements

- Ubuntu 20.04+ or Debian 11+
- Ansible 2.9+
- iptables support

## Role Variables

### Service Configuration
- `ufw_enabled`: Enable/disable UFW (default: `true`)
- `ufw_state`: UFW state (default: `enabled`)
- `ufw_logging`: Logging level (default: `on`)

### Default Policies
- `ufw_default_input_policy`: Input policy (default: `deny`)
- `ufw_default_output_policy`: Output policy (default: `allow`)
- `ufw_default_forward_policy`: Forward policy (default: `deny`)

### VPN Services
- `ufw_openvpn_enabled`: Enable OpenVPN rules (default: `true`)
- `ufw_wireguard_enabled`: Enable WireGuard rules (default: `true`)
- `ufw_amneziawg_enabled`: Enable AmneziaWG rules (default: `false`)

### SSH Configuration
- `ufw_ssh_port`: SSH port (default: `22`)
- `ufw_ssh_rule`: SSH rule action (default: `allow`)
- `ufw_rate_limit_ssh`: Enable SSH rate limiting (default: `true`)

### Monitoring
- `ufw_node_exporter_enabled`: Allow Node Exporter (default: `true`)
- `ufw_wg_exporter_enabled`: Allow WireGuard Exporter (default: `true`)

## Example Playbook

```yaml
- hosts: vpn_servers
  become: true
  roles:
    - role: ufw
      vars:
        ufw_ssh_port: "2222"
        ufw_wireguard_port: "51820"
        ufw_openvpn_port: "1194"
        ufw_trusted_networks:
          - "10.0.0.0/8"
          - "192.168.1.0/24"
        ufw_custom_rules:
          - rule: allow
            port: "8080"
            proto: tcp
            src: "192.168.1.0/24"
            comment: "Management interface"
```

## Custom Rules

```yaml
ufw_rules:
  - rule: allow
    port: "443"
    proto: tcp
    comment: "HTTPS access"
  - rule: deny
    src: "192.168.100.0/24"
    comment: "Block subnet"
```

## Interface Rules

```yaml
ufw_interface_rules:
  - interface: "wg0"
    direction: "in"
    rule: "allow"
  - interface: "tun0"
    direction: "in"
    rule: "allow"
```

## Application Profiles

```yaml
ufw_applications:
  - name: "OpenSSH"
    rule: allow
  - name: "Nginx Full"
    rule: allow
```

## Security Features

- **Rate Limiting**: SSH connection rate limiting
- **Trusted Networks**: Automatic whitelist for private networks
- **Blocked Networks**: Blacklist configuration
- **Logging**: Comprehensive firewall logging
- **Validation**: Configuration syntax checking

## Integration

### Fail2Ban Integration
Works with Fail2Ban for dynamic IP blocking.

### VPN Services Integration
Automatically configures rules for:
- OpenVPN (UDP 1194)
- WireGuard (UDP 51820)
- AmneziaWG (UDP 51821)

### Monitoring Integration
Configures access for:
- Node Exporter (TCP 9100)
- WireGuard Exporter (TCP 9586)

## Validation

The role includes comprehensive validation:
- Service status verification
- Rule configuration checking
- iptables integration testing
- Log file accessibility
- Configuration syntax validation

## License

MIT

## Author Information

VPN Infrastructure Team