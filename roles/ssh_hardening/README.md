# SSH Hardening Role

This Ansible role implements comprehensive SSH hardening with key-only authentication and security configurations for VPN servers.

## Features

- **Key-Only Authentication**: Disables password authentication
- **Strong Cryptography**: Modern ciphers, MACs, and key exchange algorithms
- **Host Key Management**: Generates and manages secure host keys
- **Moduli Hardening**: Removes weak Diffie-Hellman moduli
- **Connection Limits**: Rate limiting and session controls
- **Security Banner**: Configurable login banner
- **Comprehensive Logging**: Enhanced SSH logging
- **Configuration Validation**: Syntax checking and testing

## Requirements

- Ubuntu 20.04+ or Debian 11+
- Ansible 2.9+
- OpenSSH 7.0+

## Role Variables

### Service Configuration
- `ssh_enabled`: Enable/disable SSH service (default: `true`)
- `ssh_port`: SSH port (default: `22`)
- `ssh_listen_address`: Listen address (default: `0.0.0.0`)

### Authentication Settings
- `ssh_permit_root_login`: Allow root login (default: `no`)
- `ssh_password_authentication`: Password auth (default: `no`)
- `ssh_pubkey_authentication`: Public key auth (default: `yes`)
- `ssh_max_auth_tries`: Max auth attempts (default: `3`)

### Connection Settings
- `ssh_max_sessions`: Max sessions per connection (default: `2`)
- `ssh_max_startups`: Connection rate limiting (default: `10:30:60`)
- `ssh_client_alive_interval`: Keep-alive interval (default: `300`)
- `ssh_client_alive_count_max`: Keep-alive max count (default: `2`)

### Cryptographic Settings
- `ssh_ciphers`: Allowed ciphers (secure defaults)
- `ssh_macs`: Allowed MACs (secure defaults)
- `ssh_kex_algorithms`: Key exchange algorithms (secure defaults)
- `ssh_host_key_algorithms`: Host key algorithms (secure defaults)

### Security Features
- `ssh_x11_forwarding`: X11 forwarding (default: `no`)
- `ssh_agent_forwarding`: Agent forwarding (default: `no`)
- `ssh_tcp_forwarding`: TCP forwarding (default: `no`)
- `ssh_compression`: Compression (default: `no`)

## Example Playbook

```yaml
- hosts: vpn_servers
  become: true
  roles:
    - role: ssh_hardening
      vars:
        ssh_port: "2222"
        ssh_max_auth_tries: 2
        ssh_allow_users:
          - "admin"
          - "ansible"
        ssh_banner_enabled: true
        ssh_regenerate_moduli: true
```

## Host Keys

The role generates secure host keys:
- **RSA**: 4096-bit keys
- **Ed25519**: 256-bit keys  
- **ECDSA**: 521-bit keys

Weak DSA keys are automatically removed.

## Cryptographic Hardening

### Ciphers
- chacha20-poly1305@openssh.com
- aes256-gcm@openssh.com
- aes128-gcm@openssh.com
- aes256-ctr, aes192-ctr, aes128-ctr

### MACs
- hmac-sha2-256-etm@openssh.com
- hmac-sha2-512-etm@openssh.com
- hmac-sha2-256, hmac-sha2-512

### Key Exchange
- curve25519-sha256@libssh.org
- diffie-hellman-group16-sha512
- diffie-hellman-group18-sha512
- diffie-hellman-group14-sha256

## Moduli Hardening

The role can:
- Remove weak moduli (< 3071 bits)
- Generate new strong moduli
- Validate moduli strength

Set `ssh_regenerate_moduli: true` to generate new moduli (time-intensive).

## User Access Control

```yaml
ssh_allow_users:
  - "admin"
  - "ansible"

ssh_deny_users:
  - "guest"

ssh_allow_groups:
  - "ssh-users"

ssh_deny_groups:
  - "no-ssh"
```

## Custom Configuration

```yaml
ssh_custom_options:
  "Match User ansible":
    - "PasswordAuthentication yes"
    - "PubkeyAuthentication yes"
  "Match Address 192.168.1.0/24":
    - "PasswordAuthentication yes"
```

## Security Banner

```yaml
ssh_banner_enabled: true
ssh_banner_content: |
  **************************************************************************
  *                     AUTHORIZED ACCESS ONLY                            *
  *                                                                        *
  *   This system is for authorized users only. All activities are        *
  *   monitored and logged. Unauthorized access is prohibited.            *
  **************************************************************************
```

## Integration

### Fail2Ban Integration
- Compatible with Fail2Ban SSH jails
- Enhanced logging for intrusion detection
- Aggressive filtering patterns

### UFW Integration
- Works with UFW firewall rules
- Supports custom SSH ports
- Rate limiting integration

## Validation

The role performs comprehensive validation:
- Configuration syntax checking
- Service status verification
- Host key validation
- Permission checking
- Moduli strength verification
- Connection testing

## Security Considerations

- **Backup**: Original configuration is backed up
- **Validation**: All changes are validated before applying
- **Gradual Deployment**: Test on non-production systems first
- **Key Management**: Ensure SSH keys are deployed before disabling passwords
- **Emergency Access**: Consider console access for recovery

## Common Issues

### Locked Out Prevention
1. Deploy SSH keys before running the role
2. Test SSH key authentication
3. Keep console/KVM access available
4. Use `ssh_custom_options` for temporary password access

### Performance Impact
- Moduli generation can take hours
- Strong cryptography may impact performance on older systems
- Consider `ssh_regenerate_moduli: false` for faster deployment

## License

MIT

## Author Information

VPN Infrastructure Team