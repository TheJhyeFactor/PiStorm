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
    """Test monitor mode functionality"""
    print("🔍 Testing Monitor Mode Functionality")
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
    
    # 2. Check current mode
    print(f"🔧 Checking current mode...")
    rc, out, err = run_cmd(f"iwconfig {mon_iface}")
    if "Mode:Monitor" in out:
        print(f"✅ Already in monitor mode")
    else:
        print(f"⚠️ Not in monitor mode. Current: {out}")
        
        # Set to monitor mode
        print(f"🔧 Setting to monitor mode...")
        run_cmd(f"sudo ip link set {mon_iface} down")
        run_cmd(f"sudo iw dev {mon_iface} set type monitor")
        run_cmd(f"sudo ip link set {mon_iface} up")
        
        # Verify
        rc, out, err = run_cmd(f"iwconfig {mon_iface}")
        if "Mode:Monitor" in out:
            print(f"✅ Successfully set to monitor mode")
        else:
            print(f"❌ Failed to set monitor mode!")
            return False
    
    # 3. Test packet capture
    print(f"📦 Testing packet capture (15 seconds on channel 6)...")
    
    # Set to a common channel first
    print(f"🔧 Setting to channel 6...")
    run_cmd(f"sudo iwconfig {mon_iface} channel 6")
    time.sleep(2)
    
    # Start airodump for 15 seconds
    cmd = f"timeout 15 sudo airodump-ng -w /tmp/monitor_test --output-format pcap --channel 6 {mon_iface}"
    print(f"Running: {cmd}")
    
    rc, out, err = run_cmd(cmd, timeout=20)
    
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