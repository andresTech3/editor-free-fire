"""
audio_beat_analyzer.py — Dynamic Audio & Semantic Analysis Layer
================================================================
Implements:
1. Whisper word-level transcription & semantic tagging:
   - Trigger_analysis ("sensibilidad", "pecho", "cabeza", "botón", "mira")
   - Trigger_meme ("amigo", "problema", "youtuber", "mentira", "falla")
   - Trigger_stats ("dispositivo", "itel", "dpi", "configuración")
2. Librosa musical beat & transient extraction:
   - BPM, Beat frames, Onset envelope
   - Beat-snapping: t_cut = argmin |t - t_trigger|
3. Mathematical Audio Ducking (Auto-Sidechain):
   - RMS envelope (window N=2048)
   - Threshold theta = -30 dBFS -> Target gain -16 dB (0.158) vs -3 dB (0.707)
   - One-pole IIR smoothing: G[n] = alpha * G[n-1] + (1-alpha) * G_target
     alpha_attack = exp(-1 / (0.020 * fs))
     alpha_release = exp(-1 / (0.250 * fs))
"""

import math
import numpy as np
import librosa
import soundfile as sf
import whisper


# ── 1. SEMANTIC TRIGGER DEFINITIONS ──────────────────────────────────────────
SEMANTIC_TRIGGERS = {
    "analysis": [
        "sensibilidad", "sensi", "pecho", "cabeza", "rojo", "botón", "boton",
        "mira", "apuntar", "subir mira", "disparo", "tiro"
    ],
    "meme": [
        "amigo", "problema", "youtuber", "mentira", "falla", "manco", "manquito",
        "no pega", "humillado", "locura", "mentiroso"
    ],
    "stats": [
        "dispositivo", "itel", "dpi", "configuración", "configuracion", "celular",
        "xiaomi", "samsung", "iphone", "ajustes", "pantalla"
    ]
}


def analyze_voiceover_semantics(voiceover_path: str, whisper_model: str = "base") -> dict:
    """
    Transcribes the input voiceover using Whisper with word-level timestamps.
    Returns:
    - total_duration: float
    - words: list of (word, start, end)
    - triggers: dict mapping trigger_type -> list of timestamps
    - first_sentence_end: float (for hook duration t_hook)
    """
    print(f"🎙️ [Whisper] Loading Whisper model '{whisper_model}'...")
    model = whisper.load_model(whisper_model)

    print(f"🔍 [Whisper] Transcribing voiceover with word-level timestamps: {voiceover_path}")
    result = model.transcribe(voiceover_path, word_timestamps=True, verbose=False)

    all_words = []
    triggers = {"analysis": [], "meme": [], "stats": []}
    first_sentence_end = 6.0

    segments = result.get("segments", [])
    if segments:
        first_seg = segments[0]
        first_sentence_end = max(4.0, min(8.0, first_seg.get("end", 6.0)))

    for seg in segments:
        for w in seg.get("words", []):
            word_str = w["word"].strip().lower()
            # Clean punctuation
            clean_word = "".join(c for c in word_str if c.isalnum())
            st = float(w["start"])
            en = float(w["end"])
            all_words.append({"word": clean_word, "start": st, "end": en})

            for cat, keywords in SEMANTIC_TRIGGERS.items():
                if any(kw in clean_word for kw in keywords):
                    triggers[cat].append({
                        "word": clean_word,
                        "time": st,
                        "duration": en - st
                    })

    duration = 15.0
    try:
        dur_raw = librosa.get_duration(path=voiceover_path)
        duration = float(dur_raw)
    except Exception:
        if all_words:
            duration = all_words[-1]["end"] + 1.0

    print(f"✅ [Whisper] Parsed {len(all_words)} words | Duration: {duration:.2f}s")
    print(f"   • Analysis Triggers: {len(triggers['analysis'])}")
    print(f"   • Meme Triggers:     {len(triggers['meme'])}")
    print(f"   • Stats Triggers:    {len(triggers['stats'])}")
    print(f"   • First sentence hook: {first_sentence_end:.2f}s")

    return {
        "duration": duration,
        "words": all_words,
        "triggers": triggers,
        "first_sentence_end": first_sentence_end,
        "text": result.get("text", "")
    }


