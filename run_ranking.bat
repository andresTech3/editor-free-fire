@echo off
chcp 65001 > nul
title ViralClip - 5 Clips Formato Ranking
color 0E

echo.
echo ============================================================
echo    ViralClip Maker - FORMATO RANKING (5 Clips)
echo    Todos los clips con layout ranking_list
echo    Ideal para: Si te ries pierdes, Top 5, Compilaciones
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
echo Generando 5 clips en formato Ranking...
echo Video: %VIDEO%
echo.

python main.py %VIDEO% --clips 5 --layout ranking_list

echo.
echo Listo! Revisa la carpeta output/
pause
