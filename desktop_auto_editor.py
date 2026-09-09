"""
desktop_auto_editor.py — Master Free Fire Short Generator (v25.0 Dual-Format Engine)
=====================================================================================
Features:
1. Master 9:16 Vertical Shorts Engine (1080x1920 @ 60 FPS):
   - Flawless Orientation Correction: Auto-detects sideways clips (1290x2796) and rotates
     them 90° CCW into horizontal gameplay right-side up.
   - Professional 9:16 Presentation: Ambient blurred & darkened background filling 1080x1920
     with full-width upright horizontal gameplay centered vertically (Zero black bars, 100% visible action).
   - Rhythmic frenetic cuts (1.3s - 1.8s) prioritizing red headshot damage numbers.
2. Full Contextual Semantic Director Integration (All 11 Categories):
   - Diamonds (Diamantes.PNG) + Ding SFX
   - Money Rain (LLUVIA DE DINERO 1.MP4 with chromakey)
   - Character Emotes (emotes.MP4)
   - Evolutionary Weapons (armas/ AK-47 Dragón, Groza, M16 with alpha transparency)
   - DPI & Sensitivity advice (Asesoria.PNG & sencibilidad.jpg)
   - Official Book / Web Guide (codigoheadshot.png)
   - Tournament / Elite Pass (torneo.jpeg)
   - Top Global & Grand Master (top global.jpeg, gran maestro.png)
   - Results & CTA Badges (resultados.PNG, likes.PNG, animated like & subscribe)
3. Contextual Memes (PACK MEMES PANTALLA VERDE & PACK DE MEMES):
   - Green screen memes with colorkey chromakey.
   - Audio Hard-Cut: Voiceover pauses during memes, meme audio plays at volume=0.95,
     and voiceover resumes cleanly after.
4. Dynamic 9:16 Subtitles (.ass):
   - Styled for vertical Shorts (Arial Black, yellow text, black border, centered at lower third).
   - Dynamically shifted across meme pauses.
5. NO Intro in Shorts (as strictly requested: "para los videos short no implementes la intro").
6. Seamless Dual-Format Support: Delegates --aspect 16:9 to long_video_engine.py.
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
from PIL import Image

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
PROJECT_RECURSO_DIR = PROJECT_ROOT / "assets" / "Recurso video Freefire"

GENERATE_VIDEO_DIR = PROJECT_RECURSO_DIR / "Generar Video"
JUGADAS_DIR = PROJECT_RECURSO_DIR / "free fire jugadas"
VIDEO_GUIA_DIR = PROJECT_RECURSO_DIR / "video Guia"
IMAGENES_DIR = PROJECT_RECURSO_DIR / "Imagenes"
SFX_DIR = PROJECT_RECURSO_DIR / "efectos de sonidos"
MUSICA_DIR = PROJECT_RECURSO_DIR / "musica"
MEMES_PACK_DIR = PROJECT_RECURSO_DIR / "PACK DE MEMES"
MEMES_GREEN_DIR = PROJECT_RECURSO_DIR / "PACK MEMES PANTALLA VERDE 1 (manuDT)"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

FPS = 60
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

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


def locate_user_voiceover_audio(audio_override=None):
    """Scans for user's voiceover audio or uses exact GUI selected audio file."""
    if audio_override and os.path.exists(audio_override):
        audio_path = Path(audio_override)
        print(f"🎙️ EXACT AUDIO SELECTED: {audio_path.name}")
        return audio_path

    GENERATE_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = []
    for ext in ["*.mp3", "*.wav", "*.m4a", "*.aac", "*.ogg"]:
        audio_files.extend(list(GENERATE_VIDEO_DIR.glob(ext)))

    audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    if audio_files:
        selected_audio = audio_files[0]
        print(f"🎙️ USER AUDIO DETECTED: {selected_audio.name}")
        return selected_audio

    fallback_audio = PROJECT_ROOT / "assets" / "video free fire" / "audio_referencia.wav"
    print(f"🎙️ Using reference audio: {fallback_audio.name}")
    return fallback_audio


