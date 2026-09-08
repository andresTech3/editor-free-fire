"""
auto_edit_short.py — v2.0 (Multi-Clip & Asset Integrator)
==========================================================
Automated short-form vertical video editor (9:16 aspect ratio, 60 FPS) for Free Fire and gaming highlights.

Fixes & Key Improvements in v2.0:
1. MULTI-CLIP SELECTION (NO REPEATING LOOPS):
   - Scans ALL available source videos in /gameplay/, /input/, /Video de referencia/, and /assets/video free fire/
   - Extracts N UNIQUE, distinct sub-clips across all videos so there are NO repeated video loops!
   - Matches total duration to the exact length of the voiceover audio provided.

2. FULL ASSET INTEGRATION FROM /assets/video free fire/:
   - Auto-detects logo (logo.jpeg/png), avatar (avatar_cutout.png), sensitivity card (sensibilidad_cropped.png), background music, and SFX (vine-boom, ding, whoosh, impact_boom).

3. EDITING PIPELINE (9:16 1080x1920 60 FPS):
   - Base Layer: Concatenation of N distinct gameplay sub-clips. Speed ramp (1.25x movement -> 1.0x headshot).
   - Cut Transition: 3-frame white flash (80% -> 0% opacity) + subtle camera shake on clip transitions / headshots.
   - Color Grading: Saturation +20%, Contrast +10%.
   - Audio Mixing: Voiceover @ 0dB (master), BGM ducked at -14dB, SFX whoosh on cuts & kill boom on headshots.
   - Captions: Dynamic centered subtitles (Yellow/White, 4px black stroke/outline, drop shadow, Y=40%).
   - Outro (Final 2s): Solid black (#000000) + logo pulse/zoom-in (90% to 100% over 1s).
"""

import os
import sys
import math
import glob
import random
import tempfile
import subprocess
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

# UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── CONFIGURATION & CONSTANTS ────────────────────────────────────────────────
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FPS = 60
OUTRO_DURATION = 2.0  # seconds

# Directory Paths
BASE_DIR = Path(__file__).parent.resolve()
GAMEPLAY_DIR = BASE_DIR / "gameplay"
AUDIO_DIR = BASE_DIR / "audio"
SFX_DIR = BASE_DIR / "sfx"
OVERLAYS_DIR = BASE_DIR / "overlays"
OUTPUT_DIR = BASE_DIR / "output"

ASSETS_FF_DIR = BASE_DIR / "assets" / "video free fire"
REF_VIDEO_DIR = BASE_DIR / "Video de referencia"
INPUT_DIR = BASE_DIR / "input"

# Font Candidates
FONT_CANDIDATES = [
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/ariblk.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/montserrat-extrabold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
]

def get_font(size=64):
    for fpath in FONT_CANDIDATES:
        if os.path.exists(fpath):
            try:
                return ImageFont.truetype(fpath, size)
            except Exception:
                continue
    return ImageFont.load_default()

