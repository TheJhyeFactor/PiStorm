#!/usr/bin/env python3
"""
WiFi Crack Listener - Windows Version
Monitors for new capture files and processes them using hashcat with GPU acceleration
Designed for distributed processing from Raspberry Pi to Windows PC
"""

import os
import time
import json
import requests
import subprocess
import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Temporary: Disable Pi API for testing
DISABLE_PI_API = True

# Configuration
INCOMING_DIR = Path(__file__).parent.parent / "incoming"
WORDLISTS_DIR = Path(__file__).parent.parent / "wordlists"
RESULTS_DIR = Path(__file__).parent.parent / "results"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Pi configuration
PI_IP = "192.168.0.218"
PI_API_PORT = 5000
PI_API_KEY = "4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f"  # Match your Pi's API key

# Hashcat configuration
HASHCAT_PATH = r"C:\tools\hashcat-6.2.6\hashcat.exe"
WPA_HASH_MODE = 22000  # WPA/WPA2 PMKID/EAPOL mode for hashcat v6+

class CaptureHandler(FileSystemEventHandler):
    def __init__(self):
        self.processed_files = set()
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        if file_path.suffix.lower() in ['.cap', '.pcap', '.hccapx', '.22000']:
            self.process_capture(file_path)
    
    def process_capture(self, file_path):
        """Process a capture file through the complete analysis pipeline"""
        print(f"[INFO] 🔥 GPU Processing capture: {file_path.name}")
        
        # Avoid duplicate processing
        file_hash = self.get_file_hash(file_path)
        if file_hash in self.processed_files:
            print(f"[SKIP] Already processed: {file_path.name}")
            return
        
        self.processed_files.add(file_hash)
        
        try:
            # Notify Pi that GPU processing is starting
            self.notify_pi_gpu_status(file_path.name, "gpu_ready", 0, {
                "step": "File received - Preparing for GPU processing"
            })
            
            # Convert capture to hashcat format if needed
            hashcat_file = self.convert_to_hashcat_format(file_path)
            if not hashcat_file:
                self.notify_pi_gpu_status(file_path.name, "error", 0, {
                    "error": "Failed to convert capture file format"
                })
                return
            
            # Notify Pi that GPU cracking has started
            self.notify_pi_gpu_status(file_path.name, "gpu_cracking", 10, {
                "step": "🚀 RTX 4070 Super GPU cracking started"
            })
            
            # Run hashcat analysis
            result = self.run_hashcat_analysis(hashcat_file, file_path.stem)
            
            # Send final results back to Pi
            if result["status"] == "completed" and result["cracked_passwords"]:
                self.notify_pi_gpu_status(file_path.name, "completed", 100, {
                    "step": f"🎉 GPU cracked {len(result['cracked_passwords'])} password(s)!"
                })
            elif result["status"] == "no_crack":
                self.notify_pi_gpu_status(file_path.name, "completed", 100, {
                    "step": "GPU processing complete - No passwords cracked"
                })
            else:
                self.notify_pi_gpu_status(file_path.name, "error", 0, {
                    "error": "GPU processing failed"
                })
            
            self.send_results_to_pi(file_path.name, result)
            
        except Exception as e:
            error_msg = f"Error processing {file_path.name}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.log_error(error_msg)
            self.notify_pi_gpu_status(file_path.name, "error", 0, {
                "error": error_msg
            })
            self.send_results_to_pi(file_path.name, {"status": "error", "message": error_msg})
    
    def get_file_hash(self, file_path):
        """Generate hash of file for duplicate detection"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def convert_to_hccapx(self, cap_file, hccapx_file):
        """Convert .cap to .hccapx format using multiple fallback tools"""
        # Try multiple conversion tools in order of preference
        # Convert to WSL paths for WSL commands
        wsl_cap_file = cap_file.replace('C:', '/mnt/c').replace('\\', '/')
        wsl_hccapx_file = hccapx_file.replace('C:', '/mnt/c').replace('\\', '/')
        
        tools = [
            f"hcxpcapngtool -o {hccapx_file} {cap_file}",
            f"wsl hcxpcapngtool -o {wsl_hccapx_file} {wsl_cap_file}",  # WSL version
            f"cap2hccapx {cap_file} {hccapx_file}",
            f"aircrack-ng -J {Path(hccapx_file).stem} {cap_file}"  # Fallback
        ]
        
        for cmd in tools:
            try:
                print(f"[INFO] Trying conversion: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                if result.returncode == 0 and Path(hccapx_file).exists():
                    print(f"[SUCCESS] Converted using: {cmd}")
                    return True
                elif result.stderr:
                    print(f"[WARNING] {cmd} failed: {result.stderr.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"[ERROR] {cmd} error: {e}")
                continue
        
        print(f"[ERROR] All conversion tools failed for {cap_file}")
        return False
    
    def convert_to_hashcat_format(self, file_path):
        """Convert capture file to hashcat format - try conversion, fallback to direct"""
        try:
            # For .cap/.pcap files, try conversion first
            if file_path.suffix.lower() in ['.cap', '.pcap']:
                output_file = RESULTS_DIR / f"{file_path.stem}.22000"
                
                # Try WSL hcxtools conversion
                wsl_input = str(file_path).replace('C:', '/mnt/c').replace('\\', '/')
                wsl_output = str(output_file).replace('C:', '/mnt/c').replace('\\', '/')
                
                try:
                    cmd = f"wsl hcxpcapngtool -o {wsl_output} {wsl_input}"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0 and output_file.exists():
                        print(f"[SUCCESS] Converted to hashcat format: {output_file.name}")
                        return output_file
                    else:
                        print(f"[INFO] Conversion failed, will try direct processing")
                        print(f"[DEBUG] Error: {result.stderr}")
                        
                except Exception as e:
                    print(f"[INFO] Conversion error: {e}")
            
            # Direct processing fallback - hashcat can handle many formats directly
            print(f"[INFO] Using direct processing for: {file_path.name}")
            return file_path
            
        except Exception as e:
            print(f"[ERROR] Conversion process failed: {e}")
            return file_path
    
    def run_hashcat_analysis(self, hashcat_file, base_name):
        """Run hashcat analysis with multiple modes and wordlists"""
        results = {
            "status": "completed",
            "file": base_name,
            "timestamp": time.time(),
            "cracked_passwords": [],
            "wordlists_used": [],
            "modes_tried": [],
            "total_time": 0,
            "gpu_info": "RTX 4070 Super"
        }
        
        start_time = time.time()
        
        # Try different hashcat modes for WiFi in order of preference
        wifi_modes = [
            ("22000", "WPA-PBKDF2-PMKID+EAPOL"),  # Modern WPA/WPA2
            ("2500", "WPA/WPA2 Legacy"),           # Legacy WPA/WPA2
            ("22001", "WPA3-SAE"),                 # WPA3
            ("16800", "WPA-PMKID")                 # PMKID only
        ]
        
        # Get available wordlists
        wordlists = self.get_wordlists()
        
        for mode_idx, (mode, mode_desc) in enumerate(wifi_modes):
            print(f"[INFO] 🔍 Trying WiFi mode {mode} ({mode_desc})")
            results["modes_tried"].append(f"{mode} ({mode_desc})")
            
            # Update progress for mode switching
            mode_progress = 10 + int((mode_idx / len(wifi_modes)) * 80)
            self.notify_pi_gpu_status(f"{base_name}.cap", "gpu_cracking", mode_progress, {
                "step": f"Testing mode {mode}: {mode_desc}",
                "mode": mode,
                "mode_description": mode_desc
            })
            
            for wl_idx, wordlist in enumerate(wordlists):
                print(f"[INFO] 🚀 GPU Mode {mode} + Wordlist: {wordlist.name}")
                
                # Calculate combined progress
                total_combinations = len(wifi_modes) * len(wordlists)
                current_combination = mode_idx * len(wordlists) + wl_idx
                progress = 10 + int((current_combination / total_combinations) * 80)
                
                self.notify_pi_gpu_status(f"{base_name}.cap", "gpu_cracking", progress, {
                    "step": f"Mode {mode} + {wordlist.name}",
                    "mode": mode,
                    "wordlist": wordlist.name,
                    "combination": f"{current_combination + 1}/{total_combinations}"
                })
                
                # Create session name for recovery
                session_name = f"{base_name}_{mode}_{wordlist.stem}"
                potfile = RESULTS_DIR / f"{session_name}.pot"
                
                cmd = [
                    HASHCAT_PATH,
                    "-m", mode,
                    "-a", "0",  # Dictionary attack
                    "--potfile-path", str(potfile),
                    "--session", session_name,
                    "--quiet",
                    "--status",
                    "--status-timer", "5",
                    "-O",  # Optimized kernel
                    "-w", "3",  # High workload
                    str(hashcat_file),
                    str(wordlist)
                ]
                
                try:
                    print(f"[INFO] 💻 GPU Command: hashcat -m {mode} -O -w 3 [session: {session_name}]")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                    
                    results["wordlists_used"].append(f"{wordlist.name} (mode {mode})")
                    
                    # Check for successful crack
                    if potfile.exists():
                        cracked = self.parse_potfile(potfile)
                        if cracked:
                            results["cracked_passwords"].extend(cracked)
                            print(f"[SUCCESS] 🎉 GPU cracked {len(cracked)} password(s)!")
                            print(f"[CRACKED] Mode: {mode} ({mode_desc})")
                            print(f"[CRACKED] Wordlist: {wordlist.name}")
                            print(f"[CRACKED] Passwords: {', '.join(cracked)}")
                            
                            # Notify success immediately
                            self.notify_pi_gpu_status(f"{base_name}.cap", "gpu_cracking", 95, {
                                "step": f"🎉 SUCCESS! Mode {mode} cracked: {', '.join(cracked)}",
                                "cracked_passwords": cracked,
                                "successful_mode": f"{mode} ({mode_desc})",
                                "successful_wordlist": wordlist.name
                            })
                            
                            # Success - return immediately
                            results["total_time"] = time.time() - start_time
                            results["successful_mode"] = f"{mode} ({mode_desc})"
                            results["successful_wordlist"] = wordlist.name
                            return results
                    
                    # Check stdout for status messages
                    if "Status...........: Cracked" in result.stdout:
                        print(f"[INFO] Hashcat reports crack, checking potfile...")
                    
                    print(f"[INFO] No passwords found with mode {mode} + {wordlist.name}")
                    
                except subprocess.TimeoutExpired:
                    print(f"[TIMEOUT] ⏰ GPU timeout: mode {mode} + {wordlist.name}")
                    self.notify_pi_gpu_status(f"{base_name}.cap", "gpu_cracking", progress, {
                        "step": f"Timeout: mode {mode} + {wordlist.name}"
                    })
                except FileNotFoundError:
                    print(f"[ERROR] Hashcat not found.")
                    results["status"] = "error"
                    results["message"] = "Hashcat not installed"
                    return results
                except Exception as e:
                    print(f"[ERROR] GPU error: mode {mode} + {wordlist.name}: {str(e)}")
        
        results["total_time"] = time.time() - start_time
        
        if not results["cracked_passwords"]:
            results["status"] = "no_crack"
            print(f"[INFO] 🔍 GPU processing complete - No passwords cracked")
            print(f"[INFO] Tried {len(results['modes_tried'])} modes with {len(wordlists)} wordlists")
        else:
            print(f"[SUCCESS] 🚀 GPU processing complete - {len(results['cracked_passwords'])} passwords cracked!")
        
        return results
    
    def get_wordlists(self):
        """Get ordered list of wordlists to try"""
        wordlists = []
        
        # Priority order: WiFi-specific first, then general
        priority_files = [
            "wifi-wpa-probable.txt",
            "probable-v2-wpa-top306.txt",
            "probable-v2-wpa-top12000.txt",
            "darkweb2017-top10000.txt",
            "rockyou.txt"
        ]
        
        # Add priority wordlists if they exist
        for filename in priority_files:
            file_path = WORDLISTS_DIR / filename
            if file_path.exists() and file_path.stat().st_size > 100:  # Ensure file has content
                wordlists.append(file_path)
        
        # Add any other wordlists found
        for file_path in WORDLISTS_DIR.glob("*.txt"):
            if file_path not in wordlists and file_path.stat().st_size > 100:
                wordlists.append(file_path)
        
        return wordlists
    
    def parse_potfile(self, potfile):
        """Parse hashcat potfile to extract cracked passwords"""
        cracked = []
        try:
            with open(potfile, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        # Format: hash:password
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            cracked.append(parts[1])
        except Exception as e:
            print(f"[ERROR] Failed to parse potfile: {e}")
        
        return cracked
    
    def notify_pi_gpu_status(self, filename, phase, progress=0, additional_data=None):
        """Notify Pi of GPU processing status updates"""
        if DISABLE_PI_API:
            print(f"[TEST] GPU Status: {phase} ({progress}%) - {filename}")
            return
        try:
            url = f"http://{PI_IP}:{PI_API_PORT}/api/gpu_status"
            headers = {
                "Authorization": f"Bearer {PI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "filename": filename,
                "phase": phase,  # gpu_ready, gpu_cracking, completed, error
                "progress": progress,
                "gpu_info": "RTX 4070 Super",
                "processor": "windows-pc",
                "timestamp": time.time()
            }
            
            if additional_data:
                data.update(additional_data)
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"[SUCCESS] GPU status '{phase}' sent to Pi for {filename}")
            else:
                print(f"[ERROR] Failed to send GPU status to Pi: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Network error sending GPU status to Pi: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to send GPU status to Pi: {e}")

    def send_results_to_pi(self, filename, results):
        """Send analysis results back to Pi via API"""
        if DISABLE_PI_API:
            print(f"[TEST] Results: {results['status']} - {filename}")
            if results.get('cracked_passwords'):
                print(f"[TEST] Cracked: {', '.join(results['cracked_passwords'])}")
            return
        try:
            url = f"http://{PI_IP}:{PI_API_PORT}/api/crack_result"
            headers = {
                "Authorization": f"Bearer {PI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "filename": filename,
                "results": results,
                "processor": "windows-pc",
                "gpu_info": "RTX 4070 Super",
                "timestamp": time.time()
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"[SUCCESS] Results sent to Pi for {filename}")
            else:
                print(f"[ERROR] Failed to send results to Pi: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Network error sending results to Pi: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to send results to Pi: {e}")
    
    def log_error(self, message):
        """Log error to file"""
        log_file = LOGS_DIR / f"crack_errors_{time.strftime('%Y%m%d')}.log"
        try:
            with open(log_file, 'a') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass  # Don't fail on logging errors

def main():
    """Main function to start the file watcher"""
    print("=== 🚀 WiFi Crack GPU Listener - Windows PC ===")
    print(f"🔥 GPU: RTX 4070 Super Ready for Distributed Processing")
    print(f"📁 Monitoring: {INCOMING_DIR}")
    print(f"📚 Wordlists: {WORDLISTS_DIR}")
    print(f"📊 Results: {RESULTS_DIR}")
    print(f"🌐 Pi API: {PI_IP}:{PI_API_PORT}")
    print(f"🔑 Authenticated: API Key configured")
    print("=" * 50)
    
    # Ensure directories exist
    for directory in [INCOMING_DIR, WORDLISTS_DIR, RESULTS_DIR, LOGS_DIR]:
        directory.mkdir(exist_ok=True)
    
    # Check for required tools
    tools_ok = True
    
    try:
        subprocess.run([HASHCAT_PATH, "--version"], capture_output=True, timeout=5)
        print("[OK] Hashcat found")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[WARNING] Hashcat not found in PATH")
        tools_ok = False
    
    # Check for hcxtools in multiple locations
    hcx_found = False
    hcx_paths = [
        "hcxpcapngtool",
        "wsl hcxpcapngtool"
    ]
    
    for hcx_path in hcx_paths:
        try:
            if "wsl" in hcx_path:
                result = subprocess.run("wsl hcxpcapngtool --version", shell=True, capture_output=True, timeout=10)
            else:
                result = subprocess.run([hcx_path, "--version"], capture_output=True, timeout=5)
            
            if result.returncode == 0:
                print(f"[OK] hcxtools found: {hcx_path}")
                hcx_found = True
                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    if not hcx_found:
        print("[WARNING] hcxpcapngtool not found - .cap conversion will use fallback methods")
    
    # Check wordlists
    wordlists = list(WORDLISTS_DIR.glob("*.txt"))
    valid_wordlists = [w for w in wordlists if w.stat().st_size > 100]
    print(f"[INFO] Found {len(valid_wordlists)} valid wordlists")
    
    if not valid_wordlists:
        print("[WARNING] No valid wordlists found")
    
    # Start file watcher
    event_handler = CaptureHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
    
    try:
        observer.start()
        print(f"[INFO] Started monitoring {INCOMING_DIR}")
        print("[INFO] Waiting for capture files... (Ctrl+C to stop)")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[INFO] Stopping listener...")
        observer.stop()
    
    observer.join()
    print("[INFO] Listener stopped")

if __name__ == "__main__":
    main()