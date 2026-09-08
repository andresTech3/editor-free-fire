---
title: Codigo Headshot Free Fire Studio
emoji: ⚡
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# 🔥 Free Fire Short Video Generator & Interactive Studio (v26.0)


Sistema profesional de edición automatizada y estudio interactivo GUI para la creación de **Videos Virales Shorts en formato 9:16 (60 FPS)** orientados a YouTube Shorts, TikTok y Instagram Reels de Free Fire.

---

## 🚀 Inicio Rápido (1 Clic)

Simplemente ejecuta el acceso directo en tu Escritorio o en la raíz del proyecto:
👉 **`C:\Users\SnyX\Desktop\Generar_Video_FreeFire.bat`**  
o  
👉 **`Generar_Video_FreeFire.bat`** (en la raíz del proyecto)

Se abrirá el **Estudio Interactivo en Modo Oscuro (Tkinter GUI)** donde podrás:
1. Seleccionar o arrastrar tus archivos de audio de locución (`/Generar Video/`).
2. Activar/Desactivar la música de fondo (Phonk/Hype) con ducking automático a -18dB.
3. Seleccionar el modo de entrada del Hook (Auto-Detección por voz, Pega Todo Rojo, Pega Amarillo).
4. Ajustar densidad de memes semánticos de pantalla verde (`PACK MEMES PANTALLA VERDE 1 (manuDT)`).
5. Renderizar en 1 clic y abrir el video final en alta definición (`output/final_short_916.mp4`).

---

## 📁 Estructura del Proyecto Organizada

```
Edicion en Capcut/
├── Generar_Video_FreeFire.bat   # Launcher directo .bat
├── desktop_gui.py               # Aplicación GUI de estudio interactivo
├── desktop_auto_editor.py       # Motor principal de edición y renderizado (v18.0)
├── README.md                    # Documentación del proyecto
├── output/
│   └── final_short_916.mp4      # Video final renderizado (1080x1920 60 FPS)
└── assets/
    └── Recurso video Freefire/  # CARPETA ÚNICA DE RECURSOS DEL PROYECTO
        ├── Generar Video/       # Audios de locución subidos por el usuario (.mp3 / .wav)
        ├── free fire jugadas/   # recopilacion_tiros_rojo 1..5.mp4 y recopilacion_fallando.mp4
        ├── video Guia/          # emotes.MP4 y Animate_the_image_*.mp4 (video animado de libro)
        ├── Imagenes/            # avatar_cutout.png, sencibilidad.jpg, logo.jpeg, personajes PNG
        ├── efectos de sonidos/  # SFX (vine-boom, whoosh, ding, punch, error)
        ├── musica/              # Pistas de música Phonk / Hype de fondo
        └── PACK MEMES PANTALLA VERDE 1 (manuDT)/  # 205 Memes en pantalla verde (Chromakey)
```

---

## 🎯 Características Principales del Motor v18.0

- **Detección Inteligente de Hook por Voz**: Lee la locución. Si habla de pecheadas o tiros fallados, abre con el clip `recopilacion_fallando.mp4`. Si no, entra directo con `recopilacion_tiros_rojo`.
- **Pureza Absoluta de Tiros Rojos (Clips #2 al N)**: El cuerpo principal del video usa **exclusivamente compilaciones de tiros a la cabeza**. Los clips de fallos están 100% prohibidos del desarrollo principal.
- **Rampas de Velocidad Frenéticas (Speed Ramp 1.5x)**: Acelera los desplazamientos y caminatas a 1.5x para mantener un ritmo hiperactivo, e impacta a 1.0x velocidad normal con micro-zoom (1.06x) al conectar el tiro rojo.
- **Superposición de Memes de Pantalla Verde en Alta Densidad**: Indexa los **205 memes** de la carpeta y los superpone con extracción de verde (HSV Chromakey) en cada 2 clips con bucle continuo (`auto-rewind`).
- **Disparador Inteligente de Libro / Guía**: Al detectar menciones de guías o libros, inserta el clip animado `Animate_the_image_*.mp4` con el personaje recortado flotando en pantalla.
- **Audio Ducked (-18dB) y Música en Bucle Infinito**: La música de fondo se ajusta a la duración exacta de la voz con fade-in y fade-out sin cortarse a mitad del video.
- **Tipografía Limpia sin Cuadros (`□`)**: Renderiza subtítulos nítidos en amarillo y blanco con borde negro sin artefactos de símbolos no compatibles.

---

## 🛠️ Requisitos Técnicos

- **Python 3.10+**
- **FFmpeg** (instalado en el PATH del sistema)
- Librerías Python: `opencv-python`, `pillow`, `numpy`

Para instalar dependencias si se requiere en una nueva máquina:
```bash
pip install opencv-python pillow numpy
```

---

*Proyecto configurado y optimizado al 100% para producción continua.*