# ── 2. MUSICAL BEAT & TRANSIENT EXTRACTION (LIBROSA) ─────────────────────────
def analyze_bgm_beats(bgm_path: str, target_duration: float = None) -> dict:
    """
    Computes tempo, beat grid, and transient onsets from background music.
    """
    print(f"🎵 [Librosa] Loading BGM for beat & onset analysis: {bgm_path}")
    y, sr = librosa.load(bgm_path, sr=22050, mono=True)

    # Loop BGM if shorter than voiceover target duration
    if target_duration and (len(y) / sr) < target_duration:
        repeats = int(math.ceil(target_duration / (len(y) / sr)))
        y = np.tile(y, repeats)

    print("🥁 [Librosa] Computing beat tracking and tempo...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0]) if len(tempo) > 0 else 120.0
    else:
        tempo = float(tempo)

    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    print("⚡ [Librosa] Computing onset strength envelope & transients...")
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

    print(f"✅ [Librosa] Detected Tempo: {tempo:.1f} BPM | {len(beat_times)} Beats | {len(onset_times)} Transients")

    return {
        "tempo": tempo,
        "beat_times": beat_times,
        "onset_times": onset_times,
        "sample_rate": sr
    }


def snap_to_nearest_beat(target_time: float, beat_times: list, max_distance: float = 0.6) -> float:
    """
    Snaps target_time to the nearest musical beat frame:
    t_cut = argmin |t - target_time|
    """
    if not beat_times:
        return target_time
    closest = min(beat_times, key=lambda b: abs(b - target_time))
    if abs(closest - target_time) <= max_distance:
        return float(closest)
    return float(target_time)


# ── 3. MATHEMATICAL AUDIO DUCKING (AUTO-SIDECHAIN WITH ONE-POLE IIR) ───────────
def apply_mathematical_sidechain_ducking(
    voiceover_path: str,
    bgm_path: str,
    output_mixed_path: str,
    target_duration: float
) -> str:
    """
    Mixes voiceover + sidechained BGM:
    A_out(t) = A_vo(t) + G(t) * A_bgm(t)
    where G(t) is smoothed with an exact one-pole IIR filter:
      G[n] = alpha * G[n-1] + (1 - alpha) * G_target
      alpha_attack  = exp(-1 / (0.020 * fs))   (20ms)
      alpha_release = exp(-1 / (0.250 * fs))   (250ms)
    """
    print(f"🎛️ [Sidechain Ducking] Processing Mathematical Auto-Sidechain (fs=44100Hz)...")
    fs = 44100
    y_vo, _ = librosa.load(voiceover_path, sr=fs, mono=False)
    y_bgm, _ = librosa.load(bgm_path, sr=fs, mono=False)

    # Convert to 2D [channels, samples]
    if y_vo.ndim == 1:
        y_vo = np.vstack([y_vo, y_vo])
    if y_bgm.ndim == 1:
        y_bgm = np.vstack([y_bgm, y_bgm])

    n_samples = int(target_duration * fs)

    # Resize/Pad Voiceover
    if y_vo.shape[1] < n_samples:
        pad_len = n_samples - y_vo.shape[1]
        y_vo = np.pad(y_vo, ((0, 0), (0, pad_len)))
    else:
        y_vo = y_vo[:, :n_samples]

    # Resize/Loop BGM
    if y_bgm.shape[1] < n_samples:
        repeats = int(math.ceil(n_samples / y_bgm.shape[1]))
        y_bgm = np.tile(y_bgm, (1, repeats))[:, :n_samples]
    else:
        y_bgm = y_bgm[:, :n_samples]

    # Compute Voice RMS Envelope using N=2048 sample window
    window_n = 2048
    vo_mono = np.mean(y_vo, axis=0)

    # Squared samples
    sq = vo_mono ** 2
    # Moving average with boxcar window
    kernel = np.ones(window_n) / window_n
    # Safe convolution
    rms_sq = np.convolve(sq, kernel, mode="same")
    rms_env = np.sqrt(np.maximum(rms_sq, 1e-12))

    # Convert to dBFS (reference 1.0)
    db_env = 20.0 * np.log10(rms_env)

    # Threshold theta = -30 dBFS
    # When voice is active (db > -30 dBFS): target = -16 dB = 0.158
    # When voice is silent (db <= -30 dBFS): target = -3 dB = 0.707
    g_target_active = 0.158489   # -16 dB
    g_target_silent = 0.707945   # -3 dB

    target_gains = np.where(db_env > -30.0, g_target_active, g_target_silent)

    # Exact one-pole IIR Filter Smoothing
    # alpha_attack = exp(-1 / (0.020 * fs))
    # alpha_release = exp(-1 / (0.250 * fs))
    alpha_attack = math.exp(-1.0 / (0.020 * fs))
    alpha_release = math.exp(-1.0 / (0.250 * fs))

    g_smoothed = np.zeros(n_samples, dtype=np.float32)
    current_g = g_target_silent

    for n in range(n_samples):
        target = target_gains[n]
        if target < current_g:
            # Attacking (Voice started -> dipping music)
            current_g = alpha_attack * current_g + (1.0 - alpha_attack) * target
        else:
            # Releasing (Voice stopped -> swelling music)
            current_g = alpha_release * current_g + (1.0 - alpha_release) * target
        g_smoothed[n] = current_g

    # Modulate BGM with continuous gain curve
    y_bgm_ducked = y_bgm * g_smoothed

    # Final Master Mix: Voice + Ducked BGM
    master_mix = (0.95 * y_vo) + (0.85 * y_bgm_ducked)

    # Master Limiter / Normalize to prevent clipping
    peak = np.max(np.abs(master_mix))
    if peak > 0.98:
        master_mix = master_mix * (0.98 / peak)

    # Export to WAV
    sf.write(output_mixed_path, master_mix.T, fs, subtype="PCM_16")
    print(f"✅ [Sidechain Ducking] Master Mix rendered to: {output_mixed_path}")
    return output_mixed_path
