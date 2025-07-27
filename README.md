# WiFi Crack PC - Distributed GPU Processing Station

> **⚠️ EDUCATIONAL USE ONLY**: This toolkit is designed for legitimate security research, penetration testing of networks you own, and educational purposes only. Unauthorized access to networks is illegal.

A Windows GPU-accelerated processing station for WiFi security testing, designed to work with the [PiStorm Network Security System](https://github.com/TheJhyeFactor/PiStorm).

## 🚀 Recent Updates

**Major enhancements have been deployed!** See the [main PiStorm repository](https://github.com/TheJhyeFactor/PiStorm) for complete integration details.

### ✨ New Features
- **Enhanced crack_listener.py** with improved conversion tool support
- **Better RTX 4070 Super optimization** for maximum hashcat performance
- **Real-time status updates** back to Pi controller
- **Improved error handling** and comprehensive logging
- **WSL integration** for better tool compatibility

## 🛠 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **GPU**: NVIDIA RTX 4070 Super (12GB GDDR6X, 7168 CUDA cores)
- **Python**: 3.x (✅ Installed: 3.13.1)
- **Network**: Connectivity to Pi at 192.168.0.218
- **Storage**: 50GB+ free space for wordlists and captures

## 📦 Quick Setup

> **🚀 NEW! Complete Step-by-Step Setup Guide Available**  
> **For detailed installation instructions, see: [WINDOWS_GPU_SETUP.md](WINDOWS_GPU_SETUP.md)**

### 1. Install Critical Tools via WSL
```bash
# Install WSL with Ubuntu (CRITICAL for .cap conversion)
wsl --install Ubuntu-22.04

# Install required tools in WSL
wsl sudo apt update
wsl sudo apt install hcxtools aircrack-ng hashcat

# Verify installation
wsl hcxpcapngtool --version
wsl aircrack-ng --help
```

### 2. Install Windows GPU Tools
```powershell
# Install Hashcat for Windows
choco install hashcat

# Or download manually from: https://hashcat.net/hashcat/
# Add to PATH environment variable
```

### 3. Run Enhanced Setup
```bash
# Download and run the automated setup script
python scripts/test_setup.py

# Install as Windows service
python scripts/install_windows_service.py install
```

## 🏗 Architecture Overview

```
PiStorm Network ←→ WiFi Crack PC (This System)
     │                      │
  📡 WiFi Scanner      🖥️ GPU Processing
  📱 Wio Terminal      💾 Wordlist Management
  🔄 File Transfer     📊 Real-time Status
```

## 📁 Directory Structure

```
wifi-crack-pc/
├── 📂 incoming/           # .cap files from Pi (auto-monitored)
├── 📂 wordlists/          # WiFi password dictionaries
│   ├── rockyou.txt       # 133MB general passwords
│   ├── wifi-wpa-*.txt    # WiFi-specific wordlists
│   └── darkweb2017-*.txt # Leaked password lists
├── 📂 results/           # Hashcat output and .pot files
├── 📂 logs/              # Detailed error and performance logs
├── 📂 scripts/           # Core processing scripts
├── 📂 hcxtools-master/   # Conversion utilities
└── 📂 SecLists/          # Comprehensive security wordlists
```

## ⚡ GPU Performance Specs

**RTX 4070 Super Hashcat Performance:**
- **WPA/WPA2 (22000)**: ~500-800 kH/s
- **WPA3 (22001)**: ~200-400 kH/s
- **VRAM**: 12GB GDDR6X
- **Power**: 220W TGP

Test your performance:
```bash
hashcat -b -m 22000  # WPA/WPA2 benchmark
hashcat -b -m 22001  # WPA3 benchmark
```

## 🔄 Processing Workflow

1. **📡 Capture Reception**: Pi transfers .cap files via SSH
2. **🔧 Format Conversion**: hcxtools converts to hashcat format
3. **🎯 Smart Wordlist Selection**: WiFi-specific lists prioritized
4. **🚀 GPU Acceleration**: Hashcat utilizes full RTX 4070 Super
5. **📊 Real-time Updates**: Status sent back to Pi every 30 seconds
6. **✅ Result Delivery**: Cracked passwords returned via API

## 🌐 Network Integration

### Pi Communication
- **Target Pi**: 192.168.0.218:5000
- **Protocol**: SSH (file transfer) + HTTP API (results)
- **Authentication**: SSH ed25519 key pair
- **API Endpoint**: `POST /api/crack_result`

### SSH Key Setup
```bash
# Your public key (add to Pi's authorized_keys):
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOE5MQ7edWA7D5Ai2L9EfngN/7dR2P2rLzDzEm0XAage Jhye@DESKTOP-P2GHC2L

# On the Pi:
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOE5MQ7edWA7D5Ai2L9EfngN/7dR2P2rLzDzEm0XAage Jhye@DESKTOP-P2GHC2L" >> ~/.ssh/authorized_keys
```

## 🚀 Usage

### Automatic Service (Recommended)
```bash
# Start the Windows service
net start WiFiCrackService

# Check service status
sc query WiFiCrackService
```

### Manual Operation
```bash
# Start the listener manually
cd C:\Users\Jhye\wifi-crack-pc
python scripts/crack_listener.py

# Test conversion capabilities
python scripts/test_conversion.py
```

## 📊 Monitoring & Performance

### GPU Monitoring Tools
- **nvidia-smi**: Real-time GPU usage
- **MSI Afterburner**: Advanced monitoring and overclocking
- **Task Manager**: Basic GPU utilization

### Optimal GPU Settings
```bash
# Memory overclock: +800-1000 MHz
# Core overclock: +150-200 MHz
# Power limit: 100%
# Fan curve: Aggressive (85-100%)
```

### Log Analysis
```bash
# Real-time log monitoring
Get-Content logs/crack_errors_*.log -Wait

# Performance metrics
Get-Content logs/gpu_performance.log -Tail 50
```

## 🔒 Security Features

- **🔐 SSH Key Authentication**: No password exposure
- **📁 Isolated Processing**: Sandboxed execution environment
- **🌐 Local Network Only**: API restricted to LAN
- **🗑️ Automatic Cleanup**: Temporary files removed
- **📝 Audit Logging**: Complete activity tracking

## 🛠 Troubleshooting

### Common Issues

**GPU Not Detected**
```bash
# Check NVIDIA drivers
nvidia-smi
# Update drivers from NVIDIA website
```

**Conversion Failures**
```bash
# Verify WSL tools
wsl hcxpcapngtool --version
wsl which aircrack-ng
```

**Network Connectivity**
```bash
# Test Pi connection
ping 192.168.0.218
curl -X POST http://192.168.0.218:5000/api/test
```

**Service Issues**
```bash
# Restart service as Administrator
net stop WiFiCrackService
net start WiFiCrackService
```

## 📈 Performance Optimization

### Wordlist Prioritization
1. **wifi-wpa-top306.txt** (High-probability WiFi passwords)
2. **probable-v2-wpa-top4800.txt** (Statistical analysis)
3. **darkweb2017-top10000.txt** (Breach compilation)
4. **rockyou.txt** (General password database)

### Hashcat Optimization
```bash
# Maximum performance flags
hashcat -m 22000 -w 4 -O --force
# -w 4: Nightmare workload (maximum GPU usage)
# -O: Optimized kernel (reduced VRAM usage)
# --force: Ignore driver warnings
```

## 🔗 Integration with PiStorm

This PC station is designed to work seamlessly with the [PiStorm WiFi Security System](https://github.com/TheJhyeFactor/PiStorm):

- **📡 Raspberry Pi**: Network discovery and capture
- **📱 Wio Terminal**: Real-time status display
- **💻 Windows PC**: GPU-accelerated password cracking
- **☁️ Remote API**: Distributed processing coordination

## 📄 License & Legal

This software is provided for **educational and authorized testing purposes only**. Users are responsible for compliance with all applicable laws and regulations. The authors assume no liability for misuse.

**Authorized Use Cases:**
- ✅ Personal network security testing
- ✅ Penetration testing with proper authorization
- ✅ Educational cybersecurity research
- ✅ Corporate security assessments

**Prohibited Uses:**
- ❌ Unauthorized network access
- ❌ Malicious attacks
- ❌ Commercial exploitation without permission

---

## 🤝 Contributing

This project is part of the larger PiStorm ecosystem. For contributions, please see the [main repository](https://github.com/TheJhyeFactor/PiStorm).

**Built with:** Python, Hashcat, HCXtools, WSL, NVIDIA CUDA
**Optimized for:** RTX 4070 Super, Windows 11, WiFi Security Research