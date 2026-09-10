"""
scene_state_machine.py — 4-State Dynamic Scene Synthesis Engine
==============================================================
Implements:
- State 1: Kinetic Intro & Hook (3 dynamic video planes with 3D perspective, zoom-in S(t)=1+0.35*(t/t_hook)^2)
- State 2: Educational Explanation & Dynamic Memes (Bézier arrow B(u), 50/50 split or framed layout, beat-snapped silent memes)
- State 3: Training Proof & Headshot Montage (beat transitions with camera shake X(t) and scale impulse S(t))
- State 4: Dynamic Spec Card HUD (overshoot slide-in Y(t)=Y0+600*(1-u)^3 - 30*sin(pi*u), target sensitivity numbers)
"""

import os
import math
import random
import tempfile
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.orientation_helper import get_video_orientation_filter


def render_bezier_arrow_overlay(width: int, height: int, duration_sec: float, fps: int = 60) -> list:
    """
    Renders procedural Bézier arrow sequence:
    B(u) = (1-u)^3 P0 + 3(1-u)^2 u P1 + 3(1-u) u^2 P2 + u^3 P3
    with easing u(t) = 1 - (1 - t / Delta_t)^3
    Pointing upwards towards the headshot shooting zone.
    Returns list of BGRA numpy frames.
    """
    n_frames = int(duration_sec * fps)
    frames = []

    # Control points for Free Fire shooting button flick (pointing up-right to head)
    p0 = np.array([width * 0.72, height * 0.78])   # Button base
    p1 = np.array([width * 0.70, height * 0.65])   # Upward pull
    p2 = np.array([width * 0.65, height * 0.52])   # Arc
    p3 = np.array([width * 0.52, height * 0.42])   # Headshot target zone

    for f_i in range(n_frames):
        t_rel = f_i / max(1, n_frames - 1)
        # Cubic easing: u(t) = 1 - (1 - t/Delta_t)^3
        u = 1.0 - (1.0 - t_rel) ** 3

        # Compute point along cubic Bézier
        pt = (
            ((1 - u) ** 3) * p0 +
            (3 * ((1 - u) ** 2) * u) * p1 +
            (3 * (1 - u) * (u ** 2)) * p2 +
            (u ** 3) * p3
        )

        # Transparent canvas
        img = np.zeros((height, width, 4), dtype=np.uint8)

        # Draw glowing path up to u
        steps = int(max(2, u * 40))
        pts_path = []
        for s in range(steps):
            u_s = s / 40.0
            p_s = (
                ((1 - u_s) ** 3) * p0 +
                (3 * ((1 - u_s) ** 2) * u_s) * p1 +
                (3 * (1 - u_s) * (u_s ** 2)) * p2 +
                (u_s ** 3) * p3
            )
            pts_path.append((int(p_s[0]), int(p_s[1])))

        if len(pts_path) >= 2:
            # Yellow glow stroke
            for i in range(len(pts_path) - 1):
                cv2.line(img, pts_path[i], pts_path[i+1], (0, 180, 255, 120), 12, cv2.LINE_AA)
            # Red/Gold core stroke
            for i in range(len(pts_path) - 1):
                cv2.line(img, pts_path[i], pts_path[i+1], (0, 230, 255, 255), 5, cv2.LINE_AA)

            # Arrowhead at current tip pt
            tip = (int(pt[0]), int(pt[1]))
            cv2.circle(img, tip, 10, (0, 255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(img, tip, 18, (0, 165, 255, 160), 3, cv2.LINE_AA)

        frames.append(img)

    return frames


def build_3d_kinetic_hook_filter(plane_indices: list, duration: float, out_w: int, out_h: int) -> tuple:
    """
    State 1: Builds 3 dynamic video planes with 3D perspective warp:
    Left (-30 deg Y-rot), Center (0 deg), Right (+30 deg Y-rot).
    Camera zoom-in: S(t) = 1.0 + 0.35 * (t / t_hook)^2
    """
    filter_chains = []
    p_left, p_center, p_right = plane_indices[0], plane_indices[1], plane_indices[2]

    # Individual plane width & height
    pw = int(out_w * 0.48)
    ph = int(out_h * 0.65)

    # 3D perspective projection matrices using perspective filter in FFmpeg
    # Left (-30 deg Y-rot perspective): left side taller, right side compressed
    # perspective=x0:y0:x1:y1:x2:y2:x3:y3
    # Center (Frontal): clean centered crop
    # Right (+30 deg Y-rot perspective): left side compressed, right side taller
    filter_chains.append(
        f"[{p_left}:v]scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph},"
        f"perspective=x0=0:y0=20:x1={pw}:y1=70:x2=0:y2={ph-20}:x3={pw}:y3={ph-70}[hook_left];"
    )
    filter_chains.append(
        f"[{p_center}:v]scale={int(out_w*0.65)}:{int(out_h*0.75)}:force_original_aspect_ratio=increase,"
        f"crop={int(out_w*0.65)}:{int(out_h*0.75)}[hook_center];"
    )
    filter_chains.append(
        f"[{p_right}:v]scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph},"
        f"perspective=x0=0:y0=70:x1={pw}:y1=20:x2=0:y2={ph-70}:x3={pw}:y3={ph-20}[hook_right];"
    )

    # Composite 3 planes on black backdrop
    filter_chains.append(
        f"color=c=black:s={out_w}x{out_h}:d={duration:.2f}[hook_bg];"
    )
    filter_chains.append(
        f"[hook_bg][hook_left]overlay=x=20:y=(H-h)/2[hook_comp1];"
    )
    filter_chains.append(
        f"[hook_comp1][hook_right]overlay=x=W-w-20:y=(H-h)/2[hook_comp2];"
    )
    # Center plane on top with subtle gold border
    filter_chains.append(
        f"[hook_center]pad=iw+8:ih+8:4:4:color=gold@0.8[hook_center_border];"
    )
    filter_chains.append(
        f"[hook_comp2][hook_center_border]overlay=x=(W-w)/2:y=(H-h)/2[hook_3d_static];"
    )

    # Apply Camera Zoom-In S(t) = 1.0 + 0.35 * (t / t_hook)^2
    # In FFmpeg, smooth scale expression:
    scale_expr = f"1.0+0.35*pow(t/{duration:.2f},2)"
    filter_chains.append(
        f"[hook_3d_static]scale=eval=frame:w='iw*({scale_expr})':h='ih*({scale_expr})',"
        f"crop={out_w}:{out_h}:(iw-{out_w})/2:(ih-{out_h})/2,fps=60,setsar=1[v_state1];"
    )

    return "\n".join(filter_chains), "v_state1"


def render_dynamic_spec_card_hud(
    out_w: int,
    out_h: int,
    duration: float = 8.0,
    sens_general: int = 100,
    sens_reddot: int = 98,
    sens_2x: int = 95,
    sens_4x: int = 90,
    dpi: int = 580,
    btn_size: int = 42
) -> str:
    """
    State 4: Generates a premium Free Fire sensitivity spec card image.
    Slide-in with overshoot is executed via FFmpeg expression:
    Y(t) = Y_target + 600*(1-u)^3 - 30*sin(pi*u), u = (t - t_start)/0.45
    """
    card_w = min(out_w - 60, 940)
    card_h = 480
    card = Image.new("RGBA", (card_w, card_h), (18, 22, 32, 240))
    draw = ImageDraw.Draw(card)
    font_title = None
    font_body = None
    font_bold = None
    for f_cand in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariblk.ttf", "arialbd.ttf"]:
        if os.path.exists(f_cand):
            try:
                font_title = ImageFont.truetype(f_cand, 26)
                font_bold = ImageFont.truetype(f_cand, 22)
                break
            except Exception:
                pass
    for f_cand in ["C:/Windows/Fonts/arial.ttf", "arial.ttf"]:
        if os.path.exists(f_cand):
            try:
                font_body = ImageFont.truetype(f_cand, 20)
                break
            except Exception:
                pass

    # Outer border
    draw.rectangle([(0, 0), (card_w - 1, card_h - 1)], outline=(255, 199, 0, 255), width=3)

    # Header
    draw.rectangle([(0, 0), (card_w, 65)], fill=(255, 46, 85, 255))
    draw.text((25, 16), "CODIGO HEADSHOT — CONFIGURACION VIP", fill=(255, 255, 255), font=font_title or font_bold)

    # Specs table
    specs = [
        ("General:", f"{sens_general}%", "Mira Punto Rojo:", f"{sens_reddot}%"),
        ("Mira 2X:", f"{sens_2x}%", "Mira 4X:", f"{sens_4x}%"),
        ("DPI Recomendado:", f"{dpi}", "Boton de Disparo:", f"{btn_size}%")
    ]

    y_offset = 100
    for row in specs:
        draw.text((35, y_offset), row[0], fill=(160, 175, 200), font=font_body)
        draw.text((230, y_offset), row[1], fill=(255, 199, 0), font=font_bold)
        draw.text((card_w // 2 + 30, y_offset), row[2], fill=(160, 175, 200), font=font_body)
        draw.text((card_w // 2 + 250, y_offset), row[3], fill=(255, 199, 0), font=font_bold)
        y_offset += 75

    # Footer note
    draw.text((35, card_h - 45), "codigoheadshot.online — 100% Tiros Rojos", fill=(255, 255, 255), font=font_body)

    out_path = Path(tempfile.gettempdir()) / "dynamic_spec_card.png"
    card.save(out_path)
    return str(out_path)
