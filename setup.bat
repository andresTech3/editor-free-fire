@echo off
chcp 65001 > nul
title ViralClip Maker - Instalador
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║          🎬 ViralClip Maker - Instalador             ║
echo  ║        Convierte videos largos en Shorts Virales     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────────────
:: 1. Verificar Python
:: ─────────────────────────────────────────────────────
echo [1/7] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ❌ Python no encontrado. Instala Python 3.9+ desde https://python.org
    pause
    exit /b 1
)
python --version
echo  ✅ Python OK
echo.

:: ─────────────────────────────────────────────────────
:: 2. Verificar Node.js (necesario para Remotion)
:: ─────────────────────────────────────────────────────
echo [2/7] Verificando Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ❌ Node.js no encontrado. Instala Node.js 18+ desde https://nodejs.org
    pause
    exit /b 1
)
node --version
echo  ✅ Node.js OK
echo.

:: ─────────────────────────────────────────────────────
:: 3. Crear entorno virtual
:: ─────────────────────────────────────────────────────
echo [3/7] Configurando entorno virtual Python...
if not exist "venv" (
    python -m venv venv
    echo  ✅ Entorno virtual creado
) else (
    echo  ✅ Entorno virtual ya existe
)
call venv\Scripts\activate.bat
echo  ✅ Entorno virtual activado
echo.

:: ─────────────────────────────────────────────────────
:: 4. Verificar/Instalar FFmpeg
:: ─────────────────────────────────────────────────────
echo [4/7] Verificando FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ⚠️  FFmpeg no encontrado. Intentando instalar via winget...
    winget install --id Gyan.FFmpeg -e --silent >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ╔══════════════════════════════════════════════════════╗
        echo  ║  ⚠️  ACCION REQUERIDA: Instalar FFmpeg manualmente   ║
        echo  ║                                                       ║
        echo  ║  1. Ve a: https://www.gyan.dev/ffmpeg/builds/        ║
        echo  ║  2. Descarga "ffmpeg-release-essentials.zip"         ║
        echo  ║  3. Extrae a C:\ffmpeg                               ║
        echo  ║  4. Agrega C:\ffmpeg\bin al PATH del sistema         ║
        echo  ║  5. Vuelve a ejecutar este script                    ║
        echo  ╚══════════════════════════════════════════════════════╝
        echo.
        pause
    ) else (
        echo  ✅ FFmpeg instalado. Reinicia el terminal y ejecuta setup.bat de nuevo.
        pause
        exit /b 0
    )
) else (
    echo  ✅ FFmpeg OK
)
echo.

:: ─────────────────────────────────────────────────────
:: 5. Instalar dependencias Python
:: ─────────────────────────────────────────────────────
echo [5/7] Instalando dependencias Python...
echo  📦 Actualizando pip...
python -m pip install --upgrade pip --quiet

echo  📦 Instalando PyTorch (CPU)...
pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu --quiet

echo  📦 Instalando Whisper + análisis de audio + visión...
pip install openai-whisper opencv-python Pillow librosa soundfile numpy scipy --quiet

echo  📦 Instalando NLP + CLI...
pip install textblob nltk rich typer toml --quiet

echo  📦 Descargando datos NLTK...
python -c "import nltk; nltk.download('vader_lexicon', quiet=True); nltk.download('punkt', quiet=True)"

echo  📦 Descargando datos TextBlob...
python -m textblob.download_corpora --quiet 2>nul

echo  ✅ Dependencias Python instaladas
echo.

:: ─────────────────────────────────────────────────────
:: 6. Instalar dependencias de Remotion
:: ─────────────────────────────────────────────────────
echo [6/7] Instalando dependencias de Remotion...
cd remotion
npm install --silent
cd ..
echo  ✅ Remotion instalado
echo.

:: ─────────────────────────────────────────────────────
:: 7. Verificar instalación
:: ─────────────────────────────────────────────────────
echo [7/7] Verificando instalación...
python -c "import whisper, cv2, librosa, PIL, rich; print('  ✅ Todas las librerías Python verificadas')" 2>&1
echo.

echo  ╔══════════════════════════════════════════════════════╗
echo  ║   🎉 ¡Instalación completada exitosamente!          ║
echo  ║                                                       ║
echo  ║   Uso:                                               ║
echo  ║   python main.py input/tu_video.mp4                 ║
echo  ║   python main.py input/video.mp4 --clips 5          ║
echo  ║   python main.py input/video.mp4 --no-subtitles     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause
