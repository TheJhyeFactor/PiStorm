#!/bin/bash
# PiStorm Testing Script
# Quick launcher for PiStorm testing interface

echo "🚀 PiStorm Testing Interface Launcher"
echo "====================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

# Check if pistorm_tester.py exists
if [ ! -f "pistorm_tester.py" ]; then
    echo "❌ pistorm_tester.py not found in current directory"
    exit 1
fi

# Install required packages if needed
echo "📦 Checking required packages..."
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ tkinter not available - GUI mode will be disabled"
    GUI_AVAILABLE=false
else
    GUI_AVAILABLE=true
fi

python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing requests module..."
    pip3 install requests
fi

# Show menu
echo ""
echo "Choose testing mode:"
echo "1. 🖥️  GUI Mode (recommended)"
echo "2. 📱 CLI Interactive Mode"
echo "3. ⚡ Quick Health Check"
echo "4. 🧪 Full Test Suite"
echo "5. 🔧 Individual Tests"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        if [ "$GUI_AVAILABLE" = true ]; then
            echo "🖥️ Starting GUI mode..."
            python3 pistorm_tester.py --gui
        else
            echo "❌ GUI not available, falling back to CLI"
            python3 pistorm_tester.py --cli
        fi
        ;;
    2)
        echo "📱 Starting CLI interactive mode..."
        python3 pistorm_tester.py --cli
        ;;
    3)
        echo "⚡ Running quick health check..."
        python3 pistorm_tester.py --test health
        ;;
    4)
        echo "🧪 Running full test suite..."
        python3 pistorm_tester.py --test all
        ;;
    5)
        echo "🔧 Individual test menu..."
        echo ""
        echo "Available individual tests:"
        echo "a) API Connectivity"
        echo "b) Network Scan"
        echo "c) Monitor Mode"
        echo "d) System Health"
        echo ""
        read -p "Select test (a-d): " test_choice
        
        case $test_choice in
            a) python3 pistorm_tester.py --test api ;;
            b) python3 pistorm_tester.py --test scan ;;
            c) python3 pistorm_tester.py --test monitor ;;
            d) python3 pistorm_tester.py --test health ;;
            *) echo "❌ Invalid test option" ;;
        esac
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "✅ Testing complete!"