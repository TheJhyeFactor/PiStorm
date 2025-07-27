@echo off
echo === Installing Missing WiFi Crack Tools ===
echo.

echo [1/4] Checking for WSL...
wsl --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ WSL is installed
    echo [2/4] Installing hcxtools in WSL...
    wsl sudo apt update
    wsl sudo apt install -y hcxtools
    echo ✓ hcxtools installed in WSL
) else (
    echo ! WSL not found - installing...
    echo [2/4] Installing WSL (requires restart)...
    wsl --install Ubuntu
    echo ! Please restart Windows and run this script again
    pause
    exit /b 1
)

echo [3/4] Checking for aircrack-ng...
where aircrack-ng >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ aircrack-ng found
) else (
    echo ! aircrack-ng not found
    echo   Download from: https://www.aircrack-ng.org/downloads.html
)

echo [4/4] Testing conversion tools...
echo Testing hcxtools via WSL...
wsl hcxpcapngtool --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ WSL hcxtools working
) else (
    echo ! WSL hcxtools failed
)

echo.
echo === Installation Complete ===
echo Your WiFi crack listener now has multiple conversion fallbacks:
echo - WSL hcxpcapngtool
echo - Native hcxpcapngtool (if installed)
echo - aircrack-ng (if installed)
echo - Direct hashcat processing
echo.
pause