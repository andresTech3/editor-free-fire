@echo off
chcp 65001 >nul
cls
title 🚀 DESPLEGAR CÓDIGO HEADSHOT A VERCEL
echo ===============================================================================
echo     ⚡ PUBLICAR NUEVA VERSIÓN DEL WEB STUDIO EN VERCEL ⚡
echo ===============================================================================
echo.
echo  Subiendo carpeta web_studio a https://editor-free-fire.vercel.app ...
echo.

cd /d "%~dp0web_studio"
npx vercel --prod --yes

echo.
echo ===============================================================================
echo  ✅ ¡DESPLIEGUE A VERCEL COMPLETADO CON ÉXITO!
echo  👉 Tu aplicación pública mundial: https://editor-free-fire.vercel.app
echo ===============================================================================
echo.
pause
