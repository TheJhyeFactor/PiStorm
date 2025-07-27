#!/usr/bin/env python3
"""
WiFi Hardware Diagnostic Tool
Comprehensive diagnosis of WiFi hardware and driver issues
"""

import subprocess
import time
import os
import re
from pathlib import Path

def run_cmd(cmd, timeout=30):
    """Run command with timeout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"

def check_interface_details():
    """Check detailed interface information"""
    print("🔍 DETAILED INTERFACE ANALYSIS")
    print("=" * 50)
    
    # Get all wireless interfaces
    rc, out, err = run_cmd("iw dev")
    if rc == 0:
        print("📡 Wireless Interfaces:")
        print(out)
    else:
        print(f"❌ Failed to get wireless interfaces: {err}")
    
    # Check interface capabilities
    interfaces = ["wlan0", "wlan1"]
    for iface in interfaces:
        print(f"\n🔧 Interface {iface} Details:")
        print("-" * 30)
        
        # Check if interface exists
        rc, out, err = run_cmd(f"ip link show {iface}")
        if rc == 0:
            print(f"✅ {iface} exists")
            print(f"Details: {out.strip()}")
        else:
            print(f"❌ {iface} not found")
            continue
        
        # Check interface info
        rc, out, err = run_cmd(f"iw dev {iface} info")
        if rc == 0:
            print(f"📋 {iface} info:")
            print(out)
        
        # Check interface capabilities
        rc, out, err = run_cmd(f"iw phy | grep -A 20 'Wiphy.*{iface}'")
        if rc == 0:
            print(f"⚡ {iface} capabilities:")
            print(out[:500])  # Limit output
        
        # Check if interface is up
        rc, out, err = run_cmd(f"iwconfig {iface}")
        if rc == 0:
            print(f"📊 {iface} status:")
            print(out)

def check_usb_wifi_adapters():
    """Check for USB WiFi adapters"""
    print("\n📱 USB WIFI ADAPTER CHECK")
    print("=" * 40)
    
    rc, out, err = run_cmd("lsusb | grep -i wireless")
    if rc == 0 and out.strip():
        print("✅ USB WiFi Adapters Found:")
        print(out)
    else:
        print("⚠️ No USB WiFi adapters detected")
    
    # Check all USB devices
    rc, out, err = run_cmd("lsusb")
    if rc == 0:
        print("\n📋 All USB Devices:")
        for line in out.split('\n'):
            if any(keyword in line.lower() for keyword in ['wireless', 'wifi', '802.11', 'wlan', 'realtek', 'ralink', 'atheros']):
                print(f"  📡 {line}")

def check_kernel_modules():
    """Check WiFi kernel modules"""
    print("\n🔧 KERNEL MODULE CHECK")
    print("=" * 35)
    
    # Common WiFi modules
    wifi_modules = [
        "cfg80211", "mac80211", "brcmfmac", "brcmutil",
        "rt2x00lib", "rt2x00usb", "rt73usb", "rt2800lib",
        "rtl8xxxu", "rtl8192cu", "ath9k", "ath9k_htc"
    ]
    
    rc, out, err = run_cmd("lsmod")
    if rc == 0:
        loaded_modules = out.split('\n')
        for module in wifi_modules:
            found = any(module in line for line in loaded_modules)
            status = "✅" if found else "❌"
            print(f"{status} {module}")

def test_raw_packet_capture():
    """Test raw packet capture with different methods"""
    print("\n🕵️ RAW PACKET CAPTURE TEST")
    print("=" * 40)
    
    # First ensure we have a monitor interface
    mon_iface = "wlan1"
    
    # Quick setup
    print(f"🔧 Setting up {mon_iface} for testing...")
    setup_commands = [
        f"sudo ip link set {mon_iface} down",
        f"sudo iw dev {mon_iface} set type monitor",
        f"sudo ip link set {mon_iface} up"
    ]
    
    for cmd in setup_commands:
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            print(f"❌ Failed: {cmd}")
            return
    
    print("✅ Monitor mode setup complete")
    
    # Test different capture methods
    capture_tests = [
        {
            "name": "tcpdump basic",
            "cmd": f"timeout 3 sudo tcpdump -i {mon_iface} -c 1 -n",
            "expect": "packet"
        },
        {
            "name": "tcpdump verbose",
            "cmd": f"timeout 3 sudo tcpdump -i {mon_iface} -c 1 -v",
            "expect": "packet"
        },
        {
            "name": "airodump basic",
            "cmd": f"timeout 3 sudo airodump-ng {mon_iface}",
            "expect": "CH"
        }
    ]
    
    for test in capture_tests:
        print(f"\n🧪 Testing: {test['name']}")
        rc, out, err = run_cmd(test['cmd'])
        
        if test['expect'] in out.lower() or test['expect'] in err.lower():
            print(f"✅ {test['name']}: WORKING")
            print(f"   Output sample: {(out + err)[:100]}...")
        else:
            print(f"❌ {test['name']}: NO PACKETS")
            print(f"   STDOUT: {out[:100]}")
            print(f"   STDERR: {err[:100]}")

def test_antenna_and_power():
    """Test antenna and power settings"""
    print("\n📡 ANTENNA AND POWER TEST")
    print("=" * 35)
    
    iface = "wlan1"
    
    # Check current power
    rc, out, err = run_cmd(f"iwconfig {iface}")
    if rc == 0:
        print("📊 Current interface status:")
        print(out)
        
        # Look for power information
        if "Tx-Power" in out:
            power_match = re.search(r'Tx-Power[=:](\d+)', out)
            if power_match:
                power = power_match.group(1)
                print(f"🔋 Current Tx Power: {power} dBm")
        
        # Check if interface is actually receiving
        if "Mode:Monitor" in out:
            print("✅ Interface in monitor mode")
        else:
            print("❌ Interface not in monitor mode")
    
    # Try setting different power levels
    power_tests = [20, 25, 30]
    for power in power_tests:
        print(f"\n🔋 Testing power level: {power} dBm")
        rc, out, err = run_cmd(f"sudo iwconfig {iface} txpower {power}")
        if rc == 0:
            print(f"✅ Set power to {power} dBm")
        else:
            print(f"❌ Failed to set power: {err}")

def check_physical_environment():
    """Check for physical environment issues"""
    print("\n🌐 PHYSICAL ENVIRONMENT CHECK")
    print("=" * 40)
    
    # Scan for nearby networks with normal interface
    print("🔍 Scanning for nearby networks...")
    rc, out, err = run_cmd("sudo iw dev wlan0 scan | grep SSID")
    
    if rc == 0 and out.strip():
        networks = out.strip().split('\n')
        print(f"✅ Found {len(networks)} networks nearby:")
        for network in networks[:5]:  # Show first 5
            print(f"   📡 {network.strip()}")
        print("💡 There IS WiFi activity in the area!")
    else:
        print("❌ No networks found - this could indicate:")
        print("   - Antenna not connected properly")
        print("   - No WiFi activity in area")
        print("   - Hardware/driver issues")

def hardware_recommendations():
    """Provide hardware recommendations"""
    print("\n💡 HARDWARE RECOMMENDATIONS")
    print("=" * 40)
    
    print("🔧 If still having 24-byte capture issues:")
    print("1. 📡 Check antenna connections are secure")
    print("2. 🔌 Try different USB ports (USB 2.0 vs 3.0)")
    print("3. 🔄 Try external USB WiFi adapter with monitor mode support")
    print("4. 📶 Move closer to WiFi networks for testing")
    print("5. 🔋 Ensure adequate power supply to Pi")
    print("")
    print("🎯 Recommended USB WiFi Adapters for monitor mode:")
    print("   - ALFA AWUS036ACS (dual-band, excellent monitor mode)")
    print("   - ALFA AWUS036NHA (2.4GHz, proven monitor mode)")
    print("   - Panda PAU09 (budget option, good compatibility)")
    print("   - TP-Link AC600T (dual-band, monitor mode support)")

def main():
    """Run complete hardware diagnostic"""
    print("🚀 PiStorm WiFi Hardware Diagnostic")
    print("=" * 50)
    print("This tool will diagnose why you're only getting 24-byte captures")
    print("=" * 50)
    
    # Run all diagnostic tests
    check_interface_details()
    check_usb_wifi_adapters()
    check_kernel_modules() 
    test_raw_packet_capture()
    test_antenna_and_power()
    check_physical_environment()
    hardware_recommendations()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC COMPLETE")
    print("=" * 50)
    print("Review the results above to identify the root cause")
    print("of the 24-byte capture issue.")

if __name__ == "__main__":
    main()