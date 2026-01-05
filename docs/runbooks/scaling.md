# Runbook: Scaling VPN Infrastructure

## Overview
This runbook covers procedures for scaling the VPN infrastructure up or down based on demand.

## Capacity Indicators

### When to Scale Up
- Average peer count per server > 200
- Bandwidth utilization > 70% sustained
- CPU load > 80% sustained
- Latency increase > 20%

### When to Scale Down
- Average peer count per server < 50
- Bandwidth utilization < 20% sustained
- Cost optimization initiatives

## Adding New Servers

### 1. Provision Infrastructure

#### Using Terraform (Recommended)

```hcl
# Example: Hetzner Cloud
resource "hcloud_server" "eu_wg_006" {
  name        = "eu-wg-006"
  server_type = "cx21"
  image       = "ubuntu-22.04"
  location    = "nbg1"

  labels = {
    role        = "vpn"
    protocol    = "wireguard"
    region      = "europe"
    environment = "production"
  }
}

# Example: DigitalOcean
resource "digitalocean_droplet" "na_wg_005" {
  name   = "na-wg-005"
  size   = "s-2vcpu-4gb"
  image  = "ubuntu-22-04-x64"
  region = "nyc3"

  tags = ["vpn", "wireguard", "production"]
}

# Example: Vultr
resource "vultr_instance" "apac_wg_004" {
  plan        = "vc2-2c-4gb"
  region      = "sgp"
  os_id       = 387  # Ubuntu 22.04
  label       = "apac-wg-004"
  hostname    = "apac-wg-004"
}
```

#### Manual Provisioning

**Hetzner Cloud:**
```bash
hcloud server create \
  --name eu-wg-006 \
  --type cx21 \
  --image ubuntu-22.04 \
  --location nbg1 \
  --ssh-key ansible
```

**DigitalOcean:**
```bash
doctl compute droplet create na-wg-005 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --region nyc3 \
  --ssh-keys <key-id>
```

**Vultr:**
```bash
vultr-cli instance create \
  --label apac-wg-004 \
  --region sgp \
  --plan vc2-2c-4gb \
  --os 387
```

### 2. Update Inventory

```yaml
# inventories/production/hosts.yml
eu_wireguard:
  hosts:
    # ... existing servers ...
    eu-wg-006:
      ansible_host: <new-server-ip>
```

### 3. Generate Keys

```bash
# Generate WireGuard keys for new server
mkdir -p inventories/production/host_vars/eu-wg-006

# Generate and encrypt keys
wg genkey | tee >(wg pubkey > /tmp/pub.key) > /tmp/priv.key

cat > inventories/production/host_vars/eu-wg-006/vault.yml << EOF
---
wg_private_key: "$(cat /tmp/priv.key)"
# Public key: $(cat /tmp/pub.key)
EOF

ansible-vault encrypt inventories/production/host_vars/eu-wg-006/vault.yml
rm /tmp/priv.key /tmp/pub.key
```

### 4. Deploy

```bash
# Deploy to new server only
ansible-playbook playbooks/deploy/wireguard-dashboard.yml \
  --limit eu-wg-006 \
  -v

# Verify deployment
ansible-playbook playbooks/maintenance/health-check.yml \
  --limit eu-wg-006
```

### 5. Add to Monitoring

The new server will be auto-discovered by VictoriaMetrics if:
- node_exporter is running (port 9100)
- Service discovery is configured

Manual verification:
```bash
# Check metrics endpoint
curl http://<new-server-ip>:9100/metrics

# Verify in VictoriaMetrics
curl "http://vm.example.com/api/v1/query?query=up{instance='eu-wg-006:9100'}"
```

### 6. Add to DNS Load Balancing

**Using Cloudflare:**
```bash
# Add weighted DNS record
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone-id>/dns_records" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "eu.vpn.example.com",
    "content": "<new-server-ip>",
    "ttl": 60,
    "proxied": false
  }'
```

**Using PowerDNS:**
```bash
pdnsutil add-record example.com eu.vpn A 60 <new-server-ip>
```

## Removing Servers

### 1. Drain Connections

```bash
# Stop accepting new connections (firewall)
ansible <server-to-remove> -m shell -a "
  iptables -I INPUT -p udp --dport 51820 -j DROP
"

# Wait for existing peers to disconnect (check metrics)
# Or set a maintenance window
```

### 2. Remove from DNS

**Cloudflare:**
```bash
# Get record ID
RECORD_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones/<zone-id>/dns_records?name=eu.vpn.example.com" \
  -H "Authorization: Bearer <token>" | jq -r '.result[] | select(.content=="<server-ip>") | .id')

# Delete record
curl -X DELETE "https://api.cloudflare.com/client/v4/zones/<zone-id>/dns_records/$RECORD_ID" \
  -H "Authorization: Bearer <token>"
```

### 3. Wait for DNS TTL

```bash
# Wait for DNS propagation (TTL + buffer)
sleep 120
```

### 4. Verify No Active Connections

```bash
ansible <server-to-remove> -m shell -a "wg show wg0"
# Should show 0 peers or only stale peers
```

### 5. Terminate Instance

**Hetzner:**
```bash
hcloud server delete eu-wg-006
```

**DigitalOcean:**
```bash
doctl compute droplet delete <droplet-id> --force
```

**Vultr:**
```bash
vultr-cli instance delete <instance-id>
```

### 6. Update Inventory

Remove the server from `hosts.yml` and delete `host_vars/<hostname>/`.

### 7. Clean up Secrets

```bash
rm -rf inventories/production/host_vars/<removed-server>
```

## Recommended VPS Providers

| Provider | Regions | Best For | Pricing |
|----------|---------|----------|---------|
| **Hetzner** | EU (DE, FI) | Europe, cost-effective | €4-15/mo |
| **DigitalOcean** | Global | Simplicity, reliability | $12-24/mo |
| **Vultr** | Global | Performance, coverage | $10-20/mo |
| **Linode** | Global | Developer-friendly | $10-20/mo |
| **OVH** | EU, NA | High bandwidth | €5-15/mo |
| **Contabo** | EU | Budget, high specs | €5-10/mo |
| **BuyVM** | US, EU | Unlimited bandwidth | $3.50-15/mo |

## Capacity Planning

### Sizing Guidelines

| Server Size | vCPU | RAM | Max Peers | Bandwidth |
|-------------|------|-----|-----------|-----------|
| Small | 1 | 1GB | 50 | 100 Mbps |
| Medium | 2 | 4GB | 200 | 500 Mbps |
| Large | 4 | 8GB | 500 | 1 Gbps |
| XLarge | 8 | 16GB | 1000 | 2+ Gbps |

### Cost Optimization

1. Use smaller instances for low-traffic regions
2. Consider providers with unmetered bandwidth (OVH, BuyVM)
3. Use spot instances where available
4. Monitor and right-size based on actual usage
5. Consider ARM instances for better price/performance
