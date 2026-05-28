<#
.SYNOPSIS
    XMRT-DAO Windows Mining Setup - Download, verify, and configure XMRig for the XMRT-DAO pool.
.DESCRIPTION
    Downloads the latest XMRig Windows release, verifies SHA256 checksums,
    generates config.json pointed at pool.mobilemonero.com:3333, and creates
    a start-mining.ps1 launcher. Designed for the XMRT-DAO Privateer Fleet.
.PARAMETER WalletAddress
    Your Monero wallet address. If omitted, the script prompts for one.
.PARAMETER WorkerName
    Worker name shown in the pool dashboard (default: windows-rig).
.PARAMETER PoolURL
    Mining pool URL (default: pool.mobilemonero.com:3333).
.PARAMETER SkipHashVerify
    Skip SHA256 hash verification (not recommended).
.EXAMPLE
    .\setup-xmrt-windows.ps1 -WalletAddress "42uyNpCQbD1W1mBscqS3S4YNR1o..."
#>
param([string]$WalletAddress="",[string]$WorkerName="windows-rig",[string]$PoolURL="pool.supportxmr.com:3333",[switch]$SkipHashVerify=$false)

$XMRIG_API="https://xmrig.com/miner"
$XMRIG_GH="https://github.com/xmrig/xmrig/releases"
$INSTALL_DIR="$env:USERPROFILE\xmrt-miner"
$CONFIG_FILE="$INSTALL_DIR\config.json"
$LAUNCH_SCRIPT="$INSTALL_DIR\start-mining.ps1"

function Write-Info{Write-Host "[*] $args" -ForegroundColor Cyan}
function Write-Success{Write-Host "[+] $args" -ForegroundColor Green}
function Write-Warn{Write-Host "[!] $args" -ForegroundColor Yellow}
function Write-Err{Write-Host "[x] $args" -ForegroundColor Red}

Write-Info "Fetching latest XMRig version from xmrig.com/miner..."
try{$p=Invoke-WebRequest -Uri $XMRIG_API -UseBasicParsing -TimeoutSec 15;$m=[regex]::Match($p.Content,'version is ([\d\.]+)');if($m.Success){$VER=$m.Groups[1].Value}else{throw"no match"};Write-Success "Latest: v$VER"}catch{Write-Warn "Fallback to 6.26.0";$VER="6.26.0"}

$ZIP="xmrig-$VER-windows-x64.zip"
$XMRIG_ZIP="$INSTALL_DIR\$ZIP"

Write-Host "`n  === XMRT-DAO Windows Miner Setup v$VER ===`n" -ForegroundColor Green

if(-not(Test-Path $INSTALL_DIR)){New-Item -ItemType Directory -Path $INSTALL_DIR -Force|Out-Null;Write-Success "Dir created"}

Write-Info "Downloading XMRig v$VER ..."
try{Invoke-WebRequest -Uri "$XMRIG_GH/download/v$VER/$ZIP" -OutFile $XMRIG_ZIP -UseBasicParsing -TimeoutSec 60;Write-Success "Downloaded"}catch{Write-Err "Download failed: $_";exit 1}

if(-not $SkipHashVerify){
    Write-Info "Verifying SHA256..."
    try{$hc=Invoke-WebRequest -Uri "$XMRIG_GH/download/v$VER/SHA256SUMS" -UseBasicParsing -TimeoutSec 15;$line=($hc.Content -split "`n")|Where-Object{$_ -match [regex]::Escape($ZIP)};if($line){$exp=($line -split '\s+')[0].Trim().ToLower();$act=(Get-FileHash -Path $XMRIG_ZIP -Algorithm SHA256).Hash.ToLower();if($act-eq$exp){Write-Success "Hash verified"}else{Write-Err "HASH MISMATCH!";Remove-Item $XMRIG_ZIP -Force;exit 1}}else{Write-Warn "Hash not found in checksums"}}catch{Write-Warn "Verify skipped: $_"}
}

Write-Info "Extracting..."
try{Add-Type -AssemblyName System.IO.Compression.FileSystem;[System.IO.Compression.ZipFile]::ExtractToDirectory($XMRIG_ZIP,$INSTALL_DIR);Remove-Item $XMRIG_ZIP -Force;Write-Success "Extracted"}catch{Write-Err "Extract failed: $_";exit 1}

if([string]::IsNullOrEmpty($WalletAddress)){$WalletAddress=Read-Host "Enter your Monero wallet address"}

Write-Info "Generating config.json..."
$cfg=@{autosave=$true;cpu=@{enabled=$true;"max-threads-hint"=50};pools=@(@{url=$PoolURL;user="$WalletAddress+$WorkerName";pass="x";keepalive=$true;nicehash=$false;tls=$false});api=@{enabled=$true;host="127.0.0.1";port=19090;"access-token"=$null;restricted=$true};log_file="$INSTALL_DIR\xmrig.log"}
$cfg|ConvertTo-Json -Depth 10|Set-Content -Path $CONFIG_FILE -Encoding UTF8;Write-Success "config.json created"

$lc="@`"`n# XMRT-DAO Mining Launcher`nSet-Location `"$INSTALL_DIR`"`n.\xmrig.exe --config=config.json`n`"@"
$lc|Set-Content -Path $LAUNCH_SCRIPT -Encoding UTF8;Write-Success "Launch script created"

Get-ChildItem $INSTALL_DIR -Exclude "xmrig.exe","config.json","start-mining.ps1","xmrig.log" -Recurse|Where-Object{-not $_.PSIsContainer}|Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "`n  === Setup Complete! ===" -ForegroundColor Green
Write-Host "  Pool: $PoolURL`n  Worker: $WorkerName`n  Config: $CONFIG_FILE`n  Launcher: $LAUNCH_SCRIPT`n" -ForegroundColor White
Write-Host "  Start: cd $INSTALL_DIR && .\start-mining.ps1`n" -ForegroundColor Cyan

$sn=Read-Host "Start mining now? (Y/N)"
if($sn-eq"Y"-or$sn-eq"y"){Write-Info "Starting XMRig...";Set-Location $INSTALL_DIR;&".\xmrig.exe" --config=config.json}
