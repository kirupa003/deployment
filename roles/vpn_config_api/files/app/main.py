"""
VPN Configuration API
Centralized API for VPN gateway and client configuration management
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import hashlib
import secrets
import asyncpg
import subprocess
import base64
import os
import logging
import io
import qrcode

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VPN Configuration API",
    description="Centralized API for VPN peer configuration management",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database pool
db_pool = None

# ============================================
# Models
# ============================================

class ServerRegistration(BaseModel):
    hostname: str
    public_ip: str
    private_ip: Optional[str] = None
    region: str
    country_code: str
    city: Optional[str] = None
    protocol: str = Field(..., pattern="^(wireguard|amneziawg|openvpn)$")
    listen_port: int
    public_key: str
    max_peers: int = 250
    # AmneziaWG params
    awg_jc: Optional[int] = None
    awg_jmin: Optional[int] = None
    awg_jmax: Optional[int] = None
    awg_s1: Optional[int] = None
    awg_s2: Optional[int] = None
    awg_h1: Optional[int] = None
    awg_h2: Optional[int] = None
    awg_h3: Optional[int] = None
    awg_h4: Optional[int] = None

class PeerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    public_key: str
    allowed_ips: List[str] = ["0.0.0.0/0", "::/0"]
    dns_servers: List[str] = ["1.1.1.1"]
    persistent_keepalive: int = 25
    mtu: int = 1420
    expires_days: Optional[int] = None
    notes: Optional[str] = None

class ConfigCreate(BaseModel):
    """Create a new VPN config with auto-generated keys"""
    name: str
    email: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = "mobile"  # mobile, desktop, router
    server_id: Optional[str] = None  # If not specified, auto-select best server
    region: Optional[str] = None  # Preferred region (europe, north_america, asia_pacific)
    allowed_ips: List[str] = ["0.0.0.0/0", "::/0"]
    dns_servers: List[str] = ["1.1.1.1"]
    expires_days: Optional[int] = None
    notes: Optional[str] = None

class ConfigCreateResponse(BaseModel):
    """Response with generated config and keys"""
    peer_id: str
    name: str
    config: str  # Full WireGuard config file content
    private_key: str  # Client private key (only returned once!)
    public_key: str  # Client public key
    assigned_ip: str
    server_endpoint: str
    server_public_key: str
    qr_code: Optional[str] = None  # Base64 encoded QR code PNG
    client_token: str  # Token for future config retrieval

class PeerUpdate(BaseModel):
    enabled: Optional[bool] = None
    allowed_ips: Optional[List[str]] = None
    dns_servers: Optional[List[str]] = None
    expires_at: Optional[datetime] = None

class PeerResponse(BaseModel):
    id: str
    name: str
    public_key: str
    assigned_ip: str
    enabled: bool
    created_at: datetime
    last_handshake: Optional[datetime] = None

class ConfigResponse(BaseModel):
    config: str
    format: str = "wireguard"
    server_endpoint: str
    qr_data: Optional[str] = None

# ============================================
# Database
# ============================================

async def get_db():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "vpn_configs"),
            user=os.getenv("DB_USER", "vpn_api"),
            password=os.getenv("DB_PASSWORD", ""),
            min_size=2,
            max_size=10
        )
    return db_pool

# ============================================
# WireGuard Key Generation
# ============================================

def generate_wireguard_keypair() -> tuple[str, str]:
    """Generate WireGuard private and public key pair"""
    try:
        # Generate private key
        private_key_result = subprocess.run(
            ["wg", "genkey"],
            capture_output=True, text=True, check=True
        )
        private_key = private_key_result.stdout.strip()

        # Generate public key from private key
        public_key_result = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True, text=True, check=True
        )
        public_key = public_key_result.stdout.strip()

        return private_key, public_key
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate WireGuard keys: {e}")
        raise HTTPException(status_code=500, detail="Key generation failed")
    except FileNotFoundError:
        # Fallback: generate keys using Python (X25519)
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key_obj = X25519PrivateKey.generate()
        private_key_bytes = private_key_obj.private_bytes_raw()
        public_key_bytes = private_key_obj.public_key().public_bytes_raw()

        private_key = base64.b64encode(private_key_bytes).decode()
        public_key = base64.b64encode(public_key_bytes).decode()

        return private_key, public_key

def generate_preshared_key() -> str:
    """Generate WireGuard preshared key"""
    try:
        result = subprocess.run(
            ["wg", "genpsk"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: generate random 32-byte key
        return base64.b64encode(secrets.token_bytes(32)).decode()

def generate_qr_code(config: str) -> str:
    """Generate QR code for WireGuard config, return as base64 PNG"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(config)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return None