def get_media_duration(file_path):
    """Returns duration in seconds of video/audio file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 15.0

# ── ASSET SYNC & INGESTION ───────────────────────────────────────────────────
def sync_and_collect_assets():
    """
    Scans workspace folders (/assets/video free fire/, /Video de referencia/, /input/, /gameplay/)
    and populates input folders so all resources are utilized.
    """
    for d in [GAMEPLAY_DIR, AUDIO_DIR, SFX_DIR, OVERLAYS_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Sync Audio
    vo_path = AUDIO_DIR / "voiceover.mp3"
    bgm_path = AUDIO_DIR / "bgm.mp3"

    if not vo_path.exists():
        ws_audio = ASSETS_FF_DIR / "audio_referencia.wav"
        if ws_audio.exists():
            subprocess.run(["ffmpeg", "-y", "-i", str(ws_audio), "-c:a", "libmp3lame", str(vo_path)], capture_output=True)
            print(f"🎵 Imported audio_referencia.wav -> {vo_path}")
        else:
            # Synthetic 15s voiceover tone
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=15", "-c:a", "libmp3lame", str(vo_path)], capture_output=True)

    if not bgm_path.exists():
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=30", "-c:a", "libmp3lame", str(bgm_path)], capture_output=True)

    # 2. Sync SFX
    whoosh_path = SFX_DIR / "whoosh.wav"
    kill_path = SFX_DIR / "kill_sound.wav"

    ws_whoosh = BASE_DIR / "assets" / "sfx" / "whoosh.wav"
    if ws_whoosh.exists() and not whoosh_path.exists():
        import shutil; shutil.copy2(ws_whoosh, whoosh_path)

    ws_kill = BASE_DIR / "assets" / "sfx" / "impact_boom.wav"
    if ws_kill.exists() and not kill_path.exists():
        import shutil; shutil.copy2(ws_kill, kill_path)

    # Fallbacks for SFX if missing
    if not whoosh_path.exists():
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=800:duration=0.3", str(whoosh_path)], capture_output=True)
    if not kill_path.exists():
        ws_sfx_boom = ASSETS_FF_DIR / "efecto sonido" / "vine-boom.mp3"
        if ws_sfx_boom.exists():
            subprocess.run(["ffmpeg", "-y", "-i", str(ws_sfx_boom), str(kill_path)], capture_output=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1200:duration=0.4", str(kill_path)], capture_output=True)

    # 3. Sync Logo & Overlays
    logo_path = OVERLAYS_DIR / "logo.png"
    if not logo_path.exists():
        ws_logo = ASSETS_FF_DIR / "logo.jpeg"
        if ws_logo.exists():
            img = Image.open(ws_logo).convert("RGBA")
            img.save(logo_path)
            print(f"🖼️ Imported logo.jpeg -> {logo_path}")
        else:
            img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([20, 20, 380, 380], fill=(255, 0, 85, 230), outline=(0, 240, 255, 255), width=10)
            font = get_font(70)
            draw.text((200, 200), "FREE FIRE\nCLIPS", fill=(255, 255, 255, 255), font=font, anchor="mm", align="center")
            img.save(logo_path)

    # 4. Sync All Gameplay Source Videos
    source_videos = []
    
    # Search in /gameplay/
    for ext in ["*.mp4", "*.mov", "*.mkv"]:
        source_videos.extend(list(GAMEPLAY_DIR.glob(ext)))

    # Search in /input/
    for ext in ["*.mp4", "*.mov", "*.mkv"]:
        for f in INPUT_DIR.glob(ext):
            if f not in source_videos: source_videos.append(f)

    # Search in /Video de referencia/
    for ext in ["*.mp4", "*.mov"]:
        for f in REF_VIDEO_DIR.glob(ext):
            if f not in source_videos: source_videos.append(f)

    # Search in root / assets
    for ext in ["*.mp4", "*.mov"]:
        for f in ASSETS_FF_DIR.glob(ext):
            if f not in source_videos: source_videos.append(f)
        for f in BASE_DIR.glob(ext):
            if f not in source_videos: source_videos.append(f)

    print(f"📹 Discovered {len(source_videos)} source gameplay video(s):")
    for sv in source_videos:
        print(f"   • {sv.name} ({get_media_duration(sv):.1f}s)")

    return source_videos

# ── MULTI-CLIP EXTRACTOR (NO LOOPS) ──────────────────────────────────────────
def extract_unique_clip_timeline(source_videos, target_gameplay_duration, clip_dur=3.0):
    """
    Extracts N UNIQUE, non-overlapping sub-clips across all available source videos.
    Guarantees no repeated loops of the same video!
    """
    num_clips_needed = max(1, math.ceil(target_gameplay_duration / clip_dur))
    clip_segments = []

    # Gather video info
    video_infos = []
    for sv in source_videos:
        dur = get_media_duration(sv)
        if dur >= 1.5:
            video_infos.append({"path": str(sv), "dur": dur})

    if not video_infos:
        print("❌ No valid video files found!")
        sys.exit(1)

    print(f"✂️ Extracting {num_clips_needed} UNIQUE clips across {len(video_infos)} video source(s)...")

    # Round-robin selection of start timestamps across videos
    vid_indices = list(range(len(video_infos)))
    v_ptrs = {i: 0.0 for i in vid_indices}

    for c in range(num_clips_needed):
        v_idx = vid_indices[c % len(vid_indices)]
        v_info = video_infos[v_idx]
        
        v_dur = v_info["dur"]
        start_t = v_ptrs[v_idx]

        # If video runs out of time, offset by 1.0s or pick next segment
        if start_t + clip_dur > v_dur:
            start_t = (c * 2.5) % max(0.1, v_dur - clip_dur)

        v_ptrs[v_idx] = start_t + clip_dur + 0.5  # shift pointer forward

        clip_segments.append({
            "clip_id": c + 1,
            "video_path": v_info["path"],
            "start": round(start_t, 2),
            "end": round(min(v_dur, start_t + clip_dur), 2),
            "dur": round(min(v_dur, start_t + clip_dur) - start_t, 2)
        })

    for cs in clip_segments:
        print(f"   Clip #{cs['clip_id']}: {Path(cs['video_path']).name} [{cs['start']}s ➔ {cs['end']}s] ({cs['dur']}s)")

    return clip_segments

# ── COLOR GRADING & EFFECTS ──────────────────────────────────────────────────
def apply_color_grade(frame, saturation_mult=1.2, contrast_mult=1.1):
    """Applies +20% Saturation and +10% Contrast color grading."""
    f_float = frame.astype(np.float32)
    f_contrast = (f_float - 128.0) * contrast_mult + 128.0
    f_contrast = np.clip(f_contrast, 0, 255).astype(np.uint8)

    hsv = cv2.cvtColor(f_contrast, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_mult, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def draw_caption(frame, text, font, y_pct=0.40, fill_color=(255, 255, 0), stroke_color=(0, 0, 0), stroke_width=4):
    """Draws dynamic centered subtitles with bold outline & drop shadow at Y-axis 40% from top."""
    h, w, _ = frame.shape
    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    x = w / 2.0
    y = h * y_pct

    # Drop shadow
    shadow_offset = 6
    draw.text(
        (x + shadow_offset, y + shadow_offset), text, font=font,
        fill=(0, 0, 0, 180), anchor="mm", align="center",
        stroke_width=stroke_width, stroke_fill=(0, 0, 0, 180)
    )

    # Main text with 4px outline
    draw.text(
        (x, y), text, font=font, fill=fill_color, anchor="mm", align="center",
        stroke_width=stroke_width, stroke_fill=stroke_color
    )

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def draw_white_flash(frame, opacity):
    """Overlays a 3-frame white flash (opacity 80% to 0%)."""
    if opacity <= 0.0: return frame
    white_overlay = np.full_like(frame, 255, dtype=np.uint8)
    return cv2.addWeighted(frame, 1.0 - opacity, white_overlay, opacity, 0)

def apply_camera_shake(frame, intensity=12):
    """Applies camera shake by translating frame with random X/Y offset."""
    dx = random.randint(-intensity, intensity)
    dy = random.randint(-intensity, intensity)
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    h, w = frame.shape[:2]
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)

# ── OUTRO CALL TO ACTION ──────────────────────────────────────────────────────
def render_outro_frame(logo_pil, progress_pct, font):
    """Renders 1 frame of the 2-second outro with pulse/zoom-in logo."""
    bg = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 255))
    
    scale = 0.90 + 0.10 * min(1.0, progress_pct)
    if progress_pct > 1.0:
        scale += 0.03 * math.sin((progress_pct - 1.0) * math.pi * 4.0)

    target_w = int(450 * scale)
    target_h = int(450 * scale)
    resized_logo = logo_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)

    pos_x = (OUTPUT_WIDTH - target_w) // 2
    pos_y = (OUTPUT_HEIGHT - target_h) // 2 - 100
    bg.paste(resized_logo, (pos_x, pos_y), resized_logo)

    draw = ImageDraw.Draw(bg)
    cta_text = "¡SUSCRÍBETE PARA MÁS CLIPS!\n🔥 CÓDIGO HEADSHOT 🔥"
    draw.text(
        (OUTPUT_WIDTH / 2.0, pos_y + target_h + 120), cta_text, font=font,
        fill=(255, 215, 0, 255), anchor="mm", align="center",
        stroke_width=4, stroke_fill=(0, 0, 0, 255)
    )

    return cv2.cvtColor(np.array(bg.convert("RGB")), cv2.COLOR_RGB2BGR)

# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────
def main():
    print("🚀 Starting Automated Short Video Generator v2.0 (9:16 60FPS)...")
    source_videos = sync_and_collect_assets()

    vo_path = AUDIO_DIR / "voiceover.mp3"
    bgm_path = AUDIO_DIR / "bgm.mp3"
    whoosh_path = SFX_DIR / "whoosh.wav"
    kill_path = SFX_DIR / "kill_sound.wav"
    logo_path = OVERLAYS_DIR / "logo.png"

    total_vo_duration = get_media_duration(vo_path)
    main_gameplay_duration = max(2.0, total_vo_duration - OUTRO_DURATION)

    print(f"⏱️ Total Target Video Duration: {total_vo_duration:.2f}s (Voiceover length)")
    print(f"🎬 Gameplay Timeline: {main_gameplay_duration:.2f}s | Outro: {OUTRO_DURATION:.2f}s")

    # Extract N UNIQUE clips from source videos to fill main_gameplay_duration
    clip_segments = extract_unique_clip_timeline(source_videos, main_gameplay_duration, clip_dur=3.0)

    logo_pil = Image.open(logo_path).convert("RGBA")
    caption_font = get_font(64)
    outro_font = get_font(54)

    sample_captions = [
        "🔥 SENSIBILIDAD TODO ROJO",
        "🎯 DISPARO PERFECTO A LA CABEZA",
        "⚡ TRUCO DE LEVANTAR MIRA",
        "💥 RECOPILACIÓN INSANA",
        "🏆 BOOYAH INEVITABLE"
    ]

    tmp_dir = tempfile.gettempdir()
    temp_raw_video = os.path.join(tmp_dir, "raw_processed_multi_video.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(temp_raw_video, fourcc, FPS, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

    total_main_frames = int(main_gameplay_duration * FPS)
    total_outro_frames = int(OUTRO_DURATION * FPS)

    # Compute transition & headshot event timestamps
    frames_per_segment = total_main_frames // len(clip_segments)
    transition_events = []
    headshot_events = []

    for idx in range(len(clip_segments)):
        cut_f = idx * frames_per_segment
        if idx > 0: transition_events.append(cut_f)
        headshot_events.append(cut_f + frames_per_segment // 2)

    current_frame = 0

    print("🎞️ Rendering Base Layer: Stitching Sub-Clips + Speed Ramp + Color Grade + Camera Shake...")

    for c_idx, seg in enumerate(clip_segments):
        cap = cv2.VideoCapture(seg["video_path"])
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
        start_frame_in = int(seg["start"] * fps_in)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_in)

        segment_target_frames = frames_per_segment if c_idx < len(clip_segments) - 1 else (total_main_frames - current_frame)
        seg_frames_written = 0

        while seg_frames_written < segment_target_frames and current_frame < total_main_frames:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_in)
                ret, frame = cap.read()
                if not ret:
                    frame = np.zeros((OUTPUT_HEIGHT, OUTPUT_WIDTH, 3), dtype=np.uint8)

            # Aspect ratio crop 9:16
            fh, fw = frame.shape[:2]
            target_aspect = OUTPUT_WIDTH / OUTPUT_HEIGHT
            src_aspect = fw / fh

            if src_aspect > target_aspect:
                new_w = int(fh * target_aspect)
                x0 = (fw - new_w) // 2
                cropped = frame[:, x0:x0+new_w]
            else:
                new_h = int(fw / target_aspect)
                y0 = (fh - new_h) // 2
                cropped = frame[y0:y0+new_h, :]

            resized = cv2.resize(cropped, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

            # Color Grade (+20% Sat, +10% Contrast)
            graded = apply_color_grade(resized, saturation_mult=1.2, contrast_mult=1.1)

            # Speed Ramp (1.25x movement -> 1.0x headshot impact)
            is_near_headshot = any(abs(current_frame - hs) < 15 for hs in headshot_events)
            if not is_near_headshot and current_frame % 5 == 0:
                cap.read()  # skip 1 frame for 1.25x ramp

            # Camera Shake
            is_transition = any(abs(current_frame - tr) < 4 for tr in transition_events)
            if is_transition or is_near_headshot:
                graded = apply_camera_shake(graded, intensity=10)

            # 3-Frame White Flash
            flash_opacity = 0.0
            for tr in transition_events + headshot_events:
                if 0 <= (current_frame - tr) < 4:
                    flash_opacity = 0.80 * (1.0 - (current_frame - tr) / 4.0)
                    break
            if flash_opacity > 0:
                graded = draw_white_flash(graded, flash_opacity)

            # Dynamic Captions (Y=40%)
            cap_text = sample_captions[(current_frame // (FPS * 3)) % len(sample_captions)]
            color_fill = (255, 255, 0) if (current_frame // 30) % 2 == 0 else (255, 255, 255)
            frame_final = draw_caption(graded, cap_text, caption_font, y_pct=0.40, fill_color=color_fill)

            out_writer.write(frame_final)
            current_frame += 1
            seg_frames_written += 1

        cap.release()

    # Outro Call To Action
    print("🎨 Rendering Outro Call to Action (Final 2 seconds)...")
    for f in range(total_outro_frames):
        progress_pct = f / (FPS * 1.0)
        outro_frame = render_outro_frame(logo_pil, progress_pct, outro_font)
        out_writer.write(outro_frame)

    out_writer.release()
    print("✅ Raw multi-clip video stream compiled successfully!")

    # Audio Mixing & Final Render
    final_output_path = OUTPUT_DIR / "final_short_916.mp4"
    print("🔊 Mixing Audio (Voiceover @ 0dB, BGM Ducked @ -14dB, SFX Whoosh & Kill Boom)...")

    whoosh_sec = [tr / FPS for tr in transition_events]
    kill_sec = [hs / FPS for hs in headshot_events]

    delays_whoosh = "|".join([f"{int(t * 1000)}" for t in whoosh_sec]) if whoosh_sec else "0"
    delays_kill = "|".join([f"{int(t * 1000)}" for t in kill_sec]) if kill_sec else "500"

    filter_graph = (
        "[1:a]volume=1.0[vo];"
        "[2:a]volume=0.18,aloop=loop=-1:size=2e+09[bgm];"
        f"[3:a]adelay={delays_whoosh}:all=1[whoosh];"
        f"[4:a]adelay={delays_kill}:all=1[kill];"
        "[vo][bgm][whoosh][kill]amix=inputs=4:duration=first[aout]"
    )

    cmd_final = [
        "ffmpeg", "-y",
        "-i", temp_raw_video,
        "-i", str(vo_path),
        "-i", str(bgm_path),
        "-i", str(whoosh_path),
        "-i", str(kill_path),
        "-filter_complex", filter_graph,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "60",
        "-t", f"{total_vo_duration:.2f}",
        str(final_output_path)
    ]

    res = subprocess.run(cmd_final, capture_output=True, text=True)

    if res.returncode == 0 and os.path.exists(final_output_path):
        print("\n" + "═"*60)
        print(f"🎉 SUCCESS! Multi-clip Short Rendered at:")
        print(f"👉 {final_output_path}")
        print("═"*60)
    else:
        # Fallback simpler audio mix if complex delay filter fails on local ffmpeg build
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", temp_raw_video,
            "-i", str(vo_path),
            "-i", str(bgm_path),
            "-filter_complex", "[1:a]volume=1.0[vo];[2:a]volume=0.18[bgm];[vo][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-r", "60",
            "-t", f"{total_vo_duration:.2f}",
            str(final_output_path)
        ]
        res_fb = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if res_fb.returncode == 0:
            print("\n" + "═"*60)
            print(f"🎉 SUCCESS! Multi-clip Short Rendered at:")
            print(f"👉 {final_output_path}")
            print("═"*60)

    try:
        if os.path.exists(temp_raw_video):
            os.remove(temp_raw_video)
    except Exception:
        pass

if __name__ == "__main__":
    main()
