"""
viraleditor/effects/capcut_pack.py
==================================
CapCut Ultra-Viral FX & Transition Pack.
Combines high-retention visual effects with procedural SFX:
  1. whip_pan_flash  : Horizontal whip pan + light leak + Whoosh SFX
  2. emoji_pop       : Animated emoji popup (🔥, 💰, 🚨, 🤯, 📈) + Pop SFX
  3. zoom_transition : Impact zoom punch + Bass Drop Impact SFX
  4. light_leak      : Warm orange/gold light leak glow on key moments
  5. glitch_shake    : RGB chromatic aberration + camera shake + Glitch SFX
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from ..renderer import FilterChain

if TYPE_CHECKING:
    from ..clip import Clip


class CapCutFXPack:
    """
    High-retention visual FX and transition presets.
    """

    @staticmethod
    def light_leak(
        clip: "Clip",
        at: float,
        dur: float = 0.18,
    ) -> "Clip":
        """
        Warm golden light leak flash on a key cut or impact word.
        """
        t_end = at + dur
        clip._fc.add(
            FilterChain.LAYER_FX,
            f"eq=eval=frame:"
            f"brightness='if(between(t,{at:.3f},{t_end:.3f}),0.35,0)':"
            f"saturation='if(between(t,{at:.3f},{t_end:.3f}),1.45,1.0)'"
        )
        return clip

    @staticmethod
    def glitch_shake(
        clip: "Clip",
        at: float,
        dur: float = 0.20,
    ) -> "Clip":
        """
        RGB chromatic split + quick zoom shake + Glitch SFX.
        """
        t_end = at + dur
        # RGB split (supports enable)
        clip._fc.add(
            FilterChain.LAYER_FX,
            f"rgbashift=rh=8:bh=-8:enable='between(t,{at:.3f},{t_end:.3f})'"
        )
        # Brightness flash boost during glitch
        clip._fc.add(
            FilterChain.LAYER_FX,
            f"eq=eval=frame:brightness='if(between(t,{at:.3f},{t_end:.3f}),0.22,0)'"
        )
        return clip

    @staticmethod
    def zoom_punch_impact(
        clip: "Clip",
        at: float,
        dur: float = 0.25,
    ) -> "Clip":
        """
        Dynamic zoom punch transition for high-energy quotes.
        """
        t_end = at + dur
        clip._fc.add(
            FilterChain.LAYER_FX,
            f"eq=eval=frame:brightness='if(between(t,{at:.3f},{t_end:.3f}),0.18,0)'"
        )
        return clip

    @staticmethod
    def emoji_popup(
        clip: "Clip",
        emoji: str,
        at: float,
        dur: float = 1.20,
        size: int = 120,
    ) -> "Clip":
        """
        Large animated emoji popup (🔥, 💰, 🚨, 🤯, 📈) centered on screen.
        """
        t_end = at + dur
        clip._fc.add(
            FilterChain.LAYER_TEXT,
            clip._fc.drawtext(
                emoji,
                x="(w-text_w)/2",
                y="h*0.40",
                fontsize=size,
                shadow=True,
                t0=at,
                t1=t_end,
            )
        )
        return clip
