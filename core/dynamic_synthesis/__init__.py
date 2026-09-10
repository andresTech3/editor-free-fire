"""
dynamic_synthesis — Dynamic Video Synthesis Package
"""

from .audio_beat_analyzer import (
    analyze_voiceover_semantics,
    analyze_bgm_beats,
    snap_to_nearest_beat,
    apply_mathematical_sidechain_ducking
)
from .stochastic_sampler import StochasticAssetSampler
from .scene_state_machine import (
    render_bezier_arrow_overlay,
    build_3d_kinetic_hook_filter,
    render_dynamic_spec_card_hud
)
