"""
freefire/composer.py
=====================
Motor de composición FFmpeg para el estilo "Código Headshot".

Construye el video final replicando la estructura, sincronización A/V
y animaciones alternadas paso-a-paso del video de referencia:

  1. Hook Intro      — Entrada alternada por elementos (Texto t=0.05s -> Sensibilidad t=0.15s -> Avatar t=0.35s)
  2. Sensibilidad    — Animaciones laterales cruzadas (Tabla desde izquierda t=0.15s, Avatar desde derecha t=0.35s)
  3. Gameplay        — A/V sync perfecto ultrarrápido (Two-stage seeking: fast -ss + exact -ss)
  4. CTA             — Entrada escalonada de elementos + badge final

Pipeline:
  1. Pre-renderizar cada segmento con animaciones secuenciales por capa
  2. Concatenar segmentos
  3. Mezclar audio: TTS (vol 1.0) + Audio Juego A/V Sync (vol 0.25) + SFX (vol 0.5)
  4. Agregar logo watermark permanente
"""

import os
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from .presets import (
    AVATAR_PATH, AVATAR_CUTOUT_PATH, LOGO_PATH, SENSIBILIDAD_PATH, SENSIBILIDAD_CROPPED_PATH,
    SFX_BOOM, SFX_WHOOSH, SFX_VINE_BOOM, SFX_DING,
    OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS,
    get_font_path,
)

RANKING_BOARD_PATH = str(Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "assets" / "video free fire" / "ranking_board.png")
REGIONAL_TOP_PATH = str(Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "assets" / "video free fire" / "regional_top.png")


W = OUTPUT_WIDTH
H = OUTPUT_HEIGHT
FPS = OUTPUT_FPS


def _strip_emojis(text: str) -> str:
    """Remove emoji characters that FFmpeg drawtext cannot render."""
    return "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("So", "Sk", "Sc", "Cn")
        or ch in ("#", "%", "*")
    ).strip()


def _escape_text(text: str) -> str:
    """Escapa texto para FFmpeg drawtext filter."""
    text = _strip_emojis(text)
    return (
        text.replace("\\", "\\\\")
            .replace("'", "\u2019")
            .replace(":", "\\:")
            .replace(";", "\\;")
            .replace("%", "%%")
    )


def _font_arg() -> str:
    """Returns the fontfile= argument for drawtext, or empty string."""
    font = get_font_path()
    if font:
        return f"fontfile='{font}':"
    return ""


def _run_ffmpeg(cmd: list, label: str = "") -> bool:
    """Ejecuta un comando FFmpeg y retorna True si tuvo éxito."""
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        stderr = result.stderr or ""
        print(f"  [FFmpeg error{f' ({label})' if label else ''}]: {stderr[-500:]}")
        return False
    return True


