# SSH Key Management Guide

This guide covers SSH key setup and management for the VPN infrastructure at scale.

## Overview

SSH key authentication is required for Ansible to communicate with all 30+ VPN servers. This setup provides:

- **Passwordless authentication** - No password prompts during automation
- **Secure access** - Ed25519 keys (modern, secure, fast)
- **Centralized management** - Single key pair for the Ansible controller
- **Key rotation support** - Rotate keys without downtime

## Quick Start

### 1. Generate SSH Keys

```bash
# Generate the main infrastructure key
./scripts/ssh-key-setup.sh

# This creates:
# - files/ssh/vpn-infra (private key)
# - files/ssh/vpn-infra.pub (public key)
```

### 2. Bootstrap Access to Servers

Choose based on your situation:

**Option A: New servers with cloud-init**
Add the public key to your cloud provider's user-data:

```yaml
# cloud-init user-data
#cloud-config
users:
  - name: root
    ssh_authorized_keys:
      - ssh-ed25519 AAAA... vpn-infra@ansible-controller
```

**Option B: Single server with password access**
```bash
./scripts/bootstrap-ssh.sh 185.10.1.1 root
```

**Option C: Bulk bootstrap all servers**
```bash
./scripts/bulk-ssh-bootstrap.sh vpn-infra inventories/production/hosts.yml root
```

**Option D: Using Ansible (password prompt)**
```bash
ansible-playbook -i inventories/production/hosts.yml \
    playbooks/security/ssh-bootstrap.yml -k
```

### 3. Verify Access

```bash
# Test single server
ssh -i files/ssh/vpn-infra root@185.10.1.1

# Test all servers via Ansible
ansible all -i inventories/production/hosts.yml -m ping
```

## Detailed Procedures

### Initial Setup for New Deployment

1. **Generate keys on Ansible controller:**
   ```bash
   ./scripts/ssh-key-setup.sh
   ```

2. **Configure cloud provider templates:**

   **Hetzner Cloud:**
   ```bash
   # Add key via hcloud CLI
   hcloud ssh-key create --name vpn-infra --public-key-from-file files/ssh/vpn-infra.pub

   # Create servers with key
   hcloud server create --name eu-wg-001 --type cx21 --image ubuntu-22.04 --ssh-key vpn-infra
   ```

   **DigitalOcean:**
   ```bash
   # Add key
   doctl compute ssh-key import vpn-infra --public-key-file files/ssh/vpn-infra.pub

   # Create droplet with key
   doctl compute droplet create eu-wg-001 --image ubuntu-22-04-x64 --size s-1vcpu-2gb --ssh-keys vpn-infra
   ```

   **Vultr:**
   ```bash
   # Add key via API or console, then reference in creation
   vultr-cli ssh-key create --name vpn-infra --key "$(cat files/ssh/vpn-infra.pub)"
   ```

3. **Update inventory with actual IPs:**
   ```yaml
   # inventories/production/hosts.yml
   eu_wireguard:
     hosts:
       eu-wg-001:
         ansible_host: <actual-ip>
   ```

4. **Test connectivity:**
   ```bash
   ansible all -i inventories/production/hosts.yml -m ping
   ```

### Bootstrap Existing Servers

If you have existing servers with password authentication:

1. **Bulk bootstrap with password:**
   ```bash
   # Requires sshpass
   brew install hudochenkov/sshpass/sshpass  # macOS
   # apt install sshpass                      # Debian/Ubuntu

   ./scripts/bulk-ssh-bootstrap.sh vpn-infra inventories/production/hosts.yml root
   ```

2. **Or use Ansible with password:**
   ```bash
   # -k prompts for SSH password
   ansible-playbook -i inventories/production/hosts.yml \
       playbooks/security/ssh-bootstrap.yml -k
   ```

3. **Create dedicated Ansible user (optional but recommended):**
   ```bash
   ansible-playbook -i inventories/production/hosts.yml \
       playbooks/security/ssh-bootstrap.yml -k \
       -e "create_ansible_user=true" \
       -e "ansible_service_user=ansible"
   ```

### Hardening SSH (Production)

After key-based auth is confirmed working:

```bash
# Disable password authentication across all servers
ansible-playbook -i inventories/production/hosts.yml \
    playbooks/security/ssh-bootstrap.yml \
    -e "harden_ssh=true"
```

This will:
- Disable password authentication
- Disable root password login (keep key-based)
- Disable empty passwords
- Ensure pubkey auth is enabled

## SSH Key Rotation

Regular key rotation is a security best practice.

### Rotation Procedure

1. **Generate new key pair:**
   ```bash
   ./scripts/ssh-key-setup.sh vpn-infra-new
   ```

