# Cloudflare Tunnel Setup Guide

Protect your Ansible controller with Cloudflare Tunnel (Zero Trust access).

## Overview

Cloudflare Tunnel provides:
- **Zero Trust Access** - No exposed ports to the internet
- **Identity-based authentication** - Login with SSO/email
- **Browser-based SSH** - Access terminal from any browser
- **Short-lived certificates** - No permanent SSH keys exposed
- **Audit logging** - Track who accessed what and when

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTERNET                                      │
│                                                                      │
│   DevOps User                    Cloudflare Edge                    │
│   ┌─────────────┐               ┌─────────────────┐                 │
│   │  Browser    │──────────────▶│  Cloudflare     │                 │
│   │  or CLI     │   HTTPS       │  Access         │                 │
│   └─────────────┘               │  (Zero Trust)   │                 │
│                                 └────────┬────────┘                 │
│                                          │                          │
│                            Encrypted Tunnel (outbound only)         │
│                                          │                          │
└──────────────────────────────────────────┼──────────────────────────┘
                                           │
┌──────────────────────────────────────────┼──────────────────────────┐
│   YOUR INFRASTRUCTURE (No inbound ports) │                          │
│                                          ▼                          │
│                               ┌─────────────────┐                   │
│                               │  cloudflared    │                   │
│                               │  (tunnel agent) │                   │
│                               └────────┬────────┘                   │
│                                        │                            │
│                    ┌───────────────────┼───────────────────┐        │
│                    ▼                   ▼                   ▼        │
│           ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│           │  SSH (22)    │    │  Metrics     │    │  Internal    │  │
│           │  Ansible     │    │  (9090)      │    │  Services    │  │
│           └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                                      │
│                     Ansible Controller                               │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Create Tunnel in Cloudflare Dashboard

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Access** → **Tunnels**
3. Click **Create a tunnel**
4. Name it: `vpn-ansible-controller`
5. Copy the **Tunnel Token**

### 2. Store Token in Vault

```bash
# Add to your vault file
ansible-vault edit inventories/production/group_vars/vault.yml
```

```yaml
# inventories/production/group_vars/vault.yml
vault_cloudflare_tunnel_token: "eyJhIjoiYWJjZGVm..."
vault_cloudflare_api_token: "your-api-token"  # Optional, for DNS/Access automation
vault_cloudflare_account_id: "your-account-id"
```

### 3. Configure Variables

```yaml
# inventories/production/group_vars/ansible_controller.yml
cloudflare_tunnel_token: "{{ vault_cloudflare_tunnel_token }}"
cloudflare_domain: "yourdomain.com"
cloudflare_tunnel_name: "vpn-ansible-controller"

# Access control
cloudflare_access_enabled: true
cloudflare_access_allowed_emails:
  - "admin@yourdomain.com"
  - "devops@yourdomain.com"
cloudflare_access_allowed_domains:
  - "yourdomain.com"
```

### 4. Deploy Tunnel

```bash
# Deploy to Ansible controller
ansible-playbook -i inventories/production/hosts.yml \
    playbooks/security/cloudflare-tunnel.yml \
    --ask-vault-pass
```

### 5. Configure Access Policies

In Cloudflare Zero Trust Dashboard:

1. Go to **Access** → **Applications**
2. Find `vpn-ansible-controller-ssh`
3. Add policies:
   - **Allow DevOps team** - Email ends with @yourdomain.com
   - **Require MFA** - Everyone must complete 2FA

## Access Methods

### Browser-based SSH

1. Navigate to `https://ansible.yourdomain.com`
2. Authenticate with your identity provider
3. SSH session opens in browser

### CLI with cloudflared

```bash
# Install cloudflared on your workstation
brew install cloudflared  # macOS
# apt install cloudflared  # Debian/Ubuntu

# SSH through tunnel
cloudflared access ssh --hostname ansible.yourdomain.com
```

### SSH Config (Recommended)

Add to `~/.ssh/config`:

