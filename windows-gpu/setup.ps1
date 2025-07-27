# PiStorm Windows GPU Station Setup Script
# Run as Administrator in PowerShell

Write-Host "=== PiStorm Windows GPU Station Setup ===" -ForegroundColor Cyan

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires Administrator privileges. Please run as Administrator." -ForegroundColor Red
    exit 1
}

# Create directory structure
$baseDir = "$env:USERPROFILE\wifi-crack-pc"
$directories = @("incoming", "wordlists", "results", "logs", "scripts")

Write-Host "Creating directory structure..." -ForegroundColor Yellow
foreach ($dir in $directories) {
    $fullPath = Join-Path $baseDir $dir
    if (!(Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "Created: $fullPath" -ForegroundColor Green
    } else {
        Write-Host "Exists: $fullPath" -ForegroundColor Gray
    }
}

# Check Python installation
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found. Please install Python 3.8+ from python.org" -ForegroundColor Red
    exit 1
}

# Install Python requirements
Write-Host "`nInstalling Python packages..." -ForegroundColor Yellow
try {
    pip install watchdog requests psutil
    Write-Host "Python packages installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install Python packages" -ForegroundColor Red
}

# Check hashcat installation
Write-Host "`nChecking hashcat installation..." -ForegroundColor Yellow
try {
    $hashcatVersion = hashcat --version 2>&1
    Write-Host "Found: $hashcatVersion" -ForegroundColor Green
} catch {
    Write-Host "Hashcat not found. Please install from https://hashcat.net/hashcat/" -ForegroundColor Red
    Write-Host "Add hashcat to your system PATH" -ForegroundColor Yellow
}

# Check GPU
Write-Host "`nChecking NVIDIA GPU..." -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=name --format=csv,noheader 2>&1
    Write-Host "Found GPU: $gpuInfo" -ForegroundColor Green
} catch {
    Write-Host "NVIDIA GPU or drivers not detected" -ForegroundColor Red
    Write-Host "Please install NVIDIA drivers from nvidia.com" -ForegroundColor Yellow
}

# Check/Install WSL for hcxtools
Write-Host "`nChecking WSL installation..." -ForegroundColor Yellow
try {
    $wslVersion = wsl --version 2>&1
    Write-Host "WSL is available" -ForegroundColor Green
    
    # Check if Ubuntu is installed
    $distros = wsl --list --quiet
    if ($distros -contains "Ubuntu" -or $distros -contains "Ubuntu-22.04") {
        Write-Host "Ubuntu WSL distribution found" -ForegroundColor Green
        
        # Install hcxtools in WSL
        Write-Host "Installing hcxtools in WSL..." -ForegroundColor Yellow
        wsl sudo apt update
        wsl sudo apt install -y hcxtools aircrack-ng
        Write-Host "hcxtools installed in WSL" -ForegroundColor Green
    } else {
        Write-Host "Installing Ubuntu WSL distribution..." -ForegroundColor Yellow
        wsl --install Ubuntu-22.04
        Write-Host "Please restart your computer and run this script again" -ForegroundColor Yellow
    }
} catch {
    Write-Host "WSL not available. Installing..." -ForegroundColor Yellow
    try {
        wsl --install
        Write-Host "WSL installed. Please restart your computer and run this script again" -ForegroundColor Yellow
    } catch {
        Write-Host "Failed to install WSL. Please install manually" -ForegroundColor Red
    }
}

# Download wordlists
Write-Host "`nDownloading wordlists..." -ForegroundColor Yellow
$wordlistDir = Join-Path $baseDir "wordlists"

# rockyou.txt
$rockyouPath = Join-Path $wordlistDir "rockyou.txt"
if (!(Test-Path $rockyouPath)) {
    try {
        Write-Host "Downloading rockyou.txt..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt" -OutFile $rockyouPath
        Write-Host "Downloaded: rockyou.txt" -ForegroundColor Green
    } catch {
        Write-Host "Failed to download rockyou.txt. Please download manually" -ForegroundColor Red
    }
} else {
    Write-Host "rockyou.txt already exists" -ForegroundColor Gray
}

