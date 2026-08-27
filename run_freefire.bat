@echo off
chcp 65001 >nul 2>&1
echo.
echo ============================================
echo   🔥 CÓDIGO HEADSHOT — Free Fire Edition
echo ============================================
echo.

REM Verificar que edge-tts está instalado
pip show edge-tts >nul 2>&1
if errorlevel 1 (
    echo Instalando edge-tts...
    pip install edge-tts -q
)

REM Ejecutar el editor
python freefire_editor.py generate %*

echo.
pause