```ssh-config
Host ansible-controller
    HostName ansible.yourdomain.com
    ProxyCommand cloudflared access ssh --hostname %h
    User root
    IdentityFile ~/.ssh/vpn-infra

Host ansible
    HostName ansible.yourdomain.com
    ProxyCommand cloudflared access ssh --hostname %h
    User root
```

Then simply:
```bash
ssh ansible-controller
```

## Short-Lived Certificates

Instead of managing SSH keys, use Cloudflare's short-lived certificates:

1. User authenticates via Cloudflare Access
2. Cloudflare issues a certificate valid for the session (e.g., 8 hours)
3. Certificate automatically expires
4. No permanent keys to manage or rotate

### Enable Short-Lived Certs

```yaml
# group_vars/ansible_controller.yml
cloudflare_ssh_short_lived_certs: true
```

After deployment, SSH config becomes:

```ssh-config
Host ansible-controller
    HostName ansible.yourdomain.com
    ProxyCommand cloudflared access ssh --hostname %h
    # No IdentityFile needed - certificate is automatic
```

## Firewall Configuration

After tunnel is working, you can close SSH port completely:

```bash
# On Ansible controller - block direct SSH from internet
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT      # Allow internal
iptables -A INPUT -p tcp --dport 22 -s 127.0.0.1 -j ACCEPT        # Allow localhost (tunnel)
iptables -A INPUT -p tcp --dport 22 -j DROP                        # Drop all other SSH

# Or with ufw
ufw allow from 10.0.0.0/8 to any port 22
ufw allow from 127.0.0.1 to any port 22
ufw deny 22
```

## Exposing Additional Services

### Metrics Dashboard

```yaml
cloudflare_tunnel_ingress:
  - hostname: "ansible.{{ cloudflare_domain }}"
    service: "ssh://localhost:22"
  - hostname: "metrics.{{ cloudflare_domain }}"
    service: "http://localhost:9090"
  - service: "http_status:404"
```

### Internal Web UIs

```yaml
cloudflare_tunnel_ingress:
  - hostname: "ansible.{{ cloudflare_domain }}"
    service: "ssh://localhost:22"
  - hostname: "grafana.{{ cloudflare_domain }}"
    service: "http://10.0.1.20:3000"
  - hostname: "prometheus.{{ cloudflare_domain }}"
    service: "http://10.0.1.10:9090"
  - service: "http_status:404"
```

## Monitoring

### Check Tunnel Status

```bash
# On controller
systemctl status cloudflared

# Check metrics
curl http://localhost:20241/metrics | grep cloudflared
```

### Tunnel Health Check

```bash
# Verify tunnel is connected
curl -s http://localhost:20241/ready
# Should return: "OK"
```

### View Logs

```bash
journalctl -u cloudflared -f
```

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check token is correct
cloudflared tunnel run --token <your-token>

# Check network connectivity
curl -v https://api.cloudflare.com/client/v4/

# View detailed logs
journalctl -u cloudflared -n 100 --no-pager
```

### SSH Connection Refused

1. Verify SSH is running: `systemctl status ssh`
2. Check cloudflared config: `cat /etc/cloudflared/config.yml`
3. Verify tunnel routes to localhost:22

### Access Denied

1. Check Access policies in Zero Trust dashboard
2. Verify your email is in allowed list
3. Check identity provider is configured

### Browser SSH Not Working

1. Ensure `cloudflare_ssh_browser_enabled: true`
2. Check Access application is type "ssh"
3. Verify DNS record points to tunnel

## Security Best Practices

1. **Require MFA** - Always enable multi-factor authentication
2. **Limit access** - Only allow specific email addresses/domains
3. **Use short-lived certs** - Avoid permanent SSH keys where possible
4. **Enable session logging** - Track all SSH sessions
5. **Set session timeouts** - Auto-logout after inactivity
6. **Close direct SSH** - Disable port 22 from internet after tunnel works

## Related Documentation

- [SSH-KEY-MANAGEMENT.md](./SSH-KEY-MANAGEMENT.md) - Traditional SSH key management
- [SECRETS.md](./SECRETS.md) - Ansible Vault configuration
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Access Docs](https://developers.cloudflare.com/cloudflare-one/policies/access/)
