"""
viraleditor/audio/sfx.py
========================
Procedural SFX Audio Synthesizer & FFmpeg Audio Mixer.
Generates 100% code-driven sound effects: Whoosh, Pop, Impact, Glitch, Ding.
No external audio files required!
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
import struct
import wave
import random
from pathlib import Path
from typing import Optional, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
#  PROCEDURAL AUDIO SYNTHESIZERS
# ─────────────────────────────────────────────────────────────────────────────

def _write_wav_mono(filename: str, samples: list[float], sample_rate: int = 44100):
    """Writes a list of float samples [-1.0, 1.0] to a 16-bit mono WAV file."""
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(sample_rate)
        frames = bytearray()
        for s in samples:
            # Clamp [-1.0, 1.0]
            val = max(-1.0, min(1.0, s))
            int_val = int(val * 32767.0)
            frames.extend(struct.pack("<h", int_val))
        wf.writeframes(frames)


def generate_whoosh(out_path: str, duration: float = 0.30, sample_rate: int = 44100):
    """
    Generates a Whoosh transition SFX:
    White noise burst with logarithmic frequency sweep and bell envelope.
    """
    n_samples = int(duration * sample_rate)
    samples = []
    # Simple lowpass state
    lp_state = 0.0

    for i in range(n_samples):
        t = i / n_samples
        # Envelope: bell curve peakt = 0.4
        env = math.exp(-((t - 0.4) ** 2) / 0.03)

        # Cutoff frequency sweeps from 200Hz up to 2500Hz then down to 100Hz
        freq = 200.0 + 2300.0 * math.sin(t * math.pi)
        alpha = min(1.0, 2.0 * math.pi * freq / sample_rate)

        # White noise sample
        noise = random.uniform(-1.0, 1.0)
        lp_state += alpha * (noise - lp_state)

        # Combine with subtle sub pitch curve
        sub = 0.15 * math.sin(2.0 * math.pi * (100.0 + 150.0 * t) * (i / sample_rate))

        sample = (lp_state * 0.85 + sub) * env * 0.90
        samples.append(sample)

    _write_wav_mono(out_path, samples, sample_rate)


def generate_pop(out_path: str, duration: float = 0.06, sample_rate: int = 44100):
    """
    Generates a Pop / Bubble SFX:
    Fast upward sine frequency pitch sweep (350Hz → 1400Hz) with sharp decay.
    """
    n_samples = int(duration * sample_rate)
    samples = []
    phase = 0.0

    for i in range(n_samples):
        t = i / n_samples
        # Exponential pitch sweep: 350 -> 1400 Hz
        freq = 350.0 * math.pow(4.0, t)
        phase += 2.0 * math.pi * freq / sample_rate

        # Sharp exponential decay envelope
        env = math.exp(-t * 35.0)
        sample = math.sin(phase) * env * 0.85
        samples.append(sample)

    _write_wav_mono(out_path, samples, sample_rate)


def generate_impact(out_path: str, duration: float = 0.55, sample_rate: int = 44100):
    """
    Generates a Bass Drop / Impact SFX:
    Low-frequency exponential sine drop (160Hz → 32Hz) with subtle saturation.
    """
    n_samples = int(duration * sample_rate)
    samples = []
    phase = 0.0

    for i in range(n_samples):
        t = i / n_samples
        # Pitch drop: 160Hz down to 32Hz
        freq = 32.0 + (160.0 - 32.0) * math.exp(-t * 6.0)
        phase += 2.0 * math.pi * freq / sample_rate

        # Attack-decay envelope
        attack = min(1.0, t / 0.015)
        decay = math.exp(-t * 4.5)
        env = attack * decay

        # Sine + 2nd harmonic saturation
        raw = math.sin(phase) + 0.3 * math.sin(phase * 2.0)
        sample = math.tanh(raw * 1.2) * env * 0.95
        samples.append(sample)

    _write_wav_mono(out_path, samples, sample_rate)


def generate_glitch(out_path: str, duration: float = 0.18, sample_rate: int = 44100):
    """
    Generates a Cyber Glitch SFX:
    Rapid square wave frequency steps + bit-crushed noise.
    """
    n_samples = int(duration * sample_rate)
    samples = []

    # Frequency steps
    freqs = [600, 1400, 450, 1800, 300, 2200, 800, 1200]
    step_samples = n_samples // len(freqs)
    phase = 0.0

    for i in range(n_samples):
        t = i / n_samples
        step_idx = min(len(freqs) - 1, i // step_samples)
        freq = freqs[step_idx]

        phase += 2.0 * math.pi * freq / sample_rate
        # Square wave with noise burst
        sq = 1.0 if math.sin(phase) > 0 else -1.0
        noise = random.uniform(-0.4, 0.4)

        env = min(1.0, t / 0.01) * (1.0 - t / duration)
        sample = (sq * 0.6 + noise * 0.4) * env * 0.75
        samples.append(sample)

    _write_wav_mono(out_path, samples, sample_rate)


def generate_ding(out_path: str, duration: float = 0.45, sample_rate: int = 44100):
    """
    Generates a Bell Ding SFX:
    Bright dual-harmonic sine chord (1046.5Hz C6 + 2093Hz C7) with smooth decay.
    """
    n_samples = int(duration * sample_rate)
    samples = []

    for i in range(n_samples):
        t = i / n_samples
        f1, f2, f3 = 1046.5, 2093.0, 3139.5
        t_sec = i / sample_rate

        env = math.exp(-t_sec * 8.0)
        chord = (
            0.6 * math.sin(2.0 * math.pi * f1 * t_sec) +
            0.35 * math.sin(2.0 * math.pi * f2 * t_sec) +
            0.15 * math.sin(2.0 * math.pi * f3 * t_sec)
        )
        sample = chord * env * 0.85
        samples.append(sample)

    _write_wav_mono(out_path, samples, sample_rate)


def generate_kill_ding(out_path: str, duration: float = 0.14, sample_rate: int = 44100):
    """
    Sharp electronic kill-confirm ping (800Hz → 1600Hz sweep, ultra-fast decay).
    Classic FPS headshot / kill-confirm sound feel.
    """
    n_samples = int(duration * sample_rate)
    samples = []
    phase = 0.0
    for i in range(n_samples):
        t = i / n_samples
        freq = 800.0 + 800.0 * t           # sweep up
        phase += 2.0 * math.pi * freq / sample_rate
        env = math.exp(-t * 30.0)          # very fast decay
        sample = (math.sin(phase) + 0.4 * math.sin(phase * 2.0)) * env * 0.90
        samples.append(sample)
    _write_wav_mono(out_path, samples, sample_rate)


def generate_triple_kill_fanfare(out_path: str, duration: float = 0.55, sample_rate: int = 44100):
    """
    Ascending 3-note electronic fanfare: C5 → E5 → G5.
    Triggers on multi-kill moments (triple, quadruple, dominating).
    """
    notes = [523.25, 659.25, 783.99]   # C5, E5, G5
    note_dur = duration / len(notes)
    n_per_note = int(note_dur * sample_rate)
    samples = []
    for freq in notes:
        phase = 0.0
        for i in range(n_per_note):
            t = i / n_per_note
            phase += 2.0 * math.pi * freq / sample_rate
            attack  = min(1.0, t / 0.06)
            decay   = math.exp(-t * 5.0)
            env     = attack * decay
            raw     = math.sin(phase) + 0.3 * math.sin(phase * 2.0) + 0.1 * math.sin(phase * 3.0)
            sample  = math.tanh(raw * 1.1) * env * 0.85
            samples.append(sample)
    _write_wav_mono(out_path, samples, sample_rate)


def generate_frenetic_stutter(out_path: str, duration: float = 0.22, sample_rate: int = 44100):
    """
    Ultra-fast rhythmic noise stutter (8 chops) for chaos moments.
    Timed to multi-kill or dominating events.
    """
    n_samples = int(duration * sample_rate)
    chops = 8
    chop_samples = n_samples // chops
    samples = []
    for c in range(chops):
        is_on = c % 2 == 0
        for i in range(chop_samples):
            t = i / chop_samples
            env = math.exp(-t * 12.0) if is_on else 0.0
            noise = random.uniform(-0.5, 0.5)
            tone  = 0.4 * math.sin(2.0 * math.pi * 1200.0 * (c * chop_samples + i) / sample_rate)
            samples.append((noise * 0.5 + tone) * env * 0.75 if is_on else 0.0)
    # Pad to exact duration
    while len(samples) < n_samples:
        samples.append(0.0)
    _write_wav_mono(out_path, samples[:n_samples], sample_rate)


# ─────────────────────────────────────────────────────────────────────────────
#  SFX LIBRARY MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

_SFX_DIR = Path(__file__).parent / "sfx_cache"

def ensure_sfx_library() -> dict[str, str]:
    """
    Generates all procedural SFX files if missing.
    Returns dict mapping sfx name -> absolute file path.
    """
    _SFX_DIR.mkdir(parents=True, exist_ok=True)

    files = {
        "whoosh":        str(_SFX_DIR / "whoosh.wav"),
        "pop":           str(_SFX_DIR / "pop.wav"),
        "impact":        str(_SFX_DIR / "impact.wav"),
        "glitch":        str(_SFX_DIR / "glitch.wav"),
        "ding":          str(_SFX_DIR / "ding.wav"),
        "kill_ding":     str(_SFX_DIR / "kill_ding.wav"),
        "triple_kill":   str(_SFX_DIR / "triple_kill.wav"),
        "frenetic":      str(_SFX_DIR / "frenetic_stutter.wav"),
    }

    generators = {
        "whoosh":      lambda: generate_whoosh(files["whoosh"]),
        "pop":         lambda: generate_pop(files["pop"]),
        "impact":      lambda: generate_impact(files["impact"]),
        "glitch":      lambda: generate_glitch(files["glitch"]),
        "ding":        lambda: generate_ding(files["ding"]),
        "kill_ding":   lambda: generate_kill_ding(files["kill_ding"]),
        "triple_kill": lambda: generate_triple_kill_fanfare(files["triple_kill"]),
        "frenetic":    lambda: generate_frenetic_stutter(files["frenetic"]),
    }

    for name, path in files.items():
        if not Path(path).exists():
            generators[name]()

    return files


# ─────────────────────────────────────────────────────────────────────────────
#  SFX AUDIO MIXER FOR FFMPEG
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SFXEvent:
    """An event triggering an SFX sound at a timestamp."""
    sfx_type: str        # 'whoosh' | 'pop' | 'impact' | 'glitch' | 'ding'
    timestamp: float     # seconds from clip start
    volume: float = 0.80 # 0.0 - 1.0


class SFXAudioMixer:
    """
    Builds FFmpeg filter complex / -af string to overlay SFX onto primary audio.
    """

    def __init__(self, main_volume: float = 1.25):
        self.main_volume = main_volume
        self.events: list[SFXEvent] = []
        self.sfx_files = ensure_sfx_library()

    def add_event(self, sfx_type: str, timestamp: float, volume: float = 0.80):
        if sfx_type in self.sfx_files:
            self.events.append(SFXEvent(sfx_type, max(0.0, timestamp), volume))

    def build_audio_filter(self) -> str:
        """
        Returns primary audio filter chain (-af string).
        Applies primary volume, highpass, loudnorm broadcast mastering.
        """
        return (
            f"aresample=44100,"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={self.main_volume:.2f},"
            f"highpass=f=80,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11"
        )