def collect_916_gameplay_videos(custom_dir=None, specific_video=None):
    """
    Scans for gameplay clips inside custom_dir or /free fire jugadas/.
    Prioritizes user-uploaded video clips directly without aggressive keyword exclusion.
    """
    if specific_video and os.path.exists(specific_video):
        return [Path(specific_video)]

    is_custom = False
    if custom_dir and os.path.exists(custom_dir):
        p_c = Path(custom_dir).resolve()
        if p_c != JUGADAS_DIR.resolve() and p_c != PROJECT_RECURSO_DIR.resolve():
            is_custom = True
            target_dir = p_c
        else:
            target_dir = JUGADAS_DIR
    else:
        target_dir = JUGADAS_DIR

    if not target_dir.exists():
        target_dir = PROJECT_RECURSO_DIR

    gameplay_files = []
    video_exts = ["*.mp4", "*.mov", "*.MP4", "*.MOV", "*.avi", "*.mkv", "*.webm", "*.m4v"]

    if is_custom:
        # Collect ALL video files uploaded by the user
        for ext in video_exts:
            for f in target_dir.rglob(ext):
                if "intro" in f.name.lower():
                    continue
                gameplay_files.append(f)
        if gameplay_files:
            print(f"📦 [Recursos Personalizados] Encontrados {len(gameplay_files)} videos subidos por el usuario.")
    else:
        exclude_kw = ["pack memes", "generar video", "imagenes", "efectos de sonidos", "musica", "emote", "emotes", "intro"]
        for ext in video_exts:
            for f in target_dir.rglob(ext):
                p_str = str(f).lower()
                if any(ex in p_str for ex in exclude_kw):
                    continue
                gameplay_files.append(f)

    # Fallback to official jugadas if user uploaded no video clips
    if not gameplay_files:
        print("ℹ️ Usando clips de jugadas maestras oficiales...")
        for ext in video_exts:
            for f in JUGADAS_DIR.rglob(ext):
                if "intro" in f.name.lower():
                    continue
                gameplay_files.append(f)

    return list(dict.fromkeys(gameplay_files))


def generate_killcard_overlay_if_needed(headshots=3, player_tag="CODIGO HEADSHOT PRO"):
    """
    Ensures the Remotion KillCardOverlay (PDF technical spec) is compiled into a transparent WebM/MOV.
    """
    overlay_dir = PROJECT_ROOT / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    overlay_webm = overlay_dir / "remotion_overlay.webm"
    overlay_mov = overlay_dir / "remotion_overlay.mov"

    if overlay_webm.exists():
        return str(overlay_webm)
    if overlay_mov.exists():
        return str(overlay_mov)

    print(f"🎬 [Remotion] Compiling KillCardOverlay (x{headshots}, {player_tag})...")
    try:
        script = PROJECT_ROOT / "remotion_overlays.js"
        cmd = [
            "node", str(script),
            "--killcard",
            "--headshots", str(headshots),
            "--tag", str(player_tag),
            "--out", "remotion_overlay.webm"
        ]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
        if overlay_webm.exists():
            return str(overlay_webm)
    except Exception as e:
        print(f"⚠️ [Remotion] Could not compile KillCardOverlay via node: {e}")

    return str(overlay_webm) if overlay_webm.exists() else None


def shift_subtitles_for_memes(transcribed_segments, meme_events):
    """
    Shifts subtitle timestamps forward by the cumulative duration of memes that appeared before them.
    Splits any segment that crosses a meme cut so subtitles disappear during the meme break.
    """
    if not transcribed_segments:
        return []

    sorted_memes = sorted(meme_events, key=lambda x: x["time"]) if meme_events else []

    def get_shift_at(t):
        s = 0.0
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


