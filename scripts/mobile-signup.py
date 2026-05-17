# script.py
import os
import sys
import time
import subprocess
import json
import hashlib
import random
from collections import OrderedDict

# ASCII Art and Branding
XMRT_ASCII = r"""
██╗  ██╗███╗   ███╗██████╗ ████████╗
╚██╗██╔╝████╗ ████║██╔══██╗╚══██╔══╝
 ╚███╔╝ ██╔████╔██║██████╔╝   ██║   
 ██╔██╗ ██║╚██╔╝██║██╔══██╗   ██║   
██╔╝ ██╗██║ ╚═╝ ██║██║  ██║   ██║   
╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   
D E C E N T R A L I Z E D   A U T O N O M O U S   O R G A N I Z A T I O N
"""

POOL_WALLET = "46UxNFuGM2E3UwmZWWJicaRPoRwqwW4byQkaTHkX8yPcVihp91qAVtSFipWUGJJUyTXgzSqxzDQtNLf2bsp2DX2qCCgC5mg"

def colorful_print(text, color_code):
    """Print colored text in Termux"""
    print(f"\033[{color_code}m{text}\033[0m")

def show_header():
    """Display branded welcome screen"""
    os.system('clear')
    colorful_print(XMRT_ASCII, "36")
    colorful_print("\nWelcome to XMRT DAO Mobile Mining Initiative\n", "33")
    colorful_print("="*60, "34")
    print()

def install_dependencies():
    """Install required Termux packages"""
    colorful_print("\n🔧 Setting up environment...", "35")
    packages = [
        "python", "clang", "nodejs", "openssl-tool",
        "git", "cmake", "make", "libuv", "libmicrohttpd"
    ]
    
    try:
        subprocess.run("apt update && apt upgrade -y", 
                      shell=True, check=True)
        subprocess.run(f"apt install -y {' '.join(packages)}",
                      shell=True, check=True)
        colorful_print("✅ Environment setup complete!", "32")
    except subprocess.CalledProcessError as e:
        colorful_print(f"❌ Setup failed: {str(e)}", "31")
        sys.exit(1)

def generate_user_number(username):
    """Create unique user ID from username"""
    seed = f"{username}-{time.time()}-{random.randint(1000,9999)}"
    return hashlib.sha256(seed.encode()).hexdigest()[:8].upper()

def user_registration():
    """Collect user information and create config"""
    show_header()
    colorful_print("📝 DAO Membership Registration\n", "36")
    
    user_data = OrderedDict()
    user_data['username'] = input("Choose your mining alias: ").strip()
    user_data['user_number'] = generate_user_number(user_data['username'])
    user_data['timestamp'] = int(time.time())
    
    with open('xmrt_miner.json', 'w') as f:
        json.dump(user_data, f, indent=2)
        
    colorful_print(f"\n🎉 Account created! Your Miner ID: {user_data['user_number']}", "32")
    return user_data

