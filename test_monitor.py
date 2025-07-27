#!/usr/bin/env python3
"""
Monitor Mode Test Script
Tests if monitor mode is working properly and can capture packets
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
        
        # Verify
        rc, out, err = run_cmd(f"iwconfig {mon_iface}")
        if "Mode:Monitor" in out:
            print(f"✅ Successfully set to monitor mode")
        else:
            print(f"❌ Failed to set monitor mode!")
            return False
    
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
                    return True
        
        print(f"⚠️ Channel {channel} - No significant packets")
    
    print("❌ No real packets captured on any channel!")
    return False
    
    # Check if file was created
    cap_files = [
        "/tmp/monitor_test-01.cap",
        "/tmp/monitor_test.cap",
        "/tmp/monitor_test-01.pcap"
    ]
    
    captured_file = None
    for cap_file in cap_files:
        if os.path.exists(cap_file):
            captured_file = cap_file
            break
    
    if captured_file:
        size = os.path.getsize(captured_file)
        print(f"✅ Capture file created: {captured_file}")
        print(f"📏 File size: {size} bytes")
        
        if size > 100:
            print(f"✅ Packets captured successfully!")
            
            # Analyze with tshark if available
            rc, out, err = run_cmd(f"tshark -r {captured_file} -q -z io,stat,0", timeout=10)
            if rc == 0:
                print(f"📊 Packet analysis:")
                for line in out.split('\n'):
                    if 'frames' in line.lower():
                        print(f"   {line.strip()}")
            
            # Clean up
            os.remove(captured_file)
            return True
        else:
            print(f"⚠️ File too small - may not have captured packets")
            os.remove(captured_file)
            return False
    else:
        print(f"❌ No capture file created!")
        print(f"Airodump output: {out}")
        print(f"Airodump error: {err}")
        return False

def test_deauth_capability():
    """Test if deauth attacks can be sent"""
    print(f"\n🚫 Testing Deauth Capability")
    print("=" * 30)
    
    mon_iface = "wlan1"
    
    # Test with a fake BSSID (won't affect anyone)
    fake_bssid = "00:11:22:33:44:55"
    
    print(f"🧪 Testing deauth transmission (fake target)...")
    cmd = f"timeout 3 sudo aireplay-ng -0 1 -a {fake_bssid} {mon_iface}"
    
    rc, out, err = run_cmd(cmd, timeout=5)
    
    if rc == 0 or "Sending DeAuth" in out:
        print(f"✅ Deauth capability working")
        print(f"Output: {out}")
        return True
    else:
        print(f"❌ Deauth failed")
        print(f"Error: {err}")
        print(f"Output: {out}")
        return False

def test_channel_switching():
    """Test if channel switching works"""
    print(f"\n📻 Testing Channel Switching")
    print("=" * 30)
    
    mon_iface = "wlan1"
    
    channels = [1, 6, 11]
    success = True
    
    for channel in channels:
        print(f"🔧 Setting channel {channel}...")
        rc, out, err = run_cmd(f"sudo iwconfig {mon_iface} channel {channel}")
        
        if rc == 0:
            # Verify
            rc2, out2, err2 = run_cmd(f"iwconfig {mon_iface}")
            if f"Channel:{channel}" in out2 or f"Channel {channel}" in out2:
                print(f"✅ Channel {channel} set successfully")
            else:
                print(f"⚠️ Channel {channel} set but not verified")
        else:
            print(f"❌ Failed to set channel {channel}: {err}")
            success = False
    
    return success

if __name__ == "__main__":
    print("🧪 WiFi Monitor Mode Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test monitor mode
    results.append(("Monitor Mode", test_monitor_mode()))
    
    # Test deauth capability  
    results.append(("Deauth Capability", test_deauth_capability()))
    
    # Test channel switching
    results.append(("Channel Switching", test_channel_switching()))
    
    # Summary
    print(f"\n📋 Test Results Summary")
    print("=" * 30)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Monitor mode is working correctly.")
    else:
        print("⚠️ Some tests failed. Check monitor mode configuration.")
    
    print("\nNext steps:")
    print("1. Fix any failed tests")
    print("2. Try attack again") 
    print("3. Check for EAPOL frames in capture")