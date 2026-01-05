# VPN Infrastructure Inventory

This directory contains the Ansible inventory configuration for the VPN infrastructure deployment.

## Structure

```
inventories/
├── production              # Main production inventory file
├── group_vars/            # Group-specific variables
│   ├── all.yml           # Variables for all hosts
│   ├── vpn_servers.yml   # Variables for all VPN servers
│   ├── wireguard_servers.yml  # WireGuard-specific variables
│   ├── openvpn_servers.yml    # OpenVPN-specific variables
│   ├── europe.yml        # Europe region variables
│   ├── north_america.yml # North America region variables
│   └── asia_pacific.yml  # Asia Pacific region variables
├── host_vars/            # Host-specific variables
│   └── [hostname].yml    # Individual server configurations
└── README.md            # This file
```

## Inventory Groups

### Regional Groups
- `europe`: 10 servers in European region (Frankfurt)
- `north_america`: 10 servers in North American region (Virginia)
- `asia_pacific`: 10 servers in Asia Pacific region (Singapore)

### Protocol Groups
- `wireguard_servers`: All WireGuard servers (15 total, 5 per region)
- `openvpn_servers`: All OpenVPN servers (15 total, 5 per region)

### Combined Groups
- `vpn_servers`: All VPN servers (30 total)

## Server Naming Convention

Servers follow the naming pattern: `{region}-vpn-{protocol}-{number}.example.com`

Examples:
- `eu-vpn-wg-01.example.com` - Europe WireGuard server 1
- `na-vpn-ovpn-03.example.com` - North America OpenVPN server 3
- `ap-vpn-wg-05.example.com` - Asia Pacific WireGuard server 5

## IP Address Allocation

### Management Networks
- Europe: 10.1.0.0/16
- North America: 10.2.0.0/16
- Asia Pacific: 10.3.0.0/16

### VPN Networks
- WireGuard: 10.10.0.0/24 (per server)
- OpenVPN: 10.20.0.0/24 (per server)

## Usage Examples

### Target all VPN servers
```bash
ansible-playbook -i inventories/production playbooks/health-check.yml
```

### Target specific region
```bash
ansible-playbook -i inventories/production playbooks/deploy.yml --limit europe
```

### Target specific protocol
```bash
ansible-playbook -i inventories/production playbooks/wireguard-deploy.yml --limit wireguard_servers
```

### Target specific server
```bash
ansible-playbook -i inventories/production playbooks/maintenance.yml --limit eu-vpn-wg-01.example.com
```

## Configuration Management

### Host Variables Priority (lowest to highest)
1. `all.yml` - Global defaults
2. `vpn_servers.yml` - VPN server defaults
3. `{protocol}_servers.yml` - Protocol-specific settings
4. `{region}.yml` - Region-specific settings
5. `host_vars/{hostname}.yml` - Host-specific overrides

### Host Variables Examples

The following example host variable files are provided:
- `eu-vpn-wg-01.example.com.yml` - European WireGuard server configuration
- `na-vpn-wg-01.example.com.yml` - North American WireGuard server configuration
- `ap-vpn-wg-01.example.com.yml` - Asia Pacific WireGuard server configuration
- `eu-vpn-ovpn-01.example.com.yml` - European OpenVPN server configuration

### Inventory Validation

Use the provided validation script to verify inventory structure:
```bash
python3 scripts/validate-inventory.py
```

This script validates:
- Inventory syntax and structure
- Required groups presence
- Server count per region (10 each)
- Protocol distribution (15 WireGuard, 15 OpenVPN)
- Group and host variable file syntax

### Adding New Servers

1. Add server entry to the appropriate section in `inventories/production`
2. Create host-specific variables in `inventories/host_vars/{hostname}.yml`
3. Update group variables if needed
4. Test connectivity: `ansible -i inventories/production {hostname} -m ping`

### Security Considerations

- All sensitive data should be encrypted using Ansible Vault
- SSH keys should be properly managed and rotated
- Host variables may contain encrypted secrets
- Use `ansible-vault edit` to modify encrypted files