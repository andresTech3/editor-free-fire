"""
generate_video.py — Automated Dynamic Video Synthesis Engine
============================================================
Autonomous, dynamic video synthesizer driven by Whisper semantic analysis,
Librosa musical beat-snapping, stochastic asset sampling without repetition,
4-state dynamic scene machine, and mathematical one-pole IIR audio ducking.

CLI Usage:
    python generate_video.py --audio voiceover.mp3 --bgm music.mp3 --assets_dir ./assets/ --aspect 9:16
"""

import os
import sys
import math
import random
import argparse
import tempfile
import subprocess
from pathlib import Path

# UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np

from core.dynamic_synthesis.audio_beat_analyzer import (
    analyze_voiceover_semantics,
    analyze_bgm_beats,
    snap_to_nearest_beat,
    apply_mathematical_sidechain_ducking
)
from core.dynamic_synthesis.stochastic_sampler import StochasticAssetSampler
from core.dynamic_synthesis.scene_state_machine import (
    render_dynamic_spec_card_hud
)
from core.orientation_helper import (
    get_video_orientation_filter,
    get_media_orientation_filter,
    get_green_screen_crop_filter
)

PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def main():
    parser = argparse.ArgumentParser(description="Automated Dynamic Video Synthesis Engine")
    parser.add_argument("--audio", type=str, default=None, help="Path to input voiceover audio")
    parser.add_argument("--bgm", type=str, default=None, help="Path to background music audio (optional)")
    parser.add_argument("--assets_dir", type=str, default=str(DEFAULT_ASSETS_DIR), help="Root directory for media assets")
    parser.add_argument("--gamedir", type=str, default=None, help="Optional custom gameplay clips folder")
    parser.add_argument("--aspect", type=str, default="9:16", choices=["9:16", "16:9"], help="Output aspect ratio")
    parser.add_argument("--outdir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Directory to save final video")
    parser.add_argument("--outname", type=str, default="dynamic_synthesis_video.mp4", help="Name of output video file")
    args = parser.parse_args()

    assets_path = Path(args.assets_dir).resolve()
    recurso_dir = assets_path / "Recurso video Freefire" if (assets_path / "Recurso video Freefire").exists() else assets_path

    # 1. Locate Voiceover Audio
    audio_path = args.audio
    if not audio_path or not os.path.exists(audio_path):
        gen_dir = recurso_dir / "Generar Video"
        if gen_dir.exists():
            auds = list(gen_dir.glob("*.mp3")) + list(gen_dir.glob("*.wav")) + list(gen_dir.glob("*.m4a"))
            if auds:
                audio_path = str(auds[0])
    if not audio_path or not os.path.exists(audio_path):
        print("❌ Error: No voiceover audio file provided or found.")
        sys.exit(1)

    # 2. Locate BGM Audio (optional — uses silence if not found)
    bgm_path = args.bgm
    if not bgm_path or not os.path.exists(bgm_path):
        # Search in musica/ under recurso_dir and its parents
        search_dirs = [
            recurso_dir / "musica",
            assets_path / "musica",
            assets_path / "Recurso video Freefire" / "musica",
            PROJECT_ROOT / "assets" / "Recurso video Freefire" / "musica",
        ]
        for mus_dir in search_dirs:
            if mus_dir.exists():
                bgms = (list(mus_dir.glob("*.mp3")) + list(mus_dir.glob("*.wav"))
                        + list(mus_dir.glob("*.MP3")) + list(mus_dir.glob("*.WAV")))
                if bgms:
                    bgm_path = str(bgms[0])
                    break

    has_bgm = bool(bgm_path and os.path.exists(bgm_path))
    if not has_bgm:
        print("⚠️  Warning: No BGM file found. Video will use silence for background music.")

    print("\n" + "═"*75)
    print("🚀 AUTOMATED DYNAMIC VIDEO SYNTHESIS ENGINE (WHISPER + LIBROSA + 3D)")
    print("═"*75)
    print(f"🎙️ Voiceover:  {audio_path}")
    print(f"🎵 BGM:        {bgm_path}")
    print(f"📐 Format:     {args.aspect} @ 60 FPS")

    # Dimensions
    if args.aspect == "9:16":
        out_w, out_h = 1080, 1920
    else:
        out_w, out_h = 1920, 1080

    # ── STEP 1: WHISPER SEMANTIC ANALYSIS ─────────────────────────────────────
    vo_data = analyze_voiceover_semantics(audio_path, whisper_model="base")
    total_vo_dur = vo_data["duration"]
    total_dur = round(total_vo_dur + 1.5, 2)
    t_hook = vo_data["first_sentence_end"]
    triggers = vo_data["triggers"]

    # ── STEP 2: LIBROSA BEAT & ONSET EXTRACTION ───────────────────────────────
    if has_bgm:
        bgm_data = analyze_bgm_beats(bgm_path, target_duration=total_dur)
        beat_times = bgm_data["beat_times"]
        t_hook = snap_to_nearest_beat(t_hook, beat_times, max_distance=0.7)
    else:
        # No BGM: generate evenly spaced beat grid (0.5s grid = 120 BPM equiv.)
        beat_times = [round(i * 0.5, 2) for i in range(int(total_dur / 0.5) + 1)]
        print("  (Using 120 BPM placeholder beat grid — no BGM)")

    # ── STEP 3: MATHEMATICAL AUDIO DUCKING (ONE-POLE IIR SIDECHAIN) ───────────
    tmp_audio_out = str(Path(tempfile.gettempdir()) / "sidechained_master_audio.wav")
    if has_bgm:
        apply_mathematical_sidechain_ducking(audio_path, bgm_path, tmp_audio_out, target_duration=total_dur)
    else:
        # No BGM: copy voiceover directly (no sidechain needed)
        import shutil
        shutil.copy2(audio_path, tmp_audio_out)
        print("  (No BGM — voiceover copied directly as master audio)")

    # ── STEP 4: STOCHASTIC ASSET SAMPLING (WITHOUT REPETITION) ────────────────
    sampler = StochasticAssetSampler(assets_root=str(assets_path))

    # Determine State Boundaries
    # State 1: [0.0, t_hook]
    # State 2: [t_hook, t_proof]
    # State 3: [t_proof, total_dur - 8.0]
    # State 4: [total_dur - 8.0, total_dur]
    t_proof = snap_to_nearest_beat(max(t_hook + 4.0, (total_dur - 8.0) * 0.55), beat_times)
    t_state4 = max(t_proof + 3.0, total_dur - 8.0)

    transcript_check = vo_data.get("text", "").lower()
    is_sens_check = any(k in transcript_check for k in [
        "sensibilidad", "sensi", "dpi", "mira", "configuracion", "configuración",
        "ajustes", "boton de disparo", "botón de disparo", "calibrar"
    ])
    state4_lbl = "Dynamic Spec Card HUD" if is_sens_check else "Action Climax & Call-To-Action"

    print(f"\n⏱️ Dynamic State Machine Segmentation:")
    print(f"   • State 1 (Kinetic 3D Hook):          0.00s  ➔ {t_hook:.2f}s  ({t_hook:.2f}s)")
    print(f"   • State 2 (Educational & Memes):      {t_hook:.2f}s  ➔ {t_proof:.2f}s  ({t_proof - t_hook:.2f}s)")
    print(f"   • State 3 (Training Proof Montage):   {t_proof:.2f}s  ➔ {t_state4:.2f}s  ({t_state4 - t_proof:.2f}s)")
    print(f"   • State 4 ({state4_lbl}): {t_state4:.2f}s ➔ {total_dur:.2f}s  ({total_dur - t_state4:.2f}s)")

    # ── STEP 5: SAMPLE ASSETS FOR EACH STATE ──────────────────────────────────
    # State 1: 3 PVP planes
    hook_planes = []
    for _ in range(3):
        p_vid = sampler.sample_asset("pvp")
        if p_vid:
            hook_planes.append(sampler.slice_sub_clip(p_vid, min_dur=t_hook, max_dur=t_hook + 1.0))

    # State 2: Educational Explanation Clips
    state2_clips = []
    curr_t = t_hook
    while curr_t < t_proof:
        target_clip_dur = round(random.uniform(2.2, 3.2), 2)
        next_t = snap_to_nearest_beat(curr_t + target_clip_dur, beat_times)
        dur = max(1.5, next_t - curr_t)
        clip_vid = sampler.sample_asset("pvp")
        if clip_vid:
            sub = sampler.slice_sub_clip(clip_vid, min_dur=dur, max_dur=dur + 0.5)
            sub["timeline_start"] = curr_t
            sub["timeline_dur"] = dur
            state2_clips.append(sub)
        curr_t += dur

    # State 3: Training Proof Montage Clips
    state3_clips = []
    curr_t = t_proof
    while curr_t < total_dur + 5.0:
        target_clip_dur = round(random.uniform(2.0, 3.0), 2)
        next_t = snap_to_nearest_beat(curr_t + target_clip_dur, beat_times)
        dur = max(1.5, next_t - curr_t)
        clip_vid = sampler.sample_asset("training")
        if clip_vid:
            sub = sampler.slice_sub_clip(clip_vid, min_dur=dur, max_dur=dur + 0.5)
            actual_dur = min(dur, sub["duration"])
            sub["timeline_start"] = curr_t
            sub["timeline_dur"] = actual_dur
            state3_clips.append(sub)
            curr_t += actual_dur
        else:
            curr_t += dur

    # State 2 & 3 Memes (snapped to nearest beat, guaranteed at least 2-3 memes)
    meme_events = []
    for trig in triggers.get("meme", []):
        t_trig = trig["time"]
        if t_hook <= t_trig <= total_dur - 4.0:
            m_path = sampler.sample_asset("memes")
            if m_path:
                t_snap = snap_to_nearest_beat(t_trig, beat_times)
                meme_events.append({
                    "path": m_path,
                    "start": t_snap,
                    "dur": 2.0
                })

    # Guarantee at least 2 to 3 memes distributed evenly across the short
    target_meme_count = 3 if total_dur >= 24.0 else 2
    if len(meme_events) < target_meme_count and total_dur >= 8.0:
        if target_meme_count == 3:
            fallback_anchors = [
                t_hook + (t_proof - t_hook) * 0.45,
                t_proof + (t_state4 - t_proof) * 0.35,
                t_proof + (t_state4 - t_proof) * 0.75
            ]
        else:
            fallback_anchors = [
                t_hook + (t_proof - t_hook) * 0.5,
                t_proof + (t_state4 - t_proof) * 0.5
            ]

        for fa in fallback_anchors:
            if len(meme_events) >= target_meme_count:
                break
            if fa >= total_dur - 3.0:
                continue
            if any(abs(m["start"] - fa) < 4.0 for m in meme_events):
                continue
            m_path = sampler.sample_asset("memes")
            if m_path:
                t_snap = snap_to_nearest_beat(fa, beat_times)
                meme_events.append({
                    "path": m_path,
                    "start": t_snap,
                    "dur": 2.0
                })

    meme_events.sort(key=lambda x: x["start"])
    print(f"🤡 Scheduled {len(meme_events)} Green-Screen Meme Reactions in Timeline:")
    for me in meme_events:
        print(f"   • [{me['start']:.2f}s - {me['start']+me['dur']:.2f}s] {Path(me['path']).name}")

    # ── STEP 5B: CONTEXTUAL TOPIC & ASSET DETECTION FROM WHISPER ──────────────
    transcript_norm = vo_data.get("text", "").lower()
    print(f"\n📝 Transcripción del audio:\n   \"{vo_data.get('text', '').strip()}\"")

    is_sens_topic = any(k in transcript_norm for k in [
        "sensibilidad", "sensi", "dpi", "mira", "configuracion", "configuración",
        "ajustes", "boton de disparo", "botón de disparo", "calibrar"
    ])
    if is_sens_topic:
        print("🎯 Contexto detectado: CONFIGURACIÓN / SENSIBILIDAD -> Se habilitará HUD de sensibilidad.")
    else:
        print("🎯 Contexto detectado: JUGADAS / ACCIÓN -> HUD de sensibilidad OMITIDO (no relevante para este audio).")

    # Detect visual assets matching spoken words from recurso_dir / Imagenes
    visual_events = []
    img_dir = recurso_dir / "Imagenes"
    if img_dir.exists():
        # Diamonds / Recargas
        if any(k in transcript_norm for k in ["diamante", "diamantes", "recarga", "recargas", "pase"]):
            diam_img = img_dir / "Diamantes.PNG"
            if diam_img.exists():
                t_word = next((w["start"] for w in vo_data.get("words", []) if any(k in w["word"] for k in ["diamante", "recarga", "pase"])), t_hook + 2.0)
                visual_events.append({
                    "path": str(diam_img),
                    "start": max(t_hook, t_word),
                    "dur": 2.5,
                    "label": "Diamantes"
                })
        # Book / Web Guide
        if any(k in transcript_norm for k in ["codigo", "código", "headshot", "libro", "pagina", "página", "web"]):
            web_img = img_dir / "codigoheadshot.png"
            if web_img.exists():
                t_word = next((w["start"] for w in vo_data.get("words", []) if any(k in w["word"] for k in ["codigo", "headshot", "web", "libro"])), t_hook + 5.0)
                visual_events.append({
                    "path": str(web_img),
                    "start": max(t_hook + 1.0, t_word),
                    "dur": 2.5,
                    "label": "Web Código Headshot"
                })
        # Weapons / Evolutivas
        if any(k in transcript_norm for k in ["arma", "armas", "evolutiva", "ak47", "mp40", "m1014", "escopeta"]):
            armas_dir = img_dir / "armas"
            if armas_dir.exists():
                w_files = list(armas_dir.glob("*.png"))
                if w_files:
                    t_word = next((w["start"] for w in vo_data.get("words", []) if any(k in w["word"] for k in ["arma", "evolutiva", "ak47", "mp40"])), t_hook + 3.5)
                    visual_events.append({
                        "path": str(w_files[0]),
                        "start": max(t_hook, t_word),
                        "dur": 2.5,
                        "label": "Arma Evolutiva"
                    })
        # Official Avatar
        if any(k in transcript_norm for k in ["avatar", "cuenta", "cris", "creador", "canal"]):
            av_img = img_dir / "avatar.png"
            if av_img.exists():
                t_word = next((w["start"] for w in vo_data.get("words", []) if any(k in w["word"] for k in ["avatar", "cuenta", "cris"])), t_hook + 1.5)
                visual_events.append({
                    "path": str(av_img),
                    "start": max(t_hook, t_word),
                    "dur": 2.5,
                    "label": "Avatar Oficial"
                })

    if visual_events:
        print(f"📌 Scheduled {len(visual_events)} Contextual Visual Overlays strictly matching narration topic:")
        for ve in visual_events:
            print(f"   • [{ve['start']:.2f}s - {ve['start']+ve['dur']:.2f}s] {ve['label']} ({Path(ve['path']).name})")

    # State 4 Setup
    spec_card_img = None
    cta_badge_path = None
    if is_sens_topic:
        spec_card_img = render_dynamic_spec_card_hud(out_w, out_h, duration=total_dur - t_state4)
    else:
        # Search for CTA Like & Subscribe badge
        cta_cands = [
            recurso_dir / "PACK MEMES PANTALLA VERDE 1 (manuDT)" / "ANIMACIÓN DE LIKE Y SUSCRIBETE 1.mp4",
            recurso_dir / "PACK MEMES PANTALLA VERDE 1 (manuDT)" / "ANIMACION DE LIKE Y SUSCRIBETE 1.mp4",
            assets_path / "PACK MEMES PANTALLA VERDE 1 (manuDT)" / "ANIMACIÓN DE LIKE Y SUSCRIBETE 1.mp4",
        ]
        for c_cand in cta_cands:
            if c_cand.exists():
                cta_badge_path = str(c_cand)
                break

    # ── STEP 6: COMPILE FFMPEG COMMAND ────────────────────────────────────────
    out_dir_path = Path(args.outdir).resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)
    out_name = args.outname
    if not out_name.lower().endswith(".mp4"):
        out_name += ".mp4"
    out_file_path = out_dir_path / out_name

    cmd = ["ffmpeg", "-y"]

    # Input 0: Ducked Master Audio
    cmd.extend(["-i", tmp_audio_out])

    input_idx = 1
    # State 1 inputs
    s1_indices = []
    for hp in hook_planes:
        cmd.extend(["-ss", f"{hp['start']:.2f}", "-t", f"{t_hook:.2f}", "-i", hp["path"]])
        s1_indices.append(input_idx)
        input_idx += 1

    # State 2 inputs
    s2_indices = []
    for s2 in state2_clips:
        cmd.extend(["-ss", f"{s2['start']:.2f}", "-t", f"{s2['timeline_dur']:.2f}", "-i", s2["path"]])
        s2_indices.append((input_idx, s2))
        input_idx += 1

    # State 3 inputs
    s3_indices = []
    for s3 in state3_clips:
        cmd.extend(["-ss", f"{s3['start']:.2f}", "-t", f"{s3['timeline_dur']:.2f}", "-i", s3["path"]])
        s3_indices.append((input_idx, s3))
        input_idx += 1

    # Meme inputs
    meme_indices = []
    for me in meme_events:
        cmd.extend(["-ss", "0", "-t", f"{me['dur']:.2f}", "-i", me["path"]])
        meme_indices.append((input_idx, me))
        input_idx += 1

    # Contextual Visual Event inputs
    vis_indices = []
    for ve in visual_events:
        cmd.extend(["-loop", "1", "-t", f"{ve['dur']:.2f}", "-i", ve["path"]])
        vis_indices.append((input_idx, ve))
        input_idx += 1

    # State 4 input: Spec card (if sensitivity topic) or CTA badge
    spec_in_idx = None
    cta_in_idx = None
    if is_sens_topic and spec_card_img:
        spec_in_idx = input_idx
        cmd.extend(["-loop", "1", "-t", f"{total_dur - t_state4:.2f}", "-i", spec_card_img])
        input_idx += 1
    elif cta_badge_path:
        cta_in_idx = input_idx
        cmd.extend(["-ss", "0", "-t", f"{min(4.0, total_dur - t_state4):.2f}", "-i", cta_badge_path])
        input_idx += 1

    # Build Filter Complex
    filter_parts = []

    # 1. State 1 Composition (3D Kinetic Hook)
    pw = int(out_w * 0.48)
    ph = int(out_h * 0.65)
    cw = int(out_w * 0.65)
    ch = int(out_h * 0.75)

    color_filter_clean = "eq=contrast=1.12:saturation=1.28:brightness=0.02:gamma=1.0"

    if len(s1_indices) >= 3:
        p_l, p_c, p_r = s1_indices[0], s1_indices[1], s1_indices[2]
        filter_parts.append(
            f"[{p_l}:v]scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph},"
            f"perspective=x0=0:y0=20:x1={pw}:y1=70:x2=0:y2={ph-20}:x3={pw}:y3={ph-70}[h_left];"
        )
        filter_parts.append(
            f"[{p_c}:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch}[h_center];"
        )
        filter_parts.append(
            f"[{p_r}:v]scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph},"
            f"perspective=x0=0:y0=70:x1={pw}:y1=20:x2=0:y2={ph-70}:x3={pw}:y3={ph-20}[h_right];"
        )
        filter_parts.append(
            f"color=c=black:s={out_w}x{out_h}:d={t_hook:.2f}[h_bg];"
        )
        filter_parts.append(
            f"[h_bg][h_left]overlay=x=20:y=(H-h)/2[h_cmp1];"
        )
        filter_parts.append(
            f"[h_cmp1][h_right]overlay=x=W-w-20:y=(H-h)/2[h_cmp2];"
        )
        filter_parts.append(
            f"[h_center]pad=iw+8:ih+8:4:4:color=gold@0.8[h_border];"
        )
        filter_parts.append(
            f"[h_cmp2][h_border]overlay=x=(W-w)/2:y=(H-h)/2[h_3d];"
        )
        filter_parts.append(
            f"[h_3d]trim=duration={t_hook:.2f},setpts=PTS-STARTPTS,"
            f"scale=eval=frame:w='iw*(1.0+0.35*pow(t/{t_hook:.2f},2))':h='ih*(1.0+0.35*pow(t/{t_hook:.2f},2))',"
            f"crop={out_w}:{out_h}:(iw-{out_w})/2:(ih-{out_h})/2,{color_filter_clean},setsar=1,fps=60[v_state1];"
        )
    else:
        filter_parts.append(
            f"[{s1_indices[0]}:v]trim=duration={t_hook:.2f},setpts=PTS-STARTPTS,"
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},"
            f"{color_filter_clean},setsar=1,fps=60[v_state1];"
        )

    # 2. State 2 & State 3 Clips (Fluid Gameplay, Uniform 60 FPS, Luminous Color Grade)
    concat_list = ["[v_state1]"]

    for i_num, (in_i, s2) in enumerate(s2_indices):
        lbl = f"v_s2_{i_num}"
        dur_s2 = s2["timeline_dur"]
        rot = get_video_orientation_filter(s2["path"])
        filter_parts.append(
            f"[{in_i}:v]trim=duration={dur_s2:.2f},setpts=PTS-STARTPTS,{rot}scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h}:(in_w-{out_w})/2:(in_h-{out_h})/2,{color_filter_clean},setsar=1,fps=60[{lbl}];"
        )
        concat_list.append(f"[{lbl}]")

    for i_num, (in_i, s3) in enumerate(s3_indices):
        lbl = f"v_s3_{i_num}"
        dur_s3 = s3["timeline_dur"]
        rot = get_video_orientation_filter(s3["path"])
        filter_parts.append(
            f"[{in_i}:v]trim=duration={dur_s3:.2f},setpts=PTS-STARTPTS,{rot}scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h}:(in_w-{out_w})/2:(in_h-{out_h})/2,{color_filter_clean},setsar=1,fps=60[{lbl}];"
        )
        concat_list.append(f"[{lbl}]")

    concat_str = "".join(concat_list)
    filter_parts.append(f"{concat_str}concat=n={len(concat_list)}:v=1:a=0,trim=0:{total_dur:.2f},setpts=PTS-STARTPTS[v_base];")

    curr_v = "v_base"

    # 3. Overlay Contextual Visual Events (Diamonds, Weapons, Web Guide, Avatar)
    for v_i, (v_in, ve) in enumerate(vis_indices):
        next_v = f"v_vis_{v_i}"
        v_st = ve["start"]
        v_dur = ve["dur"]
        filter_parts.append(
            f"[{v_in}:v]setpts=PTS-STARTPTS+{v_st:.2f}/TB,"
            f"scale=650:380:force_original_aspect_ratio=decrease,pad=iw+6:ih+6:3:3:color=white@0.35,setsar=1,fps=60[vis_card_{v_i}];"
        )
        filter_parts.append(
            f"[{curr_v}][vis_card_{v_i}]overlay=enable='between(t,{v_st:.2f},{v_st+v_dur:.2f})':x=(W-w)/2:y=180:eof_action=pass[{next_v}];"
        )
        curr_v = next_v

    # 4. Overlay Silent Green-Screen Memes (Upper area, rhythmically synced to cadence)
    for m_i, (m_in, me) in enumerate(meme_indices):
        next_v = f"v_meme_{m_i}"
        m_t = me["start"]
        m_dur = me["dur"]
        m_path = me["path"]
        crop_filt = get_green_screen_crop_filter(m_path)
        m_orient = get_video_orientation_filter(m_path)
        filter_parts.append(
            f"[{m_in}:v]setpts=PTS-STARTPTS+{m_t:.2f}/TB,{m_orient}{crop_filt}"
            f"scale=800:1400:force_original_aspect_ratio=decrease,chromakey=0x00FF00:0.28:0.08,setsar=1,fps=60[m_proc_{m_i}];"
        )
        filter_parts.append(
            f"[{curr_v}][m_proc_{m_i}]overlay=enable='between(t,{m_t:.2f},{m_t+m_dur:.2f})':x=(W-w)/2:y=240:eof_action=pass[{next_v}];"
        )
        curr_v = next_v

    # 5. State 4 Overlay: Sensitivity Spec Card OR Action Climax CTA Badge
    if is_sens_topic and spec_in_idx is not None:
        card_target_y = int(out_h * 0.62)
        u_expr = f"min(1.0,max(0.0,(t-{t_state4:.2f})/0.45))"
        y_expr = f"{card_target_y}+600*pow(1.0-{u_expr},3)-30*sin(3.14159*{u_expr})"

        filter_parts.append(
            f"[{spec_in_idx}:v]setpts=PTS-STARTPTS+{t_state4:.2f}/TB,"
            f"scale={out_w-60}:-1:force_original_aspect_ratio=decrease,setsar=1,fps=60[spec_scaled];"
        )
        filter_parts.append(
            f"[{curr_v}][spec_scaled]overlay=enable='between(t,{t_state4:.2f},{total_dur:.2f})':x=(W-w)/2:y='{y_expr}':eof_action=pass[v_prefinal];"
        )
        curr_v = "v_prefinal"
    elif cta_in_idx is not None:
        cta_y = int(out_h * 0.78)
        filter_parts.append(
            f"[{cta_in_idx}:v]setpts=PTS-STARTPTS+{t_state4:.2f}/TB,"
            f"scale=450:260:force_original_aspect_ratio=decrease,chromakey=0x00FF00:0.28:0.08,setsar=1,fps=60[cta_scaled];"
        )
        filter_parts.append(
            f"[{curr_v}][cta_scaled]overlay=enable='between(t,{t_state4:.2f},{min(t_state4+4.0, total_dur):.2f})':x=(W-w)/2:y={cta_y}:eof_action=pass[v_prefinal];"
        )
        curr_v = "v_prefinal"

    # Smooth finish (no freezing, no white flash, subtle 0.5s fade out to black at the end)
    fade_start = max(0.0, total_dur - 0.5)
    filter_parts.append(
        f"[{curr_v}]fade=t=out:st={fade_start:.2f}:d=0.5:color=black[v_final];"
    )

    filter_complex = "\n".join(filter_parts)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[v_final]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "12M",
        "-maxrate", "15M",
        "-bufsize", "20M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "60",
        "-t", f"{total_dur:.2f}",
        "-shortest",
        str(out_file_path)
    ])

    print(f"\n🚀 Rendering with FFmpeg: {out_file_path}")
    try:
        subprocess.run(cmd, check=True)
    finally:
        # ── CLEANUP TEMPORARY FILES ───────────────────────────────────────────
        if tmp_audio_out and os.path.exists(tmp_audio_out):
            try:
                os.remove(tmp_audio_out)
                print(f"🧹 Audio temporal ducking eliminado ({Path(tmp_audio_out).name})")
            except Exception:
                pass
        if spec_card_img and os.path.exists(spec_card_img):
            try:
                os.remove(spec_card_img)
                print(f"🧹 Spec card temporal eliminada ({Path(spec_card_img).name})")
            except Exception:
                pass

    print("\n" + "═"*75)
    print("🎉 DYNAMIC SYNTHESIS VIDEO COMPLETED SUCCESSFULLY!")
    print(f"👉 Output: {out_file_path}")
    print(f"📐 Format: {args.aspect} @ 60 FPS")
    print(f"⏱️ Duration: {total_dur:.2f}s")
    print("═"*75)


if __name__ == "__main__":
    main()
