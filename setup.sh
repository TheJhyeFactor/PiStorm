#!/bin/bash
# WiFi Penetration Testing API Setup Script for Raspberry Pi

echo "WiFi Penetration Testing API Setup Script"
echo "==========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Do not run this script as root. It will use sudo when needed."
   exit 1
fi

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt install -y aircrack-ng wireless-tools python3-pip python3-venv iw

# Download wordlists if not present
echo "Setting up wordlists..."
sudo mkdir -p /usr/share/wordlists
if [ ! -f /usr/share/wordlists/rockyou.txt ] && [ ! -f /usr/share/wordlists/rockyou.txt.gz ]; then
    echo "Downloading rockyou wordlist..."
    cd /tmp
    wget -q https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
    sudo mv rockyou.txt /usr/share/wordlists/
    echo "Wordlist installed to /usr/share/wordlists/rockyou.txt"
else
    echo "Wordlist already available"
fi

# Check if aircrack-ng suite is installed
echo "Checking aircrack-ng suite..."
for tool in aircrack-ng airodump-ng aireplay-ng; do
    if command -v $tool &> /dev/null; then
        echo "✓ $tool is installed"
    else
        echo "✗ $tool is not found"
        exit 1
    fi
done

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install flask flask-cors

# Create captures directory
echo "Creating captures directory..."
mkdir -p /home/$USER/captures
chmod 755 /home/$USER/captures

# Copy configuration file
if [ ! -f config.env ]; then
    echo "Creating configuration file..."
    cp config.env.example config.env
    echo "Please edit config.env with your settings"
fi

# Check wireless interfaces
echo "Checking wireless interfaces..."
ip link show | grep -E "wlan|wlp" || echo "No wireless interfaces found"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.env with your configuration"
echo "2. Set a strong API key in config.env"
echo "3. Source the virtual environment: source venv/bin/activate"
echo "4. Run the API: python3 wifi_api.py"
echo ""
echo "IMPORTANT: This is a real penetration testing tool."
echo "Only use on networks you own or have explicit permission to test."
echo "Unauthorized access to wireless networks is illegal."