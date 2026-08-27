@echo off
title 🐙 Conectar Repositorio GitHub con Vercel
cd /d "%~dp0"
echo ─────────────────────────────────────────────────────────────
echo   🐙 CONECTAR REPOSITORIO GITHUB Y VERCEL AUTOMÁTICO
echo ─────────────────────────────────────────────────────────────
echo.
echo  1. Ve a GitHub.com y crea un nuevo repositorio (ej: freefire-clip-extractor).
echo  2. Copia la URL del repositorio creado en GitHub.
echo.
set /p repo_url="Pega la URL de tu repositorio de GitHub (ej: https://github.com/usuario/mi-repo.git): "

if "%repo_url%"=="" (
    echo ❌ Debes ingresar una URL válida de GitHub.
    pause
    exit /b
)

echo.
echo 🚀 Conectando repositorio local con GitHub...
git branch -M main
git remote remove origin 2>nul
git remote add origin %repo_url%
git push -u origin main

if %ERRORLEVEL% EQ 0 (
    echo.
    echo 🎉 ¡REPOSITORIO SUBIDO EXITOSAMENTE A GITHUB!
    echo.
    echo 📌 PARA CONECTAR VERCEL CON TU GITHUB (Despliegues Automáticos):
    echo 1. Entra a https://vercel.com/new
    echo 2. Selecciona tu repositorio de GitHub "%repo_url%"
    echo 3. Selecciona la subcarpeta "mobile_app" como Root Directory
    echo 4. Haz clic en DEPLOY.
    echo.
    echo ¡Cada cambio o 'git push' actualizará automáticamente tu App en Vercel!
) else (
    echo.
    echo ❌ Ocurrió un error al subir a GitHub. Verifica la URL e inicio de sesión de Git.
)

pause
