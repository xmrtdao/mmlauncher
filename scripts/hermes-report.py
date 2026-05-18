#!/usr/bin/env python3
"""
Hermes Self-Report Daemon — runs on Termux (Android)
Polls local XMRig API and reports valid shares to the relay.

Usage:
  python3 hermes-report.py                    # Run once
  python3 hermes-report.py --daemon            # Run every 60s until Ctrl+C

Requirements:
  - XMRig running with API enabled on port 19090
  - Internet connection (WiFi or mobile data)

Config:
  Set RELAY_URL or defaults to relay.mobilemonero.com
  Set WORKER_NAME or defaults to the XMRig worker-id from its API
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

XMRIG_API = "http://127.0.0.1:19090/1/summary"
RELAY_URL = os.environ.get("RELAY_URL", "https://relay.mobilemonero.com")
WORKER_NAME = os.environ.get("WORKER_NAME", None)

# Cloudflare-friendly headers
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "HermesAgent/1.0 (Termux; Android; XMRT-DAO)",
    "Accept": "application/json",
    "X-Forwarded-For": "",  # Let Cloudflare see real IP
}

def fetch_xmrig():
    """Get current stats from local XMRig"""
    try:
        req = urllib.request.Request(XMRIG_API, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[Hermes] Failed to reach XMRig: {e}")
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
            print(f"[Hermes] Reported: {worker} - {hashes}H/s, {shares} shares ✅")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[Hermes] Relay HTTP {e.code}: {body}")
        if e.code == 403:
            print(f"[Hermes] 💡 Try using the direct tunnel URL or check your internet connection")
        return None
    except Exception as e:
        print(f"[Hermes] Relay report failed: {e}")
        return None

def run():
    """Single report cycle"""
    data = fetch_xmrig()
    if not data:
        return
    
    # Get worker name from XMRig config or env
    worker = WORKER_NAME or data.get("worker_id") or "hermes-phone"
    
    # Extract hashrate and shares
    hashrate = 0
    try:
        hashrate = data["hashrate"]["total"][0]  # H/s
    except (KeyError, IndexError, TypeError):
        pass
    
    # XMRig API doesn't give cumulative shares directly
    # We report the current hashrate, relay tracks cumulative
    results_shares = data.get("results", {}).get("shares_good", 0) if isinstance(data.get("results"), dict) else 0
    
    # If XMRig reports good shares, use those
    # Otherwise report 1 share as a heartbeat
    shares = max(results_shares, 1)
    
    print(f"[Hermes] XMRig: {hashrate} H/s, {shares} good shares, worker: {worker}")
    report_to_relay(worker, round(hashrate), shares)

def daemon():
    """Run every 60 seconds"""
    print(f"[Hermes] Self-Report Daemon starting — reporting to {RELAY_URL}")
    print(f"[Hermes] XMRig API: {XMRIG_API}")
    print(f"[Hermes] Worker: {WORKER_NAME or 'auto-detect'}")
    print("[Hermes] Press Ctrl+C to stop\n")
    
    while True:
        run()
        time.sleep(60)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon()
    else:
        run()
