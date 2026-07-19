#!/usr/bin/env bash
echo "========================================================"
echo "Building Ariadne OSINT Framework Standalone Executable"
echo "========================================================"
echo "[1/2] Checking and installing required dependencies..."
python3 -m pip install --upgrade pip 2>/dev/null
python3 -m pip install -r requirements.txt pyinstaller
echo "========================================================"
echo "[2/2] Running PyInstaller build engine..."
python3 -m PyInstaller Ariadne.spec 2>/dev/null || pyinstaller Ariadne.spec
echo "========================================================"
echo "Build complete! Standalone binary is located in dist/Ariadne"
echo "========================================================"
