#!/usr/bin/env python3
"""
PiStorm Function Tester
Interactive CLI/GUI tool for testing PiStorm functions before Wio Terminal deployment
"""

import os
import sys
import time
import json
import requests
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# Try to import GUI libraries (optional)
GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    GUI_AVAILABLE = True
except ImportError:
    print("GUI libraries not available, CLI mode only")

class PiStormTester:
    def __init__(self):
        self.pi_ip = "192.168.0.218"
        self.pi_port = 5000
        self.api_key = "4c273a289160db43476e823cfedc262578a7b96407c4728f4ecb24aad86c776f"
        self.base_url = f"http://{self.pi_ip}:{self.pi_port}"
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        
        # Test results storage
        self.test_results = {}
        self.logs = []
    
    def log(self, message, level="INFO"):
        """Add log entry with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(log_entry)
        print(log_entry)
    
    def api_request(self, endpoint, method="GET", data=None, timeout=10):
        """Make API request with error handling"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                "response_time": response.elapsed.total_seconds()
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection failed - is Pi API running?"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_api_connectivity(self):
        """Test basic API connectivity"""
        self.log("Testing API connectivity...")
        result = self.api_request("/ping")
        
        if result["success"]:
            self.log(f"✅ API connected ({result['response_time']:.2f}s)")
            return True
        else:
            self.log(f"❌ API connection failed: {result['error']}")
            return False
    
    def test_network_scan(self):
        """Test WiFi network scanning"""
        self.log("Testing network scan...")
        result = self.api_request("/scan", timeout=30)
        
        if result["success"] and result["status_code"] == 200:
            networks = result["data"].get("networks", [])
            self.log(f"✅ Scan completed - found {len(networks)} networks")
            
            # Show top 3 networks
            for i, network in enumerate(networks[:3]):
                signal = network.get('signal', 'Unknown')
                channel = network.get('channel', 'Unknown')
                encryption = network.get('encryption', 'Unknown')
                self.log(f"  {i+1}. {network['ssid']} (Signal: {signal}, Ch: {channel}, Enc: {encryption})")
            
            return True, networks
        else:
            self.log(f"❌ Scan failed: {result.get('error', 'Unknown error')}")
            return False, []
    
    def test_monitor_mode(self):
        """Test monitor mode capability"""
        self.log("Testing monitor mode...")
        result = self.api_request("/test_monitor", timeout=20)
        
        if result["success"] and result["status_code"] == 200:
            test_data = result["data"]
            monitor_ok = test_data.get("monitor_mode_ok", False)
            packet_count = test_data.get("packets_captured", 0)
            
            if monitor_ok and packet_count > 0:
                self.log(f"✅ Monitor mode working - captured {packet_count} packets")
                return True
            else:
                self.log(f"❌ Monitor mode issues - packets: {packet_count}")
                return False
        else:
            self.log(f"❌ Monitor test failed: {result.get('error', 'Unknown error')}")
            return False
    
    def test_target_attack(self, target_ssid=None):
        """Test handshake capture on a target"""
        if not target_ssid:
            self.log("❌ No target SSID provided for attack test")
            return False
        
        self.log(f"Testing handshake capture on: {target_ssid}")
        
        attack_data = {
            "ssid": target_ssid,
            "test_mode": True,  # Don't actually deauth in test mode
            "capture_time": 10   # Short capture for testing
        }
        
        result = self.api_request("/attack", method="POST", data=attack_data, timeout=60)
        
        if result["success"] and result["status_code"] == 200:
            attack_result = result["data"]
            handshake_captured = attack_result.get("handshake_captured", False)
            filename = attack_result.get("filename", "")
            
            if handshake_captured:
                self.log(f"✅ Handshake captured: {filename}")
                return True, filename
            else:
                self.log(f"⚠️ No handshake captured (normal in test mode)")
                return False, filename
        else:
            self.log(f"❌ Attack test failed: {result.get('error', 'Unknown error')}")
            return False, ""
    
    def test_gpu_transfer(self, test_file=None):
        """Test GPU transfer functionality"""
        if not test_file:
            self.log("⚠️ No test file provided for GPU transfer test")
            return False
        
        self.log(f"Testing GPU transfer: {test_file}")
        
        transfer_data = {"filename": test_file}
        result = self.api_request("/transfer_to_gpu", method="POST", data=transfer_data, timeout=30)
        
        if result["success"] and result["status_code"] == 200:
            transfer_result = result["data"]
            success = transfer_result.get("success", False)
            
            if success:
                self.log("✅ GPU transfer initiated successfully")
                return True
            else:
                self.log(f"❌ GPU transfer failed: {transfer_result.get('error', 'Unknown')}")
                return False
        else:
            self.log(f"❌ GPU transfer request failed: {result.get('error', 'Unknown error')}")
            return False
    
    def test_status_display(self):
        """Test status display for Wio Terminal"""
        self.log("Testing status display format...")
        result = self.api_request("/status")
        
        if result["success"] and result["status_code"] == 200:
            status_data = result["data"]
            
            # Check if status format is compatible with Wio Terminal
            required_fields = ["current_task", "networks_found", "targets_found", "gpu_status"]
            missing_fields = [field for field in required_fields if field not in status_data]
            
            if not missing_fields:
                self.log("✅ Status format compatible with Wio Terminal")
                self.log(f"  Task: {status_data.get('current_task', 'Unknown')}")
                self.log(f"  Networks: {status_data.get('networks_found', 0)}")
                self.log(f"  Targets: {status_data.get('targets_found', 0)}")
                self.log(f"  GPU: {status_data.get('gpu_status', 'Unknown')}")
                return True
            else:
                self.log(f"❌ Missing Wio Terminal fields: {missing_fields}")
                return False
        else:
            self.log(f"❌ Status request failed: {result.get('error', 'Unknown error')}")
            return False
    
    def test_system_health(self):
        """Test overall system health"""
        self.log("Testing system health...")
        result = self.api_request("/health")
        
        if result["success"] and result["status_code"] == 200:
            health_data = result["data"]
            cpu_ok = health_data.get("cpu_usage", 100) < 80
            memory_ok = health_data.get("memory_usage", 100) < 80
            disk_ok = health_data.get("disk_usage", 100) < 90
            temp_ok = health_data.get("temperature", 100) < 70
            
            issues = []
            if not cpu_ok: issues.append("High CPU")
            if not memory_ok: issues.append("High Memory")
            if not disk_ok: issues.append("Low Disk")
            if not temp_ok: issues.append("High Temperature")
            
            if not issues:
                self.log("✅ System health good")
                return True
            else:
                self.log(f"⚠️ System issues: {', '.join(issues)}")
                return False
        else:
            self.log(f"❌ Health check failed: {result.get('error', 'Unknown error')}")
            return False
    
    def run_full_test_suite(self):
        """Run complete test suite"""
        self.log("🚀 Starting PiStorm Full Test Suite")
        self.log("=" * 50)
        
        tests = [
            ("API Connectivity", self.test_api_connectivity),
            ("System Health", self.test_system_health),
            ("Network Scan", self.test_network_scan),
            ("Monitor Mode", self.test_monitor_mode),
            ("Status Display", self.test_status_display),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            self.log(f"\n📋 Running: {test_name}")
            try:
                if test_name == "Network Scan":
                    success, networks = test_func()
                    results[test_name] = success
                    if success and networks:
                        # Optionally test attack on first network
                        self.log("\n🎯 Testing attack capability...")
                        target = networks[0]["ssid"]
                        attack_result, _ = self.test_target_attack(target)
                        results["Attack Test"] = attack_result
                else:
                    results[test_name] = test_func()
            except Exception as e:
                self.log(f"❌ Test {test_name} crashed: {e}")
                results[test_name] = False
        
        # Summary
        self.log("\n" + "=" * 50)
        self.log("📊 TEST RESULTS SUMMARY")
        self.log("=" * 50)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} {test_name}")
        
        self.log(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 All tests passed! Ready for Wio Terminal deployment!")
        else:
            self.log("⚠️ Some tests failed. Fix issues before Wio deployment.")
        
        return results

class PiStormGUI:
    def __init__(self):
        if not GUI_AVAILABLE:
            raise ImportError("GUI libraries not available")
        
        self.tester = PiStormTester()
        self.root = tk.Tk()
        self.root.title("PiStorm Function Tester")
        self.root.geometry("800x600")
        
        self.setup_gui()
    
    def setup_gui(self):
        """Setup GUI layout"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Test Suite Tab
        test_frame = ttk.Frame(notebook)
        notebook.add(test_frame, text="Test Suite")
        
        # Individual Tests Tab
        individual_frame = ttk.Frame(notebook)
        notebook.add(individual_frame, text="Individual Tests")
        
        # Logs Tab
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="Logs")
        
        self.setup_test_suite_tab(test_frame)
        self.setup_individual_tests_tab(individual_frame)
        self.setup_logs_tab(logs_frame)
    
    def setup_test_suite_tab(self, parent):
        """Setup test suite tab"""
        # Configuration
        config_frame = ttk.LabelFrame(parent, text="Configuration")
        config_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(config_frame, text="Pi IP:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.pi_ip_var = tk.StringVar(value=self.tester.pi_ip)
        ttk.Entry(config_frame, textvariable=self.pi_ip_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Port:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.pi_port_var = tk.StringVar(value=str(self.tester.pi_port))
        ttk.Entry(config_frame, textvariable=self.pi_port_var, width=8).grid(row=0, column=3, padx=5, pady=5)
        
        # Test Controls
        control_frame = ttk.LabelFrame(parent, text="Test Controls")
        control_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(control_frame, text="🚀 Run Full Test Suite", 
                  command=self.run_full_suite).pack(side="left", padx=5, pady=5)
        ttk.Button(control_frame, text="🔄 Quick Health Check", 
                  command=self.quick_health_check).pack(side="left", padx=5, pady=5)
        ttk.Button(control_frame, text="🧹 Clear Logs", 
                  command=self.clear_logs).pack(side="left", padx=5, pady=5)
        
        # Results Display
        results_frame = ttk.LabelFrame(parent, text="Test Results")
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.results_tree = ttk.Treeview(results_frame, columns=("Status", "Details"), show="tree headings")
        self.results_tree.heading("#0", text="Test")
        self.results_tree.heading("Status", text="Status")
        self.results_tree.heading("Details", text="Details")
        self.results_tree.pack(fill="both", expand=True, padx=5, pady=5)
    
    def setup_individual_tests_tab(self, parent):
        """Setup individual tests tab"""
        # Individual test buttons
        tests = [
            ("🔗 Test API Connection", self.test_api_connection),
            ("📡 Test Network Scan", self.test_network_scan),
            ("📺 Test Monitor Mode", self.test_monitor_mode),
            ("💻 Test GPU Transfer", self.test_gpu_transfer),
            ("📊 Test Status Display", self.test_status_display),
            ("❤️ Test System Health", self.test_system_health),
        ]
        
        for i, (text, command) in enumerate(tests):
            row = i // 2
            col = i % 2
            ttk.Button(parent, text=text, command=command, width=25).grid(
                row=row, column=col, padx=10, pady=10, sticky="ew")
        
        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
    
    def setup_logs_tab(self, parent):
        """Setup logs tab"""
        self.log_text = scrolledtext.ScrolledText(parent, height=30)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def update_config(self):
        """Update tester configuration from GUI"""
        self.tester.pi_ip = self.pi_ip_var.get()
        self.tester.pi_port = int(self.pi_port_var.get())
        self.tester.base_url = f"http://{self.tester.pi_ip}:{self.tester.pi_port}"
    
    def log_to_gui(self, message):
        """Add log message to GUI"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def run_full_suite(self):
        """Run full test suite with GUI updates"""
        self.update_config()
        self.clear_logs()
        
        # Override tester log method to update GUI
        original_log = self.tester.log
        self.tester.log = lambda msg, level="INFO": (original_log(msg, level), self.log_to_gui(f"[{level}] {msg}"))
        
        try:
            results = self.tester.run_full_test_suite()
            self.update_results_tree(results)
        except Exception as e:
            messagebox.showerror("Error", f"Test suite failed: {e}")
        
        # Restore original log method
        self.tester.log = original_log
    
    def quick_health_check(self):
        """Quick health check"""
        self.update_config()
        self.log_to_gui("Running quick health check...")
        
        if self.tester.test_api_connectivity() and self.tester.test_system_health():
            messagebox.showinfo("Health Check", "✅ System healthy!")
        else:
            messagebox.showwarning("Health Check", "⚠️ System issues detected!")
    
    def clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
        self.tester.logs.clear()
    
    def update_results_tree(self, results):
        """Update results tree with test results"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.results_tree.insert("", "end", text=test_name, values=(status, ""))
    
    # Individual test wrapper methods
    def test_api_connection(self):
        self.update_config()
        self.log_to_gui("Testing API connection...")
        result = self.tester.test_api_connectivity()
        messagebox.showinfo("API Test", "✅ Connected!" if result else "❌ Failed!")
    
    def test_network_scan(self):
        self.update_config()
        self.log_to_gui("Testing network scan...")
        result, networks = self.tester.test_network_scan()
        msg = f"✅ Found {len(networks)} networks!" if result else "❌ Scan failed!"
        messagebox.showinfo("Scan Test", msg)
    
    def test_monitor_mode(self):
        self.update_config()
        self.log_to_gui("Testing monitor mode...")
        result = self.tester.test_monitor_mode()
        messagebox.showinfo("Monitor Test", "✅ Working!" if result else "❌ Failed!")
    
    def test_gpu_transfer(self):
        self.update_config()
        filename = tk.simpledialog.askstring("GPU Test", "Enter test filename:")
        if filename:
            result = self.tester.test_gpu_transfer(filename)
            messagebox.showinfo("GPU Test", "✅ Transfer initiated!" if result else "❌ Failed!")
    
    def test_status_display(self):
        self.update_config()
        self.log_to_gui("Testing status display...")
        result = self.tester.test_status_display()
        messagebox.showinfo("Status Test", "✅ Compatible!" if result else "❌ Issues found!")
    
    def test_system_health(self):
        self.update_config()
        self.log_to_gui("Testing system health...")
        result = self.tester.test_system_health()
        messagebox.showinfo("Health Test", "✅ Healthy!" if result else "⚠️ Issues detected!")
    
    def run(self):
        """Start GUI"""
        self.root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="PiStorm Function Tester")
    parser.add_argument("--gui", action="store_true", help="Run GUI version")
    parser.add_argument("--cli", action="store_true", help="Run CLI version")
    parser.add_argument("--test", choices=["all", "api", "scan", "monitor", "health"], 
                       help="Run specific test")
    parser.add_argument("--ip", default="192.168.0.218", help="Pi IP address")
    parser.add_argument("--port", type=int, default=5000, help="Pi port")
    
    args = parser.parse_args()
    
    # Auto-detect mode if not specified
    if not args.gui and not args.cli:
        if GUI_AVAILABLE:
            args.gui = True
        else:
            args.cli = True
    
    if args.gui and GUI_AVAILABLE:
        # Run GUI version
        try:
            app = PiStormGUI()
            app.run()
        except Exception as e:
            print(f"GUI failed: {e}")
            print("Falling back to CLI mode...")
            args.cli = True
            args.gui = False
    
    if args.cli or not GUI_AVAILABLE:
        # Run CLI version
        tester = PiStormTester()
        tester.pi_ip = args.ip
        tester.pi_port = args.port
        tester.base_url = f"http://{tester.pi_ip}:{tester.pi_port}"
        
        if args.test == "all":
            tester.run_full_test_suite()
        elif args.test == "api":
            tester.test_api_connectivity()
        elif args.test == "scan":
            tester.test_network_scan()
        elif args.test == "monitor":
            tester.test_monitor_mode()
        elif args.test == "health":
            tester.test_system_health()
        else:
            # Interactive CLI mode
            cli_menu(tester)

def cli_menu(tester):
    """Interactive CLI menu"""
    while True:
        print("\n" + "="*50)
        print("🚀 PiStorm Function Tester")
        print("="*50)
        print("1. 🔗 Test API Connection")
        print("2. 📡 Test Network Scan")
        print("3. 📺 Test Monitor Mode")
        print("4. 🎯 Test Target Attack")
        print("5. 💻 Test GPU Transfer")
        print("6. 📊 Test Status Display")
        print("7. ❤️ Test System Health")
        print("8. 🚀 Run Full Test Suite")
        print("9. 📋 View Recent Logs")
        print("0. 🚪 Exit")
        print("="*50)
        
        choice = input("Select option (0-9): ").strip()
        
        if choice == "1":
            tester.test_api_connectivity()
        elif choice == "2":
            tester.test_network_scan()
        elif choice == "3":
            tester.test_monitor_mode()
        elif choice == "4":
            ssid = input("Enter target SSID: ").strip()
            if ssid:
                tester.test_target_attack(ssid)
        elif choice == "5":
            filename = input("Enter test filename: ").strip()
            if filename:
                tester.test_gpu_transfer(filename)
        elif choice == "6":
            tester.test_status_display()
        elif choice == "7":
            tester.test_system_health()
        elif choice == "8":
            tester.run_full_test_suite()
        elif choice == "9":
            print("\n📋 Recent Logs:")
            for log in tester.logs[-10:]:
                print(log)
        elif choice == "0":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option!")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()