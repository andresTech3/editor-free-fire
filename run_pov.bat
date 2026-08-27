@echo off
chcp 65001 >nul
title ViralClip — POV Shorts Generator

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  🎬  POV Shorts Generator                           ║
echo  ║  Output → output\POV\  (DOES NOT touch Lumena)     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  📂 Put your source videos in:  input\POV videos\
echo  📁 Finished clips go to:       output\POV\
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM  CONFIGURATION — Edit these values as needed
REM ─────────────────────────────────────────────────────────────────────────────

set FOLDER=input/POV videos
set CAMPAIGN=POV
set CLIPS=5
set MAX_DUR=30

REM ─────────────────────────────────────────────────────────────────────────────

python edit_clips.py pov "%FOLDER%" --campaign %CAMPAIGN% --clips %CLIPS% --max-duration %MAX_DUR%

if errorlevel 1 (
    echo.
    echo  ❌ Something went wrong. Check the error above.
    pause
    exit /b 1
)

echo.
echo  ✅ All done! Check output\%CAMPAIGN%\ for your clips.
echo.
pause
