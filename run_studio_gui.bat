@echo off
chcp 65001 >nul
title ViralEditor Studio

echo.
echo  ╔═══════════════════════════════════════════════════════════════╗
echo  ║   🎬  ViralEditor Studio — Professional Short Editor         ║
echo  ║   No CapCut · No External Editors · 100%% Code               ║
echo  ╚═══════════════════════════════════════════════════════════════╝
echo.
echo  Installing dependencies if needed...
pip install customtkinter pdfplumber whisper -q 2>nul

echo  Launching GUI...
echo.
python studio_gui.py

if errorlevel 1 (
    echo.
    echo  ERROR launching GUI. Check Python + dependencies.
    pause
    exit /b 1
)
