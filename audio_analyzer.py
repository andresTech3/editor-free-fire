"""
audio_analyzer.py — Speech Timeline & Pause Analyzer for Long 16:9 Videos
==========================================================================
Analyzes master voiceover audio file (`voiceover.mp3`), extracts narration duration,
silence windows (>1.2s) for BGM ducking elevation (-20dB to -12dB),
and creates meme insert checkpoints with voiceover audio pause & resumption timestamps.
"""

import os
import json
import wave
import tempfile
import subprocess
from pathlib import Path
import numpy as np

MEME_KEYWORDS = [
    "informacion vale millones", "esta informacion", "que buen servicio",
    "vaya dato", "perturbador", "modo diablo", "pecheada", "fail",
    "no lo creo", "increible", "truco", "sensibilidad", "secreto", "todo rojo"
]

def get_audio_duration(audio_path: str) -> float:
    """Gets audio duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", audio_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        data = json.loads(res.stdout)
        return float(data.get("format", {}).get("duration", 0.0))
    except Exception:
        return 0.0

def analyze_voiceover_timeline(audio_path: str, meme_interval: float = 12.0):
    """
    Analyzes master voiceover audio file.
    
    Returns:
        dict: {
            "total_duration": float,
            "silence_windows": list of (start, end),
            "speech_windows": list of (start, end),
            "meme_events": list of float (timestamps to insert meme),
            "cta_events": list of float (timestamps to insert CTA like/subscribe)
        }
    """
    total_dur = get_audio_duration(audio_path)
    if total_dur <= 0.0:
        return {
            "total_duration": 60.0,
            "silence_windows": [],
            "speech_windows": [(0.0, 60.0)],
            "meme_events": [12.0, 24.0, 36.0, 48.0],
            "cta_events": [30.0]
        }

    # Extract audio to PCM WAV mono for analysis
    tmp_wav = os.path.join(tempfile.gettempdir(), "vo_analysis_temp.wav")
    cmd_ext = [
        "ffmpeg", "-y", "-i", audio_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
        tmp_wav
    ]
    subprocess.run(cmd_ext, capture_output=True)

    silence_windows = []
    speech_windows = []

    if os.path.exists(tmp_wav):
        try:
            with wave.open(tmp_wav, "rb") as wf:
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

            if len(samples) > 0:
                samples = samples / 32768.0
                win_sec = 0.2
                win_samples = int(win_sec * sr)
                
                in_silence = False
                silence_start = 0.0
                speech_start = 0.0

                for i in range(0, len(samples) - win_samples, win_samples):
                    t = i / sr
                    rms = np.sqrt(np.mean(samples[i:i + win_samples] ** 2))
                    
                    if rms < 0.035: # Silence threshold
                        if not in_silence:
                            in_silence = True
                            silence_start = t
                            if speech_start < t:
                                speech_windows.append((speech_start, t))
                    else: # Active speech
                        if in_silence:
                            in_silence = False
                            if t - silence_start >= 1.2: # Pause longer than 1.2s
                                silence_windows.append((silence_start, t))
                            speech_start = t

                if in_silence and total_dur - silence_start >= 1.2:
                    silence_windows.append((silence_start, total_dur))
                elif not in_silence and speech_start < total_dur:
                    speech_windows.append((speech_start, total_dur))
        except Exception as e:
            print(f"⚠️ Audio analysis notice: {e}")
        finally:
            try:
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)
            except Exception:
                pass

    if not speech_windows:
        speech_windows = [(0.0, total_dur)]

    # Meme insertion points (every ~12 seconds or at narrative pause boundaries)
    meme_events = []
    t_curr = 8.0
    while t_curr < total_dur - 4.0:
        # Align meme insertion to a natural pause if available nearby
        pause_match = next((s_start for (s_start, s_end) in silence_windows if abs(s_start - t_curr) < 4.0), None)
        insert_time = pause_match if pause_match is not None else t_curr
        meme_events.append(round(insert_time, 2))
        t_curr += meme_interval

    # CTA Like/Subscribe Pop-up timestamps (at second 30 and minute 4 / 240s)
    cta_events = [30.0]
    if total_dur > 240.0:
        cta_events.append(240.0)

    print(f"🎙️ [Audio Analyzer] Master Voiceover Duration: {total_dur:.2f}s")
    print(f"   • Speech Windows: {len(speech_windows)} blocks")
    print(f"   • Narrative Pauses (>1.2s): {len(silence_windows)} pauses for BGM elevation (-20dB ➔ -12dB)")
    print(f"   • Meme Checkpoints: {meme_events}")
    print(f"   • CTA Overlay Timestamps: {cta_events}s")

    return {
        "total_duration": total_dur,
        "silence_windows": silence_windows,
        "speech_windows": speech_windows,
        "meme_events": meme_events,
        "cta_events": cta_events
    }

if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else "assets/Recurso video Freefire/Generar Video/audio_referencia.wav"
    if os.path.exists(test_file):
        analyze_voiceover_timeline(test_file)