# WiFi-specific wordlist
$wifiWordlistPath = Join-Path $wordlistDir "wifi-wpa-probable.txt"
if (!(Test-Path $wifiWordlistPath)) {
    try {
        Write-Host "Downloading WiFi-specific wordlist..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/Real-Passwords/WPA-Length/Top204Thousand-probable-v2.txt" -OutFile $wifiWordlistPath
        Write-Host "Downloaded: wifi-wpa-probable.txt" -ForegroundColor Green
    } catch {
        Write-Host "Failed to download WiFi wordlist" -ForegroundColor Red
    }
} else {
    Write-Host "WiFi wordlist already exists" -ForegroundColor Gray
}

# Create firewall rule
Write-Host "`nConfiguring Windows Firewall..." -ForegroundColor Yellow
try {
    netsh advfirewall firewall add rule name="PiStorm GPU Listener" dir=in action=allow protocol=TCP localport=5000
    Write-Host "Firewall rule added for port 5000" -ForegroundColor Green
} catch {
    Write-Host "Failed to add firewall rule. Please add manually" -ForegroundColor Red
}

# Copy crack_listener.py if it exists
$listenerSource = "crack_listener.py"
$listenerDest = Join-Path $baseDir "scripts\crack_listener.py"
if (Test-Path $listenerSource) {
    Copy-Item $listenerSource $listenerDest -Force
    Write-Host "Copied crack_listener.py to scripts folder" -ForegroundColor Green
} else {
    Write-Host "crack_listener.py not found in current directory" -ForegroundColor Yellow
}

# Create test script
$testScript = @"
#!/usr/bin/env python3
# PiStorm GPU Test Script

import subprocess
import sys
from pathlib import Path

def test_hashcat():
    try:
        result = subprocess.run(['hashcat', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Hashcat: OK")
            return True
        else:
            print("❌ Hashcat: Failed")
            return False
    except FileNotFoundError:
        print("❌ Hashcat: Not found")
        return False

def test_gpu():
    try:
        result = subprocess.run(['hashcat', '-I'], capture_output=True, text=True)
        if 'CUDA' in result.stdout or 'OpenCL' in result.stdout:
            print("✅ GPU: Detected")
            return True
        else:
            print("❌ GPU: Not detected")
            return False
    except:
        print("❌ GPU: Test failed")
        return False

def test_conversion_tools():
    tools = ['wsl hcxpcapngtool --version', 'cap2hccapx', 'aircrack-ng --version']
    for tool in tools:
        try:
            result = subprocess.run(tool.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Conversion tool: {tool.split()[0]}")
                return True
        except:
            continue
    print("❌ Conversion tools: None found")
    return False

def test_wordlists():
    wordlist_dir = Path.home() / 'wifi-crack-pc' / 'wordlists'
    wordlists = list(wordlist_dir.glob('*.txt'))
    if wordlists:
        print(f"✅ Wordlists: {len(wordlists)} found")
        return True
    else:
        print("❌ Wordlists: None found")
        return False

if __name__ == "__main__":
    print("=== PiStorm GPU Station Test ===")
    tests = [test_hashcat, test_gpu, test_conversion_tools, test_wordlists]
    results = [test() for test in tests]
    
    if all(results):
        print("\n🎉 All tests passed! GPU station ready.")
        sys.exit(0)
    else:
        print(f"\n⚠️ {sum(results)}/{len(results)} tests passed. Check failed items.")
        sys.exit(1)
"@

$testScriptPath = Join-Path $baseDir "scripts\test_gpu_station.py"
$testScript | Out-File -FilePath $testScriptPath -Encoding UTF8
Write-Host "Created test script: $testScriptPath" -ForegroundColor Green

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart computer if WSL was installed" -ForegroundColor White
Write-Host "2. Run test: python $testScriptPath" -ForegroundColor White
Write-Host "3. Configure API key in crack_listener.py" -ForegroundColor White
Write-Host "4. Start listener: python $listenerDest" -ForegroundColor White

Write-Host "`nPress any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")