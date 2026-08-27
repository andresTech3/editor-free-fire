@echo off
title 🚀 Desplegar App Móvil a Vercel
cd /d "%~dp0mobile_app"
echo ─────────────────────────────────────────────────────────────
echo   🚀 DESPLEGAR APP MÓVIL PWA FREE FIRE CLIPS A VERCEL
echo ─────────────────────────────────────────────────────────────
echo.
echo  [1] Publicación Temporal Instantánea (¡Sin necesidad de cuenta!)
echo  [2] Iniciar Sesión en Vercel (npx vercel login) y publicar
echo.
set /p opt="Selecciona una opción (1 o 2) y presiona Enter: "

if "%opt%"=="1" (
    echo.
    echo 🚀 Creando enlace de despliegue temporal en Vercel...
    npx vercel deploy --temporary
    goto end
)

if "%opt%"=="2" (
    echo.
    echo 🔑 Abriendo navegador para iniciar sesión en Vercel...
    npx vercel login
    echo.
    echo 🚀 Publicando proyecto en producción...
    npx vercel --prod
    goto end
)

echo.
echo ℹ️ Opción no válida. Ejecutando inicio de sesión automático...
npx vercel login

:end
echo.
echo ─────────────────────────────────────────────────────────────
echo   Proceso finalizado. Presiona cualquier tecla para salir.
echo ─────────────────────────────────────────────────────────────
pause
