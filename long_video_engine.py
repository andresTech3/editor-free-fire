"""
long_video_engine.py — Master Programmatic Rendering Engine for 16:9 Long YouTube Videos (1920x1080 60fps)
=======================================================================================================
Architecture:
1. Intelligent Semantic Audio-to-Visual Director (Whisper Contextual Analysis).
2. Orientation Corrector: Auto-detects sideways/inverted iPhone recordings (1290x2796) and straightens them upright with transpose=2.
3. Voiceover Audio Splicer & Meme Cuts: Pauses/cuts voiceover audio during memes, plays full meme audio/video, and resumes voiceover seamlessly after.
4. Contextual Visual Overlays (Diamonds, Sensitivity menus, Book/Web guides, Emotes, Weapons) + matching SFX.
5. CONTEXTUAL Memes (strictly matched to audio speech & emotion — NEVER random!) from PACK DE MEMES (16:9).
6. OpenCV HSV Red Headshot Detection & 16:9 B-roll Crop/Scale (1920x1080 60fps).
7. Subtitle Sync & Shifting: Synchronized dynamic .ass subtitles shifted to avoid meme gaps.
8. Green-Screen Like & Subscribe CTA badge (Zero black frames).
9. Final MP4 H.264/AAC 1920x1080 60fps (+faststart).
"""

import os
import sys
import math
import time
import glob
import json
import random
import argparse
import tempfile
import subprocess
from pathlib import Path

# Set UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from audio_analyzer import analyze_voiceover_timeline, get_audio_duration
from core.semantic_director import SemanticDirector
from core.asset_catalog import (
    ASSETS_ROOT,
    DIR_GAMEPLAYS,
    DIR_IMAGES,
    DIR_PACK_MEMES,
    DIR_GREEN_MEMES,
    DIR_SFX,
    DIR_MUSIC
)
from core.orientation_helper import (
    get_video_orientation_filter,
    get_image_orientation_filter,
    get_media_orientation_filter,
    is_upright_portrait_video
)

# ── PATHS & CONFIGURATION ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
ASSETS_DIR = PROJECT_ROOT / "assets" / "Recurso video Freefire"

JUGADAS_DIR = ASSETS_DIR / "free fire jugadas"
MEMES_PACK_DIR = ASSETS_DIR / "PACK DE MEMES"
MEMES_GREEN_DIR = ASSETS_DIR / "PACK MEMES PANTALLA VERDE 1 (manuDT)"
MUSICA_DIR = ASSETS_DIR / "musica"
SFX_DIR = ASSETS_DIR / "efectos de sonidos"
IMAGENES_DIR = ASSETS_DIR / "Imagenes"
GENERATE_VIDEO_DIR = ASSETS_DIR / "Generar Video"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
OVERLAYS_DIR = PROJECT_ROOT / "overlays"

FPS = 60
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# OpenCV HSV Red Damage Numbers (Headshot) Ranges
LOWER_RED1 = np.array([0, 150, 150])
UPPER_RED1 = np.array([10, 255, 255])
LOWER_RED2 = np.array([170, 150, 150])
UPPER_RED2 = np.array([180, 255, 255])

def file_has_audio(file_path: str) -> bool:
    """Checks if a media file has an audio stream."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return "audio" in res.stdout.lower()
    except Exception:
        return False


def scan_video_for_red_headshots(video_path, sample_fps=4.0):
    """Scans gameplay video for RED HEADSHOT damage numbers."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return []

    frame_step = max(1, int(fps / sample_fps))
    headshot_moments = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        timestamp = frame_idx / fps
        h, w = frame.shape[:2]

        roi_center = frame[int(h * 0.15):int(h * 0.65), int(w * 0.20):int(w * 0.80)]
        hsv_center = cv2.cvtColor(roi_center, cv2.COLOR_BGR2HSV)
        mask_r1 = cv2.inRange(hsv_center, LOWER_RED1, UPPER_RED1)
        mask_r2 = cv2.inRange(hsv_center, LOWER_RED2, UPPER_RED2)
        red_score = float(np.sum(cv2.bitwise_or(mask_r1, mask_r2) > 0))

        if red_score > 35:
            headshot_moments.append((timestamp, red_score))

        frame_idx += frame_step
        for _ in range(frame_step - 1):
            if not cap.grab(): break

    cap.release()
    headshot_moments.sort(key=lambda x: x[1], reverse=True)
    return headshot_moments

def collect_169_gameplay_videos(custom_dir=None):
    """Scans for gameplay clips inside /free fire jugadas/ or custom_dir, excluding emotes and memes."""
    target_dir = Path(custom_dir) if (custom_dir and os.path.exists(custom_dir)) else JUGADAS_DIR
    if not target_dir.exists():
        target_dir = ASSETS_DIR

    gameplay_files = []
    exclude_kw = ["pack memes", "generar video", "imagenes", "efectos de sonidos", "musica", "emote", "emotes", "intro"]
    for ext in ["*.mp4", "*.mov", "*.MP4", "*.MOV", "*.avi", "*.mkv"]:
        for f in target_dir.rglob(ext):
            p_str = str(f).lower()
            if any(ex in p_str for ex in exclude_kw):
                continue
            gameplay_files.append(f)

    if not gameplay_files and target_dir != JUGADAS_DIR:
        for ext in ["*.mp4", "*.mov", "*.MP4", "*.MOV", "*.avi", "*.mkv"]:
            for f in JUGADAS_DIR.rglob(ext):
                p_str = str(f).lower()
                if any(ex in p_str for ex in exclude_kw):
                    continue
                gameplay_files.append(f)

    return list(dict.fromkeys(gameplay_files))

