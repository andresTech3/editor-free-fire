# 🎬 ViralClip Maker

> **Tu Opus Clip gratuito** — Convierte videos largos en Shorts virales automáticamente usando IA local.

Usa OpenAI Whisper, OpenCV, MoviePy y FFmpeg para detectar los momentos más virales de tu video y generar clips de máximo 60 segundos con:
- 🔤 Subtítulos karaoke animados (palabra por palabra)
- 🔍 Zoom dinámico estilo TikTok
- 📱 Formato 9:16 con smart crop (centra al speaker)
- 📺 Split screen arriba/abajo opcional
- 🎨 Color grading cinematográfico automático

---

## ⚡ Instalación Rápida (Windows)

### 1. Instalar FFmpeg
Ve a [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) y descarga `ffmpeg-release-essentials.zip`.
Extrae en `C:\ffmpeg` y añade `C:\ffmpeg\bin` al PATH del sistema.

O instala con winget:
```
winget install --id Gyan.FFmpeg -e
```

### 2. Ejecutar el instalador automático
```
setup.bat
```
Este script crea un entorno virtual, instala PyTorch, Whisper y todas las dependencias.

### 3. Activar el entorno virtual manualmente (si lo necesitas)
```
venv\Scripts\activate
```

---

## 🚀 Uso

### Básico
Coloca tu video en la carpeta `input/` y ejecuta:
```bash
python main.py input/tu_video.mp4
```

### Con opciones
```bash
# Generar 7 clips con split screen y estilo azul neón
python main.py input/video.mp4 --clips 7 --split-screen --style neon_blue

# Modelo Whisper más preciso (más lento)
python main.py input/video.mp4 --model small

# Video en inglés sin zoom
python main.py input/video.mp4 --lang en --no-zoom

# Ayuda completa
python main.py --help
```

### Opciones disponibles
| Opción | Valores | Default | Descripción |
|---|---|---|---|
| `--clips N` | 1-20 | 5 | Cuántos clips generar |
| `--model` | tiny/base/small | base | Modelo Whisper |
| `--lang` | es/en/auto | es | Idioma del video |
| `--style` | viral_yellow/neon_blue/fire_orange/white_bold | viral_yellow | Estilo de subtítulos |
| `--split-screen` | flag | off | Activar pantalla dividida |
| `--no-zoom` | flag | zoom activado | Desactivar zoom |
| `--no-subtitles` | flag | subtítulos activados | Desactivar subtítulos |

---

## 📁 Estructura de Carpetas

```
Edicion en Capcut/
├── 📁 input/          ← Coloca aquí tus videos largos
├── 📁 output/         ← Clips virales generados aparecen aquí
│   └── nombre_video/
│       ├── clip_01_score0.85.mp4
│       ├── clip_02_score0.72.mp4
│       └── report.txt
├── config.toml        ← Personaliza todo aquí
├── main.py            ← Punto de entrada
└── setup.bat          ← Instalador automático
```

---

## ⚙ Configuración (`config.toml`)

Edita `config.toml` para personalizar el comportamiento sin usar la línea de comandos:

```toml
[general]
max_clip_duration = 60    # Máximo 60s por clip
min_clip_duration = 20    # Mínimo 20s por clip
num_clips = 5             # 5 clips por video
language = "es"           # Idioma español

[effects]
enable_zoom = true
enable_subtitles = true
enable_split_screen = false
subtitle_style = "viral_yellow"

[analysis]
whisper_model = "base"
viral_keywords_es = ["increíble", "secreto", "nunca", ...]
```

---

## 🔥 Algoritmo de Viralidad

El sistema puntúa cada segmento del video con:

```
viral_score = (
    35% × energía_audio      ← Picos de volumen/intensidad
  + 25% × palabras_clave     ← "secreto", "increíble", números, etc.
  + 20% × intensidad_emocional  ← Análisis de sentimiento
  + 20% × ritmo_del_habla    ← Velocidad óptima 2.5-4 palabras/seg
)
```

---

## 💻 Requisitos del Sistema

- **Python:** 3.9 o superior
- **RAM:** Mínimo 4 GB (8 GB recomendado para videos largos)
- **Espacio:** ~3 GB para modelos Whisper + dependencias
- **FFmpeg:** Necesario (ver instalación)
- **GPU:** Opcional pero recomendada (NVIDIA CUDA acelera Whisper 5-10x)

### Tiempos estimados (CPU, sin GPU)
| Video | tiny | base | small |
|---|---|---|---|
| 10 min | ~1 min | ~3 min | ~8 min |
| 30 min | ~3 min | ~8 min | ~20 min |
| 60 min | ~6 min | ~15 min | ~40 min |

---

## 🎨 Estilos de Subtítulos

| Estilo | Color resaltado | Ideal para |
|---|---|---|
| `viral_yellow` | Amarillo neón 🟡 | TikTok, contenido general |
| `neon_blue` | Cian eléctrico 💙 | Tech, gaming, educativo |
| `fire_orange` | Naranja fuego 🔥 | Motivacional, deporte, noticias |
| `white_bold` | Blanco puro ⚪ | Minimalista, vlogs |

---

## 🐛 Solución de Problemas

**Error: `ffmpeg not found`**
→ Instala FFmpeg y asegúrate que está en el PATH del sistema.

**Error: `No module named 'whisper'`**
→ Ejecuta `setup.bat` o `pip install openai-whisper`.

**El modelo Whisper tarda mucho**
→ Usa `--model tiny` para pruebas. Es menos preciso pero muy rápido.

**Error de memoria (RAM)**
→ Usa `--model tiny` y genera menos clips `--clips 3`.

**Los subtítulos están desincronizados**
→ Prueba con `--model small` para mayor precisión de timestamps.

---

## 📋 Licencia

Proyecto de código abierto. Usa librerías con licencia MIT/Apache:
- [OpenAI Whisper](https://github.com/openai/whisper) (MIT)
- [MoviePy](https://github.com/Zulko/moviepy) (MIT)
- [OpenCV](https://opencv.org/) (Apache 2.0)
- [FFmpeg](https://ffmpeg.org/) (LGPL/GPL)
