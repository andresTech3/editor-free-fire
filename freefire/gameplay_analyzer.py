"""
freefire/gameplay_analyzer.py
==============================
Analiza videos de gameplay de Free Fire para detectar automáticamente
los mejores momentos (kills, headshots, acción frenética).

Usa análisis de energía de audio (RMS) y detección de cambios de escena
para encontrar los segmentos más intensos del gameplay.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass


@dataclass
class GameplayMoment:
    """Un momento detectado en el gameplay."""
    start: float       # Segundo de inicio
    end: float         # Segundo de fin
    energy: float      # Nivel de energía (0-1)
    scene_changes: int  # Número de cambios de escena en el segmento


def get_video_duration(video_path: str) -> float:
    """Obtiene la duración del video con ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def get_video_info(video_path: str) -> dict:
    """Obtiene resolución, fps y duración del video."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        data = json.loads(result.stdout)
        video_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "video"), {}
        )
        audio_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "audio"), None
        )
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
    except Exception:
        return {
            "width": 1920, "height": 1080, "fps": 30.0,
            "duration": 30.0, "has_audio": False,
        }


def analyze_audio_energy(video_path: str, window_size: float = 0.5) -> list[tuple[float, float]]:
    """
    Analiza la energía de audio del video usando FFmpeg astats filter.

    Returns:
        Lista de (timestamp, energy_normalized) ordenada por energía descendente
    """
    tmp_dir = tempfile.gettempdir()
    wav_path = os.path.join(tmp_dir, "ff_analysis.wav")

    # Extraer audio a WAV mono
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
        wav_path,
    ]
    subprocess.run(cmd, capture_output=True)

    if not os.path.exists(wav_path):
        return []

    try:
        import numpy as np

        # Leer WAV raw
        import wave
        with wave.open(wav_path, "rb") as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

        if len(samples) == 0:
            return []

        # Normalizar a [-1, 1]
        samples = samples / 32768.0

        # Calcular RMS en ventanas
        window_samples = int(window_size * sr)
        energies = []

        for i in range(0, len(samples) - window_samples, window_samples // 2):
            window = samples[i:i + window_samples]
            rms = float(np.sqrt(np.mean(window ** 2)))
            timestamp = i / sr
            energies.append((timestamp, rms))

        if not energies:
            return []

        # Normalizar energías a [0, 1]
        max_energy = max(e for _, e in energies)
        if max_energy > 0:
            energies = [(t, e / max_energy) for t, e in energies]

        return energies

    except ImportError:
        # Fallback sin numpy: distribuir uniformemente
        duration = get_video_duration(video_path)
        n_segments = max(1, int(duration / window_size))
        return [(i * window_size, 0.5 + 0.3 * (i % 3 == 0)) for i in range(n_segments)]

    finally:
        try:
            os.remove(wav_path)
        except Exception:
            pass


def detect_scene_changes(video_path: str, threshold: float = 0.3) -> list[float]:
    """
    Detecta cambios de escena usando el filtro 'select' de FFmpeg
    con scene change detection.

    Returns:
        Lista de timestamps donde ocurren cambios de escena
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-f", "lavfi",
        "-i", f"movie='{video_path.replace(os.sep, '/')}',select='gt(scene\\,{threshold})'",
        "-show_entries", "frame=pkt_pts_time",
        "-print_format", "json",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
        data = json.loads(result.stdout)
        frames = data.get("frames", [])
        return [float(f.get("pkt_pts_time", 0)) for f in frames]
    except Exception:
        # Fallback: asumir cambios de escena cada 2 segundos
        duration = get_video_duration(video_path)
        return [i * 2.0 for i in range(int(duration / 2))]


def find_best_moments(
    video_path: str,
    num_moments: int = 5,
    moment_duration: float = 2.0,
    min_gap: float = 3.0,
) -> list[GameplayMoment]:
    """
    Encuentra los N mejores momentos del gameplay.

    Args:
        video_path: Ruta al video de gameplay
        num_moments: Cuántos momentos extraer
        moment_duration: Duración de cada momento (segundos)
        min_gap: Separación mínima entre momentos (evitar solapamiento)

    Returns:
        Lista de GameplayMoment ordenada cronológicamente
    """
    video_dur = get_video_duration(video_path)

    if video_dur < moment_duration * 2:
        # Video muy corto — usar todo
        return [GameplayMoment(0, video_dur, 1.0, 0)]

    # Analizar energía de audio
    energies = analyze_audio_energy(video_path, window_size=0.5)

    if not energies:
        # Fallback: distribuir momentos uniformemente
        step = video_dur / (num_moments + 1)
        return [
            GameplayMoment(
                start=round(step * (i + 1), 2),
                end=round(min(step * (i + 1) + moment_duration, video_dur), 2),
                energy=0.7,
                scene_changes=0,
            )
            for i in range(num_moments)
        ]

    # Calcular energía promedio por ventana de moment_duration
    scored_windows = []
    for i, (t, energy) in enumerate(energies):
        if t + moment_duration > video_dur:
            break
        # Promedio de energía en la ventana
        window_energies = [
            e for ts, e in energies
            if t <= ts < t + moment_duration
        ]
        if window_energies:
            avg_energy = sum(window_energies) / len(window_energies)
            scored_windows.append((t, avg_energy))

    # Ordenar por energía descendente
    scored_windows.sort(key=lambda x: x[1], reverse=True)

    # Seleccionar los mejores sin solapamiento
    selected = []
    for t, energy in scored_windows:
        if len(selected) >= num_moments:
            break
        # Verificar que no se solape con los ya seleccionados
        overlaps = any(abs(t - s.start) < min_gap for s in selected)
        if not overlaps:
            selected.append(GameplayMoment(
                start=round(t, 2),
                end=round(min(t + moment_duration, video_dur), 2),
                energy=round(energy, 3),
                scene_changes=0,
            ))

    # Si no encontramos suficientes, rellenar con distribución uniforme
    if len(selected) < num_moments:
        step = video_dur / (num_moments + 1)
        for i in range(num_moments - len(selected)):
            t = step * (i + 1)
            if not any(abs(t - s.start) < min_gap for s in selected):
                selected.append(GameplayMoment(
                    start=round(t, 2),
                    end=round(min(t + moment_duration, video_dur), 2),
                    energy=0.5,
                    scene_changes=0,
                ))

    # Ordenar cronológicamente para el video final
    selected.sort(key=lambda m: m.start)

    return selected[:num_moments]


def select_gameplay_clips(
    video_path: str,
    total_gameplay_duration: float,
    num_clips: int = 4,
) -> list[tuple[float, float]]:
    """
    Selecciona clips de gameplay para llenar exactamente la duración necesaria.

    Args:
        video_path: Ruta al video de gameplay
        total_gameplay_duration: Duración total que deben cubrir los clips
        num_clips: Número de clips a seleccionar

    Returns:
        Lista de (start_sec, duration_sec) para cada clip
    """
    clip_duration = total_gameplay_duration / num_clips

    moments = find_best_moments(
        video_path,
        num_moments=num_clips,
        moment_duration=clip_duration,
        min_gap=max(2.0, clip_duration * 0.5),
    )

    clips = []
    for moment in moments:
        actual_dur = min(clip_duration, moment.end - moment.start)
        clips.append((moment.start, actual_dur))

    # Asegurar que cubrimos la duración total
    total = sum(d for _, d in clips)
    if total < total_gameplay_duration and clips:
        # Extender el último clip
        last_start, last_dur = clips[-1]
        extra = total_gameplay_duration - total
        clips[-1] = (last_start, last_dur + extra)

    return clips
