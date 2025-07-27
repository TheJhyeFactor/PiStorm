# PiStorm Windows GPU Station Setup Instructions

## 🎯 **What You're Setting Up**
You're creating a high-performance GPU cracking station that receives WiFi handshake files from the Raspberry Pi and uses your RTX 4070 Super GPU to crack passwords 800x faster than the Pi alone.

## 🏗️ **Architecture Overview**
- **Raspberry Pi**: Network scanning, handshake capture, coordination
- **Your Windows PC**: GPU-accelerated password cracking with hashcat
- **Wio Terminal**: Real-time status display and control

## 📋 **Prerequisites**
- Windows 10/11 with Administrator access
- NVIDIA RTX 4070 Super with latest drivers
- Python 3.8+ installed
- At least 8GB free disk space for wordlists

## 🚀 **Step-by-Step Installation**

### **Step 1: Run the Automated Setup Script**
```powershell
# Open PowerShell as Administrator
# Navigate to the PiStorm project folder
cd path\to\pistorm\windows-gpu

# Run the setup script
.\setup.ps1
```

### **Step 2: What the Script Does**
The `setup.ps1` script will automatically:

1. **📁 Create Directory Structure:**
   ```
   C:\Users\[Your Name]\wifi-crack-pc\
   ├── incoming\     (Receives .cap files from Pi)
   ├── wordlists\    (Password dictionaries)
   ├── results\      (Cracking results)
   ├── logs\         (Processing logs)
   └── scripts\      (PiStorm tools)
   ```

2. **🔧 Install Required Software:**
   - Python packages: `watchdog`, `requests`, `psutil`
   - Windows Subsystem for Linux (WSL) with Ubuntu
   - hcxtools (for .cap file conversion)
   - hashcat (if not already installed)

3. **📚 Download Wordlists:**
   - `rockyou.txt` (14M most common passwords)
   - `wifi-wpa-probable.txt` (WiFi-specific passwords)

4. **🔥 Configure Windows Firewall:**
   - Opens port 5000 for Pi communication
   - Allows incoming handshake files

### **Step 3: Manual Installations (If Needed)**

#### **Install Hashcat (if not auto-installed):**
1. Download from: https://hashcat.net/hashcat/
2. Extract to `C:\hashcat\`
3. Add to System PATH:
   - Windows Settings → Advanced → Environment Variables
   - Add `C:\hashcat\` to PATH

#### **Install NVIDIA CUDA (if needed):**
1. Download from: https://developer.nvidia.com/cuda-downloads
2. Install with default settings
3. Verify: `nvcc --version`

#### **Install hcxtools via WSL:**
```bash
# In WSL Ubuntu terminal
sudo apt update
sudo apt install hcxtools aircrack-ng
```

### **Step 4: Configuration**

#### **Edit `crack_listener.py` Configuration:**
```python
# Update these settings in crack_listener.py:
PI_IP = "192.168.0.218"  # Your Pi's IP address
PI_PORT = 5000
PI_API_KEY = "4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f"
```

#### **Verify GPU Detection:**
```powershell
# Test hashcat GPU detection
hashcat -I

# Should show your RTX 4070 Super
```

### **Step 5: Testing**

#### **Test the GPU Station:**
```powershell
# Run the test script
python C:\Users\[Your Name]\wifi-crack-pc\scripts\test_gpu_station.py
```

**Expected Output:**
```
=== PiStorm GPU Station Test ===
✅ Hashcat: OK
✅ GPU: Detected
✅ Conversion tool: hcxpcapngtool
✅ Wordlists: 2 found

🎉 All tests passed! GPU station ready.
```

### **Step 6: Start the GPU Listener**

#### **Run the Crack Listener:**
```powershell
# Start the GPU processing service
python C:\Users\[Your Name]\wifi-crack-pc\scripts\crack_listener.py
```

**You Should See:**
```
=== 🚀 PiStorm GPU Listener - Windows PC ===
🔥 GPU: RTX 4070 Super Ready for Distributed Processing
📁 Monitoring: C:\Users\[Your Name]\wifi-crack-pc\incoming
📚 Wordlists: C:\Users\[Your Name]\wifi-crack-pc\wordlists
📊 Results: C:\Users\[Your Name]\wifi-crack-pc\results
🌐 Pi API: 192.168.0.218:5000
🔑 Authenticated: API Key configured
==================================================
✅ Pi connectivity verified
Started monitoring C:\Users\[Your Name]\wifi-crack-pc\incoming
Waiting for capture files... (Ctrl+C to stop)
```

## 🔧 **How It Works**

### **Workflow:**
1. **Pi captures handshake** → Creates `.cap` file
2. **Pi transfers file** → HTTP upload to your PC's `incoming\` folder
3. **Your PC detects file** → Watchdog triggers processing
4. **GPU processes file** → RTX 4070 Super runs hashcat
5. **Result sent back** → Password or "NOT FOUND" to Pi
6. **Pi displays result** → Shows on Wio Terminal

### **Performance:**
- **Pi alone**: ~1,000 passwords/second
- **With your RTX 4070 Super**: ~800,000 passwords/second
- **Speed improvement**: 800x faster!

## 🐛 **Troubleshooting**

### **Common Issues:**

#### **"hashcat not found"**
```powershell
# Check if hashcat is in PATH
where hashcat

# If not found, add to PATH or reinstall
```

#### **"GPU not detected"**
```powershell
# Update NVIDIA drivers
# Download latest from nvidia.com

# Check GPU status
nvidia-smi
```

#### **"hcxtools not found"**
```bash
# In WSL terminal
sudo apt update
sudo apt install hcxtools

# Test
wsl hcxpcapngtool --version
```

#### **"Pi connection failed"**
```powershell
# Test Pi connectivity
ping 192.168.0.218

# Check firewall
netsh advfirewall firewall show rule name="PiStorm GPU Listener"
```

## 📊 **Monitoring Performance**

### **Watch GPU Usage:**
```powershell
# Monitor GPU utilization
nvidia-smi -l 1
```

### **Check Processing Logs:**
```powershell
# View real-time logs
Get-Content C:\Users\[Your Name]\wifi-crack-pc\logs\crack_listener.log -Wait
```

## 🎯 **Success Indicators**

### **You'll Know It's Working When:**
1. ✅ Setup script completes without errors
2. ✅ Test script shows all green checkmarks
3. ✅ GPU listener shows "Pi connectivity verified"
4. ✅ GPU utilization spikes when processing files
5. ✅ Results appear in Pi logs within minutes

## 🔐 **Security Notes**
- Only use on networks you own or have permission to test
- Keep API keys secure
- Monitor resource usage to prevent overheating
- Regular driver updates for optimal performance

## 📞 **Need Help?**
If you encounter issues:
1. Check the troubleshooting section above
2. Review logs in `C:\Users\[Your Name]\wifi-crack-pc\logs\`
3. Verify all prerequisites are met
4. Ensure firewall allows port 5000

**Your RTX 4070 Super is about to become a WiFi password cracking beast! 🔥**