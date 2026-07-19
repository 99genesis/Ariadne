@echo off
echo ========================================================
echo Building Ariadne OSINT Framework Standalone Executable
echo ========================================================
python -m PyInstaller Ariadne.spec 2>nul || pyinstaller Ariadne.spec
echo ========================================================
echo Build complete! Executable is located in dist\Ariadne.exe
echo ========================================================
