@echo off
title 3D Model Builder
cd /d "%~dp0"

python scripts\run_generator.py %*

if errorlevel 1 (
    echo.
    echo Script ended with an error. Press any key to exit...
    pause >nul
)
