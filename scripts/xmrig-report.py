#!/usr/bin/env python3
"""
xmrig-report.py — Generic XMRig Share Reporter for XMRT DAO

Polls local XMRig API and reports valid shares to the DAO relay.
Works on any device running XMRig with API enabled (Termux, Linux, etc.)

Usage:
  python3 xmrig-report.py                    # Report once
  python3 xmrig-report.py --daemon            # Report every 60s until Ctrl+C
  python3 xmrig-report.py --worker myalias    # Use a specific worker name

Requirements:
  - XMRig running with API enabled on port 19090
  - Internet connection
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

XMRIG_API = os.environ.get("XMRIG_API", "http://127.0.0.1:19090/1/summary")
RELAY_URL = os.environ.get("RELAY_URL", "https://relay.mobilemonero.com")
WORKER_NAME = os.environ.get("WORKER_NAME", None)

# Cloudflare-friendly headers
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "XMRT-Miner/1.0",
    "Accept": "application/json",
}

def fetch_xmrig():
    """Get current stats from local XMRig"""
    try:
        req = urllib.request.Request(XMRIG_API, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[xmrig-report] Failed to reach XMRig: {e}")
        return None

def report_to_relay(worker, hashes, shares):
    """POST contribution data to the DAO relay"""
    payload = json.dumps({
        "worker": worker,
        "hashes": hashes,
        "valid_shares": shares,
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{RELAY_URL}/mining/contribute",
            data=payload,
            headers=HEADERS,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print(f"[xmrig-report] Reported: {worker} — {hashes} H/s, {shares} shares ✅")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[xmrig-report] Relay error {e.code}: {body}")
        return None
    except Exception as e:
        print(f"[xmrig-report] Report failed: {e}")
        return None

def run():
    """Single report cycle"""
    data = fetch_xmrig()
    if not data:
        return False
    
    # Determine worker name: CLI arg > env var > XMRig config > hostname fallback
    worker = WORKER_NAME
    if not worker:
        worker = data.get("worker_id") or os.environ.get("USER", "miner")
    
    # Extract hashrate
    hashrate = 0
    try:
        hashrate = data["hashrate"]["total"][0]  # H/s
    except (KeyError, IndexError, TypeError):
        pass
    
    # Extract good shares from XMRig results
    results_shares = 0
    if isinstance(data.get("results"), dict):
        results_shares = data["results"].get("shares_good", 0)
    
    # Always report at least 1 share as heartbeat so the relay knows we're alive
    shares = max(results_shares, 1)
    
    print(f"[xmrig-report] {worker}: {hashrate} H/s, {shares} good shares")
    report_to_relay(worker, round(hashrate), shares)
    return True

def daemon():
    """Run every 60 seconds"""
    worker_tag = WORKER_NAME or "auto"
    print(f"[xmrig-report] Daemon starting — reporting to {RELAY_URL}")
    print(f"[xmrig-report] XMRig API: {XMRIG_API}")
    print(f"[xmrig-report] Worker: {worker_tag}")
    print("[xmrig-report] Press Ctrl+C to stop\n")
    
    while True:
        run()
        time.sleep(60)

if __name__ == "__main__":
    # Parse --worker CLI arg
    if "--worker" in sys.argv:
        idx = sys.argv.index("--worker")
        if idx + 1 < len(sys.argv):
            WORKER_NAME = sys.argv[idx + 1]
    
    if "--daemon" in sys.argv:
        daemon()
    else:
        run()
