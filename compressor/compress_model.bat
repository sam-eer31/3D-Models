@echo off
title 3D GLB/GLTF Model Compressor
cd /d "%~dp0"
python compress_model.py %*
echo.
echo Press any key to exit...
pause >nul

