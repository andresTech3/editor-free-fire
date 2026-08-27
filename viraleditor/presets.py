"""
viraleditor/presets.py
======================
Presets de edición — configuración completa de efectos por tipo de contenido.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Preset(str, Enum):
    PODCAST_VIRAL      = "podcast_viral"
    CAPCUT_ULTRA_VIRAL = "capcut_ultra_viral"
    GAMING             = "gaming"
    MOTIVATIONAL       = "motivational"
    CLEAN_MINIMAL      = "clean_minimal"
    POV_CINEMATIC      = "pov_cinematic"
    REACTION           = "reaction"


@dataclass
class PresetConfig:
    """Full configuration for a clip preset."""
    name:             str
    color_grade:      str            = "viral_punch"
    vignette:         float          = 0.75
    flash:            bool           = True
    flash_at:         float          = 0.0
    glitch:           bool           = True
    glitch_at:        float          = 0.5
    ken_burns:        bool           = False
    ken_from:         float          = 1.0
    ken_to:           float          = 1.04
    shake:            bool           = False
    hook_card:        bool           = True
    lower_third:      bool           = True
    lower_third_y:    float          = 0.68
    progress_bar:     bool           = True
    progress_color:   str            = "#FFD700"
    word_captions:    bool           = True
    caption_size:     int            = 70
    caption_y:        str            = "h*0.76"
    caption_box:      bool           = True
    letterbox:        bool           = False
    letterbox_pct:    float          = 0.07
    accent_color:     str            = "#FFD700"
    src_w:            int            = 1920
    src_h:            int            = 1080
    crop_portrait:    bool           = True
    audio_vol:        float          = 1.25
    audio_highpass:   int            = 80
    crf:              int            = 17
    description:      str            = ""
    # ── Gaming-specific fields ──────────────────────────────────────────
    gaming_sfx:       bool           = False   # inject kill/frenetic SFX events
    pov_hook_mode:    bool           = False   # use pov_gaming_hook instead of hook_card
    pov_hook_dur:     float          = 4.5     # seconds hook text stays visible
    frenetic_flashes: int            = 3       # number of flash cuts during clip
    zoom_punches:     int            = 2       # number of zoom_punch events during clip
    layout_mode:      str            = "portrait" # "portrait" (full 9:16 crop) | "full_169_blur" | "auto_dynamic_mix"


PRESETS: dict[Preset, PresetConfig] = {

    Preset.CAPCUT_ULTRA_VIRAL: PresetConfig(
        name="CapCut Ultra Viral (10M+)",
        color_grade="viral_punch",
        vignette=0.75,
        flash=True, glitch=True,
        ken_burns=False,
        hook_card=True, lower_third=True,
        progress_bar=True,  progress_color="#FFD700",
        word_captions=True, caption_size=72,
        letterbox=False,
        accent_color="#FFD700",
        audio_vol=1.30,
        crf=16,
        layout_mode="auto_dynamic_mix",
        description="10M+ View Engine: Multi-layout timeline switching (Split 2-Up, 16:9 Blur BG, Auto-Face Cut), CapCut Light Leak & Emoji popups, procedural SFX",
    ),

    Preset.PODCAST_VIRAL: PresetConfig(
        name="Podcast Viral",
        color_grade="viral_punch",
        vignette=0.75,
        flash=True,  glitch=True,
        ken_burns=False,
        hook_card=True, lower_third=True,
        progress_bar=True,  progress_color="#FFD700",
        word_captions=True, caption_size=70,
        letterbox=False,
        accent_color="#FFD700",
        audio_vol=1.25,
        crf=17,
        layout_mode="portrait",
        description="Ideal for podcast & interview clips: YuNet face auto-tracking cuts, top hook card, lower-third guest badge, gold progress bar",
    ),

    Preset.GAMING: PresetConfig(
        name="Gaming",
        color_grade="viral_punch",
        vignette=0.65,
        flash=True,   flash_at=0.0,
        glitch=True,  glitch_at=0.3,
        ken_burns=False,
        shake=False,
        hook_card=False,    # ← OFF — replaced by single POV hook
        lower_third=False,
        progress_bar=True,  progress_color="#00FF88",
        word_captions=False,  # ← OFF — no text wall, clean gameplay
        letterbox=False,
        accent_color="#00FF88",
        audio_vol=1.35,
        crf=16,
        gaming_sfx=True,
        pov_hook_mode=True,
        pov_hook_dur=4.5,
        frenetic_flashes=4,
        zoom_punches=3,
        layout_mode="portrait",
        description="Frenetic gaming clips: full 9:16 vertical crop, single POV hook, kill SFX, zoom punches, no text wall",
    ),

    Preset.MOTIVATIONAL: PresetConfig(
        name="Motivational",
        color_grade="warm",
        vignette=0.85,
        flash=False, glitch=False,
        ken_burns=True, ken_from=1.0, ken_to=1.04,
        hook_card=True, lower_third=False,
        progress_bar=False,
        word_captions=True, caption_size=78, caption_y="h*0.72", caption_box=True,
        letterbox=True, letterbox_pct=0.07,
        accent_color="#FF8C00",
        audio_vol=1.30,
        crf=17,
        layout_mode="portrait",
        description="Cinematic motivational: warm color grade, slow Ken Burns zoom, 7% black bars, deep orange captions, sub-bass impact drop",
    ),

    Preset.CLEAN_MINIMAL: PresetConfig(
        name="Clean Minimal",
        color_grade="cinematic",
        vignette=0.45,
        flash=False, glitch=False,
        ken_burns=False,
        hook_card=False, lower_third=False,
        progress_bar=False,
        word_captions=True, caption_size=62, caption_box=False,
        letterbox=False,
        accent_color="#FFFFFF",
        audio_vol=1.20,
        crf=18,
        layout_mode="portrait",
        description="Clean & elegant look: soft cinematic grade, floating white text without black box, no distractive UI elements",
    ),

    Preset.POV_CINEMATIC: PresetConfig(
        name="POV Cinematic",
        color_grade="cinematic",
        vignette=0.80,
        flash=False, glitch=False,
        ken_burns=True, ken_from=1.0, ken_to=1.03,
        hook_card=True, lower_third=False,
        progress_bar=False,
        word_captions=True, caption_size=65, caption_y="h*0.80", caption_box=False,
        letterbox=True, letterbox_pct=0.09,
        accent_color="#00E5FF",
        audio_vol=1.25,
        crf=17,
        layout_mode="portrait",
        description="First-person POV style: 9% cinematic black bars, cyan accents, low-floating captions, gentle zoom drift",
    ),

    Preset.REACTION: PresetConfig(
        name="Reaction",
        color_grade="viral_punch",
        vignette=0.65,
        flash=True, flash_at=0.0,
        glitch=True, glitch_at=0.4,
        ken_burns=False,
        hook_card=True, lower_third=True,
        progress_bar=True, progress_color="#FF4444",
        word_captions=True, caption_size=72, caption_box=True,
        letterbox=False,
        accent_color="#FF4444",
        audio_vol=1.35,
        crf=16,
        layout_mode="portrait",
        description="High-energy reaction: aggressive neon red accents, reaction emoji popups, flash cut + glitch distortion at climax",
    ),
}


def get_preset(name: str) -> PresetConfig:
    """Get a preset by name (case-insensitive). Fallback: PODCAST_VIRAL."""
    for key, cfg in PRESETS.items():
        if key.value == name.lower() or cfg.name.lower() == name.lower():
            return cfg
    return PRESETS[Preset.PODCAST_VIRAL]
