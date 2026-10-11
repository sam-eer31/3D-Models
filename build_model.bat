@echo off
title 3D Model Builder
cd /d "%~dp0"
python scripts\run_generator.py %*
echo.
echo Press any key to exit...
pause >nul
