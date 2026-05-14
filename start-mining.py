#!/usr/bin/env python3
"""
XMRT DAO Mining Launcher
Auto-detects OS, downloads xmrig, generates config, and starts mining.
Works offline after first run. Auto-donates 1% to XMRT DAO pool.
Python 3.10+, zero external dependencies (stdlib + urllib only).
"""

import os
import sys
import json
import platform
import subprocess
import urllib.request
import urllib.error
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import Optional

# ── Configuration ────────────────────────────────────────────────────────────
XMRT_DONATE_POOL = "pool.xmrtdao.org"
XMRT_DONATE_PORT = 3333
XMRT_DONATE_ADDRESS = (
    "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A"
)
XMRT_DONATE_PERCENT = 1.0
XMRIG_RELEASE_URL = "https://api.github.com/repos/xmrig/xmrig/releases/latest"
XMRIG_ANDROID_URL = "https://github.com/xmrig/xmrig/releases/latest/download/xmrig-android.tar.gz"
CACHE_DIR = Path.home() / ".xmrtdao" / "mmlauncher"
CONFIG_PATH = CACHE_DIR / "config.json"

# ── ASCII Banner ─────────────────────────────────────────────────────────────
BANNER = r"""
    _    __  __  _____   ____    ___    ___  _   _
   / \  |  \/  ||_   _| |  _ \  / _ \  / _ \| \ | |
  / _ \ | |\/| |  | |   | | | || | | || | | |  \|
 / ___ \| |  | |  | |   | |_| || |_| || |_| | |\  |
/_/   \_\_|  |_|  |_|   |____/  \___/  \___/|_| \_|

        X M R T   D A O   M i n i n g   L a u n c h e r
        -----------------------------------------------
        Auto-donate: 1% to XMRT DAO development pool
"""


def detect_os() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    is_android = "ANDROID_ROOT" in os.environ or Path("/system/bin/app_process").exists()

    if "TERMUX_VERSION" in os.environ or "TERMUX_API_VERSION" in os.environ:
        return "termux"
    if is_android:
        return "android"
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


def get_arch() -> str:
    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64"):
        return "x64"
    if arch.startswith("arm") or arch.startswith("aarch"):
        if platform.architecture()[0] == "64bit" or "64" in arch:
            return "arm64"
        return "arm"
    return arch


def get_binary_name(os_name: str) -> str:
    return "xmrig.exe" if os_name == "windows" else "xmrig"


def get_local_binary(os_name: str) -> Path:
    name = "xmrig-android" if os_name in ("termux", "android") else get_binary_name(os_name)
    return CACHE_DIR / name


def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "xmrtdao-mmlauncher/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: Path, timeout: int = 120) -> Path:
    print(f"[*] Downloading {dest.name} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "xmrtdao-mmlauncher/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"[+] Saved {len(data)} bytes to {dest}")
    return dest


