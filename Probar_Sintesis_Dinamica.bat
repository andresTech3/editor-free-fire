@echo off
title MOTOR DE SINTESIS DINAMICA FREE FIRE (BEAT SYNC + 3D)
chcp 65001 > nul
cls
echo ====================================================================
echo   🚀 EJECUTANDO MOTOR DE SÍNTESIS DINÁMICA (WHISPER + LIBROSA + 3D)
echo ====================================================================
echo.
echo [1/3] Analizando semántica de voz (Whisper word-timestamps)...
echo [2/3] Extrayendo beats musicales y sidechain IIR (Librosa)...
echo [3/3] Ensamblando 4 estados: Hook 3D, Memes al beat, Spec HUD...
echo.
python "%~dp0generate_video.py" --aspect 9:16 --outdir "%~dp0output" --outname "video_sintesis_dinamica.mp4"
echo.
if exist "%~dp0output\video_sintesis_dinamica.mp4" (
    echo ====================================================================
    echo   🎉 ¡VIDEO GENERADO CON ÉXITO!
    echo   Ubicación: output\video_sintesis_dinamica.mp4
    echo ====================================================================
    start "" "%~dp0output\video_sintesis_dinamica.mp4"
) else (
    echo ❌ Ocurrió un error al generar el video.
)
pause
