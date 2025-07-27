#!/bin/bash
# PiStorm Security Tools Installation Script
# Installs all required WiFi security tools on Raspberry Pi

echo "🚀 PiStorm Security Tools Installation"
echo "====================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (sudo ./install_security_tools.sh)"
    exit 1
fi

# Update package lists
echo "📦 Updating package lists..."
apt update

# Install core aircrack-ng suite
echo "🔧 Installing Aircrack-ng suite..."
apt install -y aircrack-ng

# Verify aircrack-ng installation
if command -v aircrack-ng &> /dev/null; then
    echo "✅ Aircrack-ng suite installed successfully"
    echo "   - aircrack-ng: WPA/WEP key cracking"
    echo "   - airodump-ng: Packet capture and network scanning"
    echo "   - aireplay-ng: Packet injection and deauth attacks"
    echo "   - airbase-ng: Rogue access point creation"
else
    echo "❌ Aircrack-ng installation failed"
    exit 1
fi

# Install additional networking tools
echo "🌐 Installing network analysis tools..."
apt install -y tcpdump tshark wireshark-common

# Install WiFite2 (automated WiFi auditing)
echo "🤖 Installing WiFite2..."
if ! command -v wifite &> /dev/null; then
    cd /opt
    git clone https://github.com/derv82/wifite2.git
    cd wifite2
    python3 setup.py install
    ln -sf /opt/wifite2/wifite /usr/local/bin/wifite
    echo "✅ WiFite2 installed"
else
    echo "✅ WiFite2 already installed"
fi

# Install Reaver (WPS attacks)
echo "🔓 Installing Reaver..."
apt install -y reaver

# Install PixieWPS
echo "✨ Installing PixieWPS..."
apt install -y pixiewps

# Install Kismet (optional - advanced network detection)
echo "👁️ Installing Kismet (optional)..."
apt install -y kismet

# Install hcxtools for advanced handshake conversion
echo "🔄 Installing hcxtools..."
apt install -y hcxtools

# Install additional Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install psutil requests

# Set proper permissions for wireless tools
echo "🔐 Setting up permissions..."
# Allow users in netdev group to use wireless tools
usermod -a -G netdev pi 2>/dev/null || true

# Create wordlist directory if it doesn't exist
echo "📚 Setting up wordlists..."
mkdir -p /usr/share/wordlists

# Download rockyou.txt if not present
if [ ! -f "/usr/share/wordlists/rockyou.txt" ]; then
    echo "⬬ Downloading rockyou.txt wordlist..."
    cd /usr/share/wordlists
    wget -q https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt.gz
    gunzip rockyou.txt.gz 2>/dev/null || true
    if [ -f "rockyou.txt" ]; then
        echo "✅ rockyou.txt downloaded"
    else
        echo "⚠️ Failed to download rockyou.txt - will use system wordlists"
    fi
fi

# Create fasttrack wordlist for quick tests
if [ ! -f "/usr/share/wordlists/fasttrack.txt" ]; then
    echo "⚡ Creating fasttrack wordlist..."
    cat > /usr/share/wordlists/fasttrack.txt << 'EOF'
password
123456
12345678
qwerty
abc123
Password
password123
admin
letmein
welcome
monkey
1234567890
password1
123456789
12345
iloveyou
sunshine
princess
charlie
666666
654321
696969
123123
EOF
    echo "✅ fasttrack.txt created"
fi

# Test all tools
echo "🧪 Testing tool installation..."
echo "================================"

tools=(
    "aircrack-ng --help"
    "airodump-ng --help" 
    "aireplay-ng --help"
    "tcpdump --version"
    "tshark --version"
    "reaver --help"
    "pixiewps --help"
)

for tool_cmd in "${tools[@]}"; do
    tool_name=$(echo "$tool_cmd" | cut -d' ' -f1)
    if $tool_cmd >/dev/null 2>&1; then
        echo "✅ $tool_name"
    else
        echo "❌ $tool_name"
    fi
done

# Check optional tools
echo ""
echo "Optional tools:"
echo "==============="

optional_tools=(
    "wifite --help"
    "kismet --version"
    "hcxpcapngtool --version"
)

for tool_cmd in "${optional_tools[@]}"; do
    tool_name=$(echo "$tool_cmd" | cut -d' ' -f1)
    if $tool_cmd >/dev/null 2>&1; then
        echo "✅ $tool_name (optional)"
    else
        echo "⚠️ $tool_name (optional - not critical)"
    fi
done

echo ""
echo "🎉 Installation complete!"
echo "========================"
echo ""
echo "📋 Next steps:"
echo "1. Reboot your Pi: sudo reboot"
echo "2. Test tools: python3 wifi_security_tools.py"
echo "3. Run PiStorm: python3 wifi_api.py"
echo ""
echo "⚠️ Important:"
echo "- Use only on networks you own or have permission to test"
echo "- WiFi security testing is for educational/authorized use only"
echo "- Ensure proper antenna connections for optimal performance"