def download_xmrig(os_name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    binary = get_local_binary(os_name)
    if binary.exists():
        return binary

    if os_name in ("termux", "android"):
        archive = CACHE_DIR / "xmrig-android.tar.gz"
        if not archive.exists():
            download_file(XMRIG_ANDROID_URL, archive)
        print("[*] Extracting android binary...")
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(path=CACHE_DIR)
        extracted = CACHE_DIR / "xmrig"
        if extracted.exists():
            extracted.rename(binary)
            binary.chmod(0o755)
        archive.unlink(missing_ok=True)
        return binary

    arch = get_arch()
    tag = fetch_json(XMRIG_RELEASE_URL)["tag_name"]
    base_url = f"https://github.com/xmrig/xmrig/releases/download/{tag}/xmrig-{tag}"
    if os_name == "windows":
        url = f"{base_url}-msvc-win64.zip"
        archive = CACHE_DIR / "xmrig.zip"
    elif os_name == "macos":
        url = f"{base_url}-macos-{arch}.tar.gz"
        archive = CACHE_DIR / "xmrig.tar.gz"
    else:
        url = f"{base_url}-linux-{arch}.tar.gz"
        archive = CACHE_DIR / "xmrig.tar.gz"

    if not archive.exists():
        download_file(url, archive)

    print("[*] Extracting...")
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as zf:
            for member in zf.namelist():
                if member.endswith(get_binary_name(os_name)):
                    zf.extract(member, CACHE_DIR)
                    src = CACHE_DIR / member
                    src.rename(binary)
                    binary.chmod(0o755)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            for member in tf.getmembers():
                if member.isfile() and member.name.endswith(get_binary_name(os_name)):
                    tf.extract(member, CACHE_DIR)
                    src = CACHE_DIR / member.name
                    src.rename(binary)
                    binary.chmod(0o755)

    archive.unlink(missing_ok=True)
    if not binary.exists():
        raise RuntimeError("Failed to extract xmrig binary.")
    return binary


def get_suggested_threads() -> int:
    try:
        cpu_count = os.cpu_count() or 2
        if detect_os() in ("termux", "android"):
            return max(1, int(cpu_count * 0.5))
        return max(1, cpu_count - 1)
    except Exception:
        return 2


def get_wallet_address() -> str:
    env_addr = os.environ.get("XMRT_WALLET", os.environ.get("XMR_WALLET", "")).strip()
    if env_addr:
        print(f"[+] Using wallet from environment variable.")
        return env_addr

    print("\n[!] No XMRT_WALLET or XMR_WALLET environment variable found.")
    print("    Enter your Monero wallet address for mining rewards:")
    while True:
        try:
            addr = input("Wallet Address: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[-] Aborted.")
            sys.exit(1)
        if len(addr) >= 95 and addr.startswith("4"):
            return addr
        print("    That doesn't look like a standard Monero address. Please retry.")


def generate_config(wallet: str, threads: int, os_name: str) -> dict:
    donate = {
        "url": f"{XMRT_DONATE_POOL}:{XMRT_DONATE_PORT}",
        "user": XMRT_DONATE_ADDRESS,
        "pass": "xmrt_donation",
        "keepalive": True,
        "tls": False,
        "nicehash": False,
    }

    config = {
        "api": {"id": None, "worker-id": None},
        "http": {"enabled": False, "host": "127.0.0.1", "port": 0, "access-token": None, "restricted": True},
        "autosave": True,
        "background": False,
        "colors": True,
        "title": True,
        "randomx": {"init": -1, "init-avx2": -1, "mode": "auto", "1gb-pages": False, "rdmsr": True, "wrmsr": True},
        "cpu": {
            "enabled": True,
            "huge-pages": True,
            "huge-pages-jit": False,
            "hw-aes": None,
            "priority": None,
            "memory-pool": False,
            "yield": True,
            "max-threads-hint": threads,
            "asm": True,
            "argon2-impl": None,
            "astrobwt-max-size": 550,
            "astrobwt-avx2": False,
            "argon2": [0, 2, 3],
            "astrobwt": [0, 1, 2, 3],
            "cn": [[1, 0], [1, 1], [1, 2]],
            "cn-extremes": [[1, 0], [1, 1], [1, 2]],
            "cn-heavy": [[1, 0], [1, 2]],
            "cn-lite": [[1, 0], [1, 1], [1, 2], [1, 3]],
            "cn-pico": [[2, 0], [2, 1], [2, 2], [2, 3]],
            "cn/gpu": [[1, 0], [1, 1], [1, 2], [1, 3], [1, 4], [1, 5], [1, 6], [1, 7]],
            "panthera": [0, 1, 2, 3],
            "rx": [0, 1, 2, 3],
            "rx/wow": [0, 2, 3],
            "cn/upx2": [[3, 0], [3, 1], [3, 2], [3, 3]],
            "ghostrider": [[8, 0], [8, 1], [8, 2]],
        },
        "opencl": {"enabled": False, "cache": True, "loader": None, "platform": "AMD", "adl": True},
        "cuda": {"enabled": False, "loader": None, "nvml": True},
        "donate-level": 1,
        "donate-over-proxy": 1,
        "log-file": None,
        "pools": [
            {
                "url": "randomxmonero.auto.nicehash.com:9200",
                "user": wallet,
                "pass": "x",
                "nicehash": True,
                "keepalive": True,
                "tls": False,
            },
            donate,
        ],
        "print-time": 60,
        "retries": 5,
        "retry-pause": 5,
        "syslog": False,
        "user-agent": None,
        "watch": False,
    }

    if os_name in ("termux", "android"):
        config["randomx"]["1gb-pages"] = False
        config["cpu"]["huge-pages"] = False

    return config


def ensure_config(os_name: str) -> Path:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            if data.get("pools", [{}])[0].get("user"):
                print("[+] Using cached config.json")
                return CONFIG_PATH
        except Exception:
            pass

    wallet = get_wallet_address()
    threads = get_suggested_threads()
    config = generate_config(wallet, threads, os_name)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    print(f"[+] Config written to {CONFIG_PATH}")
    print(f"[+] Mining threads: {threads}")
    return CONFIG_PATH


def launch(binary: Path, config: Path):
    cmd = [str(binary), "-c", str(config)]
    print("\n[*] Starting xmrig...\n")
    try:
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        print("\n[-] Interrupted by user. Exiting.")


def main() -> int:
    print(BANNER)
    os_name = detect_os()
    arch = get_arch()
    print(f"[*] Detected OS : {os_name}")
    print(f"[*] Detected Arch: {arch}")
    print(f"[*] Cache dir   : {CACHE_DIR}")
    print()

    try:
        binary = get_local_binary(os_name)
        if not binary.exists():
            print("[*] xmrig not found locally. Downloading...")
            binary = download_xmrig(os_name)
        else:
            print("[+] xmrig binary found in cache.")
        config = ensure_config(os_name)
        launch(binary, config)
    except urllib.error.URLError as e:
        print(f"\n[-] Network error: {e}")
        binary = get_local_binary(os_name)
        if binary.exists() and CONFIG_PATH.exists():
            print("[!] Falling back to offline mode...")
            launch(binary, CONFIG_PATH)
        else:
            print("[-] No cached binary or config. Connect to the internet and retry.")
            return 1
    except Exception as e:
        print(f"\n[-] Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