def _get_duration(path: str) -> float:
    """Obtiene la duración de un archivo multimedia."""
    import json
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return float(json.loads(r.stdout).get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def _build_drawtext(text: str, fontsize: int = 68,
                    fontcolor: str = "white", borderw: int = 4,
                    x: str = "(w-text_w)/2", y: str | int = "h/2",
                    enable: str = "") -> str:
    """Builds a single drawtext filter string with proper escaping."""
    escaped = _escape_text(text)
    font = _font_arg()
    parts = [
        f"drawtext=text='{escaped}'",
        font.rstrip(":") if font else None,
        f"fontsize={fontsize}",
        f"fontcolor={fontcolor}",
        f"borderw={borderw}",
        f"bordercolor=black",
        f"shadowcolor=black@0.7",
        f"shadowx=3",
        f"shadowy=3",
        f"x={x}",
        f"y={y}",
    ]
    if enable:
        parts.append(f"enable='{enable}'")
    return ":".join(p for p in parts if p is not None)


# ═════════════════════════════════════════════════════════════════════════════
# SEGMENT RENDERERS — Animaciones alternadas por elemento
# ═════════════════════════════════════════════════════════════════════════════


def render_hook_segment(
    title_text: str,
    duration: float,
    output_path: str,
    gameplay_video: str | None = None,
    avatar_path: str = AVATAR_PATH,
    cutout_path: str = AVATAR_CUTOUT_PATH,
    sensi_path: str = SENSIBILIDAD_CROPPED_PATH,
) -> bool:
    """
    Segmento 1: HOOK INTRO — Entrada alternada por elementos.
      - Fondo: Video de gameplay difuminado en movimiento (blur 22:4, color balance)
      - Avatar: Tamaño grande y cerca (desde el muslo hacia arriba, scale=-1:1750)
      - Texto: Título grande en 2 líneas con resaltado de palabras clave en caja semi-transparente
    """
    font = _font_arg()
    lines = title_text.split("\n") if "\n" in title_text else [title_text]

    line1 = lines[0] if lines else "SENSIBILIDAD"
    line2 = lines[1] if len(lines) > 1 else "TODO ROJO"

    escaped1 = _escape_text(line1)
    escaped2 = _escape_text(line2)

    if not os.path.exists(cutout_path) or not os.path.exists(sensi_path):
        from .asset_processor import prepare_assets
        prepare_assets()

    has_bg_video = gameplay_video and os.path.exists(gameplay_video)
    bg_input = ["-ss", "0", "-i", gameplay_video] if has_bg_video else ["-loop", "1", "-t", str(round(duration, 3)), "-i", avatar_path]

    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=22:4,colorbalance=bs=-0.35:gs=-0.35:rs=-0.15,eq=contrast=1.1,setsar=1,fps={FPS}[bg];"
        f"[1:v]scale=960:-1[sensi];"
        f"[2:v]scale=-1:1750[avatar];"
        f"[bg][sensi]overlay=(W-w)/2:'(H-h)/2-40-(1-min(max(0\\,t-0.15)*4\\,1))*140'[bg_sensi];"
        f"[bg_sensi][avatar]overlay=(W-w)/2:'H-h+180+(1-min(max(0\\,t-0.35)*3\\,1))*250'[bg_avatar];"
        f"[bg_avatar]drawtext=text='{escaped1}':"
        + (font if font else "")
        + f"fontsize=74:fontcolor=white:borderw=5:bordercolor=black:"
        f"box=1:boxcolor=black@0.70:boxborderw=12:"
        f"shadowcolor=black@0.8:shadowx=4:shadowy=4:x=(w-text_w)/2:y=130:enable='gte(t\\,0.05)',"
        f"drawtext=text='{escaped2}':"
        + (font if font else "")
        + f"fontsize=72:fontcolor=#FFD700:borderw=5:bordercolor=black:"
        f"box=1:boxcolor=black@0.75:boxborderw=14:"
        f"shadowcolor=black@0.9:shadowx=4:shadowy=4:x=(w-text_w)/2:y=250:enable='gte(t\\,0.25)'"
        f"[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        *bg_input,
        "-loop", "1", "-t", str(round(duration, 3)), "-i", sensi_path,
        "-loop", "1", "-t", str(round(duration, 3)), "-i", cutout_path,
        "-f", "lavfi", "-t", str(round(duration, 3)),
        "-i", "anullsrc=r=44100:cl=stereo",
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "3:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-t", str(round(duration, 3)),
        output_path,
    ]
    return _run_ffmpeg(cmd, "hook")