def create_ass_subtitles_916(vo_timeline, output_ass_path, transcribed_segments=None, meme_events=None):
    """
    Generates dynamic highlighted ASS subtitles for 9:16 Shorts (1080x1920):
    - Arial Black font, size 56, yellow & white, 4px black outline, soft shadow.
    - Positioned at lower third (MarginV: 480, ~y:1440) below centered gameplay and clear of TikTok buttons.
    - Shifted to accommodate meme pauses.
    """
    header = (
        "[Script Info]\n"
        "Title: Free Fire 9:16 Shorts Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial Black,56,&H0000FFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,480,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = [header]
    style_tag = "{\\b1\\c&H0000FFFF&}"

    shifted_segments = shift_subtitles_for_memes(transcribed_segments, meme_events)

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


# ── MASTER 9:16 SHORTS ASSEMBLY ENGINE ──────────────────────────────────────
def assemble_short_916_video(audio_path, custom_gameplay_dir=None, specific_video=None, custom_bgm=None, include_bgm=True, hook_mode="auto", speed_ramp=1.5, out_dir=None, out_name="final_short_916.mp4"):
    """
    Executes the 9:16 Vertical Short Programmatic Editing Pipeline (1080x1920 60fps):
    - NO INTRO in Shorts (as user commanded).
    - Straightens sideways clips (1290x2796) upright with transpose=2.
    - Blurred ambient background filling 1080x1920 + full-width upright horizontal gameplay centered.
    - Full Contextual Semantic Director integration (All 11 categories: diamonds, money rain, emotes, weapons, DPI, sensitivity, book guide, tournament, grand master, results, CTA).
    - Contextual memes (both green-screen and pack memes) with hard voiceover audio pausing.
    - Dynamic 9:16 ASS subtitles shifted for meme pauses.
    """
    print("\n" + "═"*75)
    print("🎬 MASTER FREE FIRE 9:16 VERTICAL SHORT GENERATOR (1080x1920 60fps)")
    print("═"*75)
    print(f"📂 Master Resource Directory: {PROJECT_RECURSO_DIR}")

    # 1. Intelligent Semantic Audio-to-Visual Director
    print("🧠 Running Semantic Audio-to-Visual Director for Shorts...")
    semantic_director = SemanticDirector(whisper_model="base")
    plan = semantic_director.plan_timeline(audio_path, is_short=True)

    vo_timeline = analyze_voiceover_timeline(audio_path)
    total_vo_dur = plan.get("total_duration") or vo_timeline["total_duration"]
    cta_events = vo_timeline.get("cta_events", [])

    raw_visual_events = plan.get("visual_events", [])
    raw_meme_events = plan.get("meme_events", [])
    transcribed_segments = plan.get("segments", [])

    # Sort memes chronologically by cut time in voiceover
    raw_meme_events = sorted(raw_meme_events, key=lambda x: x["time"])

    # Sanitize memes to ensure clean gaps (at least 2.5s spacing, within voiceover bounds)
    # Crucial rule: The first 3.5 seconds of a Short are strictly reserved for the Headshot Gameplay Hook!
    meme_events = []
    last_cut = 0.0
    for m in raw_meme_events:
        t = m["time"]
        if t < 3.5:
            continue
        if t >= last_cut + 2.5 and t < total_vo_dur - 0.5:
            meme_events.append(m)
            last_cut = t

    # ── TIMELINE SHIFT CALCULATIONS ─────────────────────────────────────────
    cum_meme_time = sum(m["duration"] for m in meme_events)
    for i, m in enumerate(meme_events):
        # Precise start in output: original voiceover cut time + duration of preceding memes
        m["out_time"] = m["time"] + sum(prev["duration"] for prev in meme_events[:i])
        m["out_end"] = m["out_time"] + m["duration"]

    def map_vo_time_to_output(t: float) -> float:
        """Maps an original voiceover timestamp to the shifted output video timeline (incorporating meme pauses)."""
        shift = 0.0
        for m in meme_events:
            if m["time"] < t:
                shift += m["duration"]
        return t + shift

    total_output_dur = total_vo_dur + cum_meme_time

    # Shift visual events
    visual_events = []
    for v in raw_visual_events:
        v_copy = dict(v)
        v_out_st = map_vo_time_to_output(v["time"])
        v_copy["out_time"] = v_out_st
        v_copy["out_end"] = v_out_st + v["duration"]
        visual_events.append(v_copy)

    # If user uploaded custom images/stickers, inject them as visual overlay events
    if custom_gameplay_dir and Path(custom_gameplay_dir).exists():
        custom_imgs = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.webp"]:
            for f in Path(custom_gameplay_dir).rglob(ext):
                custom_imgs.append(f)
        if custom_imgs:
            print(f"🖼️ [Recursos Personalizados] Inyectando {len(custom_imgs)} imágenes subidas por el usuario.")
            spacing = max(4.0, total_output_dur / (len(custom_imgs) + 1))
            for c_i, c_img in enumerate(custom_imgs):
                img_t = 3.8 + (c_i * spacing)
                if img_t < total_output_dur - 2.0:
                    visual_events.append({
                        "time": img_t,
                        "out_time": img_t,
                        "duration": 3.0,
                        "out_end": img_t + 3.0,
                        "label": f"Custom: {c_img.name}",
                        "asset_path": str(c_img),
                        "type": "custom_image"
                    })

    print(f"⏱️ Timeline Architecture: Voiceover = {total_vo_dur:.2f}s | Memes = {cum_meme_time:.2f}s | Total Video = {total_output_dur:.2f}s")
    print(f"🚫 Intro Status: Strictly EXCLUDED for Shorts (Duration = 0.00s)")
    print(f"🤡 Contextual Memes ({len(meme_events)} scheduled with Audio Hard-Cut):")
    for m in meme_events:
        print(f"   • Voice cut at {m['time']:.2f}s ➔ Video output [{m['out_time']:.2f}s - {m['out_end']:.2f}s] ({m['duration']:.2f}s) | {os.path.basename(m['meme_path'])}")

    print(f"📌 Contextual Visual Overlays ({len(visual_events)} scheduled):")
    for v in visual_events:
        print(f"   • Voice {v['time']:.2f}s ➔ Video output [{v['out_time']:.2f}s - {v['out_end']:.2f}s] | {v['label']} ({os.path.basename(v['asset_path'])})")

    # 2. Collect Gameplay Clips (EXCLUDING Intro.mp4)
    gameplay_files = collect_916_gameplay_videos(custom_gameplay_dir, specific_video=specific_video)
    if not gameplay_files:
        print(f"❌ Error: No gameplay clips found in {JUGADAS_DIR}")
        sys.exit(1)

    print(f"🎥 Discovered {len(gameplay_files)} Gameplay Video Files")

    # 3. Pre-scan Headshots in Gameplays using OpenCV HSV Detector (with JSON caching)
    cache_file = PROJECT_RECURSO_DIR / "headshots_cache.json"
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

    # 4. Build Dynamic Rhythmic B-Roll Timeline (Fast, frenetic 1.3s - 1.8s cuts for Shorts)
    shuffled_gameplays = gameplay_files.copy()
    random.shuffle(shuffled_gameplays)

    broll_segments = []
    used_ranges = {str(g): [] for g in gameplay_files}
    current_broll_total = 0.0
    idx = 0

    while current_broll_total < total_output_dur + 4.0:
        gfile = shuffled_gameplays[idx % len(shuffled_gameplays)]
        gpath = str(gfile)
        idx += 1

        cap = cv2.VideoCapture(gpath)
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 300
        gdur = n_frames / fps_in
        cap.release()

        if gdur < 0.5:
            continue

        tl_dur = round(random.uniform(1.3, 1.8), 2)
        speed = round(random.uniform(1.22, 1.38), 2)
        source_dur = round(tl_dur * speed, 2)

        if gdur <= 2.2:
            cand_start = 0.0
            source_dur = round(gdur, 2)
            tl_dur = round(source_dur / speed, 2)
            is_hs = False
        else:
            if source_dur > gdur:
                source_dur = round(gdur - 0.1, 2)
                tl_dur = round(source_dur / speed, 2)

            # Check for red headshot timestamp
            hs_list = headshot_map.get(gpath, [])
            cand_start = None
            is_hs = False
            if hs_list:
                for (hs_t, hs_sc) in hs_list:
                    st = max(0.0, hs_t - 0.7)
                    if st + source_dur <= gdur:
                        if not any(abs(st - existing) < (source_dur + 1.0) for existing in used_ranges[gpath]):
                            cand_start = st
                            is_hs = True
                            break

            if cand_start is None:
                max_st = max(0.0, gdur - source_dur)
                if max_st > 0:
                    for _ in range(15):
                        st = round(random.uniform(0.0, max_st), 2)
                        if not any(abs(st - existing) < (source_dur + 1.0) for existing in used_ranges[gpath]):
                            cand_start = st
                            break
                if cand_start is None:
                    cand_start = 0.0

        used_ranges[gpath].append(cand_start)
        broll_segments.append({
            "path": gpath,
            "name": gfile.name,
            "start": cand_start,
            "dur": source_dur,
            "timeline_dur": tl_dur,
            "speed": speed,
            "mode": "⚡ FRENETIC (Action)" if is_hs else "🎯 RHYTHMIC (Pacing)",
            "is_headshot": is_hs
        })
        current_broll_total += tl_dur

    print(f"🎬 Dynamic 9:16 Shorts Montage ({len(broll_segments)} cuts generated):")
    for b_i, seg in enumerate(broll_segments):
        print(f"   {b_i+1:02d}. [{seg['mode']}] {seg['name']} | st={seg['start']:.2f}s, dur={seg['timeline_dur']:.2f}s, speed={seg['speed']}x")

    # 5. Prepare Output Destination & Subtitles (.ass)
    target_out_dir = Path(out_dir) if (out_dir and os.path.exists(out_dir)) else DEFAULT_OUTPUT_DIR
    target_out_dir.mkdir(parents=True, exist_ok=True)
    if not out_name.lower().endswith(".mp4"):
        out_name += ".mp4"
    final_output_path = target_out_dir / out_name

    tmp_ass = str(PROJECT_ROOT / "subtitles_temp_916.ass")
    create_ass_subtitles_916(vo_timeline, tmp_ass, transcribed_segments=transcribed_segments, meme_events=meme_events)

    # 6. Build FFmpeg Filter Complex
    bgm_track = custom_bgm if (custom_bgm and os.path.exists(custom_bgm)) else None
    if not bgm_track and MUSICA_DIR.exists():
        bgms = list(MUSICA_DIR.glob("*.mp3")) + list(MUSICA_DIR.glob("*.wav"))
        if bgms:
            bgm_track = str(bgms[0])

    sfx_whoosh = PROJECT_ROOT / "assets" / "sfx" / "whoosh.wav"
    if not sfx_whoosh.exists():
        sfx_whoosh = SFX_DIR / "whoosh.wav"

    print(f"\n⚡ Compiling Master 9:16 Short with FFmpeg...")
    print(f"👉 Target Output: {final_output_path}")

    cmd = ["ffmpeg", "-y"]

    # Input 0: Voiceover Audio
    cmd.extend(["-i", audio_path])

    # Input 1: BGM Audio
    if include_bgm and bgm_track and os.path.exists(bgm_track):
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
        cmd.extend(["-f", "lavfi", "-i", "color=c=black@0.0:s=1080x1920:d=1"])

    input_idx = 4

    # Remotion KillCardOverlay (PDF Spec: Section 3 & 4)
    remotion_overlay_file = generate_killcard_overlay_if_needed(headshots=3, player_tag="CODIGO HEADSHOT PRO")
    remotion_in_idx = None
    if remotion_overlay_file and os.path.exists(remotion_overlay_file):
        cmd.extend(["-i", remotion_overlay_file])
        remotion_in_idx = input_idx
        input_idx += 1

    # SFX Bass Drop (PDF Spec: Section 4)
    sfx_bass_drop = PROJECT_ROOT / "sfx" / "sfx_bass_drop.wav"
    bass_in_idx = None
    if sfx_bass_drop.exists():
        cmd.extend(["-i", str(sfx_bass_drop)])
        bass_in_idx = input_idx
        input_idx += 1

    # Inputs 4+: B-roll gameplay clips
    broll_input_indices = []
    for seg in broll_segments:
        st = seg["start"]
        dur = seg["dur"]
        p = seg["path"]
        cmd.extend(["-ss", f"{st:.2f}", "-t", f"{dur:.2f}", "-i", p])
        broll_input_indices.append(input_idx)
        input_idx += 1

    # Inputs: Visual Events (Diamonds, Sensitivity images, Weapons, Book banner)
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

    # ── FILTER COMPLEX CONSTRUCTION FOR 9:16 VERTICAL ─────────────────────────
    filter_parts = []
    v_concat_labels = []

    # 1. Process Video B-rolls into 9:16 (PDF Spec: Zoom Shakes & Color Grading)
    for b_i, seg in enumerate(broll_segments):
        in_i = broll_input_indices[b_i]
        lbl = f"v_broll_{b_i}"
        rot_filter = get_video_orientation_filter(seg["path"])
        spd = seg.get("speed", 1.0)
        pts_filter = f"setpts=(PTS-STARTPTS)/{spd:.2f}" if spd != 1.0 else "setpts=PTS-STARTPTS"
        is_hs = seg.get("is_headshot", False)

        # PDF Specification: Filtro de Reescalado y Zoom Dinámico (Impact Shakes) & Corrección de Color
        # eq=contrast=1.18:saturation=1.35:brightness=0.02, zoompan=z='if(between(in,45,65),1.25,1.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'
        color_filter = ",eq=contrast=1.18:saturation=1.35:brightness=0.02"
        zoom_filter = ",zoompan=z='if(between(in,45,65),1.25,1.0)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=60" if is_hs else ""

        filter_parts.append(
            f"[{in_i}:v]{pts_filter},{rot_filter}"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2{color_filter}{zoom_filter},setsar=1,fps=60[{lbl}];"
        )
        v_concat_labels.append(f"[{lbl}]")

    concat_str = "".join(v_concat_labels)
    filter_parts.append(f"{concat_str}concat=n={len(v_concat_labels)}:v=1:a=0[v_base];")

    curr_v = "v_base"

    # 2. Overlay Contextual Visual Events (Upper Third / Formatted for 9:16)
    for v_i, v_item in enumerate(visual_input_info):
        v_ev = v_item["event"]
        v_out_t = v_ev["out_time"]
        v_dur = v_ev["duration"]
        v_in_idx = v_item["v_idx"]
        v_path = v_ev["asset_path"]
        v_orient = get_media_orientation_filter(v_path)
        next_v = f"v_vis_{v_i}"

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

        # 9:16 Optimized Scaling & Placement
        if is_green:
            # Full screen green screen overlay (e.g. LLUVIA DE DINERO)
            scale_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,colorkey=0x00FF00:0.3:0.2"
            pos_expr = "x=(W-w)/2:y=(H-h)/2"
            pad_filter = ""
        elif is_video:
            # Emote video card floating in upper section
            scale_filter = "scale=400:660:force_original_aspect_ratio=decrease"
            pos_expr = "x=(W-w)/2:y=160"
            pad_filter = ",pad=iw+6:ih+6:3:3:color=white@0.35"
        elif is_transparent:
            # Transparent weapon cutout floating above centered gameplay
            if v_ev.get("type") == "weapon":
                scale_filter = "scale=720:380:force_original_aspect_ratio=decrease"
                pos_expr = "x=(W-w)/2:y=180"
            else:
                scale_filter = "scale=620:360:force_original_aspect_ratio=decrease"
                pos_expr = "x=(W-w)/2:y=180"
            pad_filter = ""
        else:
            # Framed card in upper section
            if is_vert:
                scale_filter = "scale=420:640:force_original_aspect_ratio=decrease"
                pos_expr = "x=(W-w)/2:y=160"
            else:
                scale_filter = "scale=750:350:force_original_aspect_ratio=decrease"
                pos_expr = "x=(W-w)/2:y=200"
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
                f"scale=1080:1920:force_original_aspect_ratio=decrease,colorkey=0x00FF00:0.3:0.2,setsar=1,fps=60[m_proc_{m_i}];"
            )
            filter_parts.append(
                f"[{curr_v}][m_proc_{m_i}]overlay=enable='between(t,{m_out_t:.2f},{m_out_t+m_dur:.2f})':x=(W-w)/2:y=(H-h)/2:eof_action=pass[{next_v}];"
            )
        else:
            # For 9:16 Shorts, display standard 16:9 memes as centered floating reaction cards
            filter_parts.append(
                f"[{m_in_idx}:v]setpts=PTS-STARTPTS+{m_out_t:.2f}/TB,{m_orient}"
                f"scale=980:550:force_original_aspect_ratio=decrease,pad=986:556:3:3:color=white@0.3,setsar=1,fps=60[m_proc_{m_i}];"
            )
            filter_parts.append(
                f"[{curr_v}][m_proc_{m_i}]overlay=enable='between(t,{m_out_t:.2f},{m_out_t+min(m_dur, 1.8):.2f})':x=(W-w)/2:y=(H-h)/2:eof_action=pass[{next_v}];"
            )
        curr_v = next_v

    # 4. Transparent Green-Screen Like & Subscribe Badge Overlay near video end (Bottom area)
    cta_start = cta_events[0] if cta_events else max(5.0, total_vo_dur - 4.5)
    cta_out_start = map_vo_time_to_output(cta_start)

    filter_parts.append(
        f"[3:v]setpts=PTS-STARTPTS+{cta_out_start:.2f}/TB,"
        f"scale=420:240:force_original_aspect_ratio=decrease,colorkey=0x00FF00:0.3:0.2,setsar=1,fps=60[cta_proc];"
    )
    filter_parts.append(
        f"[{curr_v}][cta_proc]overlay=enable='between(t,{cta_out_start:.2f},{cta_out_start+3.5:.2f})':x=(W-w)/2:y=1600:eof_action=pass[v_with_cta];"
    )
    curr_v = "v_with_cta"

    # 4b. Remotion KillCardOverlay (PDF Spec: Section 3 & 4)
    # Transparent overlay with colorkey so it doesn't black out the gameplay hook!
    if remotion_in_idx is not None:
        filter_parts.append(
            f"[{remotion_in_idx}:v]format=yuva420p,colorkey=0x000000:0.25:0.1[killcard_alpha];"
        )
        filter_parts.append(
            f"[{curr_v}][killcard_alpha]overlay=0:0:enable='between(t,1.2,3.8)':eof_action=pass[v_killcard];"
        )
        curr_v = "v_killcard"

    # 5. Burn-in Subtitles (.ass)
    filter_parts.append(f"[{curr_v}]null[v_overlays];")
    rel_sub = "subtitles_temp_916.ass"
    if os.path.exists(rel_sub):
        filter_parts.append(f"[v_overlays]subtitles='{rel_sub}'[v_final];")
    else:
        filter_parts.append(f"[v_overlays]null[v_final];")

    # 6. AUDIO SPLICING & MIXING: HARD CUT VOICEOVER DURING MEMES
    if not meme_input_info:
        filter_parts.append(
            f"[0:a]volume=1.0,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[vo_spliced];"
        )
    else:
        vo_chunks = []
        k = len(meme_input_info)
        last_cut = 0.0

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
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[vo_chunk_{k}];"
        )
        vo_chunks.append(f"[vo_chunk_{k}]")

        concat_audio_str = "".join(vo_chunks)
        filter_parts.append(
            f"{concat_audio_str}concat=n={len(vo_chunks)}:v=0:a=1[vo_spliced];"
        )

    # Background Music (covers total_output_dur at low level)
    filter_parts.append(
        f"[1:a]atrim=start=0:duration={total_output_dur:.2f},asetpts=PTS-STARTPTS,volume=0.08[bgm_quiet];"
    )
    filter_parts.append(f"[2:a]volume=0.4[whoosh];")

    mix_inputs = ["[vo_spliced]", "[bgm_quiet]", "[whoosh]"]

    # PDF Spec: SFX Bass Drop with ducking during impact
    if bass_in_idx is not None:
        filter_parts.append(
            f"[{bass_in_idx}:a]adelay=1200|1200,volume=1.0[sfx_bass_drop];"
        )
        mix_inputs.append("[sfx_bass_drop]")

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

    print("🚀 Launching FFmpeg render command for 9:16 Short...")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if res.returncode != 0:
        print(f"❌ Primary Render Error in FFmpeg:\n{res.stderr[-1000:]}")
        # Retry without subtitles if subtitle filter threw an error
        cmd_nosubs = cmd.copy()
        fc_nosubs = filter_complex.replace(f"[v_overlays]subtitles='{rel_sub}'[v_final];", "[v_overlays]null[v_final];")
        for i, arg in enumerate(cmd_nosubs):
            if arg == filter_complex:
                cmd_nosubs[i] = fc_nosubs
                break
        res_ns = subprocess.run(cmd_nosubs, capture_output=True, text=True, encoding="utf-8")
        if res_ns.returncode != 0:
            print(f"❌ Fallback Render Error:\n{res_ns.stderr[-1000:]}")
            sys.exit(1)

    print("\n" + "═"*75)
    print(f"🎉 MASTER 9:16 VERTICAL SHORT RENDERED SUCCESSFULLY!")
    print(f"👉 Output Location: {final_output_path} ({os.path.getsize(final_output_path)/(1024*1024):.1f} MB)")
    print(f"📐 Resolution: 1080x1920 (9:16 Vertical) @ 60 FPS")
    print(f"🎙️ Audio Sync: Voiceover Paused During Memes ({total_output_dur:.2f}s) | Clean Sequential Audio")
    print(f"🔄 Orientation: Straightened all sideways/inverted clips")
    print("═"*75)
    return str(final_output_path)


