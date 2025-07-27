# PiStorm Setup Guide

Complete installation and configuration guide for the PiStorm distributed WiFi security testing platform.

## 📋 Prerequisites

### Hardware Requirements
- **Raspberry Pi 3B+ or newer** with Raspberry Pi OS
- **Windows PC** with NVIDIA GPU (RTX series recommended)
- **Wio Terminal** for control interface
- **Two USB WiFi adapters** (or Pi with built-in WiFi + USB adapter)
- **MicroSD card** (32GB+ recommended)

### Network Requirements
- All devices on same subnet
- Internet access for package downloads
- Static IP addresses recommended

## 🔧 Raspberry Pi Setup

### 1. System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y aircrack-ng wireless-tools python3-pip tshark tcpdump wireshark-common git

# Install Python packages
pip3 install flask flask-cors requests pathlib python-dateutil
```

### 2. WiFi Interface Setup
```bash
# Check available interfaces
ip link show | grep wlan
iw dev

# Identify monitor-capable interfaces
sudo iw list | grep "monitor"
```

### 3. Clone and Configure PiStorm
```bash
# Clone repository
git clone https://github.com/TheJhyeFactor/PiStorm.git
cd PiStorm

# Copy configuration
cp config.env.example config.env

# Edit configuration
nano config.env
```

### 4. Configuration Settings
Edit `config.env`:
```bash
# Generate secure API key
API_KEY=$(openssl rand -hex 32)

# Set interfaces (auto-detected if available)
SCAN_IFACE=wlan0
MON_IFACE=wlan1

# Set directories
CAP_DIR=/home/pi/captures
WORDLIST_DIR=/usr/share/wordlists

# GPU PC settings
GPU_PC_IP=192.168.0.102
GPU_PC_USER=YourUsername
ENABLE_GPU_OFFLOAD=true
```

### 5. Test Installation
```bash
# Test monitor mode
python3 test_monitor.py

# Start API
python3 wifi_api.py
```

## 💻 Windows GPU Station Setup

### 1. Install Prerequisites
```powershell
# Install Python 3.8+
# Download from python.org

# Install NVIDIA drivers and CUDA
# Download from nvidia.com

# Install hashcat
# Download from hashcat.net
```

### 2. Install hashcat
```powershell
# Download hashcat binary
# Extract to C:\hashcat\

# Add to PATH
$env:PATH += ";C:\hashcat"

# Test installation
hashcat --version
```

### 3. Install hcxtools (WSL method)
```powershell
# Install WSL
wsl --install Ubuntu-22.04

# In WSL:
sudo apt update
sudo apt install hcxtools aircrack-ng

# Test conversion tools
wsl hcxpcapngtool --version
```

### 4. Setup PiStorm GPU Station
```powershell
# Create directories
mkdir C:\PiStorm-GPU
cd C:\PiStorm-GPU
mkdir incoming, wordlists, results, logs

# Download wordlists
# Place rockyou.txt in wordlists folder

# Copy crack_listener.py from repository
# Configure API key to match Pi
```

### 5. Test GPU Setup
```powershell
# Test hashcat with GPU
hashcat -I

# Test with sample file
hashcat -b -m 22000
```

## 📱 Wio Terminal Setup

### 1. Hardware Preparation
- Flash Arduino ESP32 bootloader
- Install required libraries
- Configure WiFi credentials

### 2. Software Configuration
```cpp
// Configure in your Wio Terminal code
const char* ssid = "YourWiFiNetwork";
const char* password = "YourPassword";
const char* pi_ip = "192.168.0.218";
const char* api_key = "your-api-key-from-pi";
```

### 3. Upload Firmware
- Compile and upload to Wio Terminal
- Test connectivity to Pi API
- Verify display functionality

## 🔗 Network Configuration

### 1. Static IP Setup (Recommended)

**Raspberry Pi:**
```bash
# Edit dhcpcd.conf
sudo nano /etc/dhcpcd.conf

# Add:
interface wlan0
static ip_address=192.168.0.218/24
static routers=192.168.0.1
static domain_name_servers=8.8.8.8
```

**Windows PC:**
- Set static IP: 192.168.0.102
- Gateway: 192.168.0.1
- DNS: 8.8.8.8

### 2. Firewall Configuration

**Windows:**
```powershell
# Allow Python through firewall
netsh advfirewall firewall add rule name="PiStorm" dir=in action=allow protocol=TCP localport=5000
```

**Pi (if ufw enabled):**
```bash
sudo ufw allow 5000
sudo ufw allow from 192.168.0.0/24
```

## 🧪 Testing Complete Setup

### 1. Test Pi API
```bash
# On Pi
python3 wifi_api.py

# Check health endpoint
curl http://localhost:5000/health
```

### 2. Test PC Connection
```bash
# From Pi, test PC connection
ping 192.168.0.102

# Test manual file transfer
scp test.cap user@192.168.0.102:/path/to/incoming/
```

### 3. Test Wio Terminal
- Power on Wio Terminal
- Connect to WiFi
- Test API connection
- Verify display updates

### 4. End-to-End Test
1. Start Pi API
2. Start Windows GPU listener
3. Use Wio Terminal to scan networks
4. Initiate test attack
5. Monitor file transfer
6. Verify GPU processing
7. Check result display

## 🔧 Troubleshooting

### Common Issues

**Pi Interface Problems:**
```bash
# Reset interfaces
sudo systemctl restart networking
sudo ifconfig wlan1 down
sudo ifconfig wlan1 up
```

**Monitor Mode Issues:**
```bash
# Kill interfering processes
sudo airmon-ng check kill
sudo systemctl stop NetworkManager

# Manual monitor mode setup
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up
```

**GPU Issues:**
```powershell
# Check GPU detection
nvidia-smi
hashcat -I

# Update drivers if needed
```

### Log Files
- **Pi**: `wifi_api.log`
- **Windows**: `crack_listener.log` 
- **System**: `/var/log/syslog` (Pi)

## 📚 Additional Resources

- [API Documentation](API.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## ⚠️ Security Notes

- Change default API keys
- Use strong passwords
- Keep software updated
- Monitor access logs
- Use only on authorized networks