def render_sensibilidad_segment(
    duration: float,
    output_path: str,
    gameplay_video: str | None = None,
    sensibilidad_path: str = SENSIBILIDAD_CROPPED_PATH,
    avatar_path: str = AVATAR_PATH,
    cutout_path: str = AVATAR_CUTOUT_PATH,
    subtitle_text: str = "SENSIBILIDAD",
) -> bool:
    """
    Segmento 2: SENSIBILIDAD — Animaciones alternadas laterales cruzadas.
      - Fondo: Video de gameplay difuminado en movimiento
      - Avatar: Tamaño grande y cerca (desde el muslo hacia arriba, scale=-1:1750)
      - Tabla: Sliders de sensibilidad recortados y destacados
      - Texto: Subtítulo con resaltado de palabras clave en amarillo/rojo
    """
    font = _font_arg()
    escaped = _escape_text(subtitle_text)

    if not os.path.exists(cutout_path) or not os.path.exists(sensibilidad_path):
        from .asset_processor import prepare_assets
        prepare_assets()

    has_bg_video = gameplay_video and os.path.exists(gameplay_video)
    bg_input = ["-ss", "1", "-i", gameplay_video] if has_bg_video else ["-loop", "1", "-t", str(round(duration, 3)), "-i", avatar_path]

    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=25:6,colorbalance=bs=-0.4:gs=-0.4:rs=-0.2,eq=contrast=1.1,setsar=1,fps={FPS}[bg];"
        f"[1:v]scale=960:-1[sensi];"
        f"[2:v]scale=-1:1750[avatar];"
        f"[bg][sensi]overlay='(W-w)/2 - (1-min(max(0\\,t-0.15)*4\\,1))*300':'(H-h)/2-40'[bg_sensi];"
        f"[bg_sensi][avatar]overlay='(W-w)/2 + (1-min(max(0\\,t-0.35)*4\\,1))*300':'H-h+180'[bg_avatar];"
        f"[bg_avatar]drawtext=text='{escaped}':"
        + (font if font else "")
        + f"fontsize=78:fontcolor=white:borderw=5:bordercolor=black:"
        f"box=1:boxcolor=black@0.65:boxborderw=12:"
        f"shadowcolor=black@0.8:shadowx=4:shadowy=4:x=(w-text_w)/2:y=120:enable='gte(t\\,0.05)',"
        f"drawtext=text='TODO ROJO 🔥':"
        + (font if font else "")
        + f"fontsize=76:fontcolor=#FF0033:borderw=5:bordercolor=black:"
        f"box=1:boxcolor=black@0.70:boxborderw=14:"
        f"shadowcolor=black@0.9:shadowx=4:shadowy=4:x=(w-text_w)/2:y=230:enable='gte(t\\,0.25)'"
        f"[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        *bg_input,
        "-loop", "1", "-t", str(round(duration, 3)), "-i", sensibilidad_path,
        "-loop", "1", "-t", str(round(duration, 3)), "-i", cutout_path,
        "-f", "lavfi", "-t", str(round(duration, 3)),
        "-i", "anullsrc=r=44100:cl=stereo",
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "3:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-t", str(round(duration, 3)),
        output_path,
    ]
    return _run_ffmpeg(cmd, "sensibilidad")


def render_gameplay_segment(
    gameplay_video: str,
    start_time: float,
    duration: float,
    overlay_text: str,
    output_path: str,
) -> bool:
    """
    Segmento de GAMEPLAY individual.
    Búsqueda en 2 etapas (Fast seek + Exact trim) con texto gigante resaltado en caja.
    """
    fast_ss = max(0.0, start_time - 3.0)
    exact_ss = start_time - fast_ss

    text_y = int(H * 0.78)
    escaped = _escape_text(overlay_text)
    font = _font_arg()

    dt = (
        f"drawtext=text='{escaped}':"
        + (font if font else "")
        + f"fontsize=84:fontcolor=#FFD700:borderw=6:bordercolor=black:"
        f"box=1:boxcolor=black@0.65:boxborderw=14:"
        f"shadowcolor=black@0.9:shadowx=4:shadowy=4:"
        f"x=(w-text_w)/2:y={text_y}:enable='gte(t\\,0.1)'"
    )

    use_ranking = "PROFESIONAL" in overlay_text.upper() and os.path.exists(RANKING_BOARD_PATH)
    use_regional = ("JUGADOR" in overlay_text.upper() or "RANKED" in overlay_text.upper()) and os.path.exists(REGIONAL_TOP_PATH)

    if use_ranking:
        fc = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"eq=contrast=1.15:saturation=1.3:brightness=0.02,setsar=1,fps={FPS}[bg];"
            f"[1:v]scale=920:-1[rank];"
            f"[bg][rank]overlay=(W-w)/2:'(H-h)/2-50-(1-min(t*4\\,1))*100'[with_rank];"
            f"[with_rank]{dt}[vout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(fast_ss, 3)),
            "-i", gameplay_video,
            "-loop", "1", "-t", str(round(duration, 3)), "-i", RANKING_BOARD_PATH,
            "-ss", str(round(exact_ss, 3)),
            "-t", str(round(duration, 3)),
            "-filter_complex", fc,
            "-map", "[vout]", "-map", "0:a",
            "-af", "aresample=async=1:first_pts=0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
    elif use_regional:
        fc = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"eq=contrast=1.15:saturation=1.3:brightness=0.02,setsar=1,fps={FPS}[bg];"
            f"[1:v]scale=980:-1[reg];"
            f"[bg][reg]overlay=(W-w)/2:'(H-h)/2-40-(1-min(t*4\\,1))*100'[with_reg];"
            f"[with_reg]{dt}[vout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(fast_ss, 3)),
            "-i", gameplay_video,
            "-loop", "1", "-t", str(round(duration, 3)), "-i", REGIONAL_TOP_PATH,
            "-ss", str(round(exact_ss, 3)),
            "-t", str(round(duration, 3)),
            "-filter_complex", fc,
            "-map", "[vout]", "-map", "0:a",
            "-af", "aresample=async=1:first_pts=0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
    else:
        vf_chain = ",".join([
            f"scale={W}:{H}:force_original_aspect_ratio=increase",
            f"crop={W}:{H}",
            "eq=contrast=1.15:saturation=1.3:brightness=0.02",
            "setsar=1",
            f"fps={FPS}",
            dt,
        ])
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(fast_ss, 3)),
            "-i", gameplay_video,
            "-ss", str(round(exact_ss, 3)),
            "-t", str(round(duration, 3)),
            "-vf", vf_chain,
            "-af", "aresample=async=1:first_pts=0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

    return _run_ffmpeg(cmd, f"gameplay_{overlay_text}")


