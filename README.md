# PiStorm - Distributed WiFi Security Testing Platform

A coordinated multi-device system for professional WiFi security assessment, combining the portability of Raspberry Pi with the power of GPU acceleration.

## 🏗️ Architecture

**Three-Device Ecosystem:**
- **🔧 Raspberry Pi 3B+**: Network scanning, handshake capture, deauth attacks
- **💻 Main PC (RTX 4070 Super)**: GPU-accelerated password cracking with hashcat
- **📱 Wio Terminal**: Real-time control interface and status display

## ⚡ Key Features

- **Distributed Processing**: Offload intensive cracking to dedicated GPU hardware
- **Real-Time Monitoring**: Live attack progress via Wio Terminal interface
- **Smart Channel Detection**: Automatic target channel identification and focusing
- **Multi-Round Deauth**: Enhanced handshake capture with multiple attack rounds
- **GPU Acceleration**: 800x faster cracking vs Pi-only processing
- **Professional Logging**: Comprehensive packet analysis and encryption detection
- **API-Driven**: RESTful interface for all device coordination
- **Monitor Mode Testing**: Automatic validation of capture capabilities
- **Advanced Analysis**: tshark integration for packet inspection
- **Security Controls**: API key authentication and rate limiting

## 🚀 Performance

- **Pi-only**: ~1,000 passwords/second
- **With RTX 4070 Super**: ~800,000 passwords/second
- **Speed improvement**: 800x faster processing

## Quick Start

### 1. Setup
```bash
# Run the setup script
./setup.sh

# Or manual setup:
sudo apt update && sudo apt install -y aircrack-ng wireless-tools python3-pip
pip install flask flask-cors
```

### 2. Configuration
```bash
# Copy and edit configuration
cp config.env.example config.env
nano config.env

# Set your API key and other settings
API_KEY=your-secure-api-key-here
WORDLIST_DIR=/usr/share/wordlists
```

### 3. Run
```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
source config.env

# Start the API
python3 wifi_api.py
```

## API Endpoints

All endpoints require `X-API-Key` header with your configured API key.

### Network Scanning
```bash
# Scan for networks
curl -H "X-API-Key: your-api-key" http://localhost:5000/scan
```

### Attack Management
```bash
# Start attack
curl -X POST -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"ssid": "target-network"}' \
     http://localhost:5000/start

# Check status
curl -H "X-API-Key: your-api-key" http://localhost:5000/status

# Get results
curl -H "X-API-Key: your-api-key" http://localhost:5000/results

# Cancel attack
curl -X POST -H "X-API-Key: your-api-key" http://localhost:5000/cancel
```

### System Information
```bash
# Health check (no auth required)
curl http://localhost:5000/health

# Configuration info
curl -H "X-API-Key: your-api-key" http://localhost:5000/config

# Available wordlists
curl -H "X-API-Key: your-api-key" http://localhost:5000/wordlists

# List capture files
curl -H "X-API-Key: your-api-key" http://localhost:5000/files
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `your-secret-api-key` | API authentication key |
| `RATE_LIMIT` | `10` | Requests per minute per IP |
| `SCAN_IFACE` | `wlan0` | Interface for scanning (auto-detected) |
| `MON_IFACE` | `wlan1` | Interface for monitor mode (auto-detected) |
| `CAP_DIR` | `/home/jhye/captures` | Directory for capture files |
| `ATTACK_TIMEOUT` | `900` | Attack timeout in seconds |
| `WORDLIST_DIR` | `/usr/share/wordlists` | Directory containing wordlists |

## Security Features

- **API Key Authentication**: All sensitive endpoints require valid API key
- **Rate Limiting**: Prevents abuse with configurable rate limits
- **Input Validation**: SSID validation prevents injection attacks
- **Process Cleanup**: Automatic cleanup of spawned processes
- **Logging**: Comprehensive audit trail of all operations

## Attack Process

1. **Network Scanning**: Uses `iw scan` to discover available networks
2. **Target Selection**: Identifies target network BSSID and channel
3. **Monitor Mode**: Switches interface to monitor mode for packet capture
4. **Handshake Capture**: Uses `airodump-ng` to capture WPA handshakes
5. **Deauthentication**: Uses `aireplay-ng` to force client reconnections
6. **Handshake Validation**: Verifies captured handshake is valid
7. **Dictionary Attack**: Uses `aircrack-ng` with multiple wordlists
8. **Result Reporting**: Returns cracked password or failure status

## Hardware Requirements

- Raspberry Pi with 2+ wireless interfaces OR single interface for fake mode
- USB WiFi adapters that support monitor mode
- aircrack-ng suite installed

## Compatible with Wio Terminal

This API is designed to work with the Wio Terminal WiFi interface. The Wio Terminal can:
- Display discovered networks from `/scan` endpoint
- Initiate attacks via `/start` endpoint
- Monitor progress through `/status` endpoint
- Retrieve results from `/results` endpoint

## Troubleshooting

### Check Interface Status
```bash
# List wireless interfaces
ip link show | grep wlan

# Check interface modes
iw dev
```

### Verify Tools
```bash
# Check required tools
which aircrack-ng airodump-ng aireplay-ng
```

### Monitor Logs
```bash
# View real-time logs
tail -f wifi_api.log
```

## Wordlist Management

The API automatically detects wordlists in standard locations:
- `/usr/share/wordlists/rockyou.txt`
- `/usr/share/wordlists/rockyou.txt.gz`
- `/usr/share/wordlists/fasttrack.txt`
- Custom directory via `WORDLIST_DIR`

Setup script automatically downloads rockyou.txt if not present.

## Legal Notice

⚠️ **IMPORTANT**: This is a real penetration testing tool that performs actual wireless attacks.

- Only use on networks you own or have explicit written permission to test
- Unauthorized access to wireless networks is illegal in most jurisdictions
- This tool is for security professionals and authorized penetration testing only
- Users are responsible for compliance with local laws and regulations