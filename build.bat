@echo off
echo ========================================================
echo Building Ariadne OSINT Framework Standalone Executable
echo ========================================================
echo [1/2] Checking and installing required dependencies...
python -m pip install --upgrade pip 2>nul
python -m pip install -r requirements.txt pyinstaller
echo ========================================================
echo [2/2] Running PyInstaller build engine...
python -m PyInstaller Ariadne.spec 2>nul || pyinstaller Ariadne.spec
echo ========================================================
echo Build complete! Executable is located in dist\Ariadne.exe
echo ========================================================
