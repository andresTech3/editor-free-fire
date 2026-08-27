@echo off
chcp 65001 > nul
title ViralClip - 5 Shorts Virales (Layouts Variados)
color 0A

echo.
echo ============================================================
echo    ViralClip Maker - 5 SHORTS VIRALES CON LAYOUTS UNICOS
echo    Cada clip tiene diferente estilo visual y hook distinto
echo    Layouts: header_banner / zoom_burst / neon_pointer /
echo             financial_highlight / zoom_burst
echo ============================================================
echo.

if "%~1"=="" (
    echo [!] Arrastra un video largo sobre este archivo o escribe la ruta.
    echo.
    set /p VIDEO="Ruta del video (ej. input/video.mp4): "
) else (
    set VIDEO="%~1"
)

if "%VIDEO%"=="" (
    echo Error: Debes especificar un archivo de video.
    pause
    exit /b 1
)

echo.
echo Generando 5 Shorts con estilos y hooks diferentes...
echo Video: %VIDEO%
echo.

python main.py %VIDEO% --clips 5

echo.
echo Listo! Revisa la carpeta output/
pause