def build_wireguard_config(
    private_key: str,
    address: str,
    dns: List[str],
    server_public_key: str,
    endpoint: str,
    allowed_ips: List[str],
    persistent_keepalive: int = 25,
    mtu: int = 1420,
    preshared_key: str = None,
    # AmneziaWG params
    awg_jc: int = None,
    awg_jmin: int = None,
    awg_jmax: int = None,
    awg_s1: int = None,
    awg_s2: int = None,
    awg_h1: int = None,
    awg_h2: int = None,
    awg_h3: int = None,
    awg_h4: int = None,
) -> str:
    """Build a complete WireGuard client configuration"""
    config = f"""[Interface]
PrivateKey = {private_key}
Address = {address}
DNS = {', '.join(dns)}
MTU = {mtu}

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint}
AllowedIPs = {', '.join(allowed_ips)}
PersistentKeepalive = {persistent_keepalive}
"""

    if preshared_key:
        config += f"PresharedKey = {preshared_key}\n"

    # Add AmneziaWG obfuscation params if provided
    if awg_jc is not None:
        config += f"""
# AmneziaWG Obfuscation
Jc = {awg_jc}
Jmin = {awg_jmin}
Jmax = {awg_jmax}
S1 = {awg_s1}
S2 = {awg_s2}
H1 = {awg_h1}
H2 = {awg_h2}
H3 = {awg_h3}
H4 = {awg_h4}
"""

    return config

# ============================================
# Authentication
# ============================================

GATEWAY_TOKENS = {}  # Loaded from env

def load_gateway_tokens():
    """Load gateway tokens from environment"""
    global GATEWAY_TOKENS
    tokens_str = os.getenv("GATEWAY_TOKENS", "")
    if tokens_str:
        for pair in tokens_str.split(","):
            if ":" in pair:
                gateway, token = pair.split(":", 1)
                GATEWAY_TOKENS[gateway] = token

