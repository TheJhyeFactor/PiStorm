#!/usr/bin/env python3
"""
Monitor Mode Test Script - REAL PACKET CAPTURE ONLY
Tests if monitor mode is working properly and can capture REAL packets
NO FAKE DATA - Must capture actual WiFi traffic
"""

import subprocess
import time
import os
import signal
from pathlib import Path

def run_cmd(cmd, timeout=30):
    """Run command with timeout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"

def test_monitor_mode():
    """Test monitor mode functionality - REAL PACKET CAPTURE"""
    print("🔍 Testing Monitor Mode Functionality - NO FAKE DATA")
    print("=" * 50)
    
    mon_iface = "wlan1"
    
    # 1. Check interface exists
    print(f"📡 Checking interface {mon_iface}...")
    rc, out, err = run_cmd(f"ip link show {mon_iface}")
    if rc != 0:
        print(f"❌ Interface {mon_iface} not found!")
        return False
    else:
        print(f"✅ Interface {mon_iface} exists")
    
    # 2. Kill interfering processes first - CRITICAL FIX
    print("🔪 Killing interfering processes...")
    interfering_processes = [
        "sudo pkill -f wpa_supplicant",
        "sudo pkill -f NetworkManager", 
        "sudo systemctl stop NetworkManager",
        "sudo systemctl stop wpa_supplicant",
        "sudo airmon-ng check kill"
    ]
    
    for cmd in interfering_processes:
        print(f"Running: {cmd}")
        run_cmd(cmd, timeout=10)
        time.sleep(1)
    
    # 3. Proper monitor mode setup with full reset
    print(f"🔧 Setting up monitor mode properly...")
    
    # Take interface down completely
    print("⬇️ Taking interface down...")
    run_cmd(f"sudo ip link set {mon_iface} down")
    time.sleep(2)
    
    # Force remove from any bridge/master
    run_cmd(f"sudo ip link set {mon_iface} nomaster", timeout=5)
    
    # Set monitor mode
    print("📡 Setting monitor mode...")
    rc, out, err = run_cmd(f"sudo iw dev {mon_iface} set type monitor")
    if rc != 0:
        print(f"❌ Failed to set monitor mode: {err}")
        return False
    
    # Bring interface up
    print("⬆️ Bringing interface up...")
    rc, out, err = run_cmd(f"sudo ip link set {mon_iface} up")
    if rc != 0:
        print(f"❌ Failed to bring interface up: {err}")
        return False
    
    time.sleep(3)  # Let interface stabilize
    
    # 4. Verify monitor mode is actually working
    print("🔍 Verifying monitor mode status...")
    rc, out, err = run_cmd(f"iwconfig {mon_iface}")
    if "Mode:Monitor" not in out:
        print(f"❌ Monitor mode verification failed!")
        print(f"Output: {out}")
        return False
    print("✅ Monitor mode verified")
    
    # 5. Test basic packet capture with multiple methods
    print(f"📦 Testing REAL packet capture - NO FAKE DATA...")
    
    # Clean up any old test files
    run_cmd("sudo rm -f /tmp/monitor_test*")
    
    # Method 1: Try tcpdump first (more reliable)
    print("🔧 Testing with tcpdump (5 seconds)...")
    cmd = f"timeout 5 sudo tcpdump -i {mon_iface} -c 10 -w /tmp/monitor_tcpdump.pcap"
    rc, out, err = run_cmd(cmd, timeout=8)
    
    if os.path.exists("/tmp/monitor_tcpdump.pcap"):
        size = os.path.getsize("/tmp/monitor_tcpdump.pcap")
        print(f"📏 tcpdump captured {size} bytes")
        if size > 24:
            print("✅ tcpdump successfully capturing packets!")
            print("🎉 MONITOR MODE IS WORKING WITH REAL PACKETS!")
            run_cmd("sudo rm -f /tmp/monitor_tcpdump.pcap")
            return True
    
    # Method 2: Try airodump-ng with different parameters
    print("🔧 Testing with airodump-ng...")
    
    # Set to active channel first
    active_channels = [6, 1, 11, 3, 9]
    
    for channel in active_channels:
        print(f"🔧 Trying channel {channel}...")
        run_cmd(f"sudo iwconfig {mon_iface} channel {channel}")
        time.sleep(1)
        
        # Use simpler airodump command
        cmd = f"timeout 8 sudo airodump-ng --write /tmp/monitor_test_ch{channel} --output-format pcap {mon_iface}"
        print(f"Running: {cmd}")
        
        rc, out, err = run_cmd(cmd, timeout=12)
        
        # Check for any generated files
        test_files = [
            f"/tmp/monitor_test_ch{channel}-01.cap",
            f"/tmp/monitor_test_ch{channel}.cap", 
            f"/tmp/monitor_test_ch{channel}-01.pcap"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                size = os.path.getsize(test_file)
                print(f"📏 Found {test_file}: {size} bytes")
                if size > 100:
                    print(f"✅ Channel {channel} - Real packets captured!")
                    print("🎉 MONITOR MODE IS WORKING WITH REAL PACKETS!")
                    run_cmd("sudo rm -f /tmp/monitor_test_ch*")
                    return True
        
        print(f"⚠️ Channel {channel} - No significant packets")
    
    print("❌ No real packets captured on any channel!")
    print("💡 This may indicate:")
    print("   - No WiFi activity in area")
    print("   - Hardware/driver issues")
    print("   - Interface still being blocked")
    return False

def test_monitor_mode_capability():
    """Main test function that can be imported"""
    success = test_monitor_mode()
    
    result = {
        "monitor_mode_ok": success,
        "interface": "wlan1",
        "test_duration": 15,
        "real_packets_required": True
    }
    
    if success:
        result["message"] = "Monitor mode working with real packet capture"
        result["packets_captured"] = "Real WiFi traffic detected"
    else:
        result["message"] = "Monitor mode failed - no real packets captured"
        result["packets_captured"] = 0
    
    return result

def main():
    """Main function for standalone execution"""
    print("🚀 PiStorm Monitor Mode Test - REAL PACKETS ONLY")
    print("=" * 60)
    
    success = test_monitor_mode()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: Monitor mode is working with REAL packet capture!")
        print("✅ Ready for handshake capture operations")
    else:
        print("❌ FAILED: Monitor mode cannot capture real packets")
        print("🔧 Check WiFi hardware, drivers, and network activity")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)