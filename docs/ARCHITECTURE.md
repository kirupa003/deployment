# VPN Infrastructure Architecture

Complete documentation for the VPN Infrastructure Management System.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Directory Structure](#directory-structure)
4. [Inventory Structure](#inventory-structure)
5. [Ansible Roles](#ansible-roles)
6. [Playbooks](#playbooks)
7. [Scripts](#scripts)
8. [Monitoring Stack](#monitoring-stack)
9. [Security Components](#security-components)
10. [Quick Reference](#quick-reference)

---

## Overview

This Ansible project manages a distributed VPN infrastructure with:

- **30 VPN servers** across 3 regions (Europe, North America, Asia Pacific)
- **3 VPN protocols**: WireGuard, AmneziaWG (obfuscated), OpenVPN
- **Zero Trust access** via Cloudflare Tunnel
- **Centralized monitoring** with VictoriaMetrics, Grafana, and Loki
- **Collaborative threat intelligence** via CrowdSec

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| Security First | Ansible Vault, Cloudflare Zero Trust, CrowdSec |
| Infrastructure as Code | Everything in Git, no manual changes |
| Idempotent Operations | All playbooks can be re-run safely |
| Secrets Never in Git | Vault encryption, .gitignore patterns |
| Regional Distribution | EU/NA/APAC with protocol diversity |

---

## Architecture Diagram

```
                                   ┌─────────────────────────────────────┐
                                   │         CLOUDFLARE EDGE             │
                                   │   ┌─────────────────────────────┐   │
                                   │   │    Zero Trust Access        │   │
                                   │   │    - MFA Authentication     │   │
                                   │   │    - Browser SSH            │   │
                                   │   └─────────────┬───────────────┘   │
                                   └─────────────────┼───────────────────┘
                                                     │ Tunnel (outbound)
┌────────────────────────────────────────────────────┼────────────────────────────────────────────────┐
│                                    CONTROL PLANE   │                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              ANSIBLE CONTROLLER                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │
│  │  │ cloudflared │  │   Ansible   │  │   Vault     │  │    SSH      │  │   Scripts   │        │   │
│  │  │  (tunnel)   │  │   Engine    │  │  Password   │  │    Keys     │  │             │        │   │
│  │  └─────────────┘  └──────┬──────┘  └─────────────┘  └─────────────┘  └─────────────┘        │   │
│  └──────────────────────────┼───────────────────────────────────────────────────────────────────┘   │
│                             │                                                                       │
│  ┌──────────────────────────┼───────────────────────────────────────────────────────────────────┐   │
│  │                    OBSERVABILITY STACK                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │   │
│  │  │ Victoria    │  │   Grafana   │  │    Loki     │  │  CrowdSec   │                          │   │
│  │  │ Metrics     │  │  Dashboards │  │    Logs     │  │    LAPI     │                          │   │
│  │  │ :9090       │  │   :3000     │  │   :3100     │  │   :8080     │                          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                          │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                    CENTRALIZED VPN CONFIG                                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐                                                            │   │
│  │  │ PostgreSQL  │  │ Config API  │◄──── Clients retrieve configs via API                     │   │
│  │  │ (vpn_configs│  │ (FastAPI)   │                                                            │   │
│  │  │  database)  │  │   :8080     │                                                            │   │
│  │  │   :5432     │  │             │                                                            │   │
│  │  └──────┬──────┘  └──────┬──────┘                                                            │   │
│  │         │                │                                                                   │   │
│  │         └────────────────┴──────────► Gateway Sync Service on each VPN server               │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                         ▼                    ▼                    ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────────────┐
│       EUROPE (12)           │  │    NORTH AMERICA (10)       │  │     ASIA PACIFIC (8)        │
│  ┌────────────────────────┐ │  │  ┌────────────────────────┐ │  │  ┌────────────────────────┐ │
│  │ WireGuard (5)          │ │  │  │ WireGuard (4)          │ │  │  │ WireGuard (3)          │ │
│  │ ├─ WG Dashboard        │ │  │  │ ├─ WG Dashboard        │ │  │  │ ├─ WG Dashboard        │ │
│  │ ├─ CoreDNS + Adblock   │ │  │  │ ├─ CoreDNS + Adblock   │ │  │  │ ├─ CoreDNS + Adblock   │ │
│  │ ├─ Node Exporter       │ │  │  │ ├─ Node Exporter       │ │  │  │ ├─ Node Exporter       │ │
│  │ ├─ WG Exporter         │ │  │  │ ├─ WG Exporter         │ │  │  │ ├─ WG Exporter         │ │
│  │ ├─ Promtail → Loki     │ │  │  │ ├─ Promtail → Loki     │ │  │  │ ├─ Promtail → Loki     │ │
│  │ ├─ CrowdSec Agent      │ │  │  │ ├─ CrowdSec Agent      │ │  │  │ ├─ CrowdSec Agent      │ │
│  │ └─ Fail2Ban            │ │  │  │ └─ Fail2Ban            │ │  │  │ └─ Fail2Ban            │ │
│  └────────────────────────┘ │  │  └────────────────────────┘ │  │  └────────────────────────┘ │
│  ┌────────────────────────┐ │  │  ┌────────────────────────┐ │  │  ┌────────────────────────┐ │
│  │ AmneziaWG (3)          │ │  │  │ AmneziaWG (2)          │ │  │  │ AmneziaWG (2)          │ │
│  │ └─ DPI Bypass          │ │  │  │ └─ DPI Bypass          │ │  │  │ └─ DPI Bypass          │ │
│  └────────────────────────┘ │  │  └────────────────────────┘ │  │  └────────────────────────┘ │
│  ┌────────────────────────┐ │  │  ┌────────────────────────┐ │  │  ┌────────────────────────┐ │
│  │ OpenVPN (4)            │ │  │  │ OpenVPN (4)            │ │  │  │ OpenVPN (3)            │ │
│  │ ├─ TCP + UDP           │ │  │  │ ├─ TCP + UDP           │ │  │  │ ├─ TCP + UDP           │ │
│  │ └─ Legacy Clients      │ │  │  │ └─ Legacy Clients      │ │  │  │ └─ Legacy Clients      │ │
│  └────────────────────────┘ │  │  └────────────────────────┘ │  │  └────────────────────────┘ │
│                             │  │                             │  │                             │
│  Providers:                 │  │  Providers:                 │  │  Providers:                 │
│  Hetzner, OVH               │  │  Vultr, Linode              │  │  DigitalOcean, Vultr        │
└─────────────────────────────┘  └─────────────────────────────┘  └─────────────────────────────┘
```

---

## Directory Structure

```
planet-proxy-devops-controller/
├── ansible.cfg                    # Ansible configuration
├── requirements.yml               # Galaxy collections/roles
├── .gitignore                     # Git ignore patterns
│
├── inventories/
│   ├── production/
│   │   ├── hosts.yml              # 30 production servers
│   │   └── group_vars/
│   │       ├── all/
│   │       │   ├── vars.yml       # Global variables
│   │       │   └── vault.yml      # Encrypted secrets
│   │       ├── vpn_servers.yml    # VPN server config
│   │       ├── wireguard_servers/
│   │       ├── amneziawg_servers/
│   │       ├── europe.yml         # Regional settings
│   │       ├── north_america.yml
│   │       └── asia_pacific.yml
│   └── staging/
│       ├── hosts.yml              # Staging servers
│       └── group_vars/
│
├── roles/                         # Ansible roles (14 total)
│   ├── common/                    # Base system setup
│   ├── hardening/                 # Security hardening
│   ├── wireguard/                 # WireGuard VPN
│   ├── amneziawg/                 # AmneziaWG (obfuscated)
│   ├── openvpn/                   # OpenVPN
│   ├── wg_dashboard/              # WireGuard Dashboard (Docker)
│   ├── vpn_config_db/             # Centralized PostgreSQL database
│   ├── vpn_config_api/            # REST API for config management
│   ├── coredns/                   # DNS with ad-blocking
│   ├── node_exporter/             # System metrics
│   ├── wg_exporter/               # WireGuard metrics
│   ├── promtail/                  # Log shipping
│   ├── fluent_bit/                # DNS analytics
│   ├── crowdsec/                  # Threat intelligence
│   ├── fail2ban/                  # Brute-force protection
│   └── cloudflare_tunnel/         # Zero Trust access
│
├── playbooks/
│   ├── deploy/                    # Deployment playbooks
│   │   ├── site.yml               # Full deployment
│   │   ├── wireguard.yml          # WireGuard only
│   │   ├── wireguard-dashboard.yml
│   │   ├── amneziawg.yml
│   │   └── openvpn.yml
│   ├── configure/                 # Configuration updates
│   │   ├── rotate-keys.yml        # Key rotation
│   │   └── update-blocklists.yml  # DNS blocklist update
│   ├── maintenance/               # Maintenance tasks
│   │   ├── health-check.yml       # Health verification
│   │   └── upgrade-packages.yml   # System updates
│   └── security/                  # Security operations
│       ├── ssh-bootstrap.yml      # SSH key distribution
│       ├── ssh-key-rotation.yml   # SSH key rotation
│       ├── cloudflare-tunnel.yml  # Zero Trust setup
│       ├── audit-servers.yml      # Security audit
│       ├── update-crowdsec.yml    # Threat updates
│       └── emergency-block.yml    # Emergency IP blocking
│
├── scripts/
│   ├── init-vault.sh              # Initialize Ansible Vault
│   ├── ssh-key-setup.sh           # Generate SSH keys
│   ├── bootstrap-ssh.sh           # Bootstrap single server
│   ├── bulk-ssh-bootstrap.sh      # Bootstrap all servers
│   ├── generate-wireguard-keys.sh # Generate WG keys
│   └── generate-openvpn-pki.sh    # Generate OpenVPN PKI
│
├── monitoring/
│   ├── dashboards/
│   │   └── vpn-overview.json      # Grafana dashboard
│   └── alerts/
│       └── vpn-alerts.yml         # VictoriaMetrics alerts
│
├── files/
│   └── ssh/                       # SSH keys (gitignored)
│       └── .gitkeep
│
├── docs/
│   ├── ARCHITECTURE.md            # This document
│   ├── SECRETS.md                 # Secrets management
│   ├── SSH-KEY-MANAGEMENT.md      # SSH key procedures
│   ├── CLOUDFLARE-TUNNEL.md       # Zero Trust setup
│   └── runbooks/
│       ├── server-down.md         # Incident response
│       ├── security-incident.md   # Security procedures
│       └── scaling.md             # Capacity planning
```

---

## Inventory Structure

### Server Distribution (30 Total)

| Region | WireGuard | AmneziaWG | OpenVPN | Total |
|--------|-----------|-----------|---------|-------|
| Europe | 5 | 3 | 4 | 12 |
| North America | 4 | 2 | 4 | 10 |
| Asia Pacific | 3 | 2 | 3 | 8 |
| **Total** | **12** | **7** | **11** | **30** |

### Inventory Groups

```yaml
all:
  children:
    # Control Plane
    ansible_controller:     # Ansible host (local)
    control_plane:          # Management servers
    observability:          # Monitoring stack

    # VPN Servers by Protocol
    wireguard_servers:      # All WireGuard
    amneziawg_servers:      # All AmneziaWG
    openvpn_servers:        # All OpenVPN

    # VPN Servers by Region
    europe:                 # EU servers
    north_america:          # NA servers
    asia_pacific:           # APAC servers

    # Combined
    vpn_servers:            # All 30 VPN servers
```

### Variable Precedence

```
all/vars.yml           → Global defaults
  └── vpn_servers.yml  → VPN-specific settings
      └── europe.yml   → Regional overrides
          └── wireguard_servers/vars.yml → Protocol settings
              └── host_vars/eu-wg-001.yml → Host-specific
```

---

## Ansible Roles

### 1. common

**Purpose**: Base system configuration applied to all servers.

| Component | Description |
|-----------|-------------|
| Package Updates | apt update, security packages |
| Time Sync | systemd-timesyncd configuration |
| Kernel Tuning | sysctl for VPN performance |
| Basic Tools | curl, vim, htop, etc. |

**Usage**:
```yaml
- hosts: all
  roles:
    - common
```

---

### 2. hardening

**Purpose**: Security hardening for production servers.

| Component | Description |
|-----------|-------------|
| SSH Hardening | Key-only auth, no root password |
| Firewall | UFW with VPN ports only |
| Unattended Upgrades | Automatic security updates |
| Kernel Security | sysctl hardening |
| Audit Logging | auditd configuration |

**Key Variables**:
```yaml
hardening_ssh_port: 22
hardening_allowed_users:
  - ansible
hardening_firewall_allowed_ports:
  - 22/tcp
  - 51820/udp   # WireGuard
```

---

### 3. wireguard

**Purpose**: Native WireGuard VPN server setup.

| Component | Description |
|-----------|-------------|
| Installation | wireguard-tools package |
| Configuration | wg0.conf with server keys |
| Systemd | wg-quick@wg0 service |
| IP Forwarding | sysctl net.ipv4.ip_forward |

**Key Variables**:
```yaml
wireguard_interface: wg0
wireguard_listen_port: 51820
wireguard_address: "10.10.0.1/24"
wireguard_private_key: "{{ vault_wg_private_key }}"
wireguard_dns: "10.10.0.1"  # CoreDNS
```

---

### 4. amneziawg

**Purpose**: AmneziaWG - obfuscated WireGuard for DPI bypass.

| Component | Description |
|-----------|-------------|
| Installation | amneziawg-tools from PPA |
| Obfuscation | Jc, Jmin, Jmax, S1, S2, H1-H4 params |
| Service | awg-quick@awg0 |

**Obfuscation Parameters**:
```yaml
amneziawg_jc: 4          # Junk packet count
amneziawg_jmin: 40       # Min junk size
amneziawg_jmax: 70       # Max junk size
amneziawg_s1: 20         # Init packet size 1
amneziawg_s2: 20         # Init packet size 2
amneziawg_h1: 1234567890 # Header transform 1
amneziawg_h2: 1234567890 # Header transform 2
amneziawg_h3: 1234567890 # Header transform 3
amneziawg_h4: 1234567890 # Header transform 4
```

**Use Case**: Countries with deep packet inspection blocking WireGuard.

---

### 5. openvpn

**Purpose**: OpenVPN server for legacy client compatibility.

| Component | Description |
|-----------|-------------|
| Installation | openvpn package |
| Dual Mode | TCP (443) + UDP (1194) |
| PKI | Easy-RSA certificate management |
| Configs | server-tcp.conf, server-udp.conf |

**Key Variables**:
```yaml
openvpn_proto: "udp"
openvpn_port: 1194
openvpn_tcp_port: 443
openvpn_cipher: "AES-256-GCM"
openvpn_auth: "SHA512"
openvpn_network: "10.8.0.0"
openvpn_netmask: "255.255.255.0"
```

---

### 6. wg_dashboard

**Purpose**: Web-based WireGuard/AmneziaWG management UI via Docker with SQLite storage.

| Component | Description |
|-----------|-------------|
| Docker | docker-ce, docker-compose-plugin |
| Dashboard | ghcr.io/wgdashboard/wgdashboard:latest |
| Web UI | Port 10086 |
| Database | SQLite (all peer configs stored in /data/db.sqlite) |
| WireGuard | /etc/wireguard mount |
| AmneziaWG | /etc/amnezia/amneziawg mount |

**Features**:
- Peer management via web UI
- QR code generation for mobile
- Real-time traffic monitoring
- SQLite database for all configurations
- Support for both WireGuard and AmneziaWG
- TOTP two-factor authentication
- Email notifications (optional)

**Data Storage**:
```
/opt/wg-dashboard/
├── data/           # SQLite database (db.sqlite)
├── conf/           # WireGuard configs (/etc/wireguard)
└── aconf/          # AmneziaWG configs (/etc/amnezia/amneziawg)
```

**Key Variables**:
```yaml
# Docker image
wg_dashboard_image: "ghcr.io/wgdashboard/wgdashboard:latest"

# Dashboard settings
wg_dashboard_port: 10086
wg_dashboard_admin_user: "admin"
wg_dashboard_admin_password: "{{ vault_wg_dashboard_password }}"
wg_dashboard_enable_totp: true

# WireGuard settings
wg_listen_port: 51820
wg_server_address: "10.66.66.1/24"

# AmneziaWG obfuscation (for DPI bypass)
amneziawg_listen_port: 51821
amneziawg_jc: 4        # Junk packet count
amneziawg_jmin: 40     # Junk packet min size
amneziawg_jmax: 70     # Junk packet max size
```

---

### 7. vpn_config_db

**Purpose**: Centralized PostgreSQL database storing all VPN configurations.

| Component | Description |
|-----------|-------------|
| Database | PostgreSQL 14+ |
| Schema | vpn_servers, vpn_peers, ip_pools, audit_log |
| Backup | Daily automated backups |
| SSL | TLS encryption for connections |

**Database Schema**:
```
┌─────────────────┐     ┌─────────────────┐
│  vpn_servers    │────<│   vpn_peers     │
├─────────────────┤     ├─────────────────┤
│ id (UUID)       │     │ id (UUID)       │
│ hostname        │     │ server_id (FK)  │
│ public_ip       │     │ name            │
│ region          │     │ public_key      │
│ protocol        │     │ assigned_ip     │
│ public_key      │     │ allowed_ips[]   │
│ listen_port     │     │ enabled         │
│ awg_* params    │     │ api_token_hash  │
└─────────────────┘     └─────────────────┘
```

**Key Variables**:
```yaml
vpn_db_host: "10.0.1.50"
vpn_db_port: 5432
vpn_db_name: "vpn_configs"
vpn_db_user: "vpn_admin"
vpn_db_password: "{{ vault_vpn_db_password }}"
```

---

### 8. vpn_config_api

**Purpose**: REST API for VPN gateway and client configuration management.

| Component | Description |
|-----------|-------------|
| Framework | FastAPI (Python) |
| Container | Docker |
| Auth | Gateway tokens, Client tokens |
| Port | 8080 |

**API Endpoints**:
```
Gateway Endpoints (for VPN servers):
  POST /api/v1/gateway/register    - Register gateway
  GET  /api/v1/gateway/peers       - Get all peers
  POST /api/v1/gateway/peers       - Create peer
  PUT  /api/v1/gateway/peers/{id}/sync - Sync status

Client Endpoints (for VPN clients):
  GET  /api/v1/client/config       - Get WireGuard config
  GET  /api/v1/client/servers      - List available servers
  POST /api/v1/client/switch-server - Request server switch

Admin Endpoints:
  GET  /api/v1/admin/servers       - List all servers
  GET  /api/v1/admin/stats         - Global statistics
```

**Client Config Retrieval**:
```bash
# Get config with client token
curl "https://vpn-api.example.com/api/v1/client/config?token=YOUR_TOKEN"
```

---

### 9. coredns

**Purpose**: DNS server with ad-blocking for VPN clients.

| Component | Description |
|-----------|-------------|
| Installation | CoreDNS binary |
| Ad-blocking | hosts plugin with blocklists |
| Upstream | Cloudflare/Quad9 DoH |
| Logging | Query logs for analytics |

**Corefile Configuration**:
```
. {
    hosts /etc/coredns/blocklist.txt {
        fallthrough
    }
    forward . tls://1.1.1.1 tls://9.9.9.9 {
        tls_servername cloudflare-dns.com
    }
    cache 3600
    log
    prometheus :9153
}
```

**Blocklist Sources**:
- StevenBlack/hosts
- AdGuard DNS filter
- Custom enterprise blocklist

---

### 8. node_exporter

**Purpose**: System metrics collection for Prometheus/VictoriaMetrics.

| Component | Description |
|-----------|-------------|
| Installation | node_exporter binary |
| Port | 9100 |
| Collectors | cpu, memory, disk, network |

**Exposed Metrics**:
- `node_cpu_seconds_total`
- `node_memory_MemAvailable_bytes`
- `node_disk_io_time_seconds_total`
- `node_network_receive_bytes_total`

---

### 9. wg_exporter

**Purpose**: WireGuard-specific metrics exporter.

| Component | Description |
|-----------|-------------|
| Installation | prometheus_wireguard_exporter |
| Port | 9586 |
| Metrics | Peer connections, transfer |

**Exposed Metrics**:
- `wireguard_peers` - Total peer count
- `wireguard_peer_last_handshake` - Connection health
- `wireguard_peer_rx_bytes` - Download per peer
- `wireguard_peer_tx_bytes` - Upload per peer

---

### 10. promtail

**Purpose**: Log shipping agent for Loki.

| Component | Description |
|-----------|-------------|
| Installation | promtail binary |
| Sources | syslog, auth.log, VPN logs |
| Destination | Central Loki server |

**Log Sources**:
```yaml
promtail_scrape_configs:
  - job: syslog
    path: /var/log/syslog
  - job: auth
    path: /var/log/auth.log
  - job: wireguard
    path: /var/log/wireguard.log
```

---

### 11. fluent_bit

**Purpose**: DNS query analytics pipeline to ClickHouse.

| Component | Description |
|-----------|-------------|
| Installation | fluent-bit package |
| Input | CoreDNS query logs |
| Output | ClickHouse for analytics |
| Parsing | Custom DNS log parser |

**Analytics Capabilities**:
- Query patterns per client
- Blocked domain statistics
- Geographic distribution
- Peak usage times

---

### 12. crowdsec

**Purpose**: Collaborative threat intelligence and IPS.

| Component | Description |
|-----------|-------------|
| Agent | Local threat detection |
| LAPI | Central decision sync |
| Bouncer | Firewall integration |
| Collections | SSH, nginx, VPN scenarios |

**How It Works**:
1. CrowdSec agent detects attacks locally
2. Reports to central LAPI
3. Community threat intelligence shared
4. Firewall bouncer blocks attackers

**Key Variables**:
```yaml
crowdsec_lapi_url: "http://10.0.1.60:8080"
crowdsec_collections:
  - crowdsecurity/linux
  - crowdsecurity/sshd
  - crowdsecurity/iptables
```

---

### 13. fail2ban

**Purpose**: Local brute-force protection (defense in depth).

| Component | Description |
|-----------|-------------|
| SSH Jail | Block SSH brute-force |
| VPN Jail | Block VPN auth failures |
| Recidive | Persistent offender banning |

**Jail Configuration**:
```yaml
fail2ban_jails:
  - name: sshd
    enabled: true
    maxretry: 3
    bantime: 3600
  - name: vpn-auth
    enabled: true
    maxretry: 5
    bantime: 7200
```

---

### 14. cloudflare_tunnel

**Purpose**: Zero Trust access to Ansible controller.

| Component | Description |
|-----------|-------------|
| cloudflared | Tunnel daemon |
| Access | Identity-based auth |
| Browser SSH | Web terminal |
| Short-lived Certs | No permanent SSH keys |

**Security Benefits**:
- No exposed ports to internet
- MFA required for all access
- Complete audit logging
- Session-based certificates

---

## Playbooks

### Deployment Playbooks (`playbooks/deploy/`)

| Playbook | Purpose | Target |
|----------|---------|--------|
| `site.yml` | Full infrastructure deployment | all |
| `wireguard.yml` | WireGuard servers only | wireguard_servers |
| `wireguard-dashboard.yml` | WG Dashboard + Docker | wireguard_servers |
| `amneziawg.yml` | AmneziaWG servers | amneziawg_servers |
| `openvpn.yml` | OpenVPN servers | openvpn_servers |

**Full Deployment**:
```bash
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/site.yml
```

### Configuration Playbooks (`playbooks/configure/`)

| Playbook | Purpose | Frequency |
|----------|---------|-----------|
| `rotate-keys.yml` | Rotate VPN keys | Quarterly |
| `update-blocklists.yml` | Update DNS blocklists | Daily |

### Maintenance Playbooks (`playbooks/maintenance/`)

| Playbook | Purpose | Frequency |
|----------|---------|-----------|
| `health-check.yml` | Verify all services | On-demand |
| `upgrade-packages.yml` | System updates | Weekly |

### Security Playbooks (`playbooks/security/`)

| Playbook | Purpose | When to Use |
|----------|---------|-------------|
| `ssh-bootstrap.yml` | Initial SSH key setup | New servers |
| `ssh-key-rotation.yml` | Rotate SSH keys | Quarterly |
| `cloudflare-tunnel.yml` | Setup Zero Trust | Initial setup |
| `audit-servers.yml` | Security audit | Monthly |
| `update-crowdsec.yml` | Update threat intel | Weekly |
| `emergency-block.yml` | Block attacker IP | Incident response |

---

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `init-vault.sh` | Initialize Ansible Vault | `./scripts/init-vault.sh` |
| `ssh-key-setup.sh` | Generate SSH key pair | `./scripts/ssh-key-setup.sh` |
| `bootstrap-ssh.sh` | Bootstrap single server | `./scripts/bootstrap-ssh.sh <ip>` |
| `bulk-ssh-bootstrap.sh` | Bootstrap all servers | `./scripts/bulk-ssh-bootstrap.sh` |
| `generate-wireguard-keys.sh` | Generate WG keys | `./scripts/generate-wireguard-keys.sh` |
| `generate-openvpn-pki.sh` | Generate OpenVPN PKI | `./scripts/generate-openvpn-pki.sh` |

---

## Monitoring Stack

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  VPN Servers    │     │  VictoriaMetrics│     │    Grafana      │
│                 │     │                 │     │                 │
│ ┌─────────────┐ │     │   Time-series   │     │   Dashboards    │
│ │node_exporter│─┼────▶│    Database     │────▶│   - VPN Overview│
│ └─────────────┘ │     │                 │     │   - Per-server  │
│ ┌─────────────┐ │     │   Alerting      │     │   - Regional    │
│ │ wg_exporter │─┼────▶│    Rules        │     │                 │
│ └─────────────┘ │     └─────────────────┘     └─────────────────┘
│                 │
│ ┌─────────────┐ │     ┌─────────────────┐
│ │  promtail   │─┼────▶│      Loki       │
│ └─────────────┘ │     │   Log Storage   │
└─────────────────┘     └─────────────────┘
```

### Alert Rules (`monitoring/alerts/vpn-alerts.yml`)

| Alert | Condition | Severity |
|-------|-----------|----------|
| VPNServerDown | up == 0 for 2m | critical |
| VPNServerHighCPU | cpu > 80% for 5m | warning |
| WireGuardInterfaceDown | interface down for 1m | critical |
| HighPeerCount | peers > 200 | warning |
| DiskSpaceLow | disk < 10% | warning |
| SSHBruteForce | auth failures > 10/min | warning |

### Grafana Dashboard

The dashboard (`monitoring/dashboards/vpn-overview.json`) displays:

- **Server Health**: CPU, memory, disk per server
- **VPN Metrics**: Active peers, bandwidth, handshake status
- **Regional View**: Traffic by region
- **Security**: Failed auth attempts, blocked IPs

---

## Security Components

### Defense in Depth

```
Layer 1: Cloudflare Tunnel (Zero Trust access to controller)
    │
Layer 2: SSH Key Authentication (no passwords)
    │
Layer 3: OS Hardening (minimal attack surface)
    │
Layer 4: Fail2Ban (local brute-force protection)
    │
Layer 5: CrowdSec (collaborative threat intelligence)
    │
Layer 6: Firewall (UFW - only VPN ports exposed)
    │
Layer 7: VPN Encryption (WireGuard/OpenVPN)
```

### Secrets Management

| Secret Type | Storage | Rotation |
|-------------|---------|----------|
| SSH Keys | `files/ssh/` (gitignored) | Quarterly |
| Ansible Vault Password | `.vault_password` (gitignored) | On compromise |
| WireGuard Keys | Vault-encrypted | Quarterly |
| OpenVPN PKI | Vault-encrypted | Yearly |
| API Tokens | Vault-encrypted | On compromise |

---

## Quick Reference

### Common Commands

```bash
# Initial Setup
./scripts/init-vault.sh                    # Initialize vault
./scripts/ssh-key-setup.sh                 # Generate SSH keys
./scripts/bulk-ssh-bootstrap.sh            # Bootstrap all servers

# Deployment
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/site.yml

# Per-protocol deployment
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/wireguard.yml
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/amneziawg.yml
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/openvpn.yml

# Maintenance
ansible-playbook -i inventories/production/hosts.yml playbooks/maintenance/health-check.yml
ansible-playbook -i inventories/production/hosts.yml playbooks/maintenance/upgrade-packages.yml

# Security
ansible-playbook -i inventories/production/hosts.yml playbooks/security/audit-servers.yml
ansible-playbook -i inventories/production/hosts.yml playbooks/security/update-crowdsec.yml

# Emergency
ansible-playbook -i inventories/production/hosts.yml playbooks/security/emergency-block.yml \
    -e "block_ip=1.2.3.4"

# Centralized VPN Config System
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/vpn-config-central.yml

# Enable gateway sync on all VPN servers
ansible-playbook -i inventories/production/hosts.yml playbooks/deploy/vpn-config-central.yml --tags sync

# Check specific region
ansible-playbook -i inventories/production/hosts.yml playbooks/maintenance/health-check.yml \
    --limit europe

# Check specific server
ansible eu-wg-001 -i inventories/production/hosts.yml -m ping
```

### Environment Variables

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password
export ANSIBLE_CONFIG=./ansible.cfg
```

### Useful Ad-hoc Commands

```bash
# Ping all servers
ansible all -i inventories/production/hosts.yml -m ping

# Check WireGuard status
ansible wireguard_servers -m shell -a "wg show"

# View active connections
ansible vpn_servers -m shell -a "ss -tunlp | grep -E '(wg|openvpn)'"

# Check disk space
ansible all -m shell -a "df -h /"

# Restart WireGuard
ansible wireguard_servers -m service -a "name=wg-quick@wg0 state=restarted"
```

### VPN Config API Usage

```bash
# CREATE NEW CONFIG (generates keys, returns config + QR code)
curl -X POST \
  -H "X-Admin-Key: ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "john-iphone",
    "email": "john@example.com",
    "device_type": "mobile",
    "region": "europe"
  }' \
  "https://vpn-api.example.com/api/v1/configs/create"

# Response includes:
# - config: Complete WireGuard config file
# - private_key: Client private key (only returned once!)
# - qr_code: Base64 PNG for mobile scanning
# - client_token: For future config retrieval

# Get client config (clients use their token)
curl "https://vpn-api.example.com/api/v1/client/config?token=CLIENT_TOKEN"

# List available servers (for server switching)
curl "https://vpn-api.example.com/api/v1/client/servers?token=CLIENT_TOKEN"

# Disable a client (revoke access)
curl -X PATCH \
  -H "X-Admin-Key: ADMIN_KEY" \
  "https://vpn-api.example.com/api/v1/configs/PEER_ID/disable"

# Delete a client config
curl -X DELETE \
  -H "X-Admin-Key: ADMIN_KEY" \
  "https://vpn-api.example.com/api/v1/configs/PEER_ID"

# Admin: Get all server stats
curl -H "X-Admin-Key: ADMIN_KEY" \
  "https://vpn-api.example.com/api/v1/admin/stats"

# Admin: List all servers
curl -H "X-Admin-Key: ADMIN_KEY" \
  "https://vpn-api.example.com/api/v1/admin/servers"
```

---

## Related Documentation

- [SECRETS.md](./SECRETS.md) - Secrets and Vault management
- [SSH-KEY-MANAGEMENT.md](./SSH-KEY-MANAGEMENT.md) - SSH key procedures
- [CLOUDFLARE-TUNNEL.md](./CLOUDFLARE-TUNNEL.md) - Zero Trust access setup
- [runbooks/server-down.md](./runbooks/server-down.md) - Server incident response
- [runbooks/security-incident.md](./runbooks/security-incident.md) - Security procedures
- [runbooks/scaling.md](./runbooks/scaling.md) - Capacity planning