def generate_remotion_overlays_if_needed():
    """Runs remotion_overlays.js to ensure transparent WebM overlays are generated."""
    hud_file = OVERLAYS_DIR / "hud_sensibilidad.webm"
    cta_file = OVERLAYS_DIR / "cta_like_subscribe.webm"

    if not hud_file.exists() or not cta_file.exists():
        print("🎬 Generating Remotion Transparent WebM Overlays...")
        try:
            node_script = PROJECT_ROOT / "remotion_overlays.js"
            subprocess.run(["node", str(node_script)], cwd=str(PROJECT_ROOT), check=True)
        except Exception as e:
            print(f"⚠️ Remotion overlay generation warning: {e}")

    return hud_file if hud_file.exists() else None, cta_file if cta_file.exists() else None

def shift_subtitles_for_memes(transcribed_segments, meme_events, hook_duration=0.0, intro_duration=0.0):
    """
    Shifts subtitle timestamps forward by the intro duration and cumulative duration of memes that appeared before them.
    Splits any segment that crosses a meme cut or the intro cut so subtitles disappear during breaks.
    """
    if not transcribed_segments:
        return []

    sorted_memes = sorted(meme_events, key=lambda x: x["time"]) if meme_events else []

    def get_shift_at(t):
        s = intro_duration if (intro_duration > 0 and t >= hook_duration) else 0.0
        for m in sorted_memes:
            if m["time"] <= t:
                s += m["duration"]
        return s

    shifted = []
    for seg in transcribed_segments:
        st = seg["start"]
        et = seg["end"]
        text = seg.get("text", "").strip()
        if not text:
            continue

        # Split segment if it crosses the hook cut point before the intro
        if intro_duration > 0 and st < hook_duration < et:
            shifted.append({"start": st, "end": hook_duration, "text": text})
            st = hook_duration

        cuts = [m for m in sorted_memes if st < m["time"] < et]
        if not cuts:
            st_out = st + get_shift_at(st)
            et_out = et + get_shift_at(st)
            if et_out > st_out:
                shifted.append({"start": st_out, "end": et_out, "text": text})
        else:
            curr_st = st
            for m in cuts:
                c_t = m["time"]
                st_out = curr_st + get_shift_at(curr_st)
                et_out = c_t + get_shift_at(curr_st)
                if et_out > st_out:
                    shifted.append({"start": st_out, "end": et_out, "text": text})
                curr_st = c_t
            st_out = curr_st + get_shift_at(curr_st)
            et_out = et + get_shift_at(curr_st)
            if et_out > st_out:
                shifted.append({"start": st_out, "end": et_out, "text": text})

    return shifted

