@echo off
title WiFi Crack Listener - Windows PC
cd /d "%~dp0\.."
echo Starting WiFi Crack Listener...
echo Project Directory: %CD%
python scripts\crack_listener.py
pause