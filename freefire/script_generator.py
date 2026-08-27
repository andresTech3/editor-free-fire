"""
freefire/script_generator.py
=============================
Genera guiones dinámicos (hook / contenido / CTA) a partir del título del video.

El guion se adapta al título para que cada video sea único pero mantenga
la estructura y tono del video de referencia "Código Headshot".

Estructura:
  hook    → Pregunta provocativa que para el scroll (2-3s de voz)
  scenes  → 3-5 frases cortas durante gameplay (0.8-1.5s c/u)
  cta     → Cierre sutil con "comenta CÓDIGO" (2-3s de voz)
"""

import random
from dataclasses import dataclass, field


@dataclass
class ScriptScene:
    """Una escena individual del guion con su texto visual y de voz."""
    overlay_text: str      # Texto grande que aparece en pantalla
    voice_line: str        # Lo que dice la voz TTS
    duration_hint: float   # Duración sugerida en segundos


@dataclass
class VideoScript:
    """Guion completo del video."""
    title: str
    hook_text: str         # Texto visual del hook (grande, pantalla completa)
    hook_voice: str        # Lo que dice la voz en el hook
    scenes: list[ScriptScene] = field(default_factory=list)
    cta_text: str = ""     # Texto visual del CTA
    cta_voice: str = ""    # Lo que dice la voz en el CTA
    cta_badge: str = ""    # Texto del badge inferior (emoji + dato)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES DE HOOK — Se adaptan al título del video
# ─────────────────────────────────────────────────────────────────────────────

