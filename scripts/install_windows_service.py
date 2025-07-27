#!/usr/bin/env python3
"""
Windows Service Installer for WiFi Crack Listener
This script helps set up the crack listener as a Windows service using NSSM
"""

import os
import sys
import subprocess
from pathlib import Path

def check_admin():
    """Check if running as administrator"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def download_nssm():
    """Download NSSM (Non-Sucking Service Manager) for Windows service management"""
    print("To run the WiFi Crack Listener as a Windows service, you need NSSM.")
    print("Please download NSSM from: https://nssm.cc/download")
    print("Extract nssm.exe to this directory or add it to your PATH")
    print()

def install_service():
    """Install the WiFi Crack Listener as a Windows service using NSSM"""
    if not check_admin():
        print("ERROR: This script must be run as Administrator to install a Windows service")
        print("Right-click Command Prompt and select 'Run as administrator'")
        return False
    
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    listener_script = script_dir / "crack_listener.py"
    
    # Find Python executable
    python_exe = sys.executable
    
    # NSSM commands
    service_name = "WiFiCrackListener"
    
    try:
        # Check if NSSM is available
        subprocess.run(["nssm", "version"], capture_output=True, check=True)
        
        print(f"Installing service: {service_name}")
        
        # Install service
        subprocess.run([
            "nssm", "install", service_name,
            python_exe, str(listener_script)
        ], check=True)
        
        # Set working directory
        subprocess.run([
            "nssm", "set", service_name, "AppDirectory", str(project_dir)
        ], check=True)
        
        # Set service description
        subprocess.run([
            "nssm", "set", service_name, "Description", 
            "WiFi Capture Analysis Listener for distributed processing"
        ], check=True)
        
        # Set service to start automatically
        subprocess.run([
            "nssm", "set", service_name, "Start", "SERVICE_AUTO_START"
        ], check=True)
        
        print(f"✅ Service '{service_name}' installed successfully!")
        print(f"   Service will start automatically on boot")
        print(f"   Python: {python_exe}")
        print(f"   Script: {listener_script}")
        print(f"   Working Dir: {project_dir}")
        print()
        print("To manage the service:")
        print(f"   Start:   nssm start {service_name}")
        print(f"   Stop:    nssm stop {service_name}")
        print(f"   Remove:  nssm remove {service_name} confirm")
        print(f"   Status:  sc query {service_name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install service: {e}")
        return False
    except FileNotFoundError:
        print("ERROR: NSSM not found in PATH")
        download_nssm()
        return False

def main():
    print("=== WiFi Crack Listener - Windows Service Installer ===")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        success = install_service()
        if success:
            print("\n🎉 Installation complete!")
            input("Press Enter to exit...")
        else:
            print("\n❌ Installation failed!")
            input("Press Enter to exit...")
    else:
        print("This script installs the WiFi Crack Listener as a Windows service.")
        print()
        print("Options:")
        print("  python install_windows_service.py install    - Install as Windows service")
        print()
        print("Requirements:")
        print("  1. Run as Administrator")
        print("  2. NSSM (Non-Sucking Service Manager) in PATH")
        print("     Download from: https://nssm.cc/download")
        print()
        print("Manual Alternative:")
        print("  Run scripts\\start_listener.bat to start manually")

if __name__ == "__main__":
    main()