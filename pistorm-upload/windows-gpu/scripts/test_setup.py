#!/usr/bin/env python3
"""
Test script to verify the WiFi crack setup
Tests hashcat installation, GPU detection, and wordlists
"""

import subprocess
import sys
from pathlib import Path

def test_hashcat():
    """Test hashcat installation and GPU detection"""
    print("=== Testing Hashcat Installation ===")
    
    # Try different hashcat paths
    hashcat_paths = [
        r"C:\tools\hashcat-6.2.6\hashcat.exe",
        "hashcat",
        "C:\\ProgramData\\chocolatey\\bin\\hashcat.bat"
    ]
    
    for path in hashcat_paths:
        try:
            result = subprocess.run([path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[OK] Hashcat found at: {path}")
                print(f"   Version: {result.stdout.strip()}")
                
                # Test GPU detection
                gpu_result = subprocess.run([path, "-I"], 
                                          capture_output=True, text=True, timeout=10)
                if "NVIDIA" in gpu_result.stdout:
                    print("[OK] NVIDIA GPU detected for acceleration")
                    print("   GPU Info:")
                    for line in gpu_result.stdout.split('\n'):
                        if 'NVIDIA' in line or 'GeForce' in line:
                            print(f"   {line.strip()}")
                else:
                    print("[WARN] GPU not detected - will use CPU only")
                
                return path
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            continue
    
    print("[ERROR] Hashcat not found in any expected location")
    return None

def test_wordlists():
    """Test available wordlists"""
    print("\n=== Testing Wordlists ===")
    
    wordlists_dir = Path(__file__).parent.parent / "wordlists"
    wordlists = list(wordlists_dir.glob("*.txt"))
    
    valid_wordlists = []
    for wordlist in wordlists:
        size = wordlist.stat().st_size
        if size > 100:  # More than 100 bytes
            valid_wordlists.append((wordlist.name, size))
            print(f"[OK] {wordlist.name} - {size:,} bytes")
        else:
            print(f"[SKIP] {wordlist.name} - {size} bytes (too small)")
    
    print(f"\nTotal valid wordlists: {len(valid_wordlists)}")
    return valid_wordlists

def test_network():
    """Test network connectivity to Pi"""
    print("\n=== Testing Network Connectivity ===")
    
    try:
        result = subprocess.run(["ping", "-n", "2", "192.168.0.218"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("[OK] Pi reachable at 192.168.0.218")
            return True
        else:
            print("[ERROR] Cannot reach Pi at 192.168.0.218")
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] Network test timeout")
        return False

def test_directories():
    """Test project directory structure"""
    print("\n=== Testing Directory Structure ===")
    
    base_dir = Path(__file__).parent.parent
    required_dirs = ["incoming", "wordlists", "results", "logs", "scripts"]
    
    all_good = True
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"[OK] {dir_name}/ directory exists")
        else:
            print(f"[ERROR] {dir_name}/ directory missing")
            all_good = False
    
    return all_good

def run_benchmark(hashcat_path):
    """Run a quick hashcat benchmark"""
    print("\n=== Running GPU Benchmark ===")
    
    try:
        print("Running hashcat benchmark for WPA/WPA2 (mode 22000)...")
        result = subprocess.run([
            hashcat_path, "-b", "-m", "22000"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Parse benchmark results
            for line in result.stdout.split('\n'):
                if 'H/s' in line and '22000' in line:
                    print(f"[OK] WPA/WPA2 Performance: {line.strip()}")
                    return True
            print("[WARN] Benchmark completed but no performance data found")
        else:
            print(f"[ERROR] Benchmark failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("[ERROR] Benchmark timeout (may still be running)")
    except Exception as e:
        print(f"[ERROR] Benchmark error: {e}")
    
    return False

def main():
    """Run all tests"""
    print("WiFi Crack PC - Setup Verification")
    print("=" * 50)
    
    # Test components
    hashcat_path = test_hashcat()
    wordlists = test_wordlists()
    network_ok = test_network()
    dirs_ok = test_directories()
    
    # Summary
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    if hashcat_path:
        print("[OK] Hashcat: READY")
        if input("\nRun GPU benchmark? (y/N): ").lower() == 'y':
            run_benchmark(hashcat_path)
    else:
        print("[ERROR] Hashcat: NOT FOUND")
        print("   Install with: choco install hashcat")
    
    if len(wordlists) > 0:
        print(f"[OK] Wordlists: {len(wordlists)} available")
    else:
        print("[ERROR] Wordlists: NONE VALID")
    
    if network_ok:
        print("[OK] Network: Pi reachable")
    else:
        print("[ERROR] Network: Cannot reach Pi")
    
    if dirs_ok:
        print("[OK] Directories: All present")
    else:
        print("[ERROR] Directories: Some missing")
    
    # Next steps
    print("\nNEXT STEPS:")
    if hashcat_path and len(wordlists) > 0 and network_ok and dirs_ok:
        print("   System ready! You can:")
        print("   1. Copy SSH key to Pi")
        print("   2. Start listener: python scripts\\crack_listener.py")
        print("   3. Or install as service with scripts\\install_windows_service.py")
    else:
        print("   Fix the issues above before proceeding")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()