async def verify_gateway_token(x_gateway_id: str = Header(...), x_gateway_token: str = Header(...)):
    """Verify gateway authentication"""
    if x_gateway_id not in GATEWAY_TOKENS:
        raise HTTPException(status_code=401, detail="Unknown gateway")
    if not secrets.compare_digest(GATEWAY_TOKENS[x_gateway_id], x_gateway_token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return x_gateway_id

async def verify_client_token(token: str = Query(...)):
    """Verify client token for config retrieval"""
    pool = await get_db()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async with pool.acquire() as conn:
        peer = await conn.fetchrow(
            "SELECT id, server_id, enabled FROM vpn_peers WHERE api_token_hash = $1",
            token_hash
        )
    if not peer:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not peer["enabled"]:
        raise HTTPException(status_code=403, detail="Peer disabled")
    return peer

# ============================================
# Startup/Shutdown
# ============================================

@app.on_event("startup")
async def startup():
    load_gateway_tokens()
    await get_db()
    logger.info("VPN Config API started")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ============================================
# Gateway Endpoints
# ============================================

@app.post("/api/v1/gateway/register")
async def register_gateway(
    server: ServerRegistration,
    gateway_id: str = Depends(verify_gateway_token)
):
    """Register or update a VPN gateway server"""
    pool = await get_db()
    async with pool.acquire() as conn:
        # Upsert server
        result = await conn.fetchrow("""
            INSERT INTO vpn_servers (
                hostname, public_ip, private_ip, region, country_code, city,
                protocol, listen_port, public_key, max_peers,
                awg_jc, awg_jmin, awg_jmax, awg_s1, awg_s2,
                awg_h1, awg_h2, awg_h3, awg_h4
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            ON CONFLICT (hostname) DO UPDATE SET
                public_ip = EXCLUDED.public_ip,
                private_ip = EXCLUDED.private_ip,
                protocol = EXCLUDED.protocol,
                listen_port = EXCLUDED.listen_port,
                public_key = EXCLUDED.public_key,
                max_peers = EXCLUDED.max_peers,
                awg_jc = EXCLUDED.awg_jc,
                awg_jmin = EXCLUDED.awg_jmin,
                awg_jmax = EXCLUDED.awg_jmax,
                awg_s1 = EXCLUDED.awg_s1,
                awg_s2 = EXCLUDED.awg_s2,
                awg_h1 = EXCLUDED.awg_h1,
                awg_h2 = EXCLUDED.awg_h2,
                awg_h3 = EXCLUDED.awg_h3,
                awg_h4 = EXCLUDED.awg_h4,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, hostname
        """, server.hostname, server.public_ip, server.private_ip,
            server.region, server.country_code, server.city,
            server.protocol, server.listen_port, server.public_key,
            server.max_peers, server.awg_jc, server.awg_jmin,
            server.awg_jmax, server.awg_s1, server.awg_s2,
            server.awg_h1, server.awg_h2, server.awg_h3, server.awg_h4)

        # Create IP pool if not exists
        await conn.execute("""
            INSERT INTO ip_pools (server_id, network, gateway)
            VALUES ($1, '10.66.66.0/24', '10.66.66.1')
            ON CONFLICT (server_id, network) DO NOTHING
        """, result["id"])

    logger.info(f"Gateway registered: {server.hostname}")
    return {"server_id": str(result["id"]), "hostname": result["hostname"]}

@app.get("/api/v1/gateway/peers")
async def get_gateway_peers(gateway_id: str = Depends(verify_gateway_token)):
    """Get all peers for this gateway (for config sync)"""
    pool = await get_db()
    async with pool.acquire() as conn:
        server = await conn.fetchrow(
            "SELECT id FROM vpn_servers WHERE hostname = $1", gateway_id
        )
        if not server:
            raise HTTPException(status_code=404, detail="Gateway not registered")

        peers = await conn.fetch("""
            SELECT id, name, public_key, assigned_ip, allowed_ips,
                   dns_servers, persistent_keepalive, mtu, enabled
            FROM vpn_peers
            WHERE server_id = $1
            ORDER BY created_at
        """, server["id"])

    return {"peers": [dict(p) for p in peers]}

@app.post("/api/v1/gateway/peers")
async def create_peer(
    peer: PeerCreate,
    gateway_id: str = Depends(verify_gateway_token)
):
    """Create a new peer on this gateway"""
    pool = await get_db()
    async with pool.acquire() as conn:
        server = await conn.fetchrow(
            "SELECT id FROM vpn_servers WHERE hostname = $1", gateway_id
        )
        if not server:
            raise HTTPException(status_code=404, detail="Gateway not registered")

        # Allocate IP
        assigned_ip = await conn.fetchval("SELECT allocate_ip($1)", server["id"])

        # Generate client token
        client_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(client_token.encode()).hexdigest()

        # Calculate expiry
        expires_at = None
        if peer.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=peer.expires_days)

        # Create peer
        result = await conn.fetchrow("""
            INSERT INTO vpn_peers (
                server_id, name, email, device_name, device_type,
                public_key, allowed_ips, assigned_ip, dns_servers,
                persistent_keepalive, mtu, expires_at, notes, api_token_hash
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id, assigned_ip
        """, server["id"], peer.name, peer.email, peer.device_name,
            peer.device_type, peer.public_key, peer.allowed_ips,
            assigned_ip, peer.dns_servers, peer.persistent_keepalive,
            peer.mtu, expires_at, peer.notes, token_hash)

    logger.info(f"Peer created: {peer.name} on {gateway_id}")
    return {
        "peer_id": str(result["id"]),
        "assigned_ip": str(result["assigned_ip"]),
        "client_token": client_token  # Return once, client must save it
    }

