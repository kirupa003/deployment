# Secrets Management Guide

This document explains how to securely manage secrets in the VPN Infrastructure.

## Option 1: Ansible Vault (Recommended for Small Teams)

### Initial Setup

```bash
# Create a strong vault password
openssl rand -base64 32 > .vault_password
chmod 600 .vault_password

# Add to .gitignore (already done)
echo ".vault_password" >> .gitignore
```

### Encrypt Secrets File

```bash
# Encrypt the vault.yml file
ansible-vault encrypt inventories/production/group_vars/all/vault.yml

# Edit encrypted file
ansible-vault edit inventories/production/group_vars/all/vault.yml

# View encrypted file
ansible-vault view inventories/production/group_vars/all/vault.yml

# Re-key (change password)
ansible-vault rekey inventories/production/group_vars/all/vault.yml
```

### Run Playbooks with Vault

```bash
# Using password file (configured in ansible.cfg)
ansible-playbook playbooks/deploy/site.yml

# Or prompt for password
ansible-playbook playbooks/deploy/site.yml --ask-vault-pass

# Or specify password file
ansible-playbook playbooks/deploy/site.yml --vault-password-file ~/.vault_pass
```

### Per-Host Secrets

For host-specific secrets (like WireGuard private keys):

```bash
# Create encrypted host_vars
mkdir -p inventories/production/host_vars/eu-wg-001
ansible-vault create inventories/production/host_vars/eu-wg-001/vault.yml
```

```yaml
# Content of host_vars/eu-wg-001/vault.yml
wireguard_private_key: "your-base64-private-key"
```

---

## Option 2: HashiCorp Vault (Recommended for Production)

### Architecture

```
┌─────────────────┐     ┌─────────────────┐
│ Ansible         │────▶│ HashiCorp Vault │
│ Controller      │     │ (secrets store) │
└─────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│ VPN Servers     │
│ (secrets never  │
│  stored on disk)│
└─────────────────┘
```

### Setup Vault Integration

1. Install the collection:
```bash
ansible-galaxy collection install community.hashi_vault
```

2. Configure authentication in `group_vars/all.yml`:
```yaml
vault_addr: "https://vault.example.com:8200"
vault_auth_method: approle
```

3. Use lookups in playbooks:
```yaml
# Retrieve secret at runtime
wireguard_private_key: "{{ lookup('community.hashi_vault.hashi_vault',
  'secret=vpn/data/wireguard/{{ inventory_hostname }}:private_key',
  url=vault_addr) }}"
```

### Vault Secrets Structure

```
vault/
├── vpn/
│   ├── wireguard/
│   │   ├── eu-wg-001    # private_key, public_key
│   │   ├── eu-wg-002
│   │   └── ...
│   ├── amneziawg/
│   │   └── ...
│   └── openvpn/
│       ├── pki          # ca_cert, dh_params, ta_key
│       └── servers/
│           └── eu-ovpn-001  # server_cert, server_key
├── monitoring/
│   ├── grafana          # admin_password
│   ├── victoriametrics  # auth_token
│   └── loki             # auth_token
└── security/
    └── crowdsec         # lapi_key, bouncer_key
```

### Store Secrets in Vault

```bash
# Enable KV secrets engine
vault secrets enable -path=vpn kv-v2

# Store WireGuard keys
vault kv put vpn/wireguard/eu-wg-001 \
  private_key="$(wg genkey)" \
  public_key="$(echo $private_key | wg pubkey)"

# Store OpenVPN PKI
vault kv put vpn/openvpn/pki \
  ca_cert=@/path/to/ca.crt \
  dh_params=@/path/to/dh.pem \
  ta_key=@/path/to/ta.key
```

---

## Option 3: Environment Variables

For automation scripts:

```bash
# Export secrets as environment variables
export VAULT_ADDR="https://vault.example.com:8200"
export VAULT_TOKEN="your-token"
export ANSIBLE_VAULT_PASSWORD="your-ansible-vault-password"

# Run playbook
ansible-playbook playbooks/deploy/site.yml
```

---

## Best Practices

### DO:
- ✅ Use Ansible Vault for all sensitive variables
- ✅ Store vault password securely (password manager, encrypted file)
- ✅ Use HashiCorp Vault for production environments
- ✅ Rotate secrets regularly
- ✅ Use different secrets per environment (staging/production)
- ✅ Encrypt host-specific secrets in `host_vars/`
- ✅ Use `no_log: true` for tasks handling secrets

### DON'T:
- ❌ Commit unencrypted secrets to git
- ❌ Store vault password in the repository
- ❌ Share secrets via email or chat
- ❌ Use the same secrets across environments
- ❌ Hardcode secrets in playbooks or roles

---

## Secret Rotation

### Rotate WireGuard Keys

```bash
ansible-playbook playbooks/configure/rotate-keys.yml --limit eu_wireguard
```

### Rotate Vault Password

```bash
# Generate new password
openssl rand -base64 32 > .vault_password_new

# Re-key all encrypted files
find . -name "vault.yml" -exec ansible-vault rekey {} \
  --old-vault-password-file .vault_password \
  --new-vault-password-file .vault_password_new \;

# Replace old password file
mv .vault_password_new .vault_password
```

---

## Emergency Procedures

### If Secrets Are Compromised

1. **Immediately rotate all affected secrets**
2. **Revoke access tokens in HashiCorp Vault**
3. **Re-key Ansible Vault files**
4. **Audit git history for exposed secrets**
5. **Update all VPN server configurations**

```bash
# Emergency key rotation for all servers
ansible-playbook playbooks/configure/rotate-keys.yml \
  -e "confirm_rotation=yes" \
  -e "auto_confirm=true"
```
