@echo off
title 🎯 Recopilador de Clips — Free Fire Edition
cd /d "%~dp0"
echo ─────────────────────────────────────────────────────────────
echo   🎯 CÓDIGO HEADSHOT — RECOPILADOR DEDICADO DE CLIPS FREE FIRE
echo ─────────────────────────────────────────────────────────────
echo.
echo Iniciando interfaz gráfica...
echo.

set PYTHONIOENCODING=utf-8
python clips_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Se produjo un error al ejecutar la interfaz gráfica.
    pause
)
