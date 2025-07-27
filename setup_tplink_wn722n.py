#!/usr/bin/env python3
"""
TP-Link TL-WN722N Setup Script for PiStorm
Configures the TP-Link adapter for monitor mode and packet injection
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

def detect_tplink_version():
    """Detect which version of TL-WN722N is connected"""
    print("🔍 DETECTING TP-LINK TL-WN722N VERSION")
    print("=" * 45)
    
    # Check USB devices
    rc, out, err = run_cmd("lsusb")
    if rc == 0:
        tplink_devices = []
        for line in out.split('\n'):
            if 'tp-link' in line.lower() or '0bda:' in line or '148f:' in line:
                tplink_devices.append(line.strip())
        
        if tplink_devices:
            print("📱 TP-Link devices found:")
            for device in tplink_devices:
                print(f"   {device}")
                
                # Determine version by USB ID
                if "0bda:8178" in device:
                    return "v1", "Realtek RTL8188EUS", device
                elif "148f:7601" in device:
                    return "v2/v3", "Ralink RT2571W/RT3070", device
                elif "2357:" in device:
                    return "v3+", "Newer chipset", device
        else:
            print("❌ No TP-Link devices detected")
            return None, None, None
    
    return None, None, None

def setup_tplink_v1():
    """Setup for TL-WN722N v1 (RTL8188EUS chipset)"""
    print("\n🔧 SETTING UP TL-WN722N V1 (RTL8188EUS)")
    print("=" * 45)
    
    # Check if driver is already installed
    rc, out, err = run_cmd("lsmod | grep 8188eu")
    if rc == 0:
        print("✅ RTL8188EUS driver already loaded")
    else:
        print("📦 Installing RTL8188EUS driver...")
        
        # Install required packages
        install_commands = [
            "sudo apt update",
            "sudo apt install -y dkms git bc",
            "sudo apt install -y raspberrypi-kernel-headers"
        ]
        
        for cmd in install_commands:
            print(f"Running: {cmd}")
            rc, out, err = run_cmd(cmd, timeout=300)
            if rc != 0:
                print(f"❌ Failed: {cmd}")
                return False
        
        # Clone and install driver
        driver_dir = "/usr/src/rtl8188eus-1.0"
        if not os.path.exists(driver_dir):
            print("⬇️ Downloading RTL8188EUS driver...")
            rc, out, err = run_cmd("cd /tmp && git clone https://github.com/aircrack-ng/rtl8188eus.git")
            if rc == 0:
                rc, out, err = run_cmd("sudo cp -r /tmp/rtl8188eus /usr/src/rtl8188eus-1.0")
                if rc == 0:
                    print("✅ Driver source copied")
                else:
                    print("❌ Failed to copy driver source")
                    return False
        
        # Install via DKMS
        print("🔨 Building and installing driver...")
        dkms_commands = [
            "sudo dkms add -m rtl8188eus -v 1.0",
            "sudo dkms build -m rtl8188eus -v 1.0", 
            "sudo dkms install -m rtl8188eus -v 1.0"
        ]
        
        for cmd in dkms_commands:
            print(f"Running: {cmd}")
            rc, out, err = run_cmd(cmd, timeout=300)
            if rc != 0:
                print(f"⚠️ DKMS command may have failed: {cmd}")
                print(f"Error: {err}")
    
    return True

def setup_tplink_v2_v3():
    """Setup for TL-WN722N v2/v3 (RT3070/MT7601U chipset)"""
    print("\n🔧 SETTING UP TL-WN722N V2/V3")
    print("=" * 35)
    
    # These versions usually work out of the box on modern Linux
    rc, out, err = run_cmd("lsmod | grep -E '(rt2800usb|mt7601u)'")
    if rc == 0:
        print("✅ Driver already loaded for v2/v3")
        return True
    else:
        print("📦 Installing drivers for v2/v3...")
        rc, out, err = run_cmd("sudo apt install -y firmware-ralink")
        if rc == 0:
            print("✅ Ralink firmware installed")
        
        # Reload modules
        reload_commands = [
            "sudo modprobe -r rt2800usb",
            "sudo modprobe rt2800usb"
        ]
        
        for cmd in reload_commands:
            run_cmd(cmd, timeout=10)
        
        return True

def find_tplink_interface():
    """Find the TP-Link interface name"""
    print("\n🔍 FINDING TP-LINK INTERFACE")
    print("=" * 35)
    
    rc, out, err = run_cmd("iw dev")
    if rc == 0:
        # Look for interface names
        interfaces = re.findall(r'Interface (\w+)', out)
        
        for iface in interfaces:
            # Check interface details
            rc_info, out_info, _ = run_cmd(f"iw dev {iface} info")
            if rc_info == 0:
                print(f"📡 Interface {iface}:")
                print(f"   {out_info.strip()}")
                
                # This is likely our TP-Link adapter if it's not wlan0
                if iface != "wlan0" or "usb" in out_info.lower():
                    print(f"✅ Found TP-Link interface: {iface}")
                    return iface
    
    # Fallback - check common interface names
    common_names = ["wlan1", "wlan2", "wlx00", "wlp0s"]
    for iface in common_names:
        rc, out, err = run_cmd(f"ip link show {iface}")
        if rc == 0:
            print(f"✅ Found interface: {iface}")
            return iface
    
    print("❌ Could not automatically detect TP-Link interface")
    return None

def test_tplink_monitor_mode(interface):
    """Test monitor mode with TP-Link adapter"""
    print(f"\n🧪 TESTING TP-LINK MONITOR MODE: {interface}")
    print("=" * 45)
    
    if not interface:
        print("❌ No interface specified")
        return False
    
    # Kill interfering processes first
    print("🔪 Killing interfering processes...")
    kill_commands = [
        "sudo airmon-ng check kill",
        "sudo systemctl stop NetworkManager",
        "sudo systemctl stop wpa_supplicant"
    ]
    
    for cmd in kill_commands:
        run_cmd(cmd, timeout=10)
        time.sleep(1)
    
    # Setup monitor mode on TP-Link adapter
    print(f"🔧 Setting up monitor mode on {interface}...")
    setup_commands = [
        f"sudo ip link set {interface} down",
        f"sudo iw dev {interface} set type monitor", 
        f"sudo ip link set {interface} up"
    ]
    
    for cmd in setup_commands:
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            print(f"❌ Failed: {cmd} - {err}")
            return False
        time.sleep(1)
    
    # Verify monitor mode
    rc, out, err = run_cmd(f"iwconfig {interface}")
    if rc == 0 and "Mode:Monitor" in out:
        print(f"✅ {interface} is in monitor mode")
    else:
        print(f"❌ {interface} failed to enter monitor mode")
        return False
    
    # Test packet capture with TP-Link adapter
    print(f"📦 Testing packet capture on {interface}...")
    
    # Set to channel 6 first
    run_cmd(f"sudo iwconfig {interface} channel 6")
    time.sleep(2)
    
    # Test with tcpdump
    print("🔧 Testing with tcpdump (5 seconds)...")
    rc, out, err = run_cmd(f"timeout 5 sudo tcpdump -i {interface} -c 5 -w /tmp/tplink_test.pcap")
    
    if os.path.exists("/tmp/tplink_test.pcap"):
        size = os.path.getsize("/tmp/tplink_test.pcap")
        print(f"📏 TP-Link captured {size} bytes")
        
        if size > 100:
            print("🎉 SUCCESS! TP-Link TL-WN722N is capturing real packets!")
            
            # Test different channels
            test_channels = [1, 6, 11]
            for channel in test_channels:
                print(f"📡 Testing channel {channel}...")
                run_cmd(f"sudo iwconfig {interface} channel {channel}")
                time.sleep(1)
                
                rc, out, err = run_cmd(f"timeout 3 sudo tcpdump -i {interface} -c 1")
                if "packet" in out.lower() or len(out) > 50:
                    print(f"✅ Channel {channel}: Active")
                else:
                    print(f"⚠️ Channel {channel}: No activity")
            
            # Clean up
            os.remove("/tmp/tplink_test.pcap")
            return True
        else:
            print(f"⚠️ Only captured {size} bytes - may need better antenna position")
    
    print("❌ TP-Link packet capture test failed")
    return False

def update_pistorm_config(tplink_interface):
    """Update PiStorm configuration to use TP-Link adapter"""
    print(f"\n⚙️ UPDATING PISTORM CONFIG")
    print("=" * 35)
    
    config_file = Path("config.env")
    if config_file.exists():
        # Read current config
        with open(config_file, 'r') as f:
            config_content = f.read()
        
        # Update monitor interface to use TP-Link
        if "MON_IFACE=" in config_content:
            config_content = re.sub(r'MON_IFACE=.*', f'MON_IFACE={tplink_interface}', config_content)
        else:
            config_content += f"\nMON_IFACE={tplink_interface}\n"
        
        # Write updated config
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        print(f"✅ Updated MON_IFACE to {tplink_interface} in config.env")
        print("🔄 Restart wifi_api.py to use new configuration")
    else:
        print("⚠️ config.env not found - you may need to set MON_IFACE manually")

def main():
    """Main setup function"""
    print("🚀 TP-LINK TL-WN722N SETUP FOR PISTORM")
    print("=" * 50)
    print("This script will configure your TP-Link adapter for monitor mode")
    print("=" * 50)
    
    # Detect TP-Link version
    version, chipset, device_info = detect_tplink_version()
    
    if not version:
        print("❌ No TP-Link TL-WN722N detected!")
        print("💡 Make sure the adapter is plugged in and recognized")
        return False
    
    print(f"✅ Detected: TL-WN722N {version}")
    print(f"📡 Chipset: {chipset}")
    print(f"📋 Device: {device_info}")
    
    # Setup based on version
    setup_success = False
    if version == "v1":
        setup_success = setup_tplink_v1()
    else:
        setup_success = setup_tplink_v2_v3()
    
    if not setup_success:
        print("❌ Driver setup failed")
        return False
    
    # Find interface
    tplink_interface = find_tplink_interface()
    if not tplink_interface:
        print("❌ Could not find TP-Link interface")
        return False
    
    # Test monitor mode
    monitor_success = test_tplink_monitor_mode(tplink_interface)
    
    if monitor_success:
        # Update PiStorm config
        update_pistorm_config(tplink_interface)
        
        print("\n" + "=" * 50)
        print("🎉 TP-LINK TL-WN722N SETUP COMPLETE!")
        print("=" * 50)
        print(f"✅ Interface: {tplink_interface}")
        print("✅ Monitor mode: Working")
        print("✅ Packet capture: Working")
        print("✅ Configuration: Updated")
        print("")
        print("🚀 Next steps:")
        print("1. Restart PiStorm: python3 wifi_api.py")
        print("2. Test with: python3 test_monitor.py")
        print("3. Should now capture REAL packets!")
        
        return True
    else:
        print("\n" + "=" * 50)
        print("❌ TP-LINK SETUP FAILED")
        print("=" * 50)
        print("💡 Try these troubleshooting steps:")
        print("1. Unplug and reconnect the adapter")
        print("2. Try a different USB port")
        print("3. Reboot the Pi: sudo reboot")
        print("4. Run this script again")
        
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)