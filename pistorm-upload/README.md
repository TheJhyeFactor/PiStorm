# 🚀 PiStorm - Distributed GPU WiFi Cracking System

**High-performance distributed WiFi security testing with Pi coordination and Windows GPU acceleration**

## 🎯 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raspberry Pi  │    │   Windows PC    │    │  Wio Terminal   │
│   Coordinator   │◄──►│  GPU Processor  │    │    Display      │
│                 │    │                 │    │                 │
│ • Captures WiFi │    │ • RTX 4070 S    │    │ • Status        │
│ • API Server    │    │ • Hashcat       │    │ • Progress      │
│ • File Transfer │    │ • hcxtools      │    │ • Results       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔥 Performance Gains

| Component | Pi Only | Pi + GPU | Improvement |
|-----------|---------|----------|-------------|
| WPA Cracking | ~50 H/s | ~600 kH/s | **12,000x faster** |
| Processing Time | Hours | Minutes | **~60x faster** |
| Success Rate | Limited | High | More wordlists |

## 📁 Repository Structure

```
PiStorm/
├── pi/                          # Raspberry Pi Components
│   ├── api/                     # Flask API Server
│   │   ├── app.py              # Main API endpoints
│   │   ├── gpu_status.py       # GPU status handling
│   │   └── auth.py             # API authentication
│   ├── capture/                # WiFi capture tools
│   │   ├── monitor.py          # WiFi monitoring
│   │   └── handshake.py        # Handshake capture
│   └── display/                # Wio Terminal integration
│       └── terminal.cpp        # Display updates
├── windows-gpu/                # Windows GPU Processing
│   ├── scripts/                # Processing scripts
│   │   ├── crack_listener.py   # Main GPU listener
│   │   ├── test_setup.py       # System verification
│   │   └── install_tools.bat   # Tool installation
│   ├── wordlists/              # Password dictionaries
│   ├── incoming/               # Capture file drop zone
│   ├── results/                # Processing results
│   └── logs/                   # Error logs
├── docs/                       # Documentation
│   ├── setup/                  # Setup guides
│   │   ├── pi-setup.md        # Pi configuration
│   │   ├── windows-setup.md   # Windows setup
│   │   └── wio-setup.md       # Wio Terminal setup
│   ├── api/                   # API documentation
│   └── troubleshooting.md     # Common issues
└── tools/                     # Utilities
    ├── network-scan/          # Network discovery
    └── benchmarks/            # Performance testing
```

## 🚀 Quick Start

### 1. Pi Setup
```bash
git clone https://github.com/TheJhyeFactor/PiStorm.git
cd PiStorm/pi
pip3 install -r requirements.txt
python3 api/app.py
```

### 2. Windows GPU Setup
```powershell
cd PiStorm/windows-gpu
python scripts/install_tools.py
python scripts/crack_listener.py
```

### 3. Test the System
```bash
# On Pi - start capture
python3 capture/monitor.py --target "TestNetwork"

# Automatic GPU processing begins
# Results displayed on Wio Terminal
```

## 🛠️ System Requirements

### Raspberry Pi
- Raspberry Pi 4 (4GB+ recommended)
- WiFi adapter with monitor mode
- MicroSD card (32GB+)
- Wio Terminal (optional display)

### Windows PC
- NVIDIA GPU (RTX series recommended)
- 16GB+ RAM
- Windows 10/11
- WSL with Ubuntu/NixOS

## 🔑 Key Features

### Distributed Processing
- **Automatic load balancing** between Pi and GPU
- **Real-time status synchronization**
- **Fault-tolerant processing** with fallbacks

### Multi-Mode WiFi Support
- **WPA/WPA2** (modes 22000, 2500)
- **WPA3** (mode 22001) 
- **PMKID** (mode 16800)
- **Automatic mode detection**

### Smart Wordlist Management
- **WiFi-optimized dictionaries**
- **Priority-based processing**
- **Custom wordlist support**

### Real-Time Monitoring
- **Live progress updates**
- **Performance metrics**
- **Wio Terminal display**

## 📊 API Endpoints

### GPU Status Updates
```http
POST /api/gpu_status
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "filename": "capture.cap",
  "phase": "gpu_cracking",
  "progress": 65,
  "gpu_info": "RTX 4070 Super",
  "step": "Processing wordlist 2/3"
}
```

### Crack Results
```http
POST /api/crack_result
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "filename": "capture.cap",
  "results": {
    "status": "completed",
    "cracked_passwords": ["password123"],
    "successful_mode": "22000 (WPA-PBKDF2)",
    "total_time": 45.2
  }
}
```

## 🔒 Security Features

- **API key authentication**
- **SSH key-based file transfer**
- **Local network communication only**
- **No cloud dependencies**

## 📈 Performance Benchmarks

### RTX 4070 Super Results
- **WPA/WPA2**: ~600 kH/s
- **WPA3**: ~200 kH/s  
- **PMKID**: ~800 kH/s
- **Memory Usage**: ~2GB VRAM

### Processing Times (Average)
- **Simple passwords**: 1-5 minutes
- **Complex passwords**: 10-30 minutes
- **Enterprise passwords**: 1-3 hours

## 🛠️ Development

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

### Testing
```bash
# Run Pi tests
cd pi && python3 -m pytest tests/

# Run Windows tests  
cd windows-gpu && python scripts/test_setup.py

# Integration tests
python tools/integration_test.py
```

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **hashcat team** - GPU acceleration framework
- **hcxtools** - WiFi capture conversion
- **Raspberry Pi Foundation** - Pi platform
- **Seeed Studio** - Wio Terminal hardware

---

**⚠️ Legal Notice**: This tool is for authorized security testing only. Users are responsible for compliance with local laws and regulations.

**🔥 Ready to supercharge your WiFi security testing with distributed GPU power!**