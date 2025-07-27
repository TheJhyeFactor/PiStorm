#!/bin/bash
# Quick TP-Link TL-WN722N Fix for PiStorm
# This will get your TP-Link adapter working immediately

echo "🚀 Quick TP-Link TL-WN722N Fix"
echo "============================="

# Check if TP-Link is connected
echo "🔍 Checking for TP-Link adapter..."
lsusb | grep -i tp-link
if [ $? -eq 0 ]; then
    echo "✅ TP-Link adapter detected"
else
    echo "❌ TP-Link adapter not found - make sure it's plugged in"
    exit 1
fi

# Find the TP-Link interface
echo "📡 Finding TP-Link interface..."
TPLINK_IFACE=""

# Check common interface names
for iface in wlan1 wlan2 wlx* wlp*; do
    if ip link show $iface >/dev/null 2>&1; then
        # Check if it's likely the TP-Link (not wlan0)
        if [ "$iface" != "wlan0" ]; then
            TPLINK_IFACE=$iface
            echo "✅ Found TP-Link interface: $TPLINK_IFACE"
            break
        fi
    fi
done

if [ -z "$TPLINK_IFACE" ]; then
    echo "❌ Could not find TP-Link interface"
    echo "💡 Available interfaces:"
    ip link show | grep wlan
    exit 1
fi

# Quick setup for monitor mode
echo "🔧 Setting up monitor mode on $TPLINK_IFACE..."

# Kill interfering processes
echo "🔪 Killing interfering processes..."
sudo airmon-ng check kill >/dev/null 2>&1
sudo systemctl stop NetworkManager >/dev/null 2>&1
sudo systemctl stop wpa_supplicant >/dev/null 2>&1

# Setup monitor mode
echo "📡 Enabling monitor mode..."
sudo ip link set $TPLINK_IFACE down
sudo iw dev $TPLINK_IFACE set type monitor
sudo ip link set $TPLINK_IFACE up

# Verify monitor mode
if iwconfig $TPLINK_IFACE | grep -q "Mode:Monitor"; then
    echo "✅ Monitor mode enabled on $TPLINK_IFACE"
else
    echo "❌ Failed to enable monitor mode"
    exit 1
fi

# Test packet capture
echo "🧪 Testing packet capture (5 seconds)..."
sudo iwconfig $TPLINK_IFACE channel 6
timeout 5 sudo tcpdump -i $TPLINK_IFACE -c 5 -w /tmp/tplink_quick_test.pcap >/dev/null 2>&1

if [ -f "/tmp/tplink_quick_test.pcap" ]; then
    SIZE=$(stat -c%s "/tmp/tplink_quick_test.pcap")
    echo "📏 Captured $SIZE bytes"
    
    if [ $SIZE -gt 100 ]; then
        echo "🎉 SUCCESS! TP-Link is capturing real packets!"
        
        # Update config.env to use TP-Link interface
        if [ -f "config.env" ]; then
            echo "⚙️ Updating config.env..."
            sed -i "s/MON_IFACE=.*/MON_IFACE=$TPLINK_IFACE/" config.env
            # Add if not exists
            if ! grep -q "MON_IFACE=" config.env; then
                echo "MON_IFACE=$TPLINK_IFACE" >> config.env
            fi
            echo "✅ Updated MON_IFACE to $TPLINK_IFACE"
        fi
        
        # Clean up test file
        rm -f /tmp/tplink_quick_test.pcap
        
        echo ""
        echo "🎯 READY TO USE!"
        echo "==============="
        echo "Your TP-Link TL-WN722N is now configured for PiStorm"
        echo "Restart wifi_api.py to use the new configuration:"
        echo ""
        echo "python3 wifi_api.py"
        echo ""
        
    else
        echo "⚠️ Only captured $SIZE bytes - may need better positioning"
        echo "💡 Try moving closer to WiFi networks or checking antenna"
    fi
else
    echo "❌ Packet capture test failed"
    echo "💡 Try running the full setup: python3 setup_tplink_wn722n.py"
fi

echo ""
echo "✅ Quick fix complete!"