def render_cta_segment(
    gameplay_video: str,
    start_time: float,
    duration: float,
    cta_text: str,
    badge_text: str,
    output_path: str,
    sensibilidad_path: str = SENSIBILIDAD_CROPPED_PATH,
    cutout_path: str = AVATAR_CUTOUT_PATH,
) -> bool:
    """
    Segmento CTA Final — Con fondo difuminado en movimiento, avatar grande desde el muslo y texto destacado.
    """
    fast_ss = max(0.0, start_time - 3.0)
    exact_ss = start_time - fast_ss

    tmp_dir = tempfile.gettempdir()
    bg_clip = os.path.join(tmp_dir, "ff_cta_bg.mp4")

    bg_vf = ",".join([
        f"scale={W}:{H}:force_original_aspect_ratio=increase",
        f"crop={W}:{H}",
        "boxblur=20:4",
        "colorbalance=bs=-0.3:gs=-0.3:rs=-0.15",
        "eq=brightness=-0.1:contrast=1.15",
        "setsar=1",
        f"fps={FPS}",
    ])

    cmd_bg = [
        "ffmpeg", "-y",
        "-ss", str(round(fast_ss, 3)),
        "-i", gameplay_video,
        "-ss", str(round(exact_ss, 3)),
        "-t", str(round(duration, 3)),
        "-vf", bg_vf,
        "-af", "aresample=async=1:first_pts=0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        bg_clip,
    ]
    if not _run_ffmpeg(cmd_bg, "cta_bg"):
        return False

    escaped_cta = _escape_text(cta_text)
    escaped_badge = _escape_text(badge_text)
    font = _font_arg()

    if not os.path.exists(cutout_path) or not os.path.exists(sensibilidad_path):
        from .asset_processor import prepare_assets
        prepare_assets()

    fc = (
        f"[1:v]scale=960:-1[sensi];"
        f"[2:v]scale=-1:1750[avatar];"
        f"[0:v][sensi]overlay=(W-w)/2:'(H-h)/2-40-(1-min(max(0\\,t-0.15)*4\\,1))*120'[bg_sensi];"
        f"[bg_sensi][avatar]overlay=(W-w)/2:'H-h+180+(1-min(max(0\\,t-0.35)*3\\,1))*200'[bg_avatar];"
        f"[bg_avatar]drawtext=text='{escaped_cta}':"
        + (font if font else "")
        + f"fontsize=74:fontcolor=#FFD700:borderw=5:bordercolor=black:"
        f"box=1:boxcolor=black@0.70:boxborderw=14:"
        f"shadowcolor=black@0.9:shadowx=4:shadowy=4:x=(w-text_w)/2:y=120:enable='gte(t\\,0.05)',"
        f"drawtext=text='{escaped_badge}':"
        + (font if font else "")
        + f"fontsize=64:fontcolor=#FF0033:borderw=5:bordercolor=black:"
        f"box=1:boxcolor=black@0.70:boxborderw=12:"
        f"shadowcolor=black@0.9:shadowx=4:shadowy=4:x=(w-text_w)/2:y=h-150:enable='gte(t\\,0.40)'"
        f"[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_clip,
        "-loop", "1", "-t", str(round(duration, 3)), "-i", sensibilidad_path,
        "-loop", "1", "-t", str(round(duration, 3)), "-i", cutout_path,
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]
    ok = _run_ffmpeg(cmd, "cta")

    try:
        os.remove(bg_clip)
    except Exception:
        pass

    return ok


