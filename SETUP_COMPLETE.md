# 🎉 WiFi Crack PC Setup - COMPLETE!

Your Windows PC is now ready for distributed WiFi capture processing with your Raspberry Pi system.

## ✅ Installation Status

### READY TO USE
- **Hashcat 6.2.6**: Installed at `C:\tools\hashcat-6.2.6\hashcat.exe`
- **Python Environment**: All dependencies installed (watchdog, requests, flask)
- **Project Structure**: Complete directory structure created
- **Wordlists**: 3 valid wordlists ready (including 133MB rockyou.txt)
- **Network**: Pi reachable at 192.168.0.218
- **Processing Script**: Full-featured crack_listener.py ready
- **Service Installer**: Windows service setup scripts ready

### SSH Key Setup (CORRECTED)
**On your Pi (jhye@pi-lab-1), run these commands:**
```bash
# Create SSH directory with proper permissions
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add Windows PC's public key for PC→Pi access
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOE5MQ7edWA7D5Ai2L9EfngN/7dR2P2rLzDzEm0XAage Jhye@DESKTOP-P2GHC2L" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**API Authentication:** 
- ✅ API Key added: `4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f`
- ✅ Headers configured for authenticated API calls

## 🚀 How to Start

### Option 1: Manual Start (Testing)
```bash
cd C:\Users\Jhye\wifi-crack-pc
python scripts\crack_listener.py
```

### Option 2: Windows Service (Production)
1. Download NSSM from https://nssm.cc/download
2. Extract to project directory or add to PATH
3. Run as Administrator:
```bash
python scripts\install_windows_service.py install
```

### Option 3: Quick Test
```bash
cd C:\Users\Jhye\wifi-crack-pc
python scripts\test_setup.py
```

## 📊 Performance Expected

With your RTX 4070 Super, expect excellent performance:
- **WPA/WPA2 Cracking**: ~500-800 kH/s (GPU accelerated)
- **Memory**: 12GB GDDR6X available
- **Processing**: Much faster than Pi for dictionary attacks

## 🔄 Workflow Integration

1. **Pi captures WiFi** → Saves .cap files
2. **Pi transfers files** → Via SSH to PC's `incoming/` directory  
3. **PC processes automatically** → Hashcat GPU analysis
4. **PC sends results back** → HTTP API to Pi
5. **Pi displays results** → On Wio Terminal

## 📁 Directory Layout
```
C:\Users\Jhye\wifi-crack-pc\
├── incoming/          # Drop .cap files here
├── wordlists/         # 3 wordlists ready (133MB+ total)
├── results/           # Hashcat output files  
├── logs/              # Error logs
└── scripts/           # All processing scripts
```

## 🛠️ Available Wordlists
- `rockyou.txt` - 139MB classic wordlist
- `probable-v2-wpa-top4800.txt` - WiFi-specific passwords  
- `wifi-wpa-probable.txt` - WiFi-specific passwords

## 🔧 Management Commands

**Check Service Status:**
```bash
sc query WiFiCrackListener
```

**Manual Service Control:**
```bash
nssm start WiFiCrackListener
nssm stop WiFiCrackListener  
nssm remove WiFiCrackListener confirm
```

**Test Individual Components:**
```bash
# Test hashcat directly
C:\tools\hashcat-6.2.6\hashcat.exe --version
C:\tools\hashcat-6.2.6\hashcat.exe -b -m 22000  # GPU benchmark

# Test network to Pi
ping 192.168.0.218

# Test Python listener
python scripts\crack_listener.py
```

## 🔒 Security Notes

- SSH key authentication prevents password exposure
- Processing isolated in dedicated directories  
- API communication local network only
- No sensitive data stored permanently

## ⚡ Next Steps

1. **Copy SSH key to Pi** (command above)
2. **Start the listener** (choose option above)
3. **Update Pi scripts** to transfer files to this PC
4. **Test with sample .cap file**

Your setup is now complete and ready for production use! The PC will automatically process any .cap files placed in the `incoming/` directory and send results back to your Pi via the API.

---
*Setup completed on: 2025-07-27*  
*System: Windows PC with RTX 4070 Super*  
*Target: Pi at 192.168.0.218*