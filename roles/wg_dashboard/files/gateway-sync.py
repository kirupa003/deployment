#!/usr/bin/env python3
"""
VPN Gateway Sync Service
Synchronizes local WireGuard configuration with central database
"""

import os
import sys
import json
import time
import hashlib
import logging
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Configuration from environment
CONFIG = {
    "api_url": os.getenv("VPN_API_URL", "http://localhost:8080"),
    "gateway_id": os.getenv("GATEWAY_ID", ""),
    "gateway_token": os.getenv("GATEWAY_TOKEN", ""),
    "sync_interval": int(os.getenv("SYNC_INTERVAL", 60)),
    "wg_interface": os.getenv("WG_INTERFACE", "wg0"),
    "protocol": os.getenv("VPN_PROTOCOL", "wireguard"),
    "region": os.getenv("VPN_REGION", "unknown"),
    "country_code": os.getenv("VPN_COUNTRY", "XX"),
    "dashboard_db": os.getenv("DASHBOARD_DB", "/opt/wg-dashboard/data/db.sqlite"),
    "public_ip": os.getenv("PUBLIC_IP", ""),
    "listen_port": int(os.getenv("WG_LISTEN_PORT", 51820)),
}

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_public_ip() -> str:
    """Get public IP address"""
    if CONFIG["public_ip"]:
        return CONFIG["public_ip"]
    try:
        resp = requests.get("https://api.ipify.org", timeout=5)
        return resp.text.strip()
    except Exception:
        return "0.0.0.0"


