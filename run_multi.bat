@echo off
chcp 65001 > nul
title ViralClip - Multi-Video (5 Clips Alternados)
color 0D

echo.
echo ============================================================
echo    ViralClip - Multi-Video: 5 Clips Siempre Diferentes
echo    Escoge videos al azar de cada carpeta automaticamente
echo    Persona hablando (Raw videos) alternado con Gameplay
echo ============================================================
echo.

set /p CAMPAIGN="Campana (ej. Lumena) [Enter = Lumena]: "
if "%CAMPAIGN%"=="" set CAMPAIGN=Lumena

echo.
echo Generando 5 clips alternados...
echo Persona: input\Raw videos\  (seleccion aleatoria)
echo Gameplay: input\Game clips\ (seleccion aleatoria)
echo Campana: %CAMPAIGN%
echo.

python edit_clips.py multi "input/Raw videos" "input/Game clips" --campaign "%CAMPAIGN%" --clips 5

echo.
echo Listo! Revisa la carpeta output/%CAMPAIGN%/
echo Cada clip tiene su archivo .txt con SEO listo para copiar.
pause