HOOK_TEMPLATES = [
    # Template: el título se inserta como variable
    {
        "text": "{titulo_upper}",
        "voice": "¿Sabías que {titulo_lower}? Quédate y te lo explico",
    },
    {
        "text": "{titulo_upper}",
        "voice": "Hoy te voy a mostrar {titulo_lower}",
    },
    {
        "text": "{titulo_upper}",
        "voice": "Atención, {titulo_lower}, mira esto",
    },
    {
        "text": "{titulo_upper}",
        "voice": "{titulo_lower}, y te lo voy a demostrar ahora mismo",
    },
    {
        "text": "{titulo_upper}",
        "voice": "Esto es algo que nadie te dice, {titulo_lower}",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# SCENES — Frases de gameplay (se eligen aleatoriamente y se adaptan)
# ─────────────────────────────────────────────────────────────────────────────

SCENE_POOLS = {
    # Frases genéricas que aplican a cualquier tema de Free Fire
    "accion": [
        ScriptScene("HEADSHOT", "Mira este headshot", 1.0),
        ScriptScene("ELIMINACIÓN", "Eliminación tras eliminación", 1.0),
        ScriptScene("BOOM", "Boom, así de fácil", 0.8),
        ScriptScene("SIN PIEDAD", "Sin piedad contra todos", 1.0),
        ScriptScene("BRUTAL", "Esto es brutal", 0.8),
        ScriptScene("LETAL", "Jugada completamente letal", 1.0),
    ],
    "sensibilidad": [
        ScriptScene("PRECISIÓN", "Con esta precisión no fallas", 1.2),
        ScriptScene("CONTROL", "Control total de la mira", 1.0),
        ScriptScene("MIRA ROJA", "La mira roja no perdona", 1.0),
        ScriptScene("APUNTAR", "Apuntar nunca fue tan fácil", 1.2),
        ScriptScene("RECOIL", "Cero recoil con esta config", 1.0),
    ],
    "competitivo": [
        ScriptScene("PROFESIONALES", "Contra los mejores profesionales", 1.2),
        ScriptScene("JUGADORES", "Destruyendo jugadores", 1.0),
        ScriptScene("TOP GLOBAL", "Jugada nivel top global", 1.0),
        ScriptScene("RANKED", "Esto es ranked de verdad", 1.0),
        ScriptScene("DOMINACIÓN", "Dominación total del mapa", 1.2),
    ],
    "dispositivo": [
        ScriptScene("DISPOSITIVO", "En cualquier dispositivo", 1.0),
        ScriptScene("CRÉEME", "Créeme, funciona", 0.8),
        ScriptScene("MÓVIL", "Desde el celular, sin excusas", 1.2),
        ScriptScene("CONFIG", "Con esta configuración", 1.0),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# CTA TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

CTA_TEMPLATES = [
    {
        "text": 'Comenta "CÓDIGO" 🔥',
        "voice": 'Si quieres esta configuración comenta "código"',
        "badge": "🤫 SECRETO",
    },
    {
        "text": 'Comenta "CÓDIGO" 🤫',
        "voice": 'Comenta "código" si quieres saber más',
        "badge": "🎯 PRECISIÓN",
    },
    {
        "text": 'Escribe "CÓDIGO" 💀',
        "voice": 'Escribe "código" en los comentarios',
        "badge": "🔥 LETAL",
    },
    {
        "text": 'Comenta "CÓDIGO" 🎯',
        "voice": 'Comenta "código" para la config completa',
        "badge": "💀 HEADSHOT",
    },
    {
        "text": '"CÓDIGO" en comentarios 🔥',
        "voice": 'Deja "código" si quieres mejorar tu aim',
        "badge": "⚡ PODER",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD DETECTION — Detecta temas del título para elegir scenes relevantes
# ─────────────────────────────────────────────────────────────────────────────

TOPIC_KEYWORDS = {
    "sensibilidad": ["sensibilidad", "sensi", "mira", "apuntar", "aim", "dpi",
                     "configuración", "config", "ajustes", "recoil"],
    "competitivo": ["ranked", "profesional", "torneo", "competitivo", "top",
                    "clasificatoria", "rango", "global", "mejor"],
    "accion": ["headshot", "kill", "eliminar", "clutch", "squad", "rush",
               "agresivo", "pelea", "error", "jugadores"],
    "dispositivo": ["celular", "móvil", "dispositivo", "gama baja", "lag",
                    "fps", "rendimiento", "emulador"],
}


def detect_topics(title: str) -> list[str]:
    """Detecta qué temas están presentes en el título."""
    title_lower = title.lower()
    found = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                found.append(topic)
                break
    # Si no se detectó ningún tema, usar genéricos
    if not found:
        found = ["accion", "sensibilidad"]
    return found


def generate_script(title: str, num_scenes: int = 4) -> VideoScript:
    """
    Genera un guion completo basado en el título del video.

    Args:
        title: Título del video (ej: "El error que comete el 90% al levantar la mira")
        num_scenes: Número de escenas de gameplay (3-6)

    Returns:
        VideoScript con hook, scenes y CTA listos para producción
    """
    # ── Detectar temas relevantes al título ──
    topics = detect_topics(title)

    # ── Generar Hook ──
    hook_template = random.choice(HOOK_TEMPLATES)
    titulo_upper = title.upper()
    # Truncar a 2 líneas si es muy largo
    words = titulo_upper.split()
    if len(words) > 6:
        mid = len(words) // 2
        titulo_upper = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])

    titulo_lower = title.lower()
    # Quitar artículos iniciales para la voz
    for prefix in ["el ", "la ", "los ", "las ", "un ", "una "]:
        if titulo_lower.startswith(prefix):
            titulo_lower = titulo_lower  # mantener para naturalidad
            break

    hook_text = hook_template["text"].format(titulo_upper=titulo_upper)
    hook_voice = hook_template["voice"].format(titulo_lower=titulo_lower)

    # ── Generar Scenes de gameplay ──
    # Siempre garantizar PROFESIONALES (Tabla de Clasificación) y JUGADORES (Top Regional)
    mandatory_scenes = [
        ScriptScene("PROFESIONALES", "Destruyendo profesionales", 1.0),
        ScriptScene("JUGADORES", "Contra los mejores jugadores", 1.0),
    ]

    available_scenes = []
    for topic in topics:
        available_scenes.extend(SCENE_POOLS.get(topic, []))
    available_scenes.extend(SCENE_POOLS["accion"])

    # Eliminar duplicados por overlay_text
    seen = {s.overlay_text for s in mandatory_scenes}
    unique_scenes = list(mandatory_scenes)
    for scene in available_scenes:
        if scene.overlay_text not in seen:
            seen.add(scene.overlay_text)
            unique_scenes.append(scene)

    random.shuffle(unique_scenes[2:])  # Mantener las obligatorias y shuffle el resto
    selected_scenes = unique_scenes[:num_scenes]

    # ── Generar CTA ──
    cta = random.choice(CTA_TEMPLATES)

    return VideoScript(
        title=title,
        hook_text=hook_text,
        hook_voice=hook_voice,
        scenes=selected_scenes,
        cta_text=cta["text"],
        cta_voice=cta["voice"],
        cta_badge=cta["badge"],
    )


def format_script_preview(script: VideoScript) -> str:
    """Formatea el guion para preview en consola."""
    lines = []
    lines.append(f"📝 GUIÓN: {script.title}")
    lines.append(f"{'=' * 50}")
    lines.append(f"")
    lines.append(f"🎣 HOOK:")
    lines.append(f"   Visual: {script.hook_text.replace(chr(10), ' | ')}")
    lines.append(f"   Voz:    {script.hook_voice}")
    lines.append(f"")
    lines.append(f"🎮 GAMEPLAY SCENES ({len(script.scenes)}):")
    for i, scene in enumerate(script.scenes, 1):
        lines.append(f"   {i}. [{scene.overlay_text}] — \"{scene.voice_line}\" ({scene.duration_hint}s)")
    lines.append(f"")
    lines.append(f"📢 CTA:")
    lines.append(f"   Visual: {script.cta_text}")
    lines.append(f"   Voz:    {script.cta_voice}")
    lines.append(f"   Badge:  {script.cta_badge}")
    return "\n".join(lines)
