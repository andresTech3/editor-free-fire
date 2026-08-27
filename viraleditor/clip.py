"""
viraleditor/clip.py
===================
Clase Clip — representa un segmento de video con su cadena de efectos.

API fluida (chainable):
    clip = Clip("video.mp4", start=45, end=105)
    clip.layout.portrait()
    clip.fx.color_grade("viral_punch")
    clip.fx.flash(at=0.0)
    clip.text.hook_card("Big Hook", "Subtitle")
    clip.text.progress_bar()
    chain_str = clip.build()
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from .renderer import FilterChain, find_font, esc

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  DATA TYPES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Caption:
    """A timed on-screen caption line."""
    text:      str
    start:     float           # seconds relative to clip start
    end:       float           # seconds relative to clip start
    highlight: bool   = False  # render in accent color


# ─────────────────────────────────────────────────────────────────────────────
#  SUB-NAMESPACES (fluent API helpers)
# ─────────────────────────────────────────────────────────────────────────────

class LayoutMixin:
    """Layout transforms — always applied first (LAYER 0)."""

    def portrait(
        self,
        src_w: int = 1920,
        src_h: int = 1080,
        crop_x: Optional[int] = None,
    ) -> "Clip":
        """Center-crop 16:9 → 9:16, then scale to out_w × out_h."""
        clip: Clip = self  # type: ignore
        fc = clip._fc
        new_w = int(src_h * fc.out_w / fc.out_h)  # ≈ 607 for 1080/1920
        x_off = crop_x if crop_x is not None else (src_w - new_w) // 2
        # Ensure within bounds
        x_off = max(0, min(x_off, src_w - new_w))
        fc.add(FilterChain.LAYER_LAYOUT, f"crop={new_w}:{src_h}:{x_off}:0")
        fc.add(FilterChain.LAYER_LAYOUT, f"scale={fc.out_w}:{fc.out_h}")
        fc.add(FilterChain.LAYER_LAYOUT, "setsar=1")
        fc.add(FilterChain.LAYER_LAYOUT, f"fps={fc.fps}")
        return clip

    def portrait_autoface(
        self,
        src_w: int = 1920,
        src_h: int = 1080,
        sample_rate: int = 6,
    ) -> "Clip":
        """
        Uses OpenCV YuNet DNN FaceTracker to analyze speaker positions per frame,
        and constructs a dynamic FFmpeg crop expression that cuts the camera
        directly to whichever speaker is active at each timestamp.
        """
        clip: Clip = self  # type: ignore
        fc = clip._fc
        new_w = int(src_h * fc.out_w / fc.out_h)  # ≈ 607 for 1080/1920

        try:
            from core.face_tracker import FaceTracker
            tracker = FaceTracker(sample_rate=sample_rate)
            crop_data, meta = tracker.analyze_clip(
                clip.src,
                start_time=clip.start,
                end_time=clip.end,
                target_width=fc.out_w,
                target_height=fc.out_h,
            )

            if crop_data:
                fps = meta["fps"]
                dur = clip.duration

                # Cluster consecutive frames into camera segments
                min_frames = int(1.2 * fps)  # at least 1.2s per shot to prevent jitter
                cuts = []
                curr_start = 0.0
                curr_x = crop_data[0]["crop_x"]
                last_cut_idx = 0

                for i, f in enumerate(crop_data):
                    x = f["crop_x"]
                    if abs(x - curr_x) > 160 and (i - last_cut_idx) >= min_frames:
                        t_sec = (f["frame_idx"] - int(clip.start * fps)) / fps
                        cuts.append((curr_start, round(t_sec, 2), curr_x))
                        curr_start = round(t_sec, 2)
                        curr_x = x
                        last_cut_idx = i

                cuts.append((curr_start, round(dur, 2), curr_x))

                # Build dynamic FFmpeg expression
                if len(cuts) > 1:
                    parts = [f"between(t,{t0:.2f},{t1:.2f})*{x}" for t0, t1, x in cuts]
                    crop_x_expr = "+".join(parts)
                    fc.add(FilterChain.LAYER_LAYOUT, f"crop={new_w}:{src_h}:'{crop_x_expr}':0")
                else:
                    x_off = cuts[0][2]
                    fc.add(FilterChain.LAYER_LAYOUT, f"crop={new_w}:{src_h}:{x_off}:0")

                fc.add(FilterChain.LAYER_LAYOUT, f"scale={fc.out_w}:{fc.out_h}")
                fc.add(FilterChain.LAYER_LAYOUT, "setsar=1")
                fc.add(FilterChain.LAYER_LAYOUT, f"fps={fc.fps}")
                return clip

        except Exception:
            pass

        # Fallback to center crop
        return self.portrait(src_w=src_w, src_h=src_h)

    def split_2up(
        self,
        top_x: int = 1200,
        bottom_x: int = 420,
        src_w: int = 1920,
        src_h: int = 1080,
        divider_color: str = "#FFD700",
    ) -> "Clip":
        """Stacked 2-speaker split screen with gold divider bar."""
        from .layouts.multilayout import MultiLayoutEngine
        return MultiLayoutEngine.split_2up(
            self, top_x=top_x, bottom_x=bottom_x,
            src_w=src_w, src_h=src_h, divider_color=divider_color
        )

    def full_169_blur(
        self,
        src_w: int = 1920,
        src_h: int = 1080,
        blur_sigma: int = 32,
        pov_text: Optional[str] = None,
    ) -> "Clip":
        """16:9 uncropped video centered over blurred moving background."""
        from .layouts.multilayout import MultiLayoutEngine
        return MultiLayoutEngine.full_169_blur(
            self, src_w=src_w, src_h=src_h, blur_sigma=blur_sigma, pov_text=pov_text
        )

    def auto_dynamic_mix(
        self,
        top_x: int = 1200,
        bottom_x: int = 420,
        src_w: int = 1920,
        src_h: int = 1080,
        divider_color: str = "#FFD700",
        pov_text: Optional[str] = None,
    ) -> "Clip":
        """Ultra-dynamic timeline multi-layout switching within a single short."""
        from .layouts.multilayout import MultiLayoutEngine
        return MultiLayoutEngine.auto_dynamic_mix(
            self, top_x=top_x, bottom_x=bottom_x,
            src_w=src_w, src_h=src_h, divider_color=divider_color, pov_text=pov_text
        )

    def picture_in_picture(
        self,
        main_x: int = 1200,
        pip_x: int = 420,
        pip_size: int = 340,
        src_w: int = 1920,
        src_h: int = 1080,
    ) -> "Clip":
        """Picture-in-picture layout (main speaker + secondary speaker box)."""
        from .layouts.multilayout import MultiLayoutEngine
        return MultiLayoutEngine.picture_in_picture(
            self, main_x=main_x, pip_x=pip_x, pip_size=pip_size,
            src_w=src_w, src_h=src_h
        )

    def scale_fit(self) -> "Clip":
        """Scale to fit 9:16 with black padding (no crop)."""
        clip: Clip = self  # type: ignore
        fc = clip._fc
        fc.add(FilterChain.LAYER_LAYOUT,
               f"scale={fc.out_w}:{fc.out_h}:force_original_aspect_ratio=decrease")
        fc.add(FilterChain.LAYER_LAYOUT,
               f"pad={fc.out_w}:{fc.out_h}:(ow-iw)/2:(oh-ih)/2")
        fc.add(FilterChain.LAYER_LAYOUT, "setsar=1")
        fc.add(FilterChain.LAYER_LAYOUT, f"fps={fc.fps}")
        return clip

    def letterbox(self, bar_pct: float = 0.08) -> "Clip":
        """Add cinematic black bars (no cropping applied here, just bars)."""
        clip: Clip = self  # type: ignore
        fc = clip._fc
        bar_h = int(fc.out_h * bar_pct)
        fc.add(FilterChain.LAYER_OVERLAY,
               f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black:t=fill")
        fc.add(FilterChain.LAYER_OVERLAY,
               f"drawbox=x=0:y={fc.out_h - bar_h}:w=iw:h={bar_h}:color=black:t=fill")
        return clip

    def portrait_from(self, src_w: int, src_h: int) -> "Clip":
        """Portrait crop from custom source dimensions."""
        return self.portrait(src_w=src_w, src_h=src_h)


class FxMixin:
    """Visual effects — color, motion, transitions (LAYERS 1-3)."""

    _GRADES = {
        "viral_punch": (
            "curves="
            "r='0/0 0.3/0.35 0.7/0.75 1/1':"
            "g='0/0 0.3/0.32 0.7/0.73 1/0.98':"
            "b='0/0 0.3/0.25 0.7/0.68 1/0.92',"
            "eq=contrast=1.08:saturation=1.18:brightness=0.02"
        ),
        "cinematic": (
            "curves="
            "r='0/0 0.25/0.22 0.75/0.78 1/1':"
            "g='0/0 0.25/0.23 0.75/0.77 1/0.97':"
            "b='0/0 0.25/0.28 0.75/0.72 1/0.93'"
        ),
        "warm": (
            "curves="
            "r='0/0 0.5/0.57 1/1':"
            "g='0/0 0.5/0.50 1/1':"
            "b='0/0 0.5/0.42 1/0.90'"
        ),
        "cool": (
            "curves="
            "r='0/0 0.5/0.44 1/0.95':"
            "g='0/0 0.5/0.50 1/1':"
            "b='0/0 0.5/0.56 1/1'"
        ),
        "flat": "",
    }

    def color_grade(self, style: str = "viral_punch") -> "Clip":
        clip: Clip = self  # type: ignore
        grade = self._GRADES.get(style, "")
        if grade:
            for f in grade.split(","):
                clip._fc.add(FilterChain.LAYER_COLOR, f.strip())
        return clip

    def vignette(self, strength: float = 0.75) -> "Clip":
        clip: Clip = self  # type: ignore
        clip._fc.add(FilterChain.LAYER_COLOR,
                     f"vignette=angle={strength:.2f}:mode=forward")
        return clip

    def flash(self, at: float = 0.0, dur: float = 0.08) -> "Clip":
        """White flash cut at timestamp 'at'."""
        clip: Clip = self  # type: ignore
        t_end = at + dur
        clip._fc.add(FilterChain.LAYER_FX,
            f"eq=eval=frame:brightness='if(between(t,{at:.3f},{t_end:.3f}),0.5,0)'"
        )
        return clip

    def glitch(self, at: float = 0.5, dur: float = 0.15) -> "Clip":
        """RGB channel split glitch effect."""
        clip: Clip = self  # type: ignore
        t_end = at + dur
        clip._fc.add(FilterChain.LAYER_FX,
            f"rgbashift=rh=7:bh=-7:enable='between(t,{at:.3f},{t_end:.3f})'"
        )
        return clip

    def zoom_punch(self, at: float = 0.0, strength: float = 0.12,
                   dur: float = 0.3) -> "Clip":
        """Quick brightness boost to simulate zoom punch feel."""
        clip: Clip = self  # type: ignore
        t_end = at + dur
        clip._fc.add(FilterChain.LAYER_FX,
            f"eq=brightness='if(between(t,{at:.3f},{t_end:.3f}),{strength:.2f},0)'"
        )
        return clip

    def ken_burns(self, zoom_from: float = 1.0, zoom_to: float = 1.04) -> "Clip":
        """Slow cinematic zoom drift over the entire clip."""
        clip: Clip = self  # type: ignore
        fc = clip._fc
        fps   = fc.fps
        total = int(clip.duration * fps)
        step  = (zoom_to - zoom_from) / max(total, 1)
        zoom_expr = (
            f"'if(eq(on\\,1)\\,{zoom_from:.3f}\\,"
            f"min(zoom+{step:.6f}\\,{zoom_to:.3f}))'"
        )
        clip._fc.add(FilterChain.LAYER_MOTION,
            f"zoompan=z={zoom_expr}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={fc.out_w}x{fc.out_h}:fps={fps}"
        )
        return clip

    def shake(self, intensity: float = 5.0, freq: float = 30.0) -> "Clip":
        """Camera shake effect (crop + position offset)."""
        clip: Clip = self  # type: ignore
        fc = clip._fc
        m = int(intensity)
        fc.add(FilterChain.LAYER_MOTION,
               f"crop=iw-{m*2}:ih-{m*2}:"
               f"x='{m}+{intensity:.1f}*sin(t*{freq:.1f})':"
               f"y='{m}+{intensity:.1f}*cos(t*{freq:.1f}*1.3)',"
               f"scale={fc.out_w}:{fc.out_h}")
        return clip


class TextMixin:
    """Text overlays — hook cards, captions, lower-thirds, bars (LAYERS 4-5)."""

    def hook_card(
        self,
        line1:       str,
        line2:       str,
        accent:      str   = "#FFD700",
        bar_h:       int   = 215,
        show_entire: bool  = True,
    ) -> "Clip":
        """Dark top bar + 2-line hook text."""
        clip: Clip = self  # type: ignore
        fc   = clip._fc
        dur  = clip.duration if show_entire else 4.0

        # Dark bar
        fc.add(FilterChain.LAYER_OVERLAY,
               fc.drawbox(y="0", h=str(bar_h), color="black@0.62"))

        # Line 1 — white, medium
        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(line1, x="(w-text_w)/2", y="50",
                           fontsize=50, color="white", t1=dur))

        # Line 2 — accent color, big bold
        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(line2, x="(w-text_w)/2", y="118",
                           fontsize=66, color=accent, t1=dur))
        return clip

    def lower_third(
        self,
        name:    str,
        title:   str,
        t0:      float = 1.0,
        t1:      float = 5.5,
        accent:  str   = "#FFD700",
        y_pct:   float = 0.68,
    ) -> "Clip":
        """Animated lower-third: name (accent) + title (white)."""
        clip: Clip = self  # type: ignore
        fc   = clip._fc
        y    = int(fc.out_h * y_pct)

        fc.add(FilterChain.LAYER_OVERLAY,
               fc.drawbox(y=str(y - 10), h="120",
                          color="black@0.72", t0=t0, t1=t1))

        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(name, x="55", y=str(y + 5),
                           fontsize=54, color=accent, t0=t0, t1=t1))

        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(title, x="55", y=str(y + 65),
                           fontsize=36, color="white@0.88",
                           shadow=True, t0=t0, t1=t1))
        return clip

    def progress_bar(
        self,
        color:  str = "#FFD700",
        height: int = 10,
    ) -> "Clip":
        """Gold progress bar that fills over clip duration."""
        clip: Clip = self  # type: ignore
        fc   = clip._fc
        dur  = clip.duration
        y    = fc.out_h - height - 4

        # Track (dark)
        fc.add(FilterChain.LAYER_OVERLAY,
               fc.drawbox(y=str(y), h=str(height), color="black@0.50"))

        # Fill (animates with time)
        fc.add(FilterChain.LAYER_OVERLAY,
               f"drawbox=x=0:y={y}:w='iw*t/{dur:.3f}':"
               f"h={height}:color={color}@0.90:t=fill")
        return clip

    def episode_tag(
        self,
        tag:   str,
        size:  int   = 34,
        color: str   = "white@0.82",
        dur:   Optional[float] = None,
    ) -> "Clip":
        """Small tag at top-right of frame."""
        clip: Clip = self  # type: ignore
        fc   = clip._fc
        t1   = dur or clip.duration
        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(tag, x="w-text_w-30", y="28",
                           fontsize=size, color=color, t1=t1))
        return clip

    def word_captions(
        self,
        captions: list[Caption],
        fontsize: int   = 70,
        accent:   str   = "#FFD700",
        y_expr:   str   = "h*0.76",
        use_box:  bool  = True,
    ) -> "Clip":
        """
        Render word-by-word captions (OpusClip style).
        Normal lines → white. Highlighted lines → accent color.
        """
        clip: Clip = self  # type: ignore
        fc = clip._fc
        for cap in captions:
            color = accent if cap.highlight else "white"
            fc.add(FilterChain.LAYER_TEXT,
                   fc.drawtext(cap.text,
                               x="(w-text_w)/2",
                               y=y_expr,
                               fontsize=fontsize,
                               color=color,
                               shadow=True,
                               box=use_box,
                               boxcolor="black@0.45",
                               t0=cap.start,
                               t1=cap.end))
        return clip

    def big_center_text(
        self,
        text:  str,
        t0:    float,
        t1:    float,
        size:  int   = 110,
        color: str   = "#FFD700",
    ) -> "Clip":
        """Large centered text (for emoji or punch words)."""
        clip: Clip = self  # type: ignore
        fc = clip._fc
        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(text, x="(w-text_w)/2", y="h*0.42",
                           fontsize=size, color=color, shadow=True,
                           t0=t0, t1=t1))
        return clip
    def pov_gaming_hook(
        self,
        text:      str,
        accent:    str   = "#00FF88",
        duration:  float = 4.5,
        bar_h:     int   = 140,
    ) -> "Clip":
        """
        Single-line gaming POV hook at the TOP of the frame.
        Shows for `duration` seconds then disappears — clean, minimal.
        Dark semi-transparent bar + 1 line accent text (no word caption wall).
        """
        clip: Clip = self  # type: ignore
        fc   = clip._fc
        safe = text[:50].strip()

        # Dark bar at top
        fc.add(FilterChain.LAYER_OVERLAY,
               f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black@0.55:t=fill"
               f":enable='between(t,0,{duration:.2f})'")

        # Accent text — centered, large
        fc.add(FilterChain.LAYER_TEXT,
               fc.drawtext(safe,
                           x="(w-text_w)/2",
                           y=f"{bar_h // 2 - 28}",
                           fontsize=58,
                           color=accent,
                           shadow=True,
                           box=False,
                           t0=0.0,
                           t1=duration))
        return clip


# ─────────────────────────────────────────────────────────────────────────────
#  CLIP CLASS
# ─────────────────────────────────────────────────────────────────────────────

class Clip(LayoutMixin, FxMixin, TextMixin):
    """
    A video segment ready for professional editing.

    Attributes:
        src      : path to source video
        start    : start time in seconds (in source video)
        end      : end time in seconds (in source video)
        duration : clip length in seconds
        meta     : arbitrary metadata dict (hook, caption, guest info, etc.)

    Chainable API:
        clip = Clip("video.mp4", 45, 105)
        clip.layout.portrait()
        clip.fx.color_grade("viral_punch")
        clip.fx.vignette()
        clip.text.hook_card("Big Hook", "Subtitle")
        clip.text.progress_bar()
        chain = clip.build()
    """

    def __init__(
        self,
        src:      str,
        start:    float = 0.0,
        end:      Optional[float] = None,
        out_w:    int   = 1080,
        out_h:    int   = 1920,
        fps:      int   = 30,
        meta:     Optional[dict] = None,
    ):
        self.src      = src
        self.start    = float(start)
        self.end      = float(end) if end is not None else float(start) + 60.0
        self.duration = self.end - self.start
        self.meta     = meta or {}

        self._fc = FilterChain(
            out_w=out_w, out_h=out_h,
            fps=fps, clip_dur=self.duration,
        )

        # Convenience namespace aliases (fluent API)
        self.layout = self   # self is LayoutMixin
        self.fx     = self   # self is FxMixin
        self.text   = self   # self is TextMixin

    # ── Core ──────────────────────────────────────────────────────────────────

    def build(self) -> str:
        """Returns the FFmpeg -vf filter chain string."""
        return self._fc.build()

    def filter_count(self) -> int:
        return self._fc.count()

    def with_meta(self, **kwargs) -> "Clip":
        self.meta.update(kwargs)
        return self

    def __repr__(self) -> str:
        import os
        return (
            f"<Clip '{os.path.basename(self.src)}' "
            f"{self.start:.1f}s→{self.end:.1f}s "
            f"({self.duration:.1f}s) | {self.filter_count()} filters>"
        )
