"""
viraleditor/layouts/multilayout.py
==================================
Multi-Layout Engine for Viral Shorts.
Implements:
  1. split_2up        : Stacked 2-speaker split screen with gold divider line
  2. full_169_blur    : 16:9 video centered over blurred moving background
  3. picture_in_picture: Main speaker portrait + secondary speaker PiP box
  4. split_3up        : 3-speaker grid layout
  5. auto_dynamic_mix : Auto-switches layouts across clip timeline for 10M+ retention
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from ..renderer import FilterChain

if TYPE_CHECKING:
    from ..clip import Clip


class MultiLayoutEngine:
    """
    Applies multi-screen layouts to a Clip's FilterChain.
    """

    @staticmethod
    def split_2up(
        clip: "Clip",
        top_x: int = 1035,
        bottom_x: int = 420,
        src_w: int = 1920,
        src_h: int = 1080,
        divider_color: str = "#FFD700",
        divider_height: int = 8,
    ) -> "Clip":
        """
        Creates a 2-up stacked split screen (9:16 portrait) with PERFECT DUAL-FACE FRAMING:
          - Top half (Guest Avi Patel): Centered at cx=1035 with top_y=100 (clean headroom)
          - Bottom half (Host): Centered at cx=420 with bottom_y=220 (clean headroom)
          - Accent gold divider bar in middle
        """
        fc = clip._fc
        half_h = fc.out_h // 2 - (divider_height // 2)   # = 956

        crop_h = int(src_h * 0.65)                      # = 702px height
        crop_w = int(crop_h * fc.out_w / half_h)        # = 793px width

        top_y_off = 100                                 # Exact headroom for Guest Avi Patel
        bottom_y_off = 220                              # Exact headroom for Host

        top_x_off = max(0, min(top_x - crop_w // 2, src_w - crop_w))
        bottom_x_off = max(0, min(bottom_x - crop_w // 2, src_w - crop_w))

        # Build split screen via FFmpeg split + crop + vstack
        fc.add(FilterChain.LAYER_LAYOUT, f"split=2[v_top][v_bot]")

        # Top stream (Guest Avi Patel)
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[v_top]crop={crop_w}:{crop_h}:{top_x_off}:{top_y_off},"
            f"scale={fc.out_w}:{half_h},setsar=1[top_scaled]"
        )
        # Bottom stream (Host)
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[v_bot]crop={crop_w}:{crop_h}:{bottom_x_off}:{bottom_y_off},"
            f"scale={fc.out_w}:{half_h},setsar=1[bot_scaled]"
        )

        # Combine stacked
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[top_scaled][bot_scaled]vstack"
        )

        # Apply overlay divider line
        divider_y = half_h
        fc.add(
            FilterChain.LAYER_OVERLAY,
            f"drawbox=x=0:y={divider_y}:w=iw:h={divider_height}:color={divider_color}:t=fill"
        )
        return clip

    @staticmethod
    def full_169_blur(
        clip: "Clip",
        src_w: int = 1920,
        src_h: int = 1080,
        blur_sigma: int = 32,
        pov_text: Optional[str] = None,
    ) -> "Clip":
        """
        Full 16:9 resolution mode:
          - Background: Full video stretched and heavily blurred (gblur=32) + darkened
          - Foreground: Original uncropped 16:9 video centered (1080x607) with sharp border
          - POV Badge: Optional POV text badge at top
        """
        fc = clip._fc
        fg_h = int(fc.out_w * src_h / src_w)   # = 1080 * 1080/1920 = 607
        fg_y = (fc.out_h - fg_h) // 2

        fc.add(FilterChain.LAYER_LAYOUT, "split=2[v_bg][v_fg]")
        # Background stream: scale to portrait + heavy blur + darken
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[v_bg]scale={fc.out_w}:{fc.out_h},"
            f"gblur=sigma={blur_sigma}:steps=3,"
            f"eq=brightness=-0.18:contrast=1.1,setsar=1[bg_blurred]"
        )
        # Foreground stream: scale 16:9 to 1080x607
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[v_fg]scale={fc.out_w}:{fg_h},setsar=1[fg_scaled]"
        )
        # Overlay foreground over blurred background centered
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[bg_blurred][fg_scaled]overlay=0:{fg_y}"
        )

        # Add thin top/bottom gold border lines to 16:9 box
        fc.add(
            FilterChain.LAYER_OVERLAY,
            f"drawbox=x=0:y={fg_y-2}:w=iw:h=4:color=#FFD700:t=fill"
        )
        fc.add(
            FilterChain.LAYER_OVERLAY,
            f"drawbox=x=0:y={fg_y+fg_h-2}:w=iw:h=4:color=#FFD700:t=fill"
        )

        # Top POV Badge overlay if pov_text provided
        if pov_text:
            clean_pov = pov_text.replace(":", "\\:").replace("'", "\\'")
            badge_text = f"POV\\: {clean_pov}"
            fc.add(
                FilterChain.LAYER_TEXT,
                fc.drawtext(
                    badge_text,
                    x="(w-text_w)/2",
                    y=str(fg_y - 110),
                    fontsize=48,
                    color="#FFD700",
                    shadow=True,
                    box=True,
                    boxcolor="black@0.80",
                )
            )
        return clip

    @staticmethod
    def auto_dynamic_mix(
        clip: "Clip",
        top_x: int = 1380,
        bottom_x: int = 420,
        src_w: int = 1920,
        src_h: int = 1080,
        divider_color: str = "#FFD700",
        pov_text: Optional[str] = None,
    ) -> "Clip":
        """
        ULTRA-DYNAMIC TIMELINE-BASED MULTI-LAYOUT SWITCHING (WITHIN A SINGLE SHORT):
          - 0.0s → 4.0s  : Split 2-Up Stacked (Guest + Host intro)
          - 4.0s → 18.0s : Single Speaker YuNet DNN Face Tracking
          - 18.0s → 25.0s: 16:9 Uncropped Blur Background (+ POV Badge)
          - 25.0s → 32.0s: Split 2-Up Stacked (Dual reaction exchange)
          - 32.0s → End  : Single Speaker Close-Up Finish
        """
        fc = clip._fc
        dur = clip.duration
        divider_height = 8
        half_h = fc.out_h // 2 - (divider_height // 2)

        # 1. Base Stream: YuNet DNN speaker face tracking
        try:
            from core.face_tracker import FaceTracker
            tracker = FaceTracker(sample_rate=6)
            crop_data, meta = tracker.analyze_clip(
                clip.src, start_time=clip.start, end_time=clip.end,
                target_width=fc.out_w, target_height=fc.out_h,
            )
            if crop_data:
                fps = meta["fps"]
                min_frames = int(1.2 * fps)
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
                if len(cuts) > 1:
                    parts = [f"between(t,{t0:.2f},{t1:.2f})*{x}" for t0, t1, x in cuts]
                    crop_x_expr = "+".join(parts)
                    fc.add(FilterChain.LAYER_LAYOUT, f"split=3[v_in1][v_in2][v_in3]")
                    new_w = int(src_h * fc.out_w / fc.out_h)
                    fc.add(FilterChain.LAYER_LAYOUT, f"[v_in1]crop={new_w}:{src_h}:'{crop_x_expr}':0,scale={fc.out_w}:{fc.out_h},setsar=1[v_base]")
                else:
                    new_w = int(src_h * fc.out_w / fc.out_h)
                    fc.add(FilterChain.LAYER_LAYOUT, f"split=3[v_in1][v_in2][v_in3]")
                    fc.add(FilterChain.LAYER_LAYOUT, f"[v_in1]crop={new_w}:{src_h}:{cuts[0][2]}:0,scale={fc.out_w}:{fc.out_h},setsar=1[v_base]")
            else:
                new_w = int(src_h * fc.out_w / fc.out_h)
                x_center = (src_w - new_w) // 2
                fc.add(FilterChain.LAYER_LAYOUT, f"split=3[v_in1][v_in2][v_in3]")
                fc.add(FilterChain.LAYER_LAYOUT, f"[v_in1]crop={new_w}:{src_h}:{x_center}:0,scale={fc.out_w}:{fc.out_h},setsar=1[v_base]")
        except Exception:
            new_w = int(src_h * fc.out_w / fc.out_h)
            x_center = (src_w - new_w) // 2
            fc.add(FilterChain.LAYER_LAYOUT, f"split=3[v_in1][v_in2][v_in3]")
            fc.add(FilterChain.LAYER_LAYOUT, f"[v_in1]crop={new_w}:{src_h}:{x_center}:0,scale={fc.out_w}:{fc.out_h},setsar=1[v_base]")

        # 2. Stream 2: Split 2-Up (Perfect Dual Face Framing)
        crop_h = int(src_h * 0.65)
        crop_w = int(crop_h * fc.out_w / half_h)
        top_y_off = 20
        bottom_y_off = 220

        top_x_off = max(0, min(top_x - crop_w // 2, src_w - crop_w))
        bottom_x_off = max(0, min(bottom_x - crop_w // 2, src_w - crop_w))

        fc.add(FilterChain.LAYER_LAYOUT, f"[v_in2]split=2[v_t][v_b]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[v_t]crop={crop_w}:{crop_h}:{top_x_off}:{top_y_off},scale={fc.out_w}:{half_h},setsar=1[t_sc]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[v_b]crop={crop_w}:{crop_h}:{bottom_x_off}:{bottom_y_off},scale={fc.out_w}:{half_h},setsar=1[b_sc]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[t_sc][b_sc]vstack,drawbox=x=0:y={half_h}:w=iw:h={divider_height}:color={divider_color}:t=fill[v_split2up]")

        # 3. Stream 3: 16:9 Blur Background
        fg_h = int(fc.out_w * src_h / src_w)
        fg_y = (fc.out_h - fg_h) // 2
        fc.add(FilterChain.LAYER_LAYOUT, f"[v_in3]split=2[v_bg][v_fg]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[v_bg]scale={fc.out_w}:{fc.out_h},gblur=sigma=32:steps=3,eq=brightness=-0.18:contrast=1.1,setsar=1[bg_bl]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[v_fg]scale={fc.out_w}:{fg_h},setsar=1[fg_sc]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[bg_bl][fg_sc]overlay=0:{fg_y},drawbox=x=0:y={fg_y-2}:w=iw:h=4:color={divider_color}:t=fill,drawbox=x=0:y={fg_y+fg_h-2}:w=iw:h=4:color={divider_color}:t=fill[v_blur169]")

        # 4. Timeline Overlay Composition
        t_split1_end = min(4.0, dur * 0.15)
        t_blur_start = min(18.0, dur * 0.45)
        t_blur_end   = min(25.0, dur * 0.65)
        t_split2_start = min(25.0, dur * 0.65)
        t_split2_end   = min(32.0, dur * 0.82)

        fc.add(FilterChain.LAYER_LAYOUT, f"[v_base][v_split2up]overlay=0:0:enable='between(t,0,{t_split1_end:.2f})+between(t,{t_split2_start:.2f},{t_split2_end:.2f})'[v_mid]")
        fc.add(FilterChain.LAYER_LAYOUT, f"[v_mid][v_blur169]overlay=0:0:enable='between(t,{t_blur_start:.2f},{t_blur_end:.2f})'")

        # Top POV Badge overlay if pov_text provided
        if pov_text:
            clean_pov = pov_text.replace(":", "\\:").replace("'", "\\'")
            badge_text = f"POV\\: {clean_pov}"
            fc.add(
                FilterChain.LAYER_TEXT,
                fc.drawtext(
                    badge_text,
                    x="(w-text_w)/2",
                    y=str(fg_y - 110),
                    fontsize=48,
                    color="#FFD700",
                    shadow=True,
                    box=True,
                    boxcolor="black@0.80",
                    t0=t_blur_start,
                    t1=t_blur_end,
                )
            )
        return clip

    @staticmethod
    def picture_in_picture(
        clip: "Clip",
        main_x: int = 1200,
        pip_x: int = 420,
        pip_size: int = 340,
        src_w: int = 1920,
        src_h: int = 1080,
    ) -> "Clip":
        """
        Picture-in-Picture layout:
          - Main screen: Guest Avi Patel portrait crop (1080x1920)
          - PiP overlay: Host face in a 340x340 rounded box at bottom-right
        """
        fc = clip._fc
        new_w = int(src_h * fc.out_w / fc.out_h)

        main_x_off = max(0, min(main_x - new_w // 2, src_w - new_w))
        pip_x_off = max(0, min(pip_x - src_h // 2, src_w - src_h))

        fc.add(FilterChain.LAYER_LAYOUT, "split=2[v_main][v_pip]")

        # Main background
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[v_main]crop={new_w}:{src_h}:{main_x_off}:0,"
            f"scale={fc.out_w}:{fc.out_h},setsar=1[main_scaled]"
        )
        # PiP square box
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[v_pip]crop={src_h}:{src_h}:{pip_x_off}:0,"
            f"scale={pip_size}:{pip_size},setsar=1[pip_scaled]"
        )

        pip_pos_x = fc.out_w - pip_size - 40
        pip_pos_y = fc.out_h - pip_size - 180

        # Overlay PiP
        fc.add(
            FilterChain.LAYER_LAYOUT,
            f"[main_scaled][pip_scaled]overlay={pip_pos_x}:{pip_pos_y}"
        )

        # PiP border frame
        fc.add(
            FilterChain.LAYER_OVERLAY,
            f"drawbox=x={pip_pos_x-3}:y={pip_pos_y-3}:"
            f"w={pip_size+6}:h={pip_size+6}:color=#FFD700:t=4"
        )
        return clip
