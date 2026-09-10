@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cls
title 🌐 CÓDIGO HEADSHOT — TÚNEL MUNDIAL PARA VERCEL
echo ===============================================================================
echo   ⚡ INICIANDO ESTUDIO WEB CONECTADO A VERCEL PARA TODO EL MUNDO ⚡
echo ===============================================================================
echo.
python "%~dp0core\start_with_tunnel.py"
pause

