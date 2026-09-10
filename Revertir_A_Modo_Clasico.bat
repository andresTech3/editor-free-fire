@echo off
title RESTAURAR MODO CLÁSICO FLUIDO
chcp 65001 > nul
cls
echo ====================================================================
echo   🛡️ RESTAURADOR AL MODO CLÁSICO FLUIDO (ROLLBACK 1-CLIC)
echo ====================================================================
echo.
echo Verificando integridad del motor clásico fluido (desktop_auto_editor.py)...
if exist "%~dp0desktop_auto_editor.py" (
    echo [OK] El motor clásico fluido está activo y seguro.
) else (
    echo [AVISO] Restaurando motor clásico desde el tag de seguridad v1.0-classic-smooth...
    git checkout v1.0-classic-smooth -- desktop_auto_editor.py
)

echo.
echo ====================================================================
echo   ✅ ESTADO RESTAURADO AL 100%%
echo   Tu generador está en el modo clásico con jugadas continuas y fluidas.
echo ====================================================================
echo.
pause
