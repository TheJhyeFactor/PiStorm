# PiStorm Troubleshooting Guide

Common issues and solutions for the PiStorm distributed WiFi security testing platform.

## 🔧 Raspberry Pi Issues

### Monitor Mode Problems

#### Interface Not Found
```bash
# Check available interfaces
ip link show | grep wlan
iw dev

# Install missing drivers
sudo apt install firmware-realtek firmware-ralink

# For USB adapters, check with lsusb
lsusb | grep -i wireless
```

#### Monitor Mode Fails
```bash
# Kill interfering processes
sudo airmon-ng check kill
sudo systemctl stop NetworkManager
sudo systemctl stop wpa_supplicant

# Manual monitor mode setup
sudo ip link set wlan1 down
sudo iw dev wlan1 set type monitor
sudo ip link set wlan1 up

# Verify mode
iwconfig wlan1
```

#### No Packets Captured (24-byte files)
```bash
# Test monitor mode capability
python3 test_monitor.py

# Check interface status
iwconfig wlan1

# Try different channel
sudo iwconfig wlan1 channel 6

# Test with tcpdump
sudo tcpdump -i wlan1 -c 10
```

### Network Scanning Issues

#### Device Busy Error
```bash
# Wait and retry
sleep 5

# Reset interface
sudo ifconfig wlan0 down
sudo ifconfig wlan0 up

# Check for competing processes
sudo lsof | grep wlan0
ps aux | grep -E "(wpa_|Network|dhcp)"
```

#### No Networks Found
```bash
# Check interface is up
sudo ifconfig wlan0 up

# Try manual scan
sudo iw dev wlan0 scan | grep SSID

# Check antenna/power
sudo iwconfig wlan0 txpower 30
```

### Handshake Capture Issues

#### No EAPOL Frames
```bash
# Check target has active clients
sudo airodump-ng wlan1 --channel 6

# Try different channels
sudo iwconfig wlan1 channel 1
sudo iwconfig wlan1 channel 11

# Increase capture time
# Edit wifi_api.py: time.sleep(30) # Longer capture
```

#### Deauth Not Working
```bash
# Test deauth capability
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 wlan1

# Check monitor mode
iwconfig wlan1

# Try different power settings
sudo iwconfig wlan1 txpower 20
```

### API Issues

#### Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000
sudo netstat -tulpn | grep 5000

# Kill existing process
sudo pkill -f wifi_api.py

# Use different port
export PORT=5001
```

#### Permission Denied
```bash
# Add user to required groups
sudo usermod -a -G netdev pi
sudo usermod -a -G sudo pi

# Check sudo privileges
sudo -l

# Fix file permissions
chmod +x wifi_api.py
chmod 600 config.env
```

## 💻 Windows GPU Station Issues

### Hashcat Problems

#### GPU Not Detected
```powershell
# Check NVIDIA drivers
nvidia-smi

# Update drivers if needed
# Download from nvidia.com

# Test hashcat GPU detection
hashcat -I

# Check CUDA installation
nvcc --version
```

#### Conversion Tools Missing
```powershell
# Install hcxtools via WSL
wsl --install Ubuntu-22.04
wsl
sudo apt update
sudo apt install hcxtools

# Test conversion
wsl hcxpcapngtool --version

# Alternative: Install native Windows version
# Download from hashcat forum
```

#### Wordlist Issues
```powershell
# Download rockyou.txt
# From: https://github.com/brannondorsey/naive-hashcat/releases

# Extract if compressed
7z x rockyou.txt.gz

# Check file encoding
file rockyou.txt
```

### File Transfer Issues

#### SSH Connection Failed
```powershell
# Test connectivity
ping 192.168.0.218

# Check SSH service on Pi
# On Pi: sudo systemctl status ssh

# Generate new SSH key
ssh-keygen -t ed25519 -f ~/.ssh/pistorm_key

# Copy to Pi manually if needed
```

#### File Not Found
```powershell
# Check incoming directory exists
ls C:\PiStorm-GPU\incoming\

# Check file permissions
icacls C:\PiStorm-GPU\incoming\

# Monitor file system events
# Use Process Monitor from Sysinternals
```

## 📱 Wio Terminal Issues

### Connection Problems

#### WiFi Connection Failed
```cpp
// Check WiFi credentials
const char* ssid = "YourNetwork";
const char* password = "YourPassword";

// Add debug output
Serial.println(WiFi.status());

// Try different WiFi channels
// Router: change to channel 1, 6, or 11

// Reset WiFi module
WiFi.disconnect();
delay(1000);
WiFi.begin(ssid, password);
```

#### API Connection Timeout
```cpp
// Increase timeout
client.setTimeout(10000); // 10 seconds

// Check IP configuration
Serial.println(WiFi.localIP());

// Test with curl from PC
curl http://192.168.0.218:5000/ping

// Add retry logic
for(int i = 0; i < 3; i++) {
    if(client.connect(server, 5000)) break;
    delay(1000);
}
```

### Display Issues

#### Screen Freezing
```cpp
// Reduce polling frequency
delay(3000); // Poll every 3 seconds, not 100ms

