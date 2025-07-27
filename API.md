# PiStorm API Documentation

Complete API reference for the PiStorm distributed WiFi security testing platform.

## 🔐 Authentication

All API endpoints (except `/health` and `/ping`) require authentication via API key.

**Header Required:**
```
X-API-Key: your-secret-api-key
```

**Rate Limiting:** 200 requests per minute per IP (configurable)

## 📡 Core Endpoints

### Network Scanning

#### `GET /scan`
Scan for available WiFi networks.

**Response:**
```json
{
  "networks": [
    {
      "ssid": "NetworkName",
      "bssid": "aa:bb:cc:dd:ee:ff",
      "signal": -45,
      "encryption": "WPA/WPA2"
    }
  ],
  "count": 12
}
```

#### `GET /networks/count`
Get total number of cached networks.

**Response:**
```json
{
  "count": 15
}
```

#### `GET /networks/page/<int:page>`
Get paginated network list (3 per page).

**Response (Text):**
```
1|NetworkName|-45|WPA
2|OtherNetwork|-67|WPA2
3|ThirdNetwork|-52|Open
```

### Attack Management

#### `POST /start`
Start WiFi attack on specified network.

**Request:**
```json
{
  "ssid": "TargetNetwork"
}
```

**Response:**
```json
{
  "message": "attack started",
  "target": "TargetNetwork"
}
```

#### `POST /attack_target/<int:network_number>`
Start attack on network by cached list number.

**Response (Text):**
```
STARTED|NetworkName
```

#### `GET /status`
Get detailed attack status.

**Response:**
```json
{
  "running": true,
  "step": "Forcing handshake capture",
  "progress": 75,
  "sub_progress": 50,
  "phase": "capture",
  "target": "TargetNetwork",
  "target_bssid": "aa:bb:cc:dd:ee:ff",
  "runtime": 145,
  "handshake_captured": false,
  "gpu_processing": true,
  "gpu_enabled": true,
  "current_wordlist": "rockyou.txt",
  "completed": false,
  "failed": false
}
```

#### `GET /status_simple`
Simplified status for embedded devices.

**Response (Text):**
```
1|75|gpu_cracking|TargetNetwork|1|1
```
Format: `running|progress|phase|target|gpu_processing|gpu_enabled`

#### `GET /text`
Ultra-simple text status (no rate limiting).

**Response (Text):**
```
1|75|gpu_cracking|TargetNetwork|password123
```

#### `POST /cancel`
Cancel running attack.

**Response:**
```json
{
  "message": "Attack cancelled"
}
```

### Results and Analysis

#### `GET /results`
Get final attack results.

**Response:**
```json
{
  "result": "password123",
  "target": "TargetNetwork",
  "final_step": "Attack completed",
  "total_runtime": 287
}
```

#### `GET /results_simple`
Simple result format.

**Response (Text):**
```
SUCCESS|password123
```
or
```
FAILED|NOT FOUND
```

#### `GET /analyze_latest`
Analyze most recent capture file.

**Response:**
```json
{
  "filename": "target-12345.cap",
  "size_bytes": 15420,
  "timestamp": 1640995200,
  "analysis": "File size: 15420 bytes",
  "encryption": "WPA2 detected",
  "packets": "Total packets: 142",
  "handshake": "Found"
}
```

### GPU Integration

#### `POST /transfer_to_gpu`
Prepare latest capture for GPU processing.

**Request:**
```json
{
  "filename": "optional-specific-file.cap"
}
```

**Response:**
```json
{
  "status": "ready_for_transfer",
  "filename": "target-12345.cap",
  "source_path": "/home/pi/captures/target-12345.cap",
  "target_path": "192.168.0.102:C:/incoming",
  "message": "File ready for manual copy to GPU PC"
}
```

#### `POST /crack_result`
Receive result from GPU PC (used by GPU station).

**Request:**
```json
{
  "target": "TargetNetwork",
  "password": "cracked_password",
  "cracked_by": "main-pc-gpu",
  "timestamp": "2024-01-01T12:00:00"
}
```

### File Management

#### `GET /files`
List capture files.

**Response:**
```json
{
  "files": [
    {
      "name": "target-12345.cap",
      "size": 15420,
      "mtime": 1640995200,
      "created": "2024-01-01T12:00:00"
    }
  ],
  "total": 5
}
```

#### `POST /upload_cap`
Upload capture file.

**Request:** Multipart form with file upload

