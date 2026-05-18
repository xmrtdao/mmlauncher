#!/usr/bin/env python3
"""
xmrig-report.py — XMRT DAO Miner Heartbeat

Polls local XMRig API and reports current hashrate to the DAO relay.
Worker name is read from XMRig's config — no CLI aliases allowed.
Only one instance per miner (tied to the XMRig worker-id).

Usage:
  python3 xmrig-report.py              # Report once
  python3 xmrig-report.py --daemon      # Report every 60s
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

XMRIG_API = os.environ.get("XMRIG_API", "http://127.0.0.1:19090/1/summary")
RELAY_URL = os.environ.get("RELAY_URL", "https://relay.mobilemonero.com")

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "XMRT-Miner/1.0",
    "Accept": "application/json",
}

def fetch_xmrig():
    try:
        req = urllib.request.Request(XMRIG_API, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[xmrig-report] XMRig unreachable: {e}")
        return None

def report_heartbeat(worker, hashrate):
    """Send current hashrate to relay (no cumulative shares — relay handles pool math)"""
    payload = json.dumps({
        "worker": worker,
        "hashrate": round(hashrate),
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{RELAY_URL}/mining/heartbeat",
            data=payload,
            headers=HEADERS,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print(f"[xmrig-report] {worker}: {hashrate} H/s ✅")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[xmrig-report] Relay error {e.code}: {body}")
        return None
    except Exception as e:
        print(f"[xmrig-report] Failed: {e}")
        return None

def run():
    data = fetch_xmrig()
    if not data:
        return False
    
    # Worker name MUST come from XMRig config — no CLI aliases
    worker = data.get("worker_id") or "unknown"
    
    hashrate = 0
    try:
        hashrate = data["hashrate"]["total"][0]
    except (KeyError, IndexError, TypeError):
        pass
    
    report_heartbeat(worker, hashrate)
    return True

def daemon():
    print(f"[xmrig-report] Heartbeat daemon → {RELAY_URL}")
    print(f"[xmrig-report] XMRig API: {XMRIG_API}")
    print(f"[xmrig-report] Worker: from XMRig config (no --worker flag)")
    print("[xmrig-report] Ctrl+C to stop\n")
    while True:
        run()
        time.sleep(60)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon()
    else:
        run()