2. **Add new key to all servers (keep old key):**
   ```bash
   ansible-playbook -i inventories/production/hosts.yml \
       playbooks/security/ssh-key-rotation.yml \
       -e "new_ssh_key=files/ssh/vpn-infra-new.pub"
   ```

3. **Update ansible.cfg to use new key:**
   ```ini
   [defaults]
   private_key_file = files/ssh/vpn-infra-new
   ```

4. **Verify new key works:**
   ```bash
   ansible all -i inventories/production/hosts.yml -m ping
   ```

5. **Remove old key from servers:**
   ```bash
   ansible-playbook -i inventories/production/hosts.yml \
       playbooks/security/ssh-key-rotation.yml \
       -e "new_ssh_key=files/ssh/vpn-infra-new.pub" \
       -e "remove_old_key=true"
   ```

6. **Archive and rename keys:**
   ```bash
   mv files/ssh/vpn-infra files/ssh/vpn-infra-old-$(date +%Y%m%d)
   mv files/ssh/vpn-infra.pub files/ssh/vpn-infra-old-$(date +%Y%m%d).pub
   mv files/ssh/vpn-infra-new files/ssh/vpn-infra
   mv files/ssh/vpn-infra-new.pub files/ssh/vpn-infra.pub
   ```

### Automated Rotation Schedule

Add to cron for quarterly rotation:

```bash
# Add to crontab on Ansible controller
# crontab -e
0 0 1 */3 * cd /path/to/vpn-infra && ./scripts/ssh-key-setup.sh vpn-infra-new && ansible-playbook -i inventories/production/hosts.yml playbooks/security/ssh-key-rotation.yml -e "new_ssh_key=files/ssh/vpn-infra-new.pub"
```

## Directory Structure

```
files/
└── ssh/
    ├── vpn-infra           # Private key (chmod 600)
    ├── vpn-infra.pub       # Public key (chmod 644)
    └── backup-*/           # Archived old keys

scripts/
├── ssh-key-setup.sh        # Generate new key pair
├── bootstrap-ssh.sh        # Bootstrap single server
└── bulk-ssh-bootstrap.sh   # Bootstrap all servers

playbooks/security/
├── ssh-bootstrap.yml       # Distribute keys via Ansible
└── ssh-key-rotation.yml    # Rotate keys
```

## Security Best Practices

1. **Never commit private keys to Git**
   ```gitignore
   # .gitignore
   files/ssh/*
   !files/ssh/.gitkeep
   ```

2. **Use Ed25519 keys** (default)
   - Faster than RSA
   - Smaller key size
   - Modern cryptography

3. **Protect private key on controller**
   ```bash
   chmod 600 files/ssh/vpn-infra
   ```

4. **Rotate keys quarterly**
   - Set calendar reminders
   - Or automate via cron

5. **Use dedicated service account**
   - Don't use root for daily operations
   - Create `ansible` user with sudo

6. **Audit authorized_keys regularly**
   ```bash
   ansible all -m shell -a "cat ~/.ssh/authorized_keys"
   ```

## Troubleshooting

### "Permission denied (publickey)"

1. Check key permissions:
   ```bash
   ls -la files/ssh/
   # Should be: -rw------- (600) for private key
   ```

2. Verify correct key is configured:
   ```bash
   ssh -vvv -i files/ssh/vpn-infra root@server-ip
   ```

3. Check server's authorized_keys:
   ```bash
   # If you have console access
   cat /root/.ssh/authorized_keys
   ```

### "Host key verification failed"

```bash
# Add to known_hosts
ssh-keyscan -H server-ip >> ~/.ssh/known_hosts

# Or disable strict checking (less secure, useful for initial setup)
ansible-playbook ... -e "ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'"
```

### "Connection timed out"

1. Verify server IP is correct
2. Check firewall allows port 22
3. Try from different network (ISP blocking?)

### Bulk bootstrap fails for some servers

```bash
# Check failed servers list
./scripts/bulk-ssh-bootstrap.sh 2>&1 | grep FAILED

# Bootstrap individually with debug
./scripts/bootstrap-ssh.sh 185.10.1.1 root
```

## Integration with Ansible

### ansible.cfg Configuration

```ini
[defaults]
private_key_file = files/ssh/vpn-infra
remote_user = root
host_key_checking = False  # Only for initial setup, enable in production

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
```

### Inventory Variables

```yaml
# inventories/production/group_vars/all.yml
ansible_ssh_private_key_file: "{{ playbook_dir }}/../../files/ssh/vpn-infra"
ansible_user: root
ansible_ssh_common_args: '-o StrictHostKeyChecking=no'  # Remove after initial setup
```

## Related Documentation

- [SECRETS.md](./SECRETS.md) - Ansible Vault and secrets management
- [runbooks/server-provisioning.md](./runbooks/server-provisioning.md) - New server setup
