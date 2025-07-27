#!/usr/bin/env python3
"""
Capture File Analysis Tool
Analyzes .cap files for handshakes, encryption type, and packet details
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def analyze_cap_file(cap_file):
    """Analyze a capture file for handshakes and encryption details"""
    print(f"\n🔍 Analyzing: {cap_file}")
    print("=" * 50)
    
    if not os.path.exists(cap_file):
        print(f"❌ File not found: {cap_file}")
        return
    
    # File size
    size = os.path.getsize(cap_file)
    print(f"📏 File size: {size} bytes")
    
    if size < 100:
        print("⚠️  File too small - likely no packets captured")
        return
    
    # Use tshark to analyze packets
    analyze_with_tshark(cap_file)
    
    # Check for handshakes with aircrack-ng
    check_handshake_aircrack(cap_file)
    
    # Check encryption type
    check_encryption_type(cap_file)

def analyze_with_tshark(cap_file):
    """Use tshark to analyze packet details"""
    print("\n📡 Packet Analysis (tshark):")
    
    # Check if tshark is available
    try:
        subprocess.run(["tshark", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ tshark not available - install with: sudo apt install tshark")
        return
    
    # Count packets by type
    try:
        # Total packets
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-q", "-z", "io,stat,0"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'frames' in line.lower():
                    print(f"📊 {line.strip()}")
        
        # 802.11 management frames
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "wlan.fc.type==0", "-q"],
            capture_output=True, text=True, timeout=10
        )
        mgmt_count = len([l for l in result.stdout.split('\n') if l.strip()])
        print(f"📋 Management frames: {mgmt_count}")
        
        # Deauth frames
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "wlan.fc.type_subtype==12", "-q"],
            capture_output=True, text=True, timeout=10
        )
        deauth_count = len([l for l in result.stdout.split('\n') if l.strip()])
        print(f"🚫 Deauth frames: {deauth_count}")
        
        # EAPOL frames (handshake)
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "eapol", "-q"],
            capture_output=True, text=True, timeout=10
        )
        eapol_count = len([l for l in result.stdout.split('\n') if l.strip()])
        print(f"🔐 EAPOL frames: {eapol_count}")
        
    except Exception as e:
        print(f"❌ tshark analysis failed: {e}")

def check_handshake_aircrack(cap_file):
    """Check for handshakes using aircrack-ng"""
    print("\n🔓 Handshake Check (aircrack-ng):")
    
    try:
        result = subprocess.run(
            ["aircrack-ng", cap_file],
            capture_output=True, text=True, timeout=15
        )
        
        output = result.stdout
        
        if "handshake" in output.lower():
            print("✅ Handshake detected!")
            # Extract handshake details
            for line in output.split('\n'):
                if 'handshake' in line.lower() or 'BSSID' in line:
                    print(f"   {line.strip()}")
        else:
            print("❌ No handshake found")
            
        # Show any networks found
        if "BSSID" in output:
            print("\n📡 Networks in capture:")
            in_network_section = False
            for line in output.split('\n'):
                if "BSSID" in line and "ESSID" in line:
                    in_network_section = True
                    print(f"   {line.strip()}")
                elif in_network_section and line.strip() and not line.startswith(' '):
                    if line.strip().replace('-', '').replace(' ', ''):
                        print(f"   {line.strip()}")
                    
    except Exception as e:
        print(f"❌ aircrack-ng analysis failed: {e}")

def check_encryption_type(cap_file):
    """Determine encryption type (WPA/WPA2/WPA3)"""
    print("\n🔒 Encryption Analysis:")
    
    try:
        # Use tshark to check for specific encryption indicators
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "wlan.rsn.version", "-T", "fields", "-e", "wlan.rsn.version"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            versions = set(result.stdout.strip().split('\n'))
            for version in versions:
                if version == "1":
                    print("🔒 WPA2 (RSN version 1) detected")
                elif version == "2":
                    print("🔒 WPA3 (RSN version 2) detected")
        
        # Check for WPA3-specific features
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "wlan.rsn.akms.type==8", "-q"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            print("🔒 WPA3-SAE detected")
        
        # Check for legacy WPA
        result = subprocess.run(
            ["tshark", "-r", cap_file, "-Y", "wlan.wpa.version", "-q"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            print("🔒 Legacy WPA detected")
            
    except Exception as e:
        print(f"❌ Encryption analysis failed: {e}")

def find_capture_files():
    """Find all capture files"""
    capture_dirs = [
        "/home/jhye/captures",
        "/home/pi/captures", 
        "/tmp",
        "."
    ]
    
    cap_files = []
    for cap_dir in capture_dirs:
        if os.path.exists(cap_dir):
            for ext in ['*.cap', '*.pcap']:
                cap_files.extend(Path(cap_dir).glob(ext))
    
    return sorted(cap_files, key=lambda x: x.stat().st_mtime, reverse=True)

if __name__ == "__main__":
    print("🔍 WiFi Capture Analysis Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # Analyze specific file
        analyze_cap_file(sys.argv[1])
    else:
        # Find and analyze recent captures
        cap_files = find_capture_files()
        
        if not cap_files:
            print("❌ No capture files found")
            print("Looking in: /home/jhye/captures, /home/pi/captures, /tmp")
        else:
            print(f"📁 Found {len(cap_files)} capture files:")
            for i, cap_file in enumerate(cap_files[:5]):  # Show last 5
                print(f"{i+1}. {cap_file}")
            
            # Analyze most recent
            if cap_files:
                print(f"\n🔍 Analyzing most recent: {cap_files[0]}")
                analyze_cap_file(str(cap_files[0]))