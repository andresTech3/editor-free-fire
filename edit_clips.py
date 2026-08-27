"""
edit_clips.py
=============
Modo Edición de Clips — Soporta Campañas (Lumena, Dreamina, General)

Comandos:
    edit  → 1 video → N clips (modo single)
    multi → 2+ videos → N clips alternados (persona + gameplay)

Uso:
    python edit_clips.py input/clip.mp4 --campaign Lumena --clips 5
    python edit_clips.py multi input/persona.mp4 input/gameplay.mp4 --campaign Lumena --clips 5
"""

import sys
import os
import time
import json
import shutil
import tempfile
import subprocess
import re
from pathlib import Path
from typing import Optional

# Forzar UTF-8 en Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = typer.Typer(
    name="edit-clips",
    help="Edita clips pre-cortados a formato 9:16 Short viral para campañas (Lumena, Dreamina, etc.).",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# HOOKS & CAMPAIGN PRESETS
# ─────────────────────────────────────────────────────────────────────────────

CAMPAIGN_PRESETS = {
    "lumena": {
        "name": "Lumena",
        "hooks": [
            ("Is Lumena the next Pokemon Go?? 🎮",              "Play Lumena free at lumena.gg"),
            ("This game gets more interesting the longer you play 🔥", "Link in bio to play free"),
            ("Lumena might be more addictive than it looks 👀",    "Free 3D game at lumena.gg"),
            ("I opened it in my browser and lost an hour ⏱",    "Play Lumena free - no download"),
            ("Pokemon Go fans NEED to see this game 🚀",        "Try Lumena 3D adventure now"),
            ("Finding this game early could end up paying off 💰", "lumena.gg — play free now"),
        ],
        "hashtags": "#lumena #lumenagg #cryptogaming #web3gaming #free2play #gaming #gamersoftiktok",
        "cta": "Play Lumena free at lumena.gg (link in bio!) Explore Firstlight, collect Lumens, and battle in PvP.",
        "seo_titles": [
            "Is Lumena The Next Pokemon Go? Free 3D Web3 Game 🎮",
            "This Free Browser Game Is More Addictive Than It Looks 🔥",
            "Why Pokemon Go Fans Are Switching To Lumena Right Now 🚀",
            "Finding This Free 3D Game Early Could Pay Off Big 💰",
            "I Played Lumena For 5 Minutes And Lost An Hour 🤯",
        ],
    },
    "dreamina": {
        "name": "Dreamina",
        "hooks": [
            ("Wait... AI made this?? 🤯",              "ByteDance's Dreamina just changed everything"),
            ("This AI video is INSANE 🔥",             "Seedance 2.5 is the future of content"),
            ("POV: You find the best AI tool 👀",      "Link in bio to try Dreamina now"),
            ("The AI going VIRAL right now 🚀",        "Dreamina Seedance 2.5 is here"),
            ("This is NOT real... 😱",                 "AI generated this entire video"),
            ("Bro this AI just changed everything 💀", "Dreamina x Seedance 2.5"),
        ],
        "hashtags": "#dreamina #dreaminacreators #seedance #dreaminaseedance2 #aivideo #aiart",
        "cta": "ByteDance's Dreamina Seedance 2.5 launches globally first on Dreamina. Try now (link in bio).",
        "seo_titles": [
            "Wait... AI Actually Generated This Entire Scene?? 🤯",
            "This AI Video Generator Is INSANE 🔥",
            "Nobody Believed AI Made This Video 😱",
            "The Most VIRAL AI Video You'll See Today 🚀",
            "AI Just Changed Video Creation Forever 💀",
        ],
    },
    "general": {
        "name": "Clips",
        "hooks": [
            ("You won't believe what happened here 🤯",  "Watch until the end"),
            ("This moment went INSTANTLY viral 🔥",       "Link in bio"),
            ("Nobody expected this to happen 👀",         "Check this out"),
            ("This is absolute CRAZINESS 🚀",            "Must see video"),
            ("Wait for it... 😱",                        "Unbelievable moment"),
        ],
        "hashtags": "#viral #trending #shorts #reels #tiktok #fyp",
        "cta": "Check link in bio for more!",
        "seo_titles": [
            "The Most INSANE Moment You'll See Today 🔥",
            "Nobody Believed This Actually Happened 🤯",
            "This Clip Is Going VIRAL Everywhere 🚀",
            "You Need To See This Incredible Scene 😱",
            "The Most Viral Short Video Right Now 💀",
        ],
    }
}

