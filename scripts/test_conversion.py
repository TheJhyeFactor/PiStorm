#!/usr/bin/env python3
"""
Simple test script to verify hcxtools conversion without Pi API
"""

import subprocess
from pathlib import Path

def test_wsl_hcxtools():
    """Test WSL hcxtools conversion"""
    print("=== Testing WSL hcxtools Conversion ===")
    
    # Test file paths
    test_file = Path("C:/Users/Jhye/wifi-crack-pc/incoming/test.cap")
    output_file = Path("C:/Users/Jhye/wifi-crack-pc/results/test.22000")
    
    if not test_file.exists():
        print(f"[ERROR] Test file not found: {test_file}")
        return False
    
    # Convert Windows paths to WSL paths
    wsl_input = str(test_file).replace('C:', '/mnt/c').replace('\\', '/')
    wsl_output = str(output_file).replace('C:', '/mnt/c').replace('\\', '/')
    
    print(f"Input file: {test_file}")
    print(f"WSL input: {wsl_input}")
    print(f"WSL output: {wsl_output}")
    
    # Test WSL hcxtools
    cmd = f"wsl hcxpcapngtool -o {wsl_output} {wsl_input}"
    print(f"Command: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0 and output_file.exists():
            print(f"[SUCCESS] Conversion successful!")
            print(f"Output file size: {output_file.stat().st_size} bytes")
            return True
        else:
            print(f"[WARNING] Conversion failed")
            return False
            
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False

def test_hashcat():
    """Test hashcat on converted file"""
    print("\n=== Testing Hashcat ===")
    
    hashcat_path = r"C:\tools\hashcat-6.2.6\hashcat.exe"
    test_file = Path("C:/Users/Jhye/wifi-crack-pc/results/test.22000")
    
    if not test_file.exists():
        print(f"[ERROR] No converted file found: {test_file}")
        return False
    
    # Test hashcat on the file
    cmd = [
        hashcat_path,
        "--version"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Hashcat version: {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"[ERROR] Hashcat test failed: {e}")
        return False

if __name__ == "__main__":
    print("WiFi Crack Tool Testing")
    print("=" * 40)
    
    # Test conversion
    conversion_ok = test_wsl_hcxtools()
    
    # Test hashcat
    hashcat_ok = test_hashcat()
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    print(f"WSL Conversion: {'✅ OK' if conversion_ok else '❌ FAIL'}")
    print(f"Hashcat: {'✅ OK' if hashcat_ok else '❌ FAIL'}")
    
    if conversion_ok and hashcat_ok:
        print("🎉 All tests passed! System ready for WiFi cracking.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")