@echo off
chcp 65001 >nul
cls
title CÓDIGO HEADSHOT — Mobile & Web Video Studio

echo ===============================================================================
echo     ⚡ CÓDIGO HEADSHOT STUDIO — SERVIDOR WEB Y MÓVIL AUTOMÁTICO ⚡
echo ===============================================================================
echo.

:: Detect Local IP Address
for /f "tokens=*" %%a in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi*','Ethernet*' | Where-Object { $_.IPAddress -notlike '127*' -and $_.IPAddress -notlike '169*' } | Select-Object -First 1).IPAddress"') do set LOCAL_IP=%%a

if "%LOCAL_IP%"=="" (
    set LOCAL_IP=localhost
)

echo  [✓] ENTORNO WEB Y VERCEL PREPARADOS
echo.
echo  -------------------------------------------------------------------------------
echo   🌐 ENLACE PÚBLICO EN VERCEL (Abierto para todo el mundo):
echo      👉   https://editor-free-fire.vercel.app
echo.
echo   📱 ENLACE LOCAL WI-FI (Celular en la misma red de casa):
echo      👉   http://%LOCAL_IP%:8000
echo.
echo   💻 EN ESTA COMPUTADORA:
echo      👉   http://localhost:8000
echo  -------------------------------------------------------------------------------
echo.
echo  [+] Abriendo interfaz de edición en tu navegador...
start http://localhost:8000

echo  [+] Iniciando Servidor Web FastAPI de Renderizado (Presiona Ctrl+C para detener)...
echo.

python web_server.py

pause