CHINESE_TO_EN = {
    "平行世界": "Parallel World", "未来": "Future", "城市": "City",
    "自然": "Nature", "海洋": "Ocean", "山": "Mountain",
    "天空": "Sky", "人": "Person", "机器人": "Robot",
    "科技": "Technology", "宇宙": "Universe", "星球": "Planet",
    "梦境": "Dream", "幻想": "Fantasy", "现实": "Reality",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def get_preset(campaign_name: str) -> dict:
    key = campaign_name.lower().strip()
    if key in CAMPAIGN_PRESETS:
        return CAMPAIGN_PRESETS[key]
    for k, preset in CAMPAIGN_PRESETS.items():
        if k in key or key in k:
            return preset
    return CAMPAIGN_PRESETS["general"]


def get_video_info(video_path: str) -> dict:
    """Obtiene duración y resolución del video con ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        data = json.loads(result.stdout)
        video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "audio"), None)
        duration = float(data.get("format", {}).get("duration", 0))
        width = int(video_stream.get("width", 1920))
        height = int(video_stream.get("height", 1080))
        fps_str = video_stream.get("r_frame_rate", "30/1")
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) > 0 else 30.0
        return {
            "width": width, "height": height, "fps": fps,
            "duration": duration, "has_audio": audio_stream is not None,
        }
    except Exception as e:
        console.print(f"[yellow]⚠ ffprobe falló: {e}. Usando valores por defecto.[/yellow]")
        return {"width": 1920, "height": 1080, "fps": 30.0, "duration": 30.0, "has_audio": False}


def trim_clip(video_path: str, start: float, duration: float, remotion_dir: str, clip_idx: int) -> tuple:
    public_input = os.path.join(remotion_dir, "public", "input")
    os.makedirs(public_input, exist_ok=True)
    stem = Path(video_path).stem
    trimmed_name = f"{stem}_clip{clip_idx}_s{int(start)}.mp4"
    trimmed_path = os.path.join(public_input, trimmed_name)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(round(start, 2)),
        "-t",  str(round(duration, 2)),
        "-i", video_path,
        "-c", "copy",
        trimmed_path
    ]
    subprocess.run(cmd, capture_output=True)
    return trimmed_path, f"input/{trimmed_name}"

# ─── Composition Layouts ─────────────────────────────────────────────────────
# Rotación de layouts creativos por clip:
#  reaction_stack  → gameplay top 65% + persona bottom 35% (ambos simultáneos)
#  pip_bubble      → gameplay pantalla completa + persona en esquina PiP
#  persona_intro   → persona full 5s → luego split gameplay+persona 25s
COMPOSE_LAYOUTS = [
    "reaction_stack",   # Clip 1
    "pip_bubble",       # Clip 2
    "persona_intro",    # Clip 3
    "reaction_stack",   # Clip 4
    "pip_bubble",       # Clip 5
]

OUT_W, OUT_H = 1080, 1920  # Formato 9:16 Shorts


def _pre_encode_segment(video_path: str, start: float, dur: float,
                         out_w: int, out_h: int, out_tmp: str) -> bool:
    """
    Pre-recorta y escala un segmento a un archivo temporal normalizado.
    Añade silencio si el video no tiene audio.
    Retorna True si tuvo éxito.
    """
    info = get_video_info(video_path)
    scale = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,"
        f"setsar=1,fps=30"
    )

    if info["has_audio"]:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(start, 3)),
            "-t",  str(round(dur, 3)),
            "-i",  video_path,
            "-vf", scale,
            "-af", "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-avoid_negative_ts", "make_zero",
            out_tmp,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(start, 3)),
            "-t",  str(round(dur, 3)),
            "-i",  video_path,
            "-f",  "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-vf", scale,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v", "-map", "1:a",
            "-t",  str(round(dur, 3)),
            "-avoid_negative_ts", "make_zero",
            out_tmp,
        ]

    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and Path(out_tmp).exists()


def compose_clips(
    persona_path: str, persona_start: float,
    gameplay_path: str, gameplay_start: float,
    clip_dur: float,
    remotion_dir: str, clip_idx: int,
    compose_style: str = "reaction_stack",
) -> tuple:
    """
    Compone un clip dinámico de duración NATURAL (clip_dur) con persona + gameplay
    visibles al mismo tiempo. Al durar exactamente clip_dur (el tiempo real disponible
    de los videos), NUNCA hay pantallas congeladas al final.

    Layouts disponibles:
      reaction_stack  → gameplay arriba (65%) + persona abajo (35%)
      pip_bubble      → gameplay pantalla completa + persona en esquina (PiP)
      persona_intro   → persona full (primeros 4s) → split stack (resto del clip)

    Returns (abs_path, rel_path_for_remotion)
    """
    public_input = os.path.join(remotion_dir, "public", "input")
    os.makedirs(public_input, exist_ok=True)
    out_name = f"composed_clip{clip_idx:02d}.mp4"
    out_path = os.path.join(public_input, out_name)

    tmp = tempfile.gettempdir()

    console.print(f"  [dim cyan]🎬 Componiendo layout [{compose_style}] — Duración natural: {clip_dur:.1f}s...[/dim cyan]")

    # ────────────────────────────────────────────────────────────────────
    # LAYOUT 1: reaction_stack
    #   Gameplay (1080×1248, arriba 65%) + Persona (1080×672, abajo 35%)
    #   Ambos corren en paralelo durante exactamente clip_dur
    # ────────────────────────────────────────────────────────────────────
    if compose_style == "reaction_stack":
        g_h = int(OUT_H * 0.65)   # 1248
        p_h = OUT_H - g_h         # 672

        g_tmp = os.path.join(tmp, f"g_stack_{clip_idx}.mp4")
        p_tmp = os.path.join(tmp, f"p_stack_{clip_idx}.mp4")

        ok_g = _pre_encode_segment(gameplay_path, gameplay_start, clip_dur, OUT_W, g_h, g_tmp)
        ok_p = _pre_encode_segment(persona_path,  persona_start,  clip_dur, OUT_W, p_h, p_tmp)

        if not (ok_g and ok_p):
            console.print("  [yellow]⚠ Pre-encode falló → fallback gameplay solo[/yellow]")
            return trim_clip(gameplay_path, gameplay_start, clip_dur, remotion_dir, clip_idx)

        cmd = [
            "ffmpeg", "-y",
            "-i", g_tmp, "-i", p_tmp,
            "-filter_complex",
            "[0:v][1:v]vstack=inputs=2[v];"
            "[0:a][1:a]amix=inputs=2:duration=shortest:dropout_transition=1[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            out_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        for f in [g_tmp, p_tmp]:
            try: os.remove(f)
            except: pass

        if r.returncode == 0 and Path(out_path).exists():
            console.print(f"  [green]✓ reaction_stack: gameplay arriba + persona abajo ({clip_dur:.1f}s natural)[/green]")
            return out_path, f"input/{out_name}"

    # ────────────────────────────────────────────────────────────────────
    # LAYOUT 2: pip_bubble
    #   Gameplay pantalla completa (1080×1920)
    #   Persona en esquina inferior izquierda (320×426)
    # ────────────────────────────────────────────────────────────────────
    elif compose_style == "pip_bubble":
        pip_w, pip_h = 320, 426   # tamaño del bubble de persona
        margin = 30               # margen desde el borde

        g_tmp = os.path.join(tmp, f"g_pip_{clip_idx}.mp4")
        p_tmp = os.path.join(tmp, f"p_pip_{clip_idx}.mp4")

        ok_g = _pre_encode_segment(gameplay_path, gameplay_start, clip_dur, OUT_W, OUT_H, g_tmp)
        ok_p = _pre_encode_segment(persona_path,  persona_start,  clip_dur, pip_w,  pip_h,  p_tmp)

        if not (ok_g and ok_p):
            console.print("  [yellow]⚠ Pre-encode falló → fallback gameplay solo[/yellow]")
            return trim_clip(gameplay_path, gameplay_start, clip_dur, remotion_dir, clip_idx)

        x_pos = margin
        y_pos = OUT_H - pip_h - margin - 200   # encima del hook text

        cmd = [
            "ffmpeg", "-y",
            "-i", g_tmp, "-i", p_tmp,
            "-filter_complex",
            f"[0:v][1:v]overlay=x={x_pos}:y={y_pos}:shortest=1[v];"
            "[0:a][1:a]amix=inputs=2:duration=shortest:dropout_transition=1[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            out_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        for f in [g_tmp, p_tmp]:
            try: os.remove(f)
            except: pass

        if r.returncode == 0 and Path(out_path).exists():
            console.print(f"  [green]✓ pip_bubble: gameplay full + persona PiP esquina ({clip_dur:.1f}s natural)[/green]")
            return out_path, f"input/{out_name}"

    # ────────────────────────────────────────────────────────────────────
    # LAYOUT 3: persona_intro
    #   Primeros 4s: persona FULL pantalla (gancho máximo)
    #   Resto: reaction_stack (gameplay arriba 65% + persona abajo 35%)
    # ────────────────────────────────────────────────────────────────────
    elif compose_style == "persona_intro":
        intro_dur = min(4.0, clip_dur * 0.3)
        stack_dur = max(2.0, clip_dur - intro_dur)
        g_h = int(OUT_H * 0.65)
        p_h = OUT_H - g_h

        intro_tmp  = os.path.join(tmp, f"intro_{clip_idx}.mp4")
        g_tmp      = os.path.join(tmp, f"g_intro_{clip_idx}.mp4")
        p_tmp      = os.path.join(tmp, f"p_intro_{clip_idx}.mp4")
        stack_tmp  = os.path.join(tmp, f"stack_{clip_idx}.mp4")

        ok_intro = _pre_encode_segment(persona_path,  persona_start,          intro_dur, OUT_W, OUT_H, intro_tmp)
        ok_g     = _pre_encode_segment(gameplay_path, gameplay_start,          stack_dur, OUT_W, g_h,   g_tmp)
        ok_p     = _pre_encode_segment(persona_path,  persona_start + intro_dur, stack_dur, OUT_W, p_h, p_tmp)

        if ok_g and ok_p:
            r_stack = subprocess.run([
                "ffmpeg", "-y",
                "-i", g_tmp, "-i", p_tmp,
                "-filter_complex",
                "[0:v][1:v]vstack=inputs=2[v];"
                "[0:a][1:a]amix=inputs=2:duration=shortest:dropout_transition=1[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                "-c:a", "aac", "-b:a", "128k",
                stack_tmp,
            ], capture_output=True)

        if ok_intro and ok_g and ok_p and r_stack.returncode == 0:
            concat_list = os.path.join(tmp, f"concat_{clip_idx}.txt")
            with open(concat_list, "w") as cf:
                cf.write(f"file '{intro_tmp.replace(chr(92), '/')}'\n")
                cf.write(f"file '{stack_tmp.replace(chr(92), '/')}'\n")

            r = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_list,
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "128k",
                out_path,
            ], capture_output=True, text=True, encoding="utf-8", errors="replace")

            for f in [intro_tmp, g_tmp, p_tmp, stack_tmp, concat_list]:
                try: os.remove(f)
                except: pass

            if r.returncode == 0 and Path(out_path).exists():
                console.print(f"  [green]✓ persona_intro: {intro_dur:.1f}s persona full → {stack_dur:.1f}s split stack ({clip_dur:.1f}s total)[/green]")
                return out_path, f"input/{out_name}"

    # Fallback universal: trim solo gameplay
    console.print("  [yellow]⚠ Layout falló → fallback gameplay solo[/yellow]")
    return trim_clip(gameplay_path, gameplay_start, clip_dur, remotion_dir, clip_idx)




    """
    Concatena un segmento de persona + un segmento de gameplay en un solo clip.
    Ambos se re-encodan a resolución común (target_w x target_h, 30fps).
    Maneja tracks de audio faltantes añadiendo silencio.

    Returns (abs_path, rel_path) del clip concatenado.
    """
    public_input = os.path.join(remotion_dir, "public", "input")
    os.makedirs(public_input, exist_ok=True)
    out_name = f"concat_clip{clip_idx:02d}.mp4"
    out_path = os.path.join(public_input, out_name)

    p_info = get_video_info(persona_path)
    g_info = get_video_info(gameplay_path)
    has_p_audio = p_info["has_audio"]
    has_g_audio = g_info["has_audio"]

    # Escalar ambos al mismo tamaño y fps para poder concatenar
    scale_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"

    # Construir filter_complex manejando audio faltante
    # [0:v] = persona video, [1:v] = gameplay video
    filter_parts = []
    map_args = []

    filter_parts.append(f"[0:v]trim={persona_start}:{persona_start + persona_dur},setpts=PTS-STARTPTS,{scale_filter}[pv]")
    filter_parts.append(f"[1:v]trim={gameplay_start}:{gameplay_start + gameplay_dur},setpts=PTS-STARTPTS,{scale_filter}[gv]")

    if has_p_audio:
        filter_parts.append(f"[0:a]atrim={persona_start}:{persona_start + persona_dur},asetpts=PTS-STARTPTS[pa]")
    else:
        filter_parts.append(f"aevalsrc=0:d={persona_dur}[pa]")

    if has_g_audio:
        filter_parts.append(f"[1:a]atrim={gameplay_start}:{gameplay_start + gameplay_dur},asetpts=PTS-STARTPTS[ga]")
    else:
        filter_parts.append(f"aevalsrc=0:d={gameplay_dur}[ga]")

    # Concat
    filter_parts.append("[pv][pa][gv][ga]concat=n=2:v=1:a=1[outv][outa]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", persona_path,
        "-i", gameplay_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        out_path
    ]

    console.print(f"  [dim cyan]Concatenando persona ({persona_dur:.0f}s) + gameplay ({gameplay_dur:.0f}s)...[/dim cyan]")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        console.print(f"  [yellow]⚠ Concat falló, usando solo gameplay. Error: {result.stderr[-200:]}[/yellow]")
        # Fallback: solo gameplay
        return trim_clip(gameplay_path, gameplay_start, gameplay_dur + persona_dur, remotion_dir, clip_idx)

    console.print(f"  [dim green]✓ Clip combinado: persona {persona_dur:.0f}s + gameplay {gameplay_dur:.0f}s = {persona_dur + gameplay_dur:.0f}s total[/dim green]")
    return out_path, f"input/{out_name}"




def make_impact_moments(duration: float) -> list:
    moments = []
    t = 4.0
    intensities = [0.85, 0.70, 0.90, 0.75, 0.80]
    i = 0
    while t < duration - 2.0:
        moments.append({"time": round(t, 2), "word": "!", "intensity": intensities[i % len(intensities)]})
        t += 5.0 + (i % 3) * 1.5
        i += 1
    return moments


def smart_pick_video(folder: str, avoid: list[str] = None, min_duration: float = 15.0) -> str | None:
    """
    Escoge aleatoriamente un video de una carpeta, evitando los de `avoid`.
    Filtra videos demasiado cortos. Si todos fueron evitados, escoge igual al azar.
    """
    import random
    avoid_set = set(os.path.abspath(p) for p in (avoid or []))
    exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

    candidates = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in exts
    ]
    # Filtrar por duración mínima
    valid = []
    for p in candidates:
        info = get_video_info(p)
        if info["duration"] >= min_duration:
            valid.append(p)

    if not valid:
        return None

    # Evitar los ya usados si hay alternativas
    fresh = [p for p in valid if os.path.abspath(p) not in avoid_set]
    pool = fresh if fresh else valid

    return random.choice(pool)


def smart_pick_segment(video_path: str, total_duration: float, target_duration: float,
                       used_starts: list[float] = None, attempts: int = 6) -> float:
    """
    Encuentra un segmento energético que NO se solape con los ya usados.
    Combina análisis de audio con selección aleatoria para garantizar variedad.
    """
    import random

    used_starts = used_starts or []
    margin = target_duration * 0.5  # Solapamiento máximo permitido: 50%

    if total_duration <= target_duration:
        return 0.0

    # Candidatos: múltiples posiciones distribuidas
    max_start = total_duration - target_duration
    n_positions = max(8, int(total_duration / (target_duration * 0.4)))
    all_positions = [round(i * max_start / (n_positions - 1), 1) for i in range(n_positions)]
    random.shuffle(all_positions)

    # Intentar encontrar posición no solapada
    for pos in all_positions:
        overlaps = any(abs(pos - u) < margin for u in used_starts)
        if not overlaps:
            console.print(f"  [dim green]✓ Segmento distinto seleccionado: {pos:.1f}s → {pos + target_duration:.1f}s[/dim green]")
            return pos

    # Si todos se solapan, usar audio energy para el mejor
    try:
        import librosa
        import numpy as np
        tmp_wav = os.path.join(tempfile.gettempdir(), "smart_seg_energy.wav")
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-ar", "22050", "-ac", "1", "-f", "wav", tmp_wav],
                       capture_output=True)
        y, sr = librosa.load(tmp_wav, sr=22050)
        hop = 512
        energy = librosa.feature.rms(y=y, hop_length=hop)[0]
        times = librosa.frames_to_time(range(len(energy)), sr=sr, hop_length=hop)
        win = int(target_duration * sr / hop)
        best, best_score = 0.0, -1.0
        for idx in range(0, len(energy) - win, max(1, win // 10)):
            score = float(np.mean(energy[idx:idx + win]))
            if score > best_score:
                best_score = score
                best = float(times[idx])
        return min(best, max_start)
    except Exception:
        return random.uniform(0, max(0.0, max_start))


def compute_crop_params(video_path: str, video_info: dict) -> tuple:
    TARGET_W, TARGET_H = 1080, 1920
    orig_w = video_info["width"]
    orig_h = video_info["height"]
    duration = video_info["duration"]
    fps = video_info["fps"]
    try:
        from core.face_tracker import FaceTracker
        tracker = FaceTracker(smoothing=0.85, sample_rate=5, console=console)
        crop_positions, crop_meta = tracker.analyze_clip(
            video_path, 0.0, duration, TARGET_W, TARGET_H
        )
        return crop_positions, crop_meta
    except Exception:
        pass

    from core.face_tracker import get_simple_crop_params
    simple = get_simple_crop_params(orig_w, orig_h, TARGET_W, TARGET_H)
    n_frames = int(duration * fps)
    crop_positions = [
        {"frame_idx": i, **simple, "has_face": False,
         "face_x": orig_w // 2, "face_y": orig_h // 2}
        for i in range(n_frames)
    ]
    crop_meta = {
        "orig_width": orig_w, "orig_height": orig_h,
        "crop_w": simple["crop_w"], "crop_h": simple["crop_h"], "fps": fps,
    }
    return crop_positions, crop_meta


def copy_logo_to_remotion(remotion_dir: str) -> str:
    project_root = os.path.dirname(os.path.abspath(__file__))
    logo_dir = os.path.join(project_root, "assets", "Logo")
    if os.path.isdir(logo_dir):
        pngs = [f for f in os.listdir(logo_dir) if f.lower().endswith(".png")]
        if pngs:
            src = os.path.join(logo_dir, pngs[0])
            dest = os.path.join(remotion_dir, "public", "logo.png")
            shutil.copy2(src, dest)
            return "logo.png"
    return ""


def render_with_remotion(remotion_dir: str, props: dict, output_path: str, clip_number: int) -> bool:
    tmp_dir = tempfile.gettempdir()
    json_path = os.path.join(tmp_dir, f"clip_props_{clip_number}.json").replace("\\", "/")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(props, f)

    cmd = [
        "npx", "remotion", "render",
        "ViralComposition",
        output_path,
        f"--props={json_path}",
        "--browser-executable=C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "--log", "info",
    ]
    result = subprocess.run(
        cmd, cwd=remotion_dir, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        shell=(os.name == "nt"),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    try:
        os.remove(json_path)
    except Exception:
        pass
    return result.returncode == 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI Command
# ─────────────────────────────────────────────────────────────────────────────

LAYOUT_ROTATION = [
    "header_banner",        # Clip 1
    "zoom_burst",           # Clip 2
    "neon_pointer",         # Clip 3
    "financial_highlight",  # Clip 4
    "zoom_burst",           # Clip 5
]

@app.command()
def edit(
    video_path: str = typer.Argument(..., help="Ruta al video de entrada"),
    campaign: str = typer.Option("Lumena", "--campaign", "-c", help="Nombre de la campaña (Lumena, Dreamina, etc.)"),
    clips: int = typer.Option(5, "--clips", "-n", help="Número de clips a generar (default: 5)"),
    max_duration: float = typer.Option(30.0, "--max-duration", "-d", help="Duración máxima de cada clip (segundos)"),
):
    """
    🎬 Genera 5 Shorts virales 9:16 con hooks y layouts únicos para la campaña seleccionada.
    """
    start_time = time.time()
    preset = get_preset(campaign)
    campaign_name = preset["name"]

    console.print()
    console.print(Panel(
        f"[bold cyan]ViralClip — Generador de {clips} Clips para {campaign_name}[/bold cyan]\n"
        f"[dim]Layouts variados  |  Hooks de {campaign_name}  |  9:16 Shorts  |  Sin subtítulos[/dim]",
        border_style="cyan",
    ))
    console.print()

    video_file = Path(video_path)
    if not video_file.exists():
        console.print(f"[bold red]❌ Archivo no encontrado:[/bold red] {video_path}")
        raise typer.Exit(1)

    project_root = os.path.dirname(os.path.abspath(__file__))
    remotion_dir = os.path.join(project_root, "remotion")

    output_dir = Path(project_root) / "output" / campaign_name
    output_dir.mkdir(parents=True, exist_ok=True)

    video_info = get_video_info(str(video_file))
    total_dur = video_info["duration"]

    console.print(f"📹 Video: [bold white]{video_file.name}[/bold white] ({total_dur:.1f}s)")
    console.print(f"🎯 Generando [bold yellow]{clips} clips[/bold yellow] de ~{max_duration:.0f}s cada uno en: [cyan]{output_dir}[/cyan]")
    console.print()

    # Calcular intervalos de tiempo para los N clips
    step = max(1.0, (total_dur - max_duration) / max(1, clips - 1)) if total_dur > max_duration else 0.0

    rendered_clips = []

    for i in range(clips):
        clip_num = i + 1
        start_sec = min(i * step, max(0.0, total_dur - max_duration)) if total_dur > max_duration else 0.0
        dur_sec = min(max_duration, total_dur - start_sec)
        if dur_sec < 5.0:
            dur_sec = min(max_duration, total_dur)
            start_sec = max(0.0, total_dur - dur_sec)

        layout_style = LAYOUT_ROTATION[i % len(LAYOUT_ROTATION)]
        hook_tuple = preset["hooks"][i % len(preset["hooks"])]
        hook_title, hook_header = hook_tuple
        seo_title = preset["seo_titles"][i % len(preset["seo_titles"])]

        console.print(f"[bold cyan]── Clip {clip_num}/{clips} ──────────────────────────────────────[/bold cyan]")
        console.print(f"  ⏱ Segmento: {start_sec:.1f}s → {start_sec + dur_sec:.1f}s ({dur_sec:.1f}s)")
        console.print(f"  🎨 Layout: [bold green]{layout_style}[/bold green]")
        console.print(f"  🎣 Hook: [bold yellow]{hook_title}[/bold yellow]")

        # 1. Trim
        trimmed_abs, rel_video = trim_clip(str(video_file), start_sec, dur_sec, remotion_dir, clip_num)
        clip_info = {**video_info, "duration": dur_sec}

        # 2. Crop
        crop_pos, crop_meta = compute_crop_params(trimmed_abs, clip_info)

        # 3. Logo
        logo_path = copy_logo_to_remotion(remotion_dir)

        # 4. Props
        output_mp4 = str((output_dir / f"clip_{clip_num:02d}_{campaign_name.lower()}.mp4").resolve())
        seo_txt_path = output_dir / f"clip_{clip_num:02d}_seo.txt"

        props = {
            "videoPath": rel_video,
            "startTime": 0.0,
            "durationInSeconds": dur_sec,
            "fps": int(round(clip_info["fps"])),
            "cropMeta": crop_meta,
            "cropPositions": crop_pos,
            "words": [],
            "captionChunks": [],
            "impactMoments": make_impact_moments(dur_sec),
            "viralScore": 0.9,
            "useZoom": True,
            "useSubtitles": False,
            "subtitleStyle": "viral_yellow",
            "logoPath": logo_path,
            "layoutStyle": layout_style,
            "hookTitle": hook_title,
            "hookHeader": hook_header,
            "rankingItems": [],
        }

        # 5. Render
        console.print("  [dim]Renderizando...[/dim]")
        ok = render_with_remotion(remotion_dir, props, output_mp4, clip_num)

        if ok and Path(output_mp4).exists():
            # Guardar SEO txt
            with open(seo_txt_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"{campaign_name.upper()} — SEO CONTENT (Clip {clip_num}/{clips})\n")
                f.write(f"Source: {video_file.name} ({start_sec:.1f}s -> {start_sec + dur_sec:.1f}s)\n")
                f.write("=" * 60 + "\n\n")
                f.write("📌 TITULO SEO (copia esto como titulo):\n")
                f.write(f"{seo_title}\n\n")
                f.write("🎣 HOOK EN PANTALLA:\n")
                f.write(f"{hook_title}\n\n")
                f.write("📝 CAPTION COMPLETA (TikTok / Reels / Shorts):\n")
                f.write("-" * 60 + "\n")
                f.write(f"{seo_title}\n\n")
                f.write(f"{preset['cta']}\n\n")
                f.write(f"{preset['hashtags']}\n")
                f.write("-" * 60 + "\n")

            rendered_clips.append(output_mp4)
            console.print(f"  [bold green]✓ Creado: {Path(output_mp4).name}[/bold green]\n")
        else:
            console.print(f"  [bold red]❌ Error renderizando Clip {clip_num}[/bold red]\n")

    elapsed = time.time() - start_time
    console.print()
    console.print(Panel(
        f"[bold green]🎉 ¡Proceso Completado! ({len(rendered_clips)}/{clips} clips creados)[/bold green]\n\n"
        f"[cyan]📁 Carpeta de salida:[/cyan] {output_dir}\n"
        f"[cyan]⏱ Tiempo total:[/cyan] {elapsed / 60:.1f} minutos\n\n"
        f"[dim]Cada clip tiene su .txt con titulo SEO y caption lista para copiar.[/dim]",
        title=f"[bold white]{campaign_name} Campaign[/bold white]",
        border_style="green",
    ))



@app.command()
def multi(
    videos: list[str] = typer.Argument(..., help="2 o mas videos de entrada (ej. input/persona.mp4 input/gameplay.mp4)"),
    campaign: str = typer.Option("Lumena", "--campaign", "-c", help="Nombre de la campaña"),
    clips: int = typer.Option(5, "--clips", "-n", help="Número total de clips a generar (default: 5)"),
    max_duration: float = typer.Option(30.0, "--max-duration", "-d", help="Duración máxima de cada clip en segundos"),
):
    """
    🎬 Genera N clips ALTERNANDO entre 2 o más videos fuente.
    Ejemplo: Clip 1 = persona hablando, Clip 2 = gameplay, Clip 3 = persona...
    Cada clip tiene su propio hook, layout visual y SEO txt.
    """
    start_time = time.time()
    preset = get_preset(campaign)
    campaign_name = preset["name"]

    if len(videos) < 1:
        console.print("[bold red]❌ Debes pasar al menos 1 video o carpeta.[/bold red]")
        raise typer.Exit(1)

    console.print()
    console.print(Panel(
        f"[bold cyan]ViralClip — Multi-Video: {clips} Clips Alternados para {campaign_name}[/bold cyan]\n"
        f"[dim]Selección aleatoria de video + segmentos distintos garantizados[/dim]",
        border_style="cyan",
    ))
    console.print()

    project_root = os.path.dirname(os.path.abspath(__file__))
    remotion_dir = os.path.join(project_root, "remotion")
    output_dir = Path(project_root) / "output" / campaign_name
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = ["👤 Persona", "🎮 Gameplay", "📸 Extra"]

    # Resolver cada entrada: puede ser carpeta (escoge al azar) o archivo concreto
    # Construir la lista de "fuentes" con sus carpetas para poder rotar en cada clip
    sources = []  # lista de dicts: {"folder": str|None, "file": Path|None, "label": str}
    for idx, vp in enumerate(videos):
        p = Path(vp)
        if p.is_dir():
            sources.append({"folder": str(p), "file": None, "label": labels[idx % len(labels)]})
        elif p.is_file():
            sources.append({"folder": None, "file": p, "label": labels[idx % len(labels)]})
        else:
            console.print(f"[bold red]❌ No encontrado:[/bold red] {vp}")
            raise typer.Exit(1)

    n_sources = len(sources)
    console.print(f"  [bold]Fuentes disponibles ({n_sources}):[/bold]")
    for idx, src in enumerate(sources):
        if src["folder"]:
            n_files = len([f for f in os.listdir(src["folder"]) if f.endswith((".mp4",".mov",".avi",".mkv"))])
            console.print(f"  {src['label']}: 📁 {Path(src['folder']).name}/ ({n_files} videos)")
        else:
            console.print(f"  {src['label']}: 📹 {src['file'].name} (fijo)")
    console.print()
    console.print("  [bold yellow]Estructura de cada clip:[/bold yellow] 👤 Persona (10s hook) + 🎮 Gameplay (20s) = 30s")
    console.print("  [bold yellow]Extras:[/bold yellow] Subtítulos del hook • Impact flashes • Zoom agresivo\n")

    rendered_clips = []
    used_videos_per_source = {i: [] for i in range(n_sources)}
    used_starts_per_video = {}

    # Detectar el último número de clip existente para no sobrescribir (ej. si ya existen 5, empezar en 6)
    existing_clips = [f for f in os.listdir(output_dir) if f.startswith("clip_") and f.endswith(".mp4")]
    existing_nums = []
    for f in existing_clips:
        m = re.search(r"clip_(\d+)_", f)
        if m:
            existing_nums.append(int(m.group(1)))
    start_offset = max(existing_nums) if existing_nums else 0

    # Duraciones: persona como hook (10s) + gameplay como cuerpo (20s)
    persona_dur = min(10.0, max_duration * 0.35)
    gameplay_dur = max_duration - persona_dur

    def hook_to_caption_chunks(hook_text: str, dur: float) -> list:
        """Convierte el hook text en caption_chunks sincronizados con la sección de persona."""
        # Dividir en grupos de 2-3 palabras para subtítulos dinámicos
        words = hook_text.replace("🎮","").replace("🔥","").replace("👀","").replace("⏱","").replace("🚀","").replace("💰","").split()
        words = [w for w in words if w]
        if not words:
            return []
        # Grupos de 2 palabras máx
        groups = []
        for j in range(0, len(words), 2):
            groups.append(" ".join(words[j:j+2]))
        interval = dur / len(groups) if groups else dur
        chunks = []
        for j, grp in enumerate(groups):
            t_start = round(j * interval, 2)
            t_end   = round(min((j + 1) * interval, dur), 2)
            chunks.append({
                "words": [{"word": grp, "start": t_start, "end": t_end, "confidence": 0.95}],
                "start": t_start,
                "end":   t_end,
                "text":  grp,
            })
        return chunks

    def make_dynamic_impacts(total: float, transition_at: float) -> list:
        """Impact flashes: en la transición persona→gameplay + cada ~6s del gameplay."""
        moments = []
        # Flash de transición
        moments.append({"time": round(transition_at - 0.1, 2), "word": "!", "intensity": 1.0})
        moments.append({"time": round(transition_at + 0.1, 2), "word": "!", "intensity": 0.9})
        # Flashes durante el gameplay
        t = transition_at + 5.0
        intensities = [0.85, 0.70, 0.90, 0.75, 0.80]
        k = 0
        while t < total - 1.5:
            moments.append({"time": round(t, 2), "word": "!", "intensity": intensities[k % len(intensities)]})
            t += 6.0 + (k % 2) * 1.5
            k += 1
        return moments

    for i in range(clips):
        clip_num = start_offset + i + 1
        hook_tuple   = preset["hooks"][i % len(preset["hooks"])]
        hook_title, hook_header = hook_tuple
        seo_title    = preset["seo_titles"][i % len(preset["seo_titles"])]
        layout_style = LAYOUT_ROTATION[i % len(LAYOUT_ROTATION)]

        console.print(f"[bold cyan]── Clip {clip_num}/{start_offset + clips} ─────────────────────────────────────────[/bold cyan]")
        console.print(f"  🎨 Layout:  [bold green]{layout_style}[/bold green]")
        console.print(f"  🎣 Hook:    [bold yellow]{hook_title}[/bold yellow]")

        # ── Persona (fuente 0) ───────────────────────────────────────────────
        p_src = sources[0]
        if p_src["folder"]:
            p_vf = Path(smart_pick_video(p_src["folder"], avoid=used_videos_per_source[0], min_duration=8.0))
            used_videos_per_source[0].append(str(p_vf))
        else:
            p_vf = p_src["file"]
        p_info = get_video_info(str(p_vf))
        p_abs  = str(p_vf.resolve())
        p_used = used_starts_per_video.get(p_abs, [])

        # ── Gameplay (fuente 1) ──────────────────────────────────────────────
        g_src = sources[1] if n_sources > 1 else sources[0]
        g_src_idx = 1 if n_sources > 1 else 0
        if g_src["folder"]:
            g_vf = Path(smart_pick_video(g_src["folder"], avoid=used_videos_per_source[g_src_idx], min_duration=8.0))
            used_videos_per_source[g_src_idx].append(str(g_vf))
        else:
            g_vf = g_src["file"]
        g_info = get_video_info(str(g_vf))
        g_abs  = str(g_vf.resolve())
        g_used = used_starts_per_video.get(g_abs, [])

        # ── Calcular puntos de inicio y duración NATURAL del clip ─────────
        # Si la persona dura 15s y el gameplay dura 25s, el clip dura lo que dure naturalmente
        p_start = smart_pick_segment(str(p_vf), p_info["duration"], min(15.0, p_info["duration"]), p_used)
        g_start = smart_pick_segment(str(g_vf), g_info["duration"], min(25.0, g_info["duration"]), g_used)

        used_starts_per_video.setdefault(p_abs, []).append(p_start)
        used_starts_per_video.setdefault(g_abs, []).append(g_start)

        # Duración efectiva = lo que dure el video más corto desde su start_sec (sin congelados)
        p_avail = p_info["duration"] - p_start
        g_avail = g_info["duration"] - g_start
        clip_dur = round(min(p_avail, g_avail), 1)

        # Límites sanos: entre 10s y 45s
        if clip_dur > 45.0:
            clip_dur = 45.0
        elif clip_dur < 10.0:
            clip_dur = round(max(5.0, min(p_info["duration"], g_info["duration"])), 1)

        console.print(f"  👤 Persona:  [white]{p_vf.name}[/white]  ({p_start:.1f}s → {p_start + clip_dur:.1f}s)")
        console.print(f"  🎮 Gameplay: [white]{g_vf.name}[/white]  ({g_start:.1f}s → {g_start + clip_dur:.1f}s)")
        console.print(f"  ⏱ Duración natural: [bold yellow]{clip_dur:.1f}s[/bold yellow] (sin congelados)")

        # ── Componer persona + gameplay con layout dinámico ────────────────
        compose_style = COMPOSE_LAYOUTS[i % len(COMPOSE_LAYOUTS)]
        combined_abs, rel_video = compose_clips(
            str(p_vf), p_start,
            str(g_vf), g_start,
            clip_dur=clip_dur,
            remotion_dir=remotion_dir, clip_idx=clip_num,
            compose_style=compose_style,
        )
        combined_info = {**g_info, "duration": clip_dur, "width": 1080, "height": 1920}

        # ── Crop del clip combinado ──────────────────────────────────────────
        crop_pos, crop_meta = compute_crop_params(combined_abs, combined_info)

        # ── Subtítulos del hook auto-sincronizados ──────────────────────────
        hook_dur = min(6.0, clip_dur * 0.4)
        caption_chunks = hook_to_caption_chunks(hook_title, hook_dur)

        # ── Impact moments dinámicos ─────────────────────────────────────────
        impact_moments = make_dynamic_impacts(clip_dur, transition_at=min(4.0, clip_dur * 0.3))

        # ── Logo ─────────────────────────────────────────────────────────────
        logo_path = copy_logo_to_remotion(remotion_dir)

        # ── Output paths ─────────────────────────────────────────────────────
        output_mp4    = str((output_dir / f"clip_{clip_num:02d}_{campaign_name.lower()}.mp4").resolve())
        seo_txt_path  = output_dir / f"clip_{clip_num:02d}_seo.txt"

        props = {
            "videoPath":         rel_video,
            "startTime":         0.0,
            "durationInSeconds": clip_dur,
            "fps":               30,
            "cropMeta":          crop_meta,
            "cropPositions":     crop_pos,
            "words":             [],
            "captionChunks":     caption_chunks,
            "impactMoments":     impact_moments,
            "viralScore":        0.95,
            "useZoom":           True,
            "useSubtitles":      True,
            "subtitleStyle":     "viral_yellow",
            "logoPath":          logo_path,
            "layoutStyle":       layout_style,
            "hookTitle":         hook_title,
            "hookHeader":        hook_header,
            "rankingItems":      [],
        }

        console.print("  [dim]Renderizando...[/dim]")
        ok = render_with_remotion(remotion_dir, props, output_mp4, clip_num)

        if ok and Path(output_mp4).exists():
            size_mb = Path(output_mp4).stat().st_size / (1024 * 1024)
            with open(seo_txt_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"{campaign_name.upper()} — SEO CONTENT (Clip {clip_num}/{clips})\n")
                f.write(f"Layout: {compose_style} (Persona + Gameplay)\n")
                f.write(f"Persona: {p_vf.name} ({p_start:.1f}s → {p_start + persona_dur:.1f}s)\n")
                f.write(f"Gameplay: {g_vf.name} ({g_start:.1f}s → {g_start + gameplay_dur:.1f}s)\n")
                f.write("=" * 60 + "\n\n")
                f.write("TITULO SEO (copia esto como titulo):\n")
                f.write(f"{seo_title}\n\n")
                f.write("HOOK EN PANTALLA (primeros 10s - con subtítulos):\n")
                f.write(f"{hook_title}\n\n")
                f.write("CAPTION COMPLETA (TikTok / Reels / Shorts):\n")
                f.write("-" * 60 + "\n")
                f.write(f"{seo_title}\n\n")
                f.write(f"{preset['cta']}\n\n")
                f.write(f"{preset['hashtags']}\n")
                f.write("-" * 60 + "\n")

            rendered_clips.append(output_mp4)
            console.print(f"  [bold green]✓ Creado: {Path(output_mp4).name}  ({size_mb:.1f} MB)[/bold green]\n")
        else:
            console.print(f"  [bold red]❌ Error renderizando Clip {clip_num}[/bold red]\n")

    elapsed = time.time() - start_time
    source_names = " + ".join([
        Path(src["folder"]).name if src["folder"] else src["file"].name
        for src in sources
    ])
    console.print()
    console.print(Panel(
        f"[bold green]🎉 ¡Proceso Completado! ({len(rendered_clips)}/{clips} clips creados)[/bold green]\n\n"
        f"[cyan]📁 Carpeta de salida:[/cyan] {output_dir}\n"
        f"[cyan]⏱ Tiempo total:[/cyan] {elapsed / 60:.1f} minutos\n\n"
        f"[dim]Fuentes: {source_names}[/dim]\n"
        f"[dim]Cada clip: 👤 Persona + 🎮 Gameplay simultáneos con 3 layouts dinámicos[/dim]",
        title=f"[bold white]{campaign_name} — Multi-Video[/bold white]",
        border_style="green",
    ))


# ═══════════════════════════════════════════════════════════════════════════════
# POV COMMAND — Completely independent section
# Cinematic Short style: black bars + bold English hook + key point overlays
# Output → output/POV/  (never mixes with Lumena or other campaigns)
# ═══════════════════════════════════════════════════════════════════════════════

# ── POV Hooks (English) ────────────────────────────────────────────────────────
POV_HOOKS = [
    "POV: You just found\nthe game everyone's addicted to",
    "POV: This free game hits\ndifferent at 2am",
    "POV: You stayed up all night\nplaying this game",
    "POV: Your friends won't stop\ntexting you about this game",
    "POV: You discovered\nthe next big thing before everyone",
    "POV: This game is actually\nbetter than it looks",
    "POV: You open the app\nand lose track of time",
    "POV: You find a game\nworth playing for free",
    "POV: You can't stop playing\neven though it's 3am",
    "POV: You introduce your friends\nto this game and they never sleep again",
]

# ── Key Points (timed overlays shown during the clip) ─────────────────────────
POV_KEY_POINTS_SETS = [
    ["🌿 Catch rare Lumens in the wild", "⚔️  Battle players worldwide", "🔗 Play FREE → lumena.gg"],
    ["🧬 Build & evolve your team", "🗺️  Explore an open world", "🎮 Download now — link in bio"],
    ["⚡ Power up your Lumens", "🌍 Join millions of players", "🔗 lumena.gg — it's free"],
    ["🎯 Strategy meets adventure", "🔥 Real-time PvP battles", "🚀 Play free → link in bio"],
    ["💎 Rare creatures to discover", "🏆 Climb the global ranks", "🔗 Start playing at lumena.gg"],
]

# ── Windows font fallback chain ────────────────────────────────────────────────
_WIN_FONTS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]

def _find_font() -> str:
    """Returns first available bold font path on Windows."""
    for f in _WIN_FONTS:
        if Path(f).exists():
            return f.replace("/", "\\\\")
    return ""

def _escape_drawtext(text: str) -> str:
    """Escapes text for FFmpeg drawtext filter."""
    return (
        text.replace("\\", "\\\\")
            .replace("'", "\u2019")
            .replace(":", "\\:")
            .replace(",", "\\,")
    )


@app.command()
def pov(
    video_folder: str = typer.Argument(
        default="input/POV videos",
        help="Folder with source videos (put your videos here)"
    ),
    campaign: str   = typer.Option("POV", "--campaign", "-c",
        help="Campaign / output folder name (default: POV → output/POV/)"),
    clips: int      = typer.Option(5,    "--clips",   "-n",  help="Number of clips to generate"),
    max_dur: float  = typer.Option(30.0, "--max-duration", "-d",
        help="Max clip duration in seconds (natural end if shorter)"),
):
    """
    🎬 NEW SECTION — POV-Style Shorts (100% independent of Lumena/multi edits).

    Layout (9:16 portrait):
    ┌──────────────────────────────┐
    │  BLACK BAR (30%)             │ ← POV Hook (bold white text, English)
    ├──────────────────────────────┤
    │  VIDEO  (50%)                │ ← Source footage centered
    ├──────────────────────────────┤
    │  BLACK BAR (20%)             │ ← Key point overlay (timed)
    └──────────────────────────────┘

    Output → output/<campaign>/  (never touches output/Lumena/)
    """
    import random
    start_time = time.time()

    # ── Resolve paths ──────────────────────────────────────────────────────────
    project_root = os.path.dirname(os.path.abspath(__file__))
    src_dir      = Path(project_root) / video_folder
    output_dir   = Path(project_root) / "output" / campaign
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create input folder if missing
    src_dir.mkdir(parents=True, exist_ok=True)

    # Detect offset (continue numbering from existing clips)
    existing = [f for f in os.listdir(output_dir) if f.startswith("clip_") and f.endswith(".mp4")]
    offsets = []
    for f in existing:
        m = re.search(r"clip_(\d+)_", f)
        if m:
            offsets.append(int(m.group(1)))
    num_offset = max(offsets) if offsets else 0

    console.print()
    console.print(Panel(
        f"[bold magenta]🎬 POV Shorts Generator — {campaign}[/bold magenta]\n"
        f"[dim]Completely independent from Lumena / multi clips[/dim]\n\n"
        f"[cyan]Source folder:[/cyan]  {src_dir}\n"
        f"[cyan]Output folder:[/cyan]  {output_dir}\n"
        f"[cyan]Clips to create:[/cyan] {clips}  |  Starting at #{num_offset + 1}",
        border_style="magenta",
    ))
    console.print()

    # ── Collect source videos ──────────────────────────────────────────────────
    exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
    all_videos = [
        str(p) for p in src_dir.iterdir()
        if p.suffix.lower() in exts and p.is_file()
    ]

    if not all_videos:
        console.print(f"[bold red]❌ No videos found in:[/bold red] {src_dir}")
        console.print(f"[yellow]Put your source videos in:  {src_dir}[/yellow]")
        raise typer.Exit(1)

    console.print(f"  [bold]Found {len(all_videos)} source video(s)[/bold] in {src_dir.name}/\n")

    font_path = _find_font()
    used_videos: list[str] = []
    used_starts: dict[str, list[float]] = {}
    rendered: list[str] = []

    for i in range(clips):
        clip_num = num_offset + i + 1
        hook_raw  = POV_HOOKS[i % len(POV_HOOKS)]
        key_pts   = POV_KEY_POINTS_SETS[i % len(POV_KEY_POINTS_SETS)]

        console.print(f"[bold magenta]── Clip {clip_num}/{num_offset + clips} ──────────────────────────────────[/bold magenta]")
        console.print(f"  🎣 Hook: [bold yellow]{hook_raw.replace(chr(10), ' ')}[/bold yellow]")

        # ── Pick video ────────────────────────────────────────────────────────
        avoid = used_videos.copy()
        candidates = [v for v in all_videos if v not in avoid]
        if not candidates:
            used_videos.clear()
            candidates = all_videos
        video_path = random.choice(candidates)
        used_videos.append(video_path)

        vi     = get_video_info(video_path)
        v_dur  = vi["duration"]
        v_name = Path(video_path).name

        # ── Pick start segment ────────────────────────────────────────────────
        used_st = used_starts.get(video_path, [])
        clip_dur = min(max_dur, v_dur)
        max_start = max(0.0, v_dur - clip_dur)

        def not_overlapping(t: float) -> bool:
            return all(abs(t - s) > clip_dur * 0.5 for s in used_st)

        candidates_t = [t * max_start / 9 for t in range(10)]
        candidates_t = [t for t in candidates_t if not_overlapping(t)]
        start_sec = random.choice(candidates_t) if candidates_t else 0.0
        clip_dur  = min(clip_dur, v_dur - start_sec)

        used_starts.setdefault(video_path, []).append(start_sec)

        console.print(f"  📁 Source: [white]{v_name}[/white]  ({start_sec:.1f}s → {start_sec + clip_dur:.1f}s | {clip_dur:.1f}s natural)")

        # ── Output path ───────────────────────────────────────────────────────
        out_mp4 = output_dir / f"clip_{clip_num:02d}_{campaign.lower()}.mp4"
        out_txt = output_dir / f"clip_{clip_num:02d}_hook.txt"

        # ── Build FFmpeg filter ───────────────────────────────────────────────
        # Layout:  1080×1920 (9:16)
        #   Top bar:   30% = 576px  → hook text centered at y=240
        #   Video:     50% = 960px  → y offset = 576
        #   Bot bar:   20% = 384px  → key points at y=1560

        W, H      = 1080, 1920
        top_h     = int(H * 0.30)   # 576px  – hook area
        vid_h     = int(H * 0.50)   # 960px  – video area
        # bottom = remaining

        hook_text = _escape_drawtext(hook_raw)
        hook_lines = hook_raw.split("\n")
        font_size_hook = 58 if max(len(l) for l in hook_lines) < 30 else 48

        # Split hook into two draw-text calls for line1 / line2
        hook_y_base = top_h // 2
        if len(hook_lines) == 2:
            draw_hook = (
                f"drawtext=text='{_escape_drawtext(hook_lines[0])}':"
                f"fontfile='{font_path}':" if font_path else ""
                f"fontsize={font_size_hook}:fontcolor=white:"
                f"x=(w-text_w)/2:y={hook_y_base - font_size_hook - 6}:"
                f"shadowcolor=black@0.6:shadowx=3:shadowy=3,"
                f"drawtext=text='{_escape_drawtext(hook_lines[1])}':"
                f"fontfile='{font_path}':" if font_path else ""
                f"fontsize={font_size_hook}:fontcolor=white:"
                f"x=(w-text_w)/2:y={hook_y_base + 6}:"
                f"shadowcolor=black@0.6:shadowx=3:shadowy=3"
            )
        else:
            draw_hook = (
                f"drawtext=text='{hook_text}':"
                f"fontfile='{font_path}':" if font_path else ""
                f"fontsize={font_size_hook}:fontcolor=white:"
                f"x=(w-text_w)/2:y={hook_y_base - font_size_hook // 2}:"
                f"shadowcolor=black@0.6:shadowx=3:shadowy=3"
            )

        # Key points — 3 items, each shown for ~clip_dur/3 seconds
        seg = clip_dur / max(len(key_pts), 1)
        draw_kps = []
        kp_y = top_h + vid_h + 60  # inside bottom bar
        for ki, kp in enumerate(key_pts):
            t0 = round(ki * seg, 2)
            t1 = round((ki + 1) * seg, 2)
            kp_esc = _escape_drawtext(kp)
            kp_draw = (
                f"drawtext=text='{kp_esc}':"
                + (f"fontfile='{font_path}':" if font_path else "")
                + f"fontsize=36:fontcolor=white@0.92:"
                f"x=(w-text_w)/2:y={kp_y}:"
                f"shadowcolor=black@0.5:shadowx=2:shadowy=2:"
                f"enable='between(t,{t0},{t1})'"
            )
            draw_kps.append(kp_draw)

        # Build complete vf chain
        vf_parts = [
            # 1. Scale video to 1080×960 (fit center, black padding)
            f"scale={W}:{vid_h}:force_original_aspect_ratio=decrease",
            f"pad={W}:{vid_h}:(ow-iw)/2:(oh-ih)/2",
            # 2. Add black bars → full 1080×1920
            f"pad={W}:{H}:0:{top_h}",
            # 3. Normalize
            "setsar=1",
            "fps=30",
            # 4. Hook text
            draw_hook,
        ] + draw_kps

        vf_chain = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(start_sec, 3)),
            "-t",  str(round(clip_dur,  3)),
            "-i",  video_path,
            "-vf", vf_chain,
            "-af", "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-avoid_negative_ts", "make_zero",
            str(out_mp4),
        ]

        console.print("  [dim]Rendering POV clip...[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        if result.returncode == 0 and out_mp4.exists():
            size_mb = out_mp4.stat().st_size / (1024 * 1024)
            # Save hook txt
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"POV SHORT — Clip {clip_num}\n")
                f.write("=" * 60 + "\n\n")
                f.write("HOOK (screen text):\n")
                f.write(f"{hook_raw.replace(chr(10), ' ')}\n\n")
                f.write("KEY POINTS (timed overlays):\n")
                for j, kp in enumerate(key_pts, 1):
                    f.write(f"  {j}. {kp}\n")
                f.write("\nSEO CAPTION (copy-paste):\n")
                f.write("-" * 60 + "\n")
                f.write(f"{hook_raw.replace(chr(10), ' ')} 🎮\n\n")
                f.write("Play FREE → lumena.gg\n")
                f.write("#lumena #gaming #pokemongo #mobilegame #gamer #freetoplay\n")
                f.write("-" * 60 + "\n")

            rendered.append(str(out_mp4))
            console.print(f"  [bold green]✓ Created: {out_mp4.name}  ({size_mb:.1f} MB | {clip_dur:.1f}s)[/bold green]\n")
        else:
            console.print(f"  [bold red]❌ FFmpeg error on Clip {clip_num}[/bold red]")
            if result.stderr:
                console.print(f"  [dim red]{result.stderr[-300:]}[/dim red]\n")

    elapsed = time.time() - start_time
    console.print()
    console.print(Panel(
        f"[bold green]🎉 Done! ({len(rendered)}/{clips} clips created)[/bold green]\n\n"
        f"[cyan]Output folder:[/cyan]  {output_dir}\n"
        f"[cyan]Total time:[/cyan]     {elapsed / 60:.1f} min\n\n"
        f"[dim]Each clip: POV hook + key points overlays + cinematic bars[/dim]\n"
        f"[dim]Hook .txt files saved alongside each clip.[/dim]",
        title=f"[bold white]{campaign} — POV Shorts[/bold white]",
        border_style="magenta",
    ))


if __name__ == "__main__":
    app()