def get_wg_public_key() -> str:
    """Get WireGuard public key from interface"""
    try:
        result = subprocess.run(
            ["wg", "show", CONFIG["wg_interface"], "public-key"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Try to generate from private key
        conf_path = f"/etc/wireguard/{CONFIG['wg_interface']}.conf"
        if os.path.exists(conf_path):
            with open(conf_path) as f:
                for line in f:
                    if line.strip().startswith("PrivateKey"):
                        private_key = line.split("=", 1)[1].strip()
                        result = subprocess.run(
                            ["wg", "pubkey"],
                            input=private_key, capture_output=True, text=True
                        )
                        return result.stdout.strip()
    return ""


def get_wg_peers() -> List[Dict]:
    """Get current WireGuard peers from interface"""
    peers = []
    try:
        result = subprocess.run(
            ["wg", "show", CONFIG["wg_interface"], "dump"],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        # Skip first line (interface info)
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) >= 5:
                peer = {
                    "public_key": parts[0],
                    "preshared_key": parts[1] if parts[1] != "(none)" else None,
                    "endpoint": parts[2] if parts[2] != "(none)" else None,
                    "allowed_ips": parts[3].split(",") if parts[3] else [],
                    "last_handshake": int(parts[4]) if parts[4] != "0" else None,
                    "rx_bytes": int(parts[5]) if len(parts) > 5 else 0,
                    "tx_bytes": int(parts[6]) if len(parts) > 6 else 0,
                }
                peers.append(peer)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get WireGuard peers: {e}")
    return peers


def get_peers_from_dashboard_db() -> List[Dict]:
    """Get peer information from WG Dashboard SQLite database"""
    peers = []
    db_path = CONFIG["dashboard_db"]
    if not os.path.exists(db_path):
        logger.warning(f"Dashboard DB not found: {db_path}")
        return peers

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query peers table (adjust based on WG Dashboard schema)
        cursor.execute("""
            SELECT name, public_key, private_key, dns, allowed_ip,
                   endpoint_allowed_ip, mtu, keepalive, enabled
            FROM peer
        """)

        for row in cursor.fetchall():
            peers.append({
                "name": row["name"],
                "public_key": row["public_key"],
                "allowed_ips": row["allowed_ip"].split(",") if row["allowed_ip"] else [],
                "dns": row["dns"].split(",") if row["dns"] else [],
                "mtu": row["mtu"],
                "keepalive": row["keepalive"],
                "enabled": bool(row["enabled"]),
            })
        conn.close()
    except Exception as e:
        logger.error(f"Failed to read dashboard DB: {e}")
    return peers


def register_gateway():
    """Register this gateway with central API"""
    headers = {
        "X-Gateway-ID": CONFIG["gateway_id"],
        "X-Gateway-Token": CONFIG["gateway_token"],
        "Content-Type": "application/json"
    }

    data = {
        "hostname": CONFIG["gateway_id"],
        "public_ip": get_public_ip(),
        "region": CONFIG["region"],
        "country_code": CONFIG["country_code"],
        "protocol": CONFIG["protocol"],
        "listen_port": CONFIG["listen_port"],
        "public_key": get_wg_public_key(),
    }

    # Add AmneziaWG params if applicable
    if CONFIG["protocol"] == "amneziawg":
        data.update({
            "awg_jc": int(os.getenv("AWG_JC", 4)),
            "awg_jmin": int(os.getenv("AWG_JMIN", 40)),
            "awg_jmax": int(os.getenv("AWG_JMAX", 70)),
            "awg_s1": int(os.getenv("AWG_S1", 0)),
            "awg_s2": int(os.getenv("AWG_S2", 0)),
            "awg_h1": int(os.getenv("AWG_H1", 1)),
            "awg_h2": int(os.getenv("AWG_H2", 2)),
            "awg_h3": int(os.getenv("AWG_H3", 3)),
            "awg_h4": int(os.getenv("AWG_H4", 4)),
        })

    try:
        resp = requests.post(
            f"{CONFIG['api_url']}/api/v1/gateway/register",
            headers=headers,
            json=data,
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"Gateway registered: {result}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to register gateway: {e}")
        return False


def sync_peer_status():
    """Sync peer handshake and traffic stats to central API"""
    headers = {
        "X-Gateway-ID": CONFIG["gateway_id"],
        "X-Gateway-Token": CONFIG["gateway_token"],
    }

    wg_peers = get_wg_peers()
    for peer in wg_peers:
        if peer["last_handshake"]:
            try:
                # Convert unix timestamp to ISO format
                handshake_time = datetime.fromtimestamp(peer["last_handshake"]).isoformat()

                resp = requests.put(
                    f"{CONFIG['api_url']}/api/v1/gateway/peers/{peer['public_key']}/sync",
                    headers=headers,
                    params={
                        "last_handshake": handshake_time,
                        "rx_bytes": peer["rx_bytes"],
                        "tx_bytes": peer["tx_bytes"],
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    logger.debug(f"Synced peer: {peer['public_key'][:8]}...")
            except requests.RequestException as e:
                logger.error(f"Failed to sync peer status: {e}")


def fetch_peer_configs():
    """Fetch peer configurations from central API"""
    headers = {
        "X-Gateway-ID": CONFIG["gateway_id"],
        "X-Gateway-Token": CONFIG["gateway_token"],
    }

    try:
        resp = requests.get(
            f"{CONFIG['api_url']}/api/v1/gateway/peers",
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("peers", [])
    except requests.RequestException as e:
        logger.error(f"Failed to fetch peer configs: {e}")
        return []


def apply_peer_config(peer: Dict):
    """Apply a peer configuration to WireGuard"""
    try:
        # Add peer using wg command
        cmd = [
            "wg", "set", CONFIG["wg_interface"],
            "peer", peer["public_key"],
            "allowed-ips", ",".join(peer["allowed_ips"]),
        ]

        if peer.get("preshared_key"):
            # Write PSK to temp file for security
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(peer["preshared_key"])
                psk_file = f.name
            cmd.extend(["preshared-key", psk_file])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if psk_file:
            os.unlink(psk_file)

        if result.returncode != 0:
            logger.error(f"Failed to add peer: {result.stderr}")
            return False

        # Save config
        subprocess.run(["wg-quick", "save", CONFIG["wg_interface"]])
        logger.info(f"Added peer: {peer['public_key'][:8]}...")
        return True
    except Exception as e:
        logger.error(f"Error applying peer config: {e}")
        return False


def sync_configs():
    """Main sync function - fetch and apply configurations"""
    logger.info("Starting config sync...")

    # Get current local peers
    local_peers = {p["public_key"]: p for p in get_wg_peers()}

    # Get peers from central API
    remote_peers = fetch_peer_configs()

    for peer in remote_peers:
        pub_key = peer["public_key"]
        if pub_key not in local_peers:
            if peer.get("enabled", True):
                logger.info(f"New peer from central DB: {pub_key[:8]}...")
                apply_peer_config(peer)
        else:
            # Check if peer should be disabled
            if not peer.get("enabled", True):
                logger.info(f"Removing disabled peer: {pub_key[:8]}...")
                subprocess.run([
                    "wg", "set", CONFIG["wg_interface"],
                    "peer", pub_key, "remove"
                ])

    logger.info("Config sync completed")


def main():
    """Main sync loop"""
    logger.info(f"VPN Gateway Sync Service starting...")
    logger.info(f"Gateway ID: {CONFIG['gateway_id']}")
    logger.info(f"API URL: {CONFIG['api_url']}")
    logger.info(f"Protocol: {CONFIG['protocol']}")
    logger.info(f"Sync interval: {CONFIG['sync_interval']}s")

    # Initial registration
    if not register_gateway():
        logger.error("Failed initial gateway registration, retrying...")
        time.sleep(10)
        if not register_gateway():
            logger.error("Gateway registration failed. Exiting.")
            sys.exit(1)

    # Main loop
    while True:
        try:
            # Sync peer status (handshakes, traffic)
            sync_peer_status()

            # Sync configurations from central DB
            sync_configs()

        except Exception as e:
            logger.error(f"Sync error: {e}")

        time.sleep(CONFIG["sync_interval"])


if __name__ == "__main__":
    main()