**Response:**
```json
{
  "status": "uploaded",
  "filename": "uploaded.cap",
  "gpu_processing": true,
  "message": "File uploaded and sent to GPU PC"
}
```

### System Information

#### `GET /health` (No Auth Required)
System health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "interfaces": {
    "scan": "wlan0",
    "monitor": "wlan1",
    "available": ["wlan0", "wlan1"],
    "monitor_tested": true
  },
  "tools_available": true,
  "wordlists_available": 3,
  "attack_running": false,
  "gpu_offload": {
    "enabled": true,
    "pc_ip": "192.168.0.102",
    "configured": true
  }
}
```

#### `GET /config`
System configuration.

**Response:**
```json
{
  "attack_timeout": 900,
  "capture_dir": "/home/pi/captures",
  "rate_limit": 200,
  "wordlist_dir": "/usr/share/wordlists",
  "gpu_offload_enabled": true,
  "gpu_pc_ip": "192.168.0.102",
  "interfaces": {
    "scan": "wlan0",
    "monitor": "wlan1",
    "available": ["wlan0", "wlan1"]
  },
  "wordlists": [
    {
      "path": "/usr/share/wordlists/rockyou.txt",
      "name": "rockyou.txt",
      "size_bytes": 139921507,
      "size_mb": 133.4
    }
  ]
}
```

#### `GET /wordlists`
Available wordlists.

**Response:**
```json
{
  "wordlists": [
    {
      "path": "/usr/share/wordlists/rockyou.txt",
      "name": "rockyou.txt", 
      "size_bytes": 139921507,
      "size_mb": 133.4
    }
  ],
  "count": 1
}
```

### Testing and Diagnostics

#### `POST /test_monitor`
Test monitor mode capability.

**Response:**
```json
{
  "status": "completed",
  "monitor_working": true,
  "interface": "wlan1",
  "message": "Monitor mode working",
  "timestamp": 1640995200
}
```

#### `GET /ping` (No Auth Required)
Simple connectivity test.

**Response (Text):**
```
pong
```

## 🎛️ Command Interface

Special endpoints for simplified device control.

#### `GET /cmd/<command>`
Execute predefined commands.

**Available Commands:**
- `menu` - Get main menu display
- `networks` - Get formatted network list
- `status` - Get formatted attack status
- `cancel` - Cancel current attack

#### `POST /cmd/attack`
Start attack via command interface.

**Request:**
```json
{
  "target": "NetworkName"
}
```

## 📊 Status Phases

### Attack Phases
- `idle` - No attack running
- `scanning` - Finding target network
- `capture` - Capturing handshake
- `gpu_ready` - Ready for GPU processing
- `gpu_cracking` - GPU processing active
- `cracking` - Pi-based cracking
- `complete` - Attack finished
- `error` - Error occurred

### Progress Ranges
- **0-20%**: Network scanning and setup
- **20-40%**: Handshake capture
- **40-60%**: Transfer preparation
- **60-95%**: Password cracking
- **95-100%**: Finalization

## 🔧 Error Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid parameters or data |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Endpoint or resource not found |
| 409 | Conflict | Attack already running |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal processing error |

## 📝 Usage Examples

### Python Client
```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://192.168.0.218:5000"
headers = {"X-API-Key": API_KEY}

# Scan networks
response = requests.get(f"{BASE_URL}/scan", headers=headers)
networks = response.json()["networks"]

# Start attack
attack_data = {"ssid": "TargetNetwork"}
response = requests.post(f"{BASE_URL}/start", json=attack_data, headers=headers)

# Monitor progress
while True:
    status = requests.get(f"{BASE_URL}/status", headers=headers).json()
    print(f"Progress: {status['progress']}% - {status['step']}")
    if not status["running"]:
        break
    time.sleep(2)
```

### Curl Examples
```bash
# Health check
curl http://192.168.0.218:5000/health

# Scan networks
curl -H "X-API-Key: your-key" http://192.168.0.218:5000/scan

# Start attack
curl -X POST -H "X-API-Key: your-key" \
     -H "Content-Type: application/json" \
     -d '{"ssid":"TargetNetwork"}' \
     http://192.168.0.218:5000/start

# Check status
curl -H "X-API-Key: your-key" http://192.168.0.218:5000/status
```

## 🛡️ Security Considerations

- Always use HTTPS in production
- Rotate API keys regularly
- Monitor access logs
- Implement IP whitelisting if needed
- Use strong, unique API keys
- Enable rate limiting appropriately