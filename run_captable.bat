@echo off
chcp 65001 >nul
title ClipFarm x The Cap Table — Podcast Clipper

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  🎙  ClipFarm × The Cap Table                              ║
echo  ║  Episode: A $31M Startup Copied Him — He Fought Back       ║
echo  ║  Guest:   Avi Patel (CEO, Kled AI / SideShift)             ║
echo  ║  Output → output\TheCapTable\  (independent section)       ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
echo  📂 Source video: input\YTDown.com_YouTube_A-31M-Startup...mp4
echo  📁 Output clips: output\TheCapTable\
echo.
echo  Rules checklist:
echo    OK  On-screen captions on every clip
echo    OK  Watermark visible (center-crop, not cut)
echo    OK  One clear speaking point per clip
echo    OK  Natural clip length (no forced 30s freeze)
echo    OK  Tags in caption.txt for TikTok/IG/YT
echo.

python clip_captable.py

if errorlevel 1 (
    echo.
    echo  ERROR: Something went wrong. See error above.
    pause
    exit /b 1
)

echo.
echo  Done! Check output\TheCapTable\ for your 5 clips + captions.
echo.
pause