# ═════════════════════════════════════════════════════════════════════════════
# COMPOSICIÓN FINAL — Ensamblaje A/V Sync + Audio mezclado
# ═════════════════════════════════════════════════════════════════════════════


def compose_final_video(
    segment_paths: list[str],
    tts_audio_path: str,
    output_path: str,
    logo_path: str = LOGO_PATH,
    sfx_boom_path: str = SFX_BOOM,
) -> bool:
    """
    Ensambla el video final concatenando todos los segmentos con A/V sync exacto.
    Mezcla 3 pistas de audio:
      - 0:a Audio del Juego mantenido al 25% de volumen (`volume=0.25`)
      - 1:a Audio TTS Narración al 100% de volumen (`volume=1.0`)
      - 2:a SFX Vine Boom / Impact al 50% de volumen (`volume=0.50`)
    """
    tmp_dir = tempfile.gettempdir()

    concat_list = os.path.join(tmp_dir, "ff_concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg_path in segment_paths:
            f.write(f"file '{seg_path.replace(os.sep, '/')}'\n")

    concat_video = os.path.join(tmp_dir, "ff_concat_raw.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        concat_video,
    ]
    if not _run_ffmpeg(cmd_concat, "concat"):
        return False

    video_dur = _get_duration(concat_video)
    with_audio = os.path.join(tmp_dir, "ff_with_audio.mp4")

    if os.path.exists(sfx_boom_path):
        audio_filter = (
            f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.25[game_bg];"
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=1.0,apad=whole_dur={round(video_dur, 3)}[tts_padded];"
            f"[2:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.5,adelay=150|150[sfx];"
            f"[game_bg][tts_padded][sfx]amix=inputs=3:duration=first:dropout_transition=1[aout]"
        )
        cmd_audio = [
            "ffmpeg", "-y",
            "-i", concat_video,
            "-i", tts_audio_path,
            "-i", sfx_boom_path,
            "-filter_complex", audio_filter,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            with_audio,
        ]
    else:
        audio_filter = (
            f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.25[game_bg];"
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=1.0,apad=whole_dur={round(video_dur, 3)}[tts_padded];"
            f"[game_bg][tts_padded]amix=inputs=2:duration=first:dropout_transition=1[aout]"
        )
        cmd_audio = [
            "ffmpeg", "-y",
            "-i", concat_video,
            "-i", tts_audio_path,
            "-filter_complex", audio_filter,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            with_audio,
        ]

    if not _run_ffmpeg(cmd_audio, "audio_mix"):
        with_audio = concat_video

    # ── Logo Watermark (Top Right to avoid overlapping center titles) ─────
    if os.path.exists(logo_path):
        logo_w = int(W * 0.22)
        logo_margin = 30

        logo_filter = (
            f"[1:v]scale={logo_w}:-1,format=rgba,"
            f"colorchannelmixer=aa=0.75[logo];"
            f"[0:v][logo]overlay=W-w-{logo_margin}:{logo_margin}[vout]"
        )

        cmd_logo = [
            "ffmpeg", "-y",
            "-i", with_audio,
            "-i", logo_path,
            "-filter_complex", logo_filter,
            "-map", "[vout]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        ok = _run_ffmpeg(cmd_logo, "logo_watermark")
    else:
        cmd_final = [
            "ffmpeg", "-y",
            "-i", with_audio,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        ok = _run_ffmpeg(cmd_final, "final_render")

    # ── Cleanup ──────────────────────────────────────────────────────────
    for tmp_file in [concat_list, concat_video, with_audio]:
        try:
            if tmp_file != output_path and os.path.exists(tmp_file):
                os.remove(tmp_file)
        except Exception:
            pass

    return ok and os.path.exists(output_path)