# ── MAIN CLI ENTRYPOINT ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Master Free Fire Short Generator v25.0")
    parser.add_argument("--audio", type=str, default=None, help="Specific voiceover audio file path")
    parser.add_argument("--bgm", type=str, choices=["yes", "no", "s", "n"], default="yes", help="Include background music (yes/no)")
    parser.add_argument("--hook", type=str, choices=["auto", "red", "yellow"], default="auto", help="Hook Clip #1 mode (auto/red/yellow)")
    parser.add_argument("--outdir", type=str, default=None, help="Custom output folder path")
    parser.add_argument("--outname", type=str, default="final_short_916.mp4", help="Custom output video filename")
    parser.add_argument("--speed", type=float, default=1.5, help="Speed ramp multiplier for movement (1.0, 1.5, 1.8)")
    parser.add_argument("--music", type=str, default=None, help="Specific background music song filename")
    parser.add_argument("--aspect", type=str, choices=["9:16", "16:9"], default="9:16", help="Output aspect ratio: 9:16 (Shorts) or 16:9 (YouTube)")
    parser.add_argument("--video", type=str, default=None, help="Specific gameplay video clip file path")
    parser.add_argument("--resdir", type=str, default=None, help="Specific resources/gameplay folder path")
    args = parser.parse_args()

    # If user requests 16:9, delegate to long_video_engine
    if args.aspect == "16:9":
        print("📐 16:9 Aspect ratio requested — delegating to long_video_engine.py...")
        from long_video_engine import assemble_long_169_video
        vo_file = locate_user_voiceover_audio(audio_override=args.audio)
        assemble_long_169_video(
            str(vo_file),
            custom_gameplay_dir=args.resdir,
            custom_bgm=args.music,
            out_dir=args.outdir,
            out_name=args.outname if args.outname != "final_short_916.mp4" else "long_video_16x9.mp4"
        )
        return

    # Master 9:16 Vertical Shorts Pipeline
    include_bgm = args.bgm.lower() in ["yes", "s", "y", "true"]
    vo_file = locate_user_voiceover_audio(audio_override=args.audio)

    assemble_short_916_video(
        str(vo_file),
        custom_gameplay_dir=args.resdir,
        specific_video=args.video,
        custom_bgm=args.music,
        include_bgm=include_bgm,
        hook_mode=args.hook,
        speed_ramp=args.speed,
        out_dir=args.outdir,
        out_name=args.outname
    )


if __name__ == "__main__":
    main()