// Add watchdog timer
// Reset if no response in 30 seconds

// Clear display buffer
display.fillScreen(TFT_BLACK);

// Check memory usage
Serial.print("Free heap: ");
Serial.println(ESP.getFreeHeap());
```

#### Parsing Errors
```cpp
// Debug response format
Serial.println("Response: " + response);

// Add bounds checking
if(response.length() > 0) {
    // Parse response
}

// Handle different response formats
int fieldCount = response.split('|').length;
if(fieldCount >= 4) {
    // Handle old format
} else if(fieldCount == 6) {
    // Handle new GPU format
}
```

## 🌐 Network Issues

### Connectivity Problems

#### Devices Can't Reach Each Other
```bash
# Check IP addresses
# Pi: ip addr show
# PC: ipconfig
# Wio: WiFi.localIP()

# Test connectivity
ping 192.168.0.218  # Pi
ping 192.168.0.102  # PC
ping 192.168.0.206  # Wio Terminal

# Check routing table
route -n
```

#### Firewall Blocking
```bash
# Pi: Check ufw status
sudo ufw status

# Allow specific IPs
sudo ufw allow from 192.168.0.0/24

# Windows: Check Windows Firewall
netsh advfirewall show allprofiles

# Add firewall rule
netsh advfirewall firewall add rule name="PiStorm" dir=in action=allow protocol=TCP localport=5000
```

### DNS Issues
```bash
# Use IP addresses instead of hostnames
# Pi API: http://192.168.0.218:5000
# Not: http://raspberrypi.local:5000

# Check DNS resolution
nslookup raspberrypi.local
```

## 🔍 Performance Issues

### Slow Processing

#### Pi CPU Overload
```bash
# Monitor CPU usage
htop
iostat 1

# Check temperature
vcgencmd measure_temp

# Reduce logging level
# In config.env: LOG_LEVEL=WARNING

# Close unnecessary processes
sudo systemctl stop bluetooth
sudo systemctl stop cups
```

#### GPU Underutilization
```powershell
# Check GPU usage
nvidia-smi -l 1

# Optimize hashcat settings
hashcat -w 4 --force # Maximum workload

# Check thermal throttling
nvidia-smi --query-gpu=temperature.gpu --format=csv
```

## 🐛 Debugging Tools

### Logging
```bash
# Pi: Real-time logs
tail -f wifi_api.log

# System logs
sudo journalctl -f -u wifi_api

# Python debugging
export PYTHONDONTWRITEBYTECODE=1
python3 -u wifi_api.py

# Enable debug mode
# In config.env: LOG_LEVEL=DEBUG
```

### Network Analysis
```bash
# Monitor network traffic
sudo tcpdump -i any port 5000

# Check API responses
curl -v http://192.168.0.218:5000/health

# Monitor WiFi packets
sudo airodump-ng wlan1 --write debug
```

### File Analysis
```bash
# Check capture file contents
file capture.cap
ls -la capture.cap

# Analyze with tshark
tshark -r capture.cap -q -z io,stat,0

# Check for handshakes
aircrack-ng capture.cap
```

## 📋 Diagnostic Commands

### Complete System Check
```bash
#!/bin/bash
# PiStorm diagnostic script

echo "=== PiStorm System Diagnostic ==="

echo "1. System Info:"
uname -a
cat /etc/os-release

echo "2. Interfaces:"
ip link show | grep wlan
iw dev

echo "3. Tools:"
which aircrack-ng airodump-ng aireplay-ng tshark

echo "4. Python packages:"
pip3 list | grep -E "(flask|requests)"

echo "5. Monitor mode test:"
python3 test_monitor.py

echo "6. API health:"
curl -s http://localhost:5000/health | jq .

echo "7. Disk space:"
df -h

echo "8. Memory:"
free -h

echo "9. Temperature:"
vcgencmd measure_temp

echo "10. Recent logs:"
tail -20 wifi_api.log
```

### Quick Fixes
```bash
# Reset everything
sudo systemctl restart networking
sudo pkill -f wifi_api
sudo pkill -f airodump
sudo pkill -f aireplay

# Restart API
cd /path/to/pistorm
source config.env
python3 wifi_api.py

# Test basic functionality
curl http://localhost:5000/ping
curl -H "X-API-Key: $API_KEY" http://localhost:5000/scan
```

## 🆘 Getting Help

### Log Collection
When reporting issues, provide:
1. Full error messages
2. `wifi_api.log` contents
3. Output of `python3 test_monitor.py`
4. System info: `uname -a`, `python3 --version`
5. Hardware: WiFi adapter models

### Common Log Patterns
- `Device or resource busy` → Interface conflict
- `Operation not permitted` → Permission issue
- `No such device` → Interface missing
- `Connection refused` → Network/firewall issue
- `Timeout` → Performance/resource issue

### Community Resources
- GitHub Issues: Report bugs and get help
- Wiki: Additional documentation
- Discussions: Community support

Remember: Most issues are network or permission related. Check connectivity and sudo access first!