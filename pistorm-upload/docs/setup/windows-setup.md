# Windows GPU Setup Guide

## 🎯 Overview
This guide sets up the Windows PC component for distributed GPU WiFi cracking.

## 📋 Prerequisites
- Windows 10/11
- NVIDIA GPU (RTX series recommended)
- 16GB+ RAM
- Python 3.9+

## 🚀 Installation

### 1. Install Base Requirements
```powershell
# Install Python (if not already installed)
winget install Python.Python.3.12

# Install chocolatey (if not already installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install hashcat
choco install hashcat
```

### 2. Setup WSL for hcxtools
```powershell
# Install WSL
wsl --install Ubuntu

# After restart, in WSL:
sudo apt update
sudo apt install hcxtools

# Test installation
wsl hcxpcapngtool --version
```

### 3. Clone and Setup PiStorm
```powershell
git clone https://github.com/TheJhyeFactor/PiStorm.git
cd PiStorm\windows-gpu

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Download Wordlists
```powershell
# Create wordlists directory
mkdir wordlists
cd wordlists

# Download rockyou.txt
curl -L -o rockyou.txt https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt

# Download WiFi-specific wordlists
curl -L -o wifi-wpa-top4800.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/WiFi-WPA/probable-v2-wpa-top4800.txt
```

## ⚙️ Configuration

### 1. Update API Configuration
Edit `scripts/crack_listener.py`:
```python
PI_IP = "192.168.0.218"  # Your Pi's IP
PI_API_KEY = "your-api-key-here"
```

### 2. Test Installation
```powershell
python scripts\test_setup.py
```

Expected output:
```
[OK] Hashcat found
[OK] hcxtools found: wsl hcxpcapngtool
[OK] Network: Pi reachable
[OK] Wordlists: 3 available
```

## 🎮 Usage

### Manual Start
```powershell
python scripts\crack_listener.py
```

### Windows Service (Recommended)
```powershell
# Run as Administrator
python scripts\install_windows_service.py install
```

## 🔧 Troubleshooting

### hashcat Not Found
- Restart PowerShell after chocolatey install
- Verify: `hashcat --version`

### WSL Issues
- Enable WSL: `dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart`
- Install distribution: `wsl --install Ubuntu`

### Network Issues
- Check Pi IP: `ping 192.168.0.218`
- Verify API key matches Pi configuration

### GPU Not Detected
- Update NVIDIA drivers
- Check CUDA support: `nvidia-smi`

## 📊 Performance Tuning

### GPU Optimization
- Set power limit to 100%
- Enable performance mode in NVIDIA Control Panel
- Monitor with MSI Afterburner

### Memory Management
- Ensure adequate system RAM (16GB+)
- Monitor GPU memory usage during processing

## 🔒 Security Notes
- API communication is local network only
- SSH keys are automatically generated
- No external internet dependencies required