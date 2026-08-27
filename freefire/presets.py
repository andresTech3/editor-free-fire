"""
freefire/presets.py
===================
Presets de edición, paleta de colores, tipografía, duraciones
y configuración visual para el estilo "Código Headshot".

Todos los valores extraídos del análisis frame-a-frame del video de referencia.
Soporta resolución dinámica de recursos para ejecutable PyInstaller (_MEIPASS).
"""

from pathlib import Path
import sys
import os

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_base_dir() -> Path:
    """Obtiene el directorio base, soportando PyInstaller (_MEIPASS)."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return PROJECT_ROOT


def resolve_path(relative_path: str) -> str:
    """Resuelve la ruta absoluta de un recurso de forma dinámica."""
    base = get_base_dir()
    p = base / relative_path
    if not p.exists() and not hasattr(sys, '_MEIPASS'):
        p = PROJECT_ROOT / relative_path
    return str(p.resolve())


# ─────────────────────────────────────────────────────────────────────────────
# RUTAS DE ASSETS Y CONFIGURACIÓN POR DEFECTO
# ─────────────────────────────────────────────────────────────────────────────

TTS_VOICE = "es-MX-JorgeNeural"
TTS_RATE = "+15%"
TTS_VOLUME = "+0%"

ASSETS_DIR = get_base_dir() / "assets" / "video free fire"
SFX_DIR = get_base_dir() / "assets" / "sfx"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output" / "FreeFire"

AVATAR_PATH = resolve_path("assets/video free fire/avatar freefire.jpeg")
AVATAR_CUTOUT_PATH = resolve_path("assets/video free fire/avatar_cutout.png")
LOGO_PATH = resolve_path("assets/video free fire/logo.jpeg")
SENSIBILIDAD_PATH = resolve_path("assets/video free fire/sensibilidad.jpeg")
SENSIBILIDAD_CROPPED_PATH = resolve_path("assets/video free fire/sensibilidad_cropped.png")

SFX_DIR_USER = ASSETS_DIR / "efecto sonido"
SFX_VINE_BOOM = resolve_path("assets/video free fire/efecto sonido/vine-boom.mp3")
SFX_DING = resolve_path("assets/video free fire/efecto sonido/ding-sound-effect_2.mp3")
SFX_ERROR = resolve_path("assets/video free fire/efecto sonido/error_CDOxCYm.mp3")

SFX_BOOM = SFX_VINE_BOOM if os.path.exists(SFX_VINE_BOOM) else resolve_path("assets/sfx/impact_boom.wav")
SFX_WHOOSH = resolve_path("assets/sfx/whoosh.wav")

# ─────────────────────────────────────────────────────────────────────────────
# PALETA DE COLORES (estilo gaming Free Fire)
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "red": "#FF0033",           # Texto principal de impacto
    "red_dark": "#CC0022",      # Sombra del rojo
    "yellow": "#FFD700",        # Acentos, rankings, badges
    "white": "#FFFFFF",         # Texto secundario
    "black": "#000000",         # Stroke, fondos
    "bg_dark": "0x111111",      # Fondo de overlays
    "orange": "#FF6600",        # Alertas, DPI
    "green_neon": "#00FF66",    # Indicadores positivos
}

# ─────────────────────────────────────────────────────────────────────────────
# TIPOGRAFÍA (Windows fonts)
# ─────────────────────────────────────────────────────────────────────────────

FONT_CANDIDATES = [
    "C:/Windows/Fonts/impact.ttf",       # Impact — el más fiel al estilo
    "C:/Windows/Fonts/arialbd.ttf",      # Arial Bold
    "C:/Windows/Fonts/ARIBLK.TTF",       # Arial Black
    "C:/Windows/Fonts/verdanab.ttf",     # Verdana Bold
    "C:/Windows/Fonts/calibrib.ttf",     # Calibri Bold
]


def get_font_path() -> str:
    """Retorna la primera fuente bold disponible, con colons escapados para FFmpeg en Windows."""
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f.replace("\\", "/").replace(":", "\\:")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# ESTRUCTURA DE DURACIÓN (proporcional al total)
# ─────────────────────────────────────────────────────────────────────────────

SEGMENT_PROPORTIONS = {
    "hook": 0.16,
    "sensibilidad": 0.16,
    "gameplay": 0.49,
    "cta": 0.19,
}


def get_segment_durations(total_duration: float) -> dict:
    """Calcula duraciones exactas de cada segmento para una duración total dada."""
    durations = {}
    for segment, proportion in SEGMENT_PROPORTIONS.items():
        durations[segment] = round(total_duration * proportion, 2)
    return durations


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE VIDEO FINAL
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 60
