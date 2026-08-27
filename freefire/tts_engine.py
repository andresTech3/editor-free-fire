"""
freefire/tts_engine.py
=======================
Motor de Text-to-Speech usando edge-tts (Microsoft Azure, gratis).

Genera archivos de audio para cada segmento del guion
con voz en español mexicano (energética, estilo gaming).
"""

import os
import asyncio
import subprocess
import tempfile
import json
from pathlib import Path
from dataclasses import dataclass

from .presets import TTS_VOICE, TTS_RATE, TTS_VOLUME


@dataclass
class TTSSegment:
    """Segmento de audio generado por TTS."""
    text: str
    audio_path: str
    duration: float


async def _generate_tts_async(
    text: str,
    output_path: str,
    voice: str = TTS_VOICE,
    rate: str = TTS_RATE,
    volume: str = TTS_VOLUME,
) -> str:
    """Genera audio TTS de forma asíncrona con edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
    )
    await communicate.save(output_path)
    return output_path


def generate_tts(
    text: str,
    output_path: str,
    voice: str = TTS_VOICE,
    rate: str = TTS_RATE,
) -> str:
    """
    Genera un archivo de audio MP3 con TTS.

    Args:
        text: Texto a convertir en voz
        output_path: Ruta del archivo de salida (.mp3)
        voice: Voz de edge-tts a usar
        rate: Velocidad de habla (ej: "+15%")

    Returns:
        Ruta del archivo generado
    """
    try:
        asyncio.run(_generate_tts_async(text, output_path, voice, rate))
    except RuntimeError:
        # Si ya hay un event loop corriendo (ej. en Jupyter), usar este workaround
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                _generate_tts_async(text, output_path, voice, rate)
            )
        finally:
            loop.close()

    return output_path


def get_audio_duration(audio_path: str) -> float:
    """Obtiene la duración de un archivo de audio con ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", audio_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        return 2.0  # Duración fallback


def mp3_to_wav(mp3_path: str, wav_path: str) -> str:
    """Convierte MP3 a WAV PCM para mezcla con FFmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", mp3_path,
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
        wav_path,
    ]
    subprocess.run(cmd, capture_output=True)
    return wav_path


def generate_script_audio(
    hook_voice: str,
    scene_voices: list[str],
    cta_voice: str,
    output_dir: str,
    voice: str = TTS_VOICE,
    rate: str = TTS_RATE,
) -> dict:
    """
    Genera todos los archivos de audio del guion completo.

    Args:
        hook_voice: Texto de voz del hook
        scene_voices: Lista de textos de voz de cada escena
        cta_voice: Texto de voz del CTA
        output_dir: Directorio donde guardar los archivos
        voice: Voz TTS a usar
        rate: Velocidad de habla

    Returns:
        Diccionario con las rutas y duraciones:
        {
            "hook": TTSSegment,
            "scenes": [TTSSegment, ...],
            "cta": TTSSegment,
            "total_duration": float,
        }
    """
    os.makedirs(output_dir, exist_ok=True)
    result = {"scenes": []}

    # ── Hook audio ──
    hook_mp3 = os.path.join(output_dir, "tts_hook.mp3")
    hook_wav = os.path.join(output_dir, "tts_hook.wav")
    generate_tts(hook_voice, hook_mp3, voice, rate)
    mp3_to_wav(hook_mp3, hook_wav)
    hook_dur = get_audio_duration(hook_wav)
    result["hook"] = TTSSegment(text=hook_voice, audio_path=hook_wav, duration=hook_dur)

    # ── Scene audios ──
    for i, scene_text in enumerate(scene_voices):
        scene_mp3 = os.path.join(output_dir, f"tts_scene_{i:02d}.mp3")
        scene_wav = os.path.join(output_dir, f"tts_scene_{i:02d}.wav")
        generate_tts(scene_text, scene_mp3, voice, rate)
        mp3_to_wav(scene_mp3, scene_wav)
        scene_dur = get_audio_duration(scene_wav)
        result["scenes"].append(
            TTSSegment(text=scene_text, audio_path=scene_wav, duration=scene_dur)
        )

    # ── CTA audio ──
    cta_mp3 = os.path.join(output_dir, "tts_cta.mp3")
    cta_wav = os.path.join(output_dir, "tts_cta.wav")
    generate_tts(cta_voice, cta_mp3, voice, rate)
    mp3_to_wav(cta_mp3, cta_wav)
    cta_dur = get_audio_duration(cta_wav)
    result["cta"] = TTSSegment(text=cta_voice, audio_path=cta_wav, duration=cta_dur)

    # ── Total ──
    total = hook_dur + sum(s.duration for s in result["scenes"]) + cta_dur
    result["total_duration"] = total

    return result


def concatenate_audio(
    audio_segments: list[str],
    output_path: str,
    gap: float = 0.1,
) -> str:
    """
    Concatena múltiples archivos de audio con un gap de silencio entre ellos.

    Args:
        audio_segments: Lista de rutas a archivos WAV
        output_path: Ruta de salida
        gap: Silencio entre segmentos (segundos)

    Returns:
        Ruta del archivo concatenado
    """
    tmp_dir = tempfile.gettempdir()
    concat_list = os.path.join(tmp_dir, "ff_tts_concat.txt")

    # Crear archivo de silencio
    silence_path = os.path.join(tmp_dir, "ff_silence.wav")
    cmd_silence = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(gap),
        "-acodec", "pcm_s16le",
        silence_path,
    ]
    subprocess.run(cmd_silence, capture_output=True)

    # Crear lista de concat
    with open(concat_list, "w", encoding="utf-8") as f:
        for i, seg_path in enumerate(audio_segments):
            f.write(f"file '{seg_path.replace(os.sep, '/')}'\n")
            if i < len(audio_segments) - 1 and gap > 0:
                f.write(f"file '{silence_path.replace(os.sep, '/')}'\n")

    # Concatenar
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True)

    # Cleanup
    try:
        os.remove(concat_list)
        os.remove(silence_path)
    except Exception:
        pass

    return output_path