def configure_miner(user_number):
    """Create XMRig configuration file with HTTP API enabled"""
    config = {
        "autosave": True,
        "cpu": True,
        "opencl": False,
        "cuda": False,
        "api": {
            "id": None,
            "worker-id": user_number,
            "http-port": 19090,
            "access-token": None,
            "restricted": True
        },
        "pools": [{
            "url": "pool.supportxmr.com:3333",
            "user": f"{POOL_WALLET}.{user_number}",
            "pass": "xmrt-dao-mobile",
            "keepalive": True,
            "tls": False
        }]
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    colorful_print("📄 Miner configuration generated", "34")

def install_miner():
    """Install and build XMRig with existence check"""
    colorful_print("\n⛏️ Installing XMRig miner...", "33")
    try:
        if not os.path.exists("xmrig"):
            subprocess.run("git clone https://github.com/xmrig/xmrig.git",
                          shell=True, check=True)
        else:
            colorful_print("⚠️ Using existing XMRig repository", "33")
        
        os.chdir("xmrig")
        
        if not os.path.exists("build/xmrig"):
            subprocess.run(
                "mkdir -p build && cd build && "
                "cmake .. -DWITH_HWLOC=OFF -DWITH_OPENCL=OFF -DWITH_CUDA=OFF && "
                "make -j$(nproc)",
                shell=True, check=True
            )
            colorful_print("✅ Miner installation complete!", "32")
        else:
            colorful_print("⚠️ Using existing XMRig build", "33")
            
    except subprocess.CalledProcessError as e:
        colorful_print(f"❌ Installation failed: {str(e)}", "31")
        sys.exit(1)
    finally:
        os.chdir("..")

def register_with_dao(user_number, username):
    """Register this miner with the XMRT DAO relay for reward tracking"""
    import urllib.request
    import json
    
    colorful_print("\n📡 Registering with XMRT DAO...", "35")
    try:
        payload = json.dumps({
            "worker": user_number,
            "alias": username,
            "hashes": 0,
            "valid_shares": 0
        }).encode()
        req = urllib.request.Request(
            "https://relay.mobilemonero.com/mining/contribute",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get("recorded"):
            colorful_print("✅ Registered! Rewards tracking active.", "32")
        else:
            colorful_print("⚠️ Registration sent but response unexpected.", "33")
    except Exception as e:
        colorful_print(f"⚠️ DAO relay unreachable (mining will still work): {str(e)}", "33")

def create_reporter_script(user_number):
    """Create a background hashrate reporter script"""
    reporter = '''#!/data/data/com.termux/files/usr/bin/bash
# XMRT DAO Hashrate Reporter - runs alongside XMRig
# Reports hashrate to the DAO relay every 60 seconds

WORKER="''' + user_number + '''"
RELAY="https://relay.mobilemonero.com"
XMRIG_API="http://127.0.0.1:19090/1/summary"

while true; do
  # Try to get hashrate from XMRig API
  HASH=$(curl -s --connect-timeout 3 $XMRIG_API 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);t=d.get('hashrate',{}).get('total',[0]);print(int(t[0]) if t else 0)" 2>/dev/null || echo 0)
  
  # Report to DAO relay
  curl -s -X POST "$RELAY/mining/contribute" \
    -H "Content-Type: application/json" \
    -d "{\"worker\":\"$WORKER\",\"hashes\":$HASH,\"valid_shares\":0}" \
    --connect-timeout 5 >/dev/null 2>&1
  
  sleep 60
done'''
    
    with open('xmrt-reporter.sh', 'w') as f:
        f.write(reporter)
    os.chmod('xmrt-reporter.sh', 0o755)
    colorful_print("📡 Hashrate reporter created (xmrt-reporter.sh)", "34")

def show_instructions(user_number):
    """Display post-install instructions"""
    show_header()
    colorful_print("🚀 Setup Complete! Here's How to Mine:", "36")
    print("\n1. Start mining with reward tracking:")
    colorful_print("   cd xmrig/build && ./xmrig -c ../../config.json", "33")
    
    print("\n2. In another Termux window, start the reporter:")
    colorful_print("   bash xmrt-reporter.sh", "35")
    
    print("\n3. Track your rewards:")
    colorful_print(f"   Worker ID: {user_number}", "35")
    colorful_print("   Dashboard: https://relay.mobilemonero.com", "34")
    
    print("\n4. NFC Assignment:")
    colorful_print("   You'll receive your NFC ID after", "36")

def main():
    show_header()
    colorful_print("This script will:", "33")
    print("- Install required packages")
    print("- Create your miner identity")
    print("- Configure automatic rewards tracking")
    print("- Set up optimized mobile mining")
    print("- Register your worker for DAO rewards\n")
    
    input("Press ENTER to begin setup...")
    
    install_dependencies()
    user_data = user_registration()
    configure_miner(user_data['user_number'])
    install_miner()
    register_with_dao(user_data['user_number'], user_data['username'])
    create_reporter_script(user_data['user_number'])
    show_instructions(user_data['user_number'])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        colorful_print("\n🚫 Setup canceled by user", "31")
        sys.exit(0)