@echo off
REM PiStorm Testing Interface Launcher for Windows

echo 🚀 PiStorm Testing Interface Launcher
echo =====================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found - please install Python 3.8+
    pause
    exit /b 1
)

REM Check if pistorm_tester.py exists
if not exist "pistorm_tester.py" (
    echo ❌ pistorm_tester.py not found in current directory
    pause
    exit /b 1
)

REM Install required packages if needed
echo 📦 Checking required packages...
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing requests module...
    pip install requests
)

REM Show menu
echo.
echo Choose testing mode:
echo 1. 🖥️  GUI Mode (recommended)
echo 2. 📱 CLI Interactive Mode
echo 3. ⚡ Quick Health Check
echo 4. 🧪 Full Test Suite
echo 5. 🔧 Individual Tests
echo.

set /p choice="Select option (1-5): "

if "%choice%"=="1" (
    echo 🖥️ Starting GUI mode...
    python pistorm_tester.py --gui
) else if "%choice%"=="2" (
    echo 📱 Starting CLI interactive mode...
    python pistorm_tester.py --cli
) else if "%choice%"=="3" (
    echo ⚡ Running quick health check...
    python pistorm_tester.py --test health
) else if "%choice%"=="4" (
    echo 🧪 Running full test suite...
    python pistorm_tester.py --test all
) else if "%choice%"=="5" (
    echo 🔧 Individual test menu...
    echo.
    echo Available individual tests:
    echo a) API Connectivity
    echo b) Network Scan
    echo c) Monitor Mode
    echo d) System Health
    echo.
    set /p test_choice="Select test (a-d): "
    
    if "!test_choice!"=="a" python pistorm_tester.py --test api
    if "!test_choice!"=="b" python pistorm_tester.py --test scan
    if "!test_choice!"=="c" python pistorm_tester.py --test monitor
    if "!test_choice!"=="d" python pistorm_tester.py --test health
) else (
    echo ❌ Invalid option
    pause
    exit /b 1
)

echo.
echo ✅ Testing complete!
pause