@app.put("/api/v1/gateway/peers/{peer_id}/sync")
async def sync_peer_status(
    peer_id: str,
    last_handshake: Optional[datetime] = None,
    rx_bytes: int = 0,
    tx_bytes: int = 0,
    gateway_id: str = Depends(verify_gateway_token)
):
    """Sync peer status from gateway (handshake, traffic)"""
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE vpn_peers SET
                last_handshake = COALESCE($1, last_handshake),
                total_rx_bytes = total_rx_bytes + $2,
                total_tx_bytes = total_tx_bytes + $3
            WHERE id = $4
        """, last_handshake, rx_bytes, tx_bytes, peer_id)
    return {"status": "synced"}

# ============================================
# Client Endpoints (Config Retrieval)
# ============================================

@app.get("/api/v1/client/config", response_class=PlainTextResponse)
async def get_client_config(peer: dict = Depends(verify_client_token)):
    """Get WireGuard config for authenticated client"""
    pool = await get_db()
    async with pool.acquire() as conn:
        config = await conn.fetchval(
            "SELECT generate_peer_config($1)", peer["id"]
        )
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@app.get("/api/v1/client/servers")
async def list_available_servers(peer: dict = Depends(verify_client_token)):
    """List all available VPN servers for client"""
    pool = await get_db()
    async with pool.acquire() as conn:
        servers = await conn.fetch("""
            SELECT id, hostname, region, country_code, city, protocol,
                   public_ip, listen_port, current_peers, max_peers
            FROM vpn_servers
            WHERE status = 'active'
            ORDER BY region, country_code
        """)
    return {"servers": [dict(s) for s in servers]}

@app.post("/api/v1/client/switch-server")
async def switch_server(
    new_server_id: str,
    peer: dict = Depends(verify_client_token)
):
    """Request to switch client to different server"""
    # This would typically queue the migration
    pool = await get_db()
    async with pool.acquire() as conn:
        # Verify server exists
        server = await conn.fetchrow(
            "SELECT id, hostname FROM vpn_servers WHERE id = $1 AND status = 'active'",
            new_server_id
        )
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

    return {
        "status": "pending",
        "message": f"Migration to {server['hostname']} queued",
        "new_server_id": new_server_id
    }

# ============================================
# Config Creation Endpoints (Admin/API Key)
# ============================================

@app.post("/api/v1/configs/create", response_model=ConfigCreateResponse)
async def create_vpn_config(
    config_req: ConfigCreate,
    x_admin_key: str = Header(...)
):
    """
    Create a new VPN configuration with auto-generated keys.
    Returns complete config file and QR code for client.

    This is the main endpoint for provisioning new VPN clients.
    """
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        # Find best server (least loaded in preferred region)
        if config_req.server_id:
            server = await conn.fetchrow(
                "SELECT * FROM vpn_servers WHERE id = $1 AND status = 'active'",
                config_req.server_id
            )
        elif config_req.region:
            server = await conn.fetchrow("""
                SELECT s.* FROM vpn_servers s
                LEFT JOIN vpn_peers p ON s.id = p.server_id
                WHERE s.status = 'active' AND s.region = $1
                GROUP BY s.id
                ORDER BY COUNT(p.id) ASC
                LIMIT 1
            """, config_req.region)
        else:
            # Auto-select least loaded server
            server = await conn.fetchrow("""
                SELECT s.* FROM vpn_servers s
                LEFT JOIN vpn_peers p ON s.id = p.server_id
                WHERE s.status = 'active'
                GROUP BY s.id
                ORDER BY COUNT(p.id) ASC
                LIMIT 1
            """)

        if not server:
            raise HTTPException(status_code=404, detail="No available servers")

        # Generate WireGuard keypair for client
        private_key, public_key = generate_wireguard_keypair()

        # Allocate IP address
        assigned_ip = await conn.fetchval("SELECT allocate_ip($1)", server["id"])

        # Generate client token for future config retrieval
        client_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(client_token.encode()).hexdigest()

        # Calculate expiry
        expires_at = None
        if config_req.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=config_req.expires_days)

        # Create peer in database
        peer = await conn.fetchrow("""
            INSERT INTO vpn_peers (
                server_id, name, email, device_name, device_type,
                public_key, allowed_ips, assigned_ip, dns_servers,
                persistent_keepalive, mtu, expires_at, notes, api_token_hash
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 25, 1420, $10, $11, $12)
            RETURNING id, assigned_ip
        """, server["id"], config_req.name, config_req.email,
            config_req.device_name, config_req.device_type,
            public_key, config_req.allowed_ips, assigned_ip,
            config_req.dns_servers, expires_at, config_req.notes, token_hash)

        # Build server endpoint
        endpoint = f"{server['public_ip']}:{server['listen_port']}"

        # Build complete WireGuard config
        config = build_wireguard_config(
            private_key=private_key,
            address=f"{assigned_ip}/32",
            dns=config_req.dns_servers,
            server_public_key=server["public_key"],
            endpoint=endpoint,
            allowed_ips=config_req.allowed_ips,
            persistent_keepalive=25,
            mtu=1420,
            # AmneziaWG params if applicable
            awg_jc=server.get("awg_jc"),
            awg_jmin=server.get("awg_jmin"),
            awg_jmax=server.get("awg_jmax"),
            awg_s1=server.get("awg_s1"),
            awg_s2=server.get("awg_s2"),
            awg_h1=server.get("awg_h1"),
            awg_h2=server.get("awg_h2"),
            awg_h3=server.get("awg_h3"),
            awg_h4=server.get("awg_h4"),
        )

        # Generate QR code
        qr_code = generate_qr_code(config)

        logger.info(f"Created config for {config_req.name} on {server['hostname']}")

        return ConfigCreateResponse(
            peer_id=str(peer["id"]),
            name=config_req.name,
            config=config,
            private_key=private_key,
            public_key=public_key,
            assigned_ip=str(assigned_ip),
            server_endpoint=endpoint,
            server_public_key=server["public_key"],
            qr_code=qr_code,
            client_token=client_token
        )


@app.get("/api/v1/configs/{peer_id}")
async def get_config_by_id(peer_id: str, x_admin_key: str = Header(...)):
    """Get config details for a peer (admin only, no private key)"""
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        peer = await conn.fetchrow("""
            SELECT p.*, s.hostname, s.public_ip, s.listen_port, s.public_key as server_public_key
            FROM vpn_peers p
            JOIN vpn_servers s ON p.server_id = s.id
            WHERE p.id = $1
        """, peer_id)

    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    return {
        "peer_id": str(peer["id"]),
        "name": peer["name"],
        "public_key": peer["public_key"],
        "assigned_ip": str(peer["assigned_ip"]),
        "server": peer["hostname"],
        "endpoint": f"{peer['public_ip']}:{peer['listen_port']}",
        "enabled": peer["enabled"],
        "created_at": peer["created_at"].isoformat(),
        "last_handshake": peer["last_handshake"].isoformat() if peer["last_handshake"] else None
    }


@app.delete("/api/v1/configs/{peer_id}")
async def delete_config(peer_id: str, x_admin_key: str = Header(...)):
    """Delete a peer configuration"""
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM vpn_peers WHERE id = $1", peer_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Peer not found")

    logger.info(f"Deleted peer: {peer_id}")
    return {"status": "deleted", "peer_id": peer_id}


@app.patch("/api/v1/configs/{peer_id}/disable")
async def disable_config(peer_id: str, x_admin_key: str = Header(...)):
    """Disable a peer (revoke access without deleting)"""
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE vpn_peers SET enabled = false WHERE id = $1", peer_id
        )

    logger.info(f"Disabled peer: {peer_id}")
    return {"status": "disabled", "peer_id": peer_id}


@app.patch("/api/v1/configs/{peer_id}/enable")
async def enable_config(peer_id: str, x_admin_key: str = Header(...)):
    """Re-enable a disabled peer"""
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE vpn_peers SET enabled = true WHERE id = $1", peer_id
        )

    logger.info(f"Enabled peer: {peer_id}")
    return {"status": "enabled", "peer_id": peer_id}


# ============================================
# Admin Endpoints
# ============================================

@app.get("/api/v1/admin/servers")
async def list_all_servers(x_admin_key: str = Header(...)):
    """List all VPN servers (admin only)"""
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        servers = await conn.fetch("SELECT * FROM server_summary ORDER BY region")
    return {"servers": [dict(s) for s in servers]}

@app.get("/api/v1/admin/stats")
async def get_global_stats(x_admin_key: str = Header(...)):
    """Get global VPN statistics"""
    if x_admin_key != os.getenv("ADMIN_API_KEY", ""):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    pool = await get_db()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM vpn_servers WHERE status = 'active') as active_servers,
                (SELECT COUNT(*) FROM vpn_peers WHERE enabled = true) as active_peers,
                (SELECT COUNT(*) FROM vpn_peers) as total_peers,
                (SELECT SUM(total_rx_bytes) FROM vpn_peers) as total_rx_bytes,
                (SELECT SUM(total_tx_bytes) FROM vpn_peers) as total_tx_bytes,
                (SELECT COUNT(*) FROM vpn_peers WHERE last_handshake > NOW() - INTERVAL '5 minutes') as connected_now
        """)
    return dict(stats)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