def create_ass_subtitles(vo_timeline, output_ass_path, transcribed_segments=None, meme_events=None, hook_duration=0.0, intro_duration=0.0):
    """
    Generates dynamic highlighted ASS subtitles centered at y:850px with Arial Black font,
    yellow/white text, 4px black outline and soft shadow.
    Uses exact transcribed text shifted to accommodate intro and meme pauses.
    """
    header = (
        "[Script Info]\n"
        "Title: Long 16:9 YouTube Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial Black,48,&H0000FFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,100,100,110,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = [header]
    style_tag = "{\\b1\\c&H0000FFFF&}"

    shifted_segments = shift_subtitles_for_memes(transcribed_segments, meme_events, hook_duration=hook_duration, intro_duration=intro_duration)

    if shifted_segments:
        for seg in shifted_segments:
            st = seg["start"]
            et = seg["end"]
            text = seg.get("text", "").strip().upper()
            if not text: continue

            m_st, s_st = divmod(st, 60)
            h_st, m_st = divmod(m_st, 60)
            m_et, s_et = divmod(et, 60)
            h_et, m_et = divmod(m_et, 60)

            t_start = f"{int(h_st):01d}:{int(m_st):02d}:{s_st:05.2f}"
            t_end = f"{int(h_et):01d}:{int(m_et):02d}:{s_et:05.2f}"

            lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{style_tag}{text}\n")
    else:
        speech_windows = vo_timeline.get("speech_windows", [])
        sample_texts = [
            "SENSIBILIDAD TODO ROJO FREE FIRE",
            "CONFIGURACIÓN SUPREMA Y DPI PERFECTO",
            "ALZA LA MIRA SIN FALLAR NINGÚN TIRO",
            "TRUCO EXCLUSIVO DE LOS PRO PLAYERS",
            "DISPARO A LA CABEZA GARANTIZADO",
            "MODO INSANO ACTIVADO TODO ROJO"
        ]
        for idx, (st, et) in enumerate(speech_windows):
            text = sample_texts[idx % len(sample_texts)]
            m_st, s_st = divmod(st, 60)
            h_st, m_st = divmod(m_st, 60)
            m_et, s_et = divmod(et, 60)
            h_et, m_et = divmod(m_et, 60)

            t_start = f"{int(h_st):01d}:{int(m_st):02d}:{s_st:05.2f}"
            t_end = f"{int(h_et):01d}:{int(m_et):02d}:{s_et:05.2f}"

            lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{style_tag}{text}\n")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return output_ass_path

# ── MASTER ASSEMBLY ENGINE ──────────────────────────────────────────────────
def assemble_long_169_video(audio_path, custom_gameplay_dir=None, custom_bgm=None, out_dir=None, out_name="long_video_16x9.mp4"):
    """
    Executes the 16:9 Long Video Programmatic Editing Pipeline:
    - Auto-detects and rotates sideways clips upright (transpose=2).
    - Hard audio splicing: pauses voiceover during memes, plays meme audio/video, resumes voiceover cleanly.
    - Shifts visual overlays and subtitles to stay synchronized.
    - Zero black screens and strictly contextual memes.
    """
    print("\n" + "═"*75)
    print("🎬 MASTER LONG 16:9 YOUTUBE VIDEO GENERATOR (1920x1080 60fps)")
    print("═"*75)
    print(f"📂 Master Resource Directory: {ASSETS_DIR}")

    # 1. Intelligent Semantic Audio-to-Visual Director
    print("🧠 Running Semantic Audio-to-Visual Director...")
    semantic_director = SemanticDirector(whisper_model="base")
    plan = semantic_director.plan_timeline(audio_path, is_short=False)

    vo_timeline = analyze_voiceover_timeline(audio_path)
    total_vo_dur = plan.get("total_duration") or vo_timeline["total_duration"]
    cta_events = vo_timeline.get("cta_events", [])

    raw_visual_events = plan.get("visual_events", [])
    raw_meme_events = plan.get("meme_events", [])
    transcribed_segments = plan.get("segments", [])

    # ── INTRO & HOOK SPECIFICATION ──────────────────────────────────────────
    # User requirement: "agrega siempre mas que todo en los videos largos la intro que te pase que se reproduzca despues del hook del video y eso si quiero que sea completo"
    intro_file_path = JUGADAS_DIR / "Intro.mp4"
    if not intro_file_path.exists():
        intro_file_path = ASSETS_DIR / "free fire jugadas" / "Intro.mp4"

    has_intro = intro_file_path.exists()
    intro_dur = 10.0 if has_intro else 0.0

    # Calculate Hook Duration (end of first statement/segment, between 3.5s and 7.5s)
    hook_duration = 5.0
    if transcribed_segments and len(transcribed_segments) > 0:
        seg0_end = transcribed_segments[0].get("end", 5.0)
        if 3.5 <= seg0_end <= 7.5:
            hook_duration = round(seg0_end, 2)
        elif seg0_end > 7.5:
            hook_duration = 5.0
        else:
            if len(transcribed_segments) > 1 and transcribed_segments[1].get("end", 0) <= 7.5:
                hook_duration = round(transcribed_segments[1]["end"], 2)
            else:
                hook_duration = round(max(3.5, seg0_end), 2)

    # Sort memes chronologically by cut time in voiceover
    raw_meme_events = sorted(raw_meme_events, key=lambda x: x["time"])

    # Sanitize memes to ensure clean gaps (memes only AFTER the hook, spaced cleanly)
    meme_events = []
    last_cut = hook_duration
    for m in raw_meme_events:
        t = m["time"]
        if t >= hook_duration + 1.2 and t >= last_cut + 2.0 and t < total_vo_dur - 0.5:
            meme_events.append(m)
            last_cut = t

    # ── TIMELINE SHIFT CALCULATIONS ─────────────────────────────────────────
    cum_meme_time = sum(m["duration"] for m in meme_events)
    for i, m in enumerate(meme_events):
        m["out_time"] = m["time"] + (intro_dur if has_intro and m["time"] >= hook_duration else 0.0) + sum(prev["duration"] for prev in meme_events[:i])
        m["out_end"] = m["out_time"] + m["duration"]

    def map_vo_time_to_output(t: float) -> float:
        """Maps an original voiceover timestamp to the shifted output video timeline (incorporating intro and meme pauses)."""
        shift = 0.0
        if has_intro and t >= hook_duration:
            shift += intro_dur
        for m in meme_events:
            if m["time"] < t:
                shift += m["duration"]
        return t + shift

    total_output_dur = total_vo_dur + (intro_dur if has_intro else 0.0) + cum_meme_time

    # Shift visual events
    visual_events = []
    for v in raw_visual_events:
        v_copy = dict(v)
        v_out_st = map_vo_time_to_output(v["time"])
        v_copy["out_time"] = v_out_st
        v_copy["out_end"] = v_out_st + v["duration"]
        visual_events.append(v_copy)

    print(f"⏱️ Timeline Architecture: Voiceover = {total_vo_dur:.2f}s | Hook = {hook_duration:.2f}s | Intro = {intro_dur:.2f}s | Memes = {cum_meme_time:.2f}s | Total Video = {total_output_dur:.2f}s")
    if has_intro:
        print(f"🌟 Complete Channel Intro: [{hook_duration:.2f}s - {hook_duration + intro_dur:.2f}s] ({intro_dur:.2f}s) ➔ {intro_file_path.name}")
    print(f"🤡 Contextual Memes ({len(meme_events)} scheduled with Audio Hard-Cut):")
    for m in meme_events:
        print(f"   • Voice cut at {m['time']:.2f}s ➔ Video output [{m['out_time']:.2f}s - {m['out_end']:.2f}s] ({m['duration']:.2f}s) | {os.path.basename(m['meme_path'])}")

    print(f"📌 Contextual Visual Overlays ({len(visual_events)} scheduled):")
    for v in visual_events:
        print(f"   • Voice {v['time']:.2f}s ➔ Video output [{v['out_time']:.2f}s - {v['out_end']:.2f}s] | {v['label']} ({os.path.basename(v['asset_path'])})")

    # 2. Collect 16:9 Gameplay Clips
    gameplay_files = collect_169_gameplay_videos(custom_gameplay_dir)
    if not gameplay_files:
        print(f"❌ Error: No 16:9 gameplay clips found in {JUGADAS_DIR}")
        sys.exit(1)

    print(f"🎥 Discovered {len(gameplay_files)} Gameplay Video Files")

    # 3. Ensure Remotion Transparent WebM Overlays
    hud_overlay, cta_overlay = generate_remotion_overlays_if_needed()

    # 4. Pre-scan Headshots in Gameplays using OpenCV HSV Detector (with JSON caching)
    cache_file = ASSETS_DIR / "headshots_cache.json"
    headshot_map = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                headshot_map = json.load(f)
            print(f"🎯 Loaded {len(headshot_map)} gameplay headshot maps from cache.")
        except Exception:
            headshot_map = {}

    if not headshot_map:
        for gfile in gameplay_files:
            hs_list = scan_video_for_red_headshots(gfile)
            if hs_list:
                headshot_map[str(gfile)] = hs_list
                print(f"🎯 OpenCV Headshot Detector: {len(hs_list)} RED HEADSHOTS detected in {gfile.name}")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(headshot_map, f)
        except Exception:
            pass

    # 5. Build Dynamic Rhythmic B-Roll Timeline (Alternating Frenetic & Slow Cuts)
    # User request: "quiero que cada video sea diferente, utilizar otros clips u otras partes del mismo clip,
    # colocar partes frenéticas rápido y después lentas"
    shuffled_gameplays = gameplay_files.copy()
    random.shuffle(shuffled_gameplays)

    # Rhythmic alternation cycle: Frenetic (fast cuts, 1.25x-1.35x speed) -> Slow (steady cuts, 1.0x speed) -> Medium
    rhythm_cycle = ['frenetic', 'frenetic', 'slow', 'frenetic', 'medium', 'slow', 'frenetic', 'frenetic', 'slow']

    used_ranges = {str(g): [] for g in gameplay_files}
    idx = 0

    # ── A. Hook Segments (Covering PRECISELY hook_duration before Intro) ───────
    hook_segments = []
    if has_intro:
        current_hook_dur = 0.0
        while current_hook_dur < hook_duration - 0.05:
            gfile = shuffled_gameplays[idx % len(shuffled_gameplays)]
            gpath = str(gfile)
            idx += 1

            cap = cv2.VideoCapture(gpath)
            fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
            n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 300
            gdur = n_frames / fps_in
            cap.release()

            safe_end = max(1.0, gdur - 2.5)
            if safe_end < 2.0:
                continue

            needed_dur = round(hook_duration - current_hook_dur, 2)
            tl_dur = min(needed_dur, round(random.uniform(1.8, 2.6), 2))
            if needed_dur - tl_dur < 1.0:
                tl_dur = needed_dur

            speed = 1.25
            source_dur = round(tl_dur * speed, 2)
            if source_dur >= safe_end - 1.0:
                source_dur = max(1.0, safe_end - 1.0)
                tl_dur = round(source_dur / speed, 2)
                if tl_dur > needed_dur:
                    tl_dur = needed_dur
                    source_dur = round(tl_dur * speed, 2)

            hs_list = headshot_map.get(gpath, [])
            cand_start = 1.0
            is_hs = False
            if hs_list:
                for (hs_t, hs_sc) in hs_list:
                    st = max(1.0, hs_t - 0.7)
                    if st + source_dur <= safe_end:
                        cand_start = st
                        is_hs = True
                        break

            used_ranges[gpath].append(cand_start)
            hook_segments.append({
                "path": gpath,
                "name": gfile.name,
                "start": cand_start,
                "dur": source_dur,
                "timeline_dur": tl_dur,
                "speed": speed,
                "mode": "🔥 HOOK (Opening Cut)",
                "is_headshot": is_hs
            })
            current_hook_dur += tl_dur

        # Ensure hook segments sum up to PRECISELY hook_duration
        if hook_segments:
            discrepancy = round(hook_duration - sum(s["timeline_dur"] for s in hook_segments), 2)
            if discrepancy != 0:
                hook_segments[-1]["timeline_dur"] = round(hook_segments[-1]["timeline_dur"] + discrepancy, 2)
                hook_segments[-1]["dur"] = round(hook_segments[-1]["timeline_dur"] * hook_segments[-1]["speed"], 2)

    # ── B. Post-Intro B-Roll Segments ──────────────────────────────────────
    post_intro_segments = []
    current_post_broll = 0.0
    target_post_broll = total_output_dur - hook_duration - (intro_dur if has_intro else 0.0) + 5.0

    while current_post_broll < target_post_broll:
        gfile = shuffled_gameplays[idx % len(shuffled_gameplays)]
        gpath = str(gfile)
        idx += 1

        cap = cv2.VideoCapture(gpath)
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 300
        gdur = n_frames / fps_in
        cap.release()

        safe_end = max(1.0, gdur - 2.5)  # Avoid tail-end iPhone Control Center swipe down
        if safe_end < 2.0:
            continue

        r_type = rhythm_cycle[len(post_intro_segments) % len(rhythm_cycle)]
        if r_type == 'frenetic':
            tl_dur = round(random.uniform(1.3, 1.8), 2)
            speed = round(random.uniform(1.22, 1.35), 2)
            mode_label = '⚡ FRENETIC (Fast)'
        elif r_type == 'slow':
            tl_dur = round(random.uniform(3.4, 4.5), 2)
            speed = 1.0
            mode_label = '🧘 SLOW (Calm/Pausado)'
        else:  # medium
            tl_dur = round(random.uniform(2.2, 2.8), 2)
            speed = 1.10
            mode_label = '🎯 MEDIUM (Transition)'

        source_dur = round(tl_dur * speed, 2)
        if source_dur >= safe_end - 1.0:
            source_dur = max(1.0, safe_end - 1.0)
            tl_dur = round(source_dur / speed, 2)

        # Check for red headshots to align action cuts
        hs_list = headshot_map.get(gpath, [])
        cand_start = None
        is_hs = False

        if hs_list and r_type in ['frenetic', 'medium']:
            for (hs_t, hs_sc) in hs_list:
                st = max(1.0, hs_t - 0.7)
                if st + source_dur <= safe_end:
                    if not any(abs(st - existing) < (source_dur + 1.5) for existing in used_ranges[gpath]):
                        cand_start = st
                        is_hs = True
                        break

        if cand_start is None:
            max_st = max(1.0, safe_end - source_dur)
            for _ in range(15):
                st = round(random.uniform(1.0, max_st), 2)
                if not any(abs(st - existing) < (source_dur + 1.5) for existing in used_ranges[gpath]):
                    cand_start = st
                    break
            if cand_start is None:
                cand_start = 1.0

        used_ranges[gpath].append(cand_start)
        post_intro_segments.append({
            "path": gpath,
            "name": gfile.name,
            "start": cand_start,
            "dur": source_dur,
            "timeline_dur": tl_dur,
            "speed": speed,
            "mode": mode_label,
            "is_headshot": is_hs
        })
        current_post_broll += tl_dur

    broll_segments = hook_segments + post_intro_segments

    print(f"🎬 Dynamic Rhythmic Montage ({len(broll_segments)} cuts generated: {len(hook_segments)} hook + {len(post_intro_segments)} post-intro):")
    for b_i, seg in enumerate(broll_segments):
        print(f"   {b_i+1:02d}. [{seg['mode']}] {seg['name']} | st={seg['start']:.2f}s, dur={seg['timeline_dur']:.2f}s, speed={seg['speed']}x")

    # 6. Prepare Output Destination & Subtitles (.ass)
    target_out_dir = Path(out_dir) if (out_dir and os.path.exists(out_dir)) else DEFAULT_OUTPUT_DIR
    target_out_dir.mkdir(parents=True, exist_ok=True)
    if not out_name.lower().endswith(".mp4"):
        out_name += ".mp4"
    final_output_path = target_out_dir / out_name

    tmp_ass = str(PROJECT_ROOT / "subtitles_temp.ass")
    create_ass_subtitles(vo_timeline, tmp_ass, transcribed_segments=transcribed_segments, meme_events=meme_events, hook_duration=hook_duration, intro_duration=intro_dur)

    # 7. Build FFmpeg Filter Complex
    bgm_track = custom_bgm if (custom_bgm and os.path.exists(custom_bgm)) else None
    if not bgm_track and MUSICA_DIR.exists():
        bgms = list(MUSICA_DIR.glob("*.mp3")) + list(MUSICA_DIR.glob("*.wav"))
        if bgms:
            bgm_track = str(bgms[0])

    sfx_whoosh = PROJECT_ROOT / "assets" / "sfx" / "whoosh.wav"
    if not sfx_whoosh.exists():
        sfx_whoosh = PROJECT_ROOT / "assets" / "Recurso video Freefire" / "efectos de sonidos" / "whoosh.wav"

    print(f"\n⚡ Compiling Master 16:9 Video with FFmpeg...")
    print(f"👉 Target Output: {final_output_path}")

    cmd = ["ffmpeg", "-y"]

    # Input 0: Voiceover Audio
    cmd.extend(["-i", audio_path])

    # Input 1: BGM Audio
    if bgm_track and os.path.exists(bgm_track):
        cmd.extend(["-stream_loop", "-1", "-i", bgm_track])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

    # Input 2: SFX Whoosh
    if sfx_whoosh.exists():
        cmd.extend(["-i", str(sfx_whoosh)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

    # Input 3: Green Screen Like & Subscribe Badge
    cta_badge_path = MEMES_GREEN_DIR / "PACK MEMES PANTALLA VERDE 1 (manuDT)" / "ANIMACIÓN DE LIKE Y SUSCRIBETE 1.mp4"
    if not cta_badge_path.exists():
        cta_badge_path = MEMES_GREEN_DIR / "ANIMACIÓN DE LIKE Y SUSCRIBETE 1.mp4"

    if cta_badge_path.exists():
        cmd.extend(["-ss", "0", "-t", "4", "-i", str(cta_badge_path)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "color=c=black@0.0:s=1920x1080:d=1"])

    input_idx = 4

    # Input 4 (Optional): Channel Intro Video & Audio
    intro_input_idx = None
    if has_intro and intro_file_path.exists():
        cmd.extend(["-ss", "0", "-t", f"{intro_dur:.2f}", "-i", str(intro_file_path)])
        intro_input_idx = input_idx
        input_idx += 1

    # Inputs 4+ (or 5+): B-roll gameplay clips
    broll_input_indices = []
    for seg in broll_segments:
        st = seg["start"]
        dur = seg["dur"]
        p = seg["path"]
        cmd.extend(["-ss", f"{st:.2f}", "-t", f"{dur:.2f}", "-i", p])
        broll_input_indices.append(input_idx)
        input_idx += 1

    # Inputs: Visual Events (Diamonds, Sensitivity images, Book banner)
    visual_input_info = []
    for v_ev in visual_events:
        v_dur = v_ev["duration"]
        v_path = v_ev["asset_path"]
        is_video = any(v_path.lower().endswith(ext) for ext in [".mp4", ".mov", ".avi"])

        if is_video:
            cmd.extend(["-ss", "0", "-t", f"{v_dur:.2f}", "-i", v_path])
        else:
            cmd.extend(["-loop", "1", "-t", f"{v_dur:.2f}", "-i", v_path])

        v_in_idx = input_idx
        input_idx += 1

        # SFX for visual event
        sfx_in_idx = None
        sfx_path = v_ev.get("sfx_path")
        if sfx_path and os.path.exists(sfx_path):
            cmd.extend(["-i", sfx_path])
            sfx_in_idx = input_idx
            input_idx += 1

        visual_input_info.append({
            "event": v_ev,
            "v_idx": v_in_idx,
            "sfx_idx": sfx_in_idx,
            "is_video": is_video
        })

    # Inputs: Contextual Memes
    meme_input_info = []
    for m_ev in meme_events:
        m_path = m_ev["meme_path"]
        m_dur = m_ev["duration"]
        cmd.extend(["-ss", "0", "-t", f"{m_dur:.2f}", "-i", m_path])
        m_in_idx = input_idx
        input_idx += 1

        has_aud = file_has_audio(m_path)
        meme_input_info.append({
            "event": m_ev,
            "idx": m_in_idx,
            "has_audio": has_aud
        })

    # ── FILTER COMPLEX CONSTRUCTION ─────────────────────────────────────────
    filter_parts = []
    v_concat_labels = []

    # 1. Process Video B-rolls with Rhythmic Speed Ramping, Orientation & Pacing
    for b_i, seg in enumerate(broll_segments):
        in_i = broll_input_indices[b_i]
        lbl = f"v_broll_{b_i}"
        rot_filter = get_video_orientation_filter(seg["path"])
        spd = seg.get("speed", 1.0)
        pts_filter = f"setpts=(PTS-STARTPTS)/{spd:.2f}" if spd != 1.0 else "setpts=PTS-STARTPTS"

        if is_upright_portrait_video(seg["path"]):
            # User requirement: Keep vertical, show whole video, blurred background behind
            filter_parts.append(
                f"[{in_i}:v]{pts_filter},split=2[bg_raw_{b_i}][fg_raw_{b_i}];"
                f"[bg_raw_{b_i}]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=25:5,eq=brightness=-0.15[bg_{b_i}];"
                f"[fg_raw_{b_i}]scale=-1:1080:force_original_aspect_ratio=decrease,setsar=1[fg_{b_i}];"
                f"[bg_{b_i}][fg_{b_i}]overlay=x=(W-w)/2:y=0,fps=60[{lbl}];"
            )
        elif seg["is_headshot"]:
            filter_parts.append(
                f"[{in_i}:v]{pts_filter},{rot_filter}"
                f"scale=2208:1242:force_original_aspect_ratio=increase,crop=1920:1080,eq=contrast=1.18:saturation=1.35:brightness=0.02,setsar=1,fps=60[{lbl}];"
            )
        else:
            filter_parts.append(
                f"[{in_i}:v]{pts_filter},{rot_filter}"
                f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=contrast=1.18:saturation=1.35:brightness=0.02,setsar=1,fps=60[{lbl}];"
            )
        v_concat_labels.append(f"[{lbl}]")

    # If has_intro, insert intro video immediately after hook segments
    if has_intro and intro_input_idx is not None:
        filter_parts.append(
            f"[{intro_input_idx}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=60[v_intro];"
        )
        v_concat_labels.insert(len(hook_segments), "[v_intro]")

    concat_str = "".join(v_concat_labels)
    filter_parts.append(f"{concat_str}concat=n={len(v_concat_labels)}:v=1:a=0[v_base];")

    curr_v = "v_base"

    # 2. Overlay Contextual Visual Events (Shifted timestamps)
    for v_i, v_item in enumerate(visual_input_info):
        v_ev = v_item["event"]
        v_out_t = v_ev["out_time"]
        v_dur = v_ev["duration"]
        v_in_idx = v_item["v_idx"]
        v_path = v_ev["asset_path"]
        v_orient = get_media_orientation_filter(v_path)
        next_v = f"v_vis_{v_i}"

        # Detect media type, green screen, orientation & transparency for professional UI scaling
        is_green = v_ev.get("is_green_screen", False) or "pantalla verde" in str(v_path).lower()
        is_video = v_item.get("is_video", False)
        is_vert = False
        is_transparent = False

        if not is_video:
            try:
                with Image.open(str(v_path)) as im:
                    im_w, im_h = im.size
                    if im_h > im_w:
                        is_vert = True
                    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                        alpha = im.convert('RGBA').split()[-1]
                        if alpha.getextrema()[0] < 255:
                            is_transparent = True
            except Exception:
                pass

        # Professional Layout & Filter Formulation
        if is_green:
            # Full-screen or centered green-screen overlay (e.g. LLUVIA DE DINERO)
            scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,colorkey=0x00FF00:0.3:0.2"
            pos_expr = "x=(W-w)/2:y=(H-h)/2"
            pad_filter = ""
        elif is_video:
            # Picture-in-picture video card (e.g. emotes.MP4 upright portrait)
            scale_filter = "scale=380:676:force_original_aspect_ratio=decrease"
            pos_expr = "x=140:y=140"
            pad_filter = ",pad=iw+6:ih+6:3:3:color=white@0.35"
        elif is_transparent:
            # Transparent floating badge/weapon cutout without artificial border box
            if v_ev.get("type") == "weapon":
                scale_filter = "scale=500:300:force_original_aspect_ratio=decrease"
                pos_expr = "x=140:y=150"
            else:
                scale_filter = "scale=440:340:force_original_aspect_ratio=decrease"
                pos_expr = "x=140:y=150"
            pad_filter = ""
        else:
            # Compact framed card for tables/menus/posters
            if is_vert:
                scale_filter = "scale=460:380:force_original_aspect_ratio=decrease"
                pos_expr = "x=140:y=150"
            else:
                scale_filter = "scale=560:300:force_original_aspect_ratio=decrease"
                pos_expr = "x=(W-w)/2:y=140"
            pad_filter = ",pad=iw+6:ih+6:3:3:color=white@0.35"

        filter_parts.append(
            f"[{v_in_idx}:v]setpts=PTS-STARTPTS+{v_out_t:.2f}/TB,{v_orient}"
            f"{scale_filter}{pad_filter},setsar=1,fps=60[vis_scale_{v_i}];"
        )
        filter_parts.append(
            f"[{curr_v}][vis_scale_{v_i}]overlay=enable='between(t,{v_out_t:.2f},{v_out_t+v_dur:.2f})':{pos_expr}:eof_action=pass[{next_v}];"
        )
        curr_v = next_v

    # 3. Overlay Contextual Memes (Shifted timestamps, reaction cut)
    for m_i, m_item in enumerate(meme_input_info):
        m_ev = m_item["event"]
        m_out_t = m_ev["out_time"]
        m_dur = m_ev["duration"]
        m_in_idx = m_item["idx"]
        m_path = m_ev["meme_path"]
        m_orient = get_video_orientation_filter(m_path)
        next_v = f"v_meme_{m_i}"

        if m_ev["is_green_screen"]:
            filter_parts.append(
                f"[{m_in_idx}:v]setpts=PTS-STARTPTS+{m_out_t:.2f}/TB,{m_orient}"
                f"scale=1280:720:force_original_aspect_ratio=decrease,colorkey=0x00FF00:0.3:0.2,setsar=1,fps=60[m_proc_{m_i}];"
            )
            filter_parts.append(
                f"[{curr_v}][m_proc_{m_i}]overlay=enable='between(t,{m_out_t:.2f},{m_out_t+m_dur:.2f})':x=(W-w)/2:y=(H-h)/2:eof_action=pass[{next_v}];"
            )
        else:
            filter_parts.append(
                f"[{m_in_idx}:v]setpts=PTS-STARTPTS+{m_out_t:.2f}/TB,{m_orient}"
                f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=60[m_proc_{m_i}];"
            )
            filter_parts.append(
                f"[{curr_v}][m_proc_{m_i}]overlay=enable='between(t,{m_out_t:.2f},{m_out_t+m_dur:.2f})':x=0:y=0:eof_action=pass[{next_v}];"
            )
        curr_v = next_v

    # 4. Transparent Green-Screen Like & Subscribe Badge Overlay near video end (Compact bottom-right corner)
    cta_start = cta_events[0] if cta_events else max(5.0, total_vo_dur - 4.5)
    cta_out_start = map_vo_time_to_output(cta_start)

    filter_parts.append(
        f"[3:v]setpts=PTS-STARTPTS+{cta_out_start:.2f}/TB,"
        f"scale=340:190:force_original_aspect_ratio=decrease,colorkey=0x00FF00:0.3:0.2,setsar=1,fps=60[cta_proc];"
    )
    filter_parts.append(
        f"[{curr_v}][cta_proc]overlay=enable='between(t,{cta_out_start:.2f},{cta_out_start+3.5:.2f})':x=W-w-80:y=H-h-80:eof_action=pass[v_overlays];"
    )

    # 5. Burn-in Subtitles (.ass)
    rel_sub = "subtitles_temp.ass"
    if os.path.exists(rel_sub):
        filter_parts.append(f"[v_overlays]subtitles='{rel_sub}'[v_final];")
    else:
        filter_parts.append(f"[v_overlays]null[v_final];")

    # 6. AUDIO SPLICING & MIXING: HARD CUT VOICEOVER DURING MEMES AND INTRO
    vo_chunks = []

    if has_intro and intro_input_idx is not None:
        # 1. Voiceover during hook
        filter_parts.append(
            f"[0:a]atrim=start=0:end={hook_duration:.3f},asetpts=PTS-STARTPTS,"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[vo_hook];"
        )
        vo_chunks.append("[vo_hook]")

        # 2. Intro audio (full 10 seconds, volume 1.0)
        filter_parts.append(
            f"[{intro_input_idx}:a]atrim=start=0:end={intro_dur:.3f},asetpts=PTS-STARTPTS,"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=1.0[intro_aud];"
        )
        vo_chunks.append("[intro_aud]")

        last_cut = hook_duration
    else:
        last_cut = 0.0

    if not meme_input_info:
        filter_parts.append(
            f"[0:a]atrim=start={last_cut:.3f}:end={total_vo_dur:.3f},asetpts=PTS-STARTPTS,"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[vo_chunk_post];"
        )
        vo_chunks.append("[vo_chunk_post]")
    else:
        for i, m_item in enumerate(meme_input_info):
            cut_time = m_item["event"]["time"]
            m_dur = m_item["event"]["duration"]
            m_idx = m_item["idx"]
            has_aud = m_item["has_audio"]

            # Voiceover segment before meme
            filter_parts.append(
                f"[0:a]atrim=start={last_cut:.3f}:end={cut_time:.3f},asetpts=PTS-STARTPTS,"
                f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[vo_chunk_{i}];"
            )
            vo_chunks.append(f"[vo_chunk_{i}]")

            # Meme audio segment
            if has_aud:
                filter_parts.append(
                    f"[{m_idx}:a]atrim=start=0:end={m_dur:.3f},asetpts=PTS-STARTPTS,"
                    f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.95[m_aud_chunk_{i}];"
                )
            else:
                filter_parts.append(
                    f"aevalsrc=0:d={m_dur:.3f}:s=44100:c=stereo,"
                    f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[m_aud_chunk_{i}];"
                )
            vo_chunks.append(f"[m_aud_chunk_{i}]")

            last_cut = cut_time

        # Final voiceover segment after last meme
        filter_parts.append(
            f"[0:a]atrim=start={last_cut:.3f}:end={total_vo_dur:.3f},asetpts=PTS-STARTPTS,"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[vo_chunk_end];"
        )
        vo_chunks.append("[vo_chunk_end]")

    concat_audio_str = "".join(vo_chunks)
    filter_parts.append(
        f"{concat_audio_str}concat=n={len(vo_chunks)}:v=0:a=1[vo_spliced];"
    )

    # Background Music (covers total_output_dur at low level; ducked during intro)
    if has_intro:
        bgm_vol_expr = f"volume='if(between(t,{hook_duration:.2f},{hook_duration+intro_dur:.2f}),0.01,0.08)':eval=frame"
    else:
        bgm_vol_expr = "volume=0.08"

    filter_parts.append(
        f"[1:a]atrim=start=0:duration={total_output_dur:.2f},asetpts=PTS-STARTPTS,{bgm_vol_expr}[bgm_quiet];"
    )
    filter_parts.append(f"[2:a]volume=0.4[whoosh];")

    mix_inputs = ["[vo_spliced]", "[bgm_quiet]", "[whoosh]"]

    # Visual Event SFX tracks
    for v_i, v_item in enumerate(visual_input_info):
        sfx_idx = v_item["sfx_idx"]
        if sfx_idx is not None:
            v_out_t = v_item["event"]["out_time"]
            delay_ms = int(v_out_t * 1000)
            lbl = f"sfx_vis_{v_i}"
            filter_parts.append(
                f"[{sfx_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.6[{lbl}];"
            )
            mix_inputs.append(f"[{lbl}]")

    mix_str = "".join(mix_inputs)
    filter_parts.append(
        f"{mix_str}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2[a_final]"
    )

    filter_complex = "\n".join(filter_parts)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[v_final]",
        "-map", "[a_final]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "12M",
        "-maxrate", "15M",
        "-bufsize", "20M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "60",
        "-t", f"{total_output_dur:.2f}",
        "-movflags", "+faststart",
        str(final_output_path)
    ])

    print("🚀 Launching FFmpeg render command...")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if res.returncode != 0:
        print(f"❌ Primary Render Error in FFmpeg:\n{res.stderr[-1000:]}")
        # Retry without subtitles if subtitle filter threw an error
        cmd_nosubs = cmd.copy()
        fc_nosubs = filter_complex.replace(f"[v_overlays]subtitles='{rel_sub}'[v_final];", "[v_overlays]copy[v_final];")
        for i, arg in enumerate(cmd_nosubs):
            if arg == filter_complex:
                cmd_nosubs[i] = fc_nosubs
                break
        res_ns = subprocess.run(cmd_nosubs, capture_output=True, text=True, encoding="utf-8")
        if res_ns.returncode != 0:
            print(f"❌ Secondary Render Error:\n{res_ns.stderr[-1000:]}")

    if os.path.exists(final_output_path):
        size_mb = os.path.getsize(final_output_path) / (1024 * 1024)
        print("\n" + "═"*75)
        print("🎉 MASTER LONG 16:9 YOUTUBE VIDEO RENDERED SUCCESSFULLY!")
        print(f"👉 Output Location: {final_output_path} ({size_mb:.1f} MB)")
        print(f"📐 Resolution: 1920x1080 (16:9 Horizontal) @ 60 FPS")
        print(f"🎙️ Audio Sync: Voiceover Paused During Memes ({total_output_dur:.2f}s) | Clean Sequential Audio")
        print(f"🔄 Orientation: Straightened all sideways/inverted clips")
        print("═"*75)
        return str(final_output_path)
    else:
        print(f"❌ Error: Render failed, output file not found at {final_output_path}")
        return None

# ── CLI ENTRY POINT ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Master 16:9 YouTube Long Video Generator for Free Fire")
    parser.add_argument("--audio", type=str, default=None, help="Path to voiceover audio file (.mp3/.wav)")
    parser.add_argument("--gameplay", type=str, default=None, help="Custom folder containing 16:9 gameplay clips")
    parser.add_argument("--music", type=str, default=None, help="Custom BGM music track (.mp3/.wav)")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory")
    parser.add_argument("--outname", type=str, default="long_video_16x9.mp4", help="Output file name")
    args = parser.parse_args()

    audio_path = args.audio
    if not audio_path:
        default_audios = list(GENERATE_VIDEO_DIR.glob("*.mp3")) + list(GENERATE_VIDEO_DIR.glob("*.wav"))
        if default_audios:
            audio_path = str(default_audios[0])
        else:
            print("❌ Error: No voiceover audio provided and none found in Generar Video/")
            sys.exit(1)

    print(f"🎙️ Selected Voiceover Audio: {audio_path}")
    assemble_long_169_video(
        audio_path=audio_path,
        custom_gameplay_dir=args.gameplay,
        custom_bgm=args.music,
        out_dir=args.outdir,
        out_name=args.outname
    )

if __name__ == "__main__":
    main()
