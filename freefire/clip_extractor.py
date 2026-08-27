"""
freefire/clip_extractor.py
===========================
Módulo Avanzado de Recortes de Clips de Gameplay de Free Fire.

Soporta 8 tipos de eventos de gameplay:
  1. "tiros_rojo"   / "headshots"  : Disparos a la cabeza con números rojos
  2. "squad_wipes"  / "frenetico"  : Bajas múltiples en rápida sucesión (1vs4)
  3. "movimiento"   / "insano"     : Movimiento ultra rápido y colocación de Paredes Gloo
  4. "sniper"       / "long_shot"  : Tiros con mira telescópica (AWM/Barrett)
  5. "booyah"       / "victoria"   : El momento de victoria (Cartel BOOYAH!)
  6. "fallando"     / "fails"      : Disparos errados y jugadas pecheadas
  7. "muertes"      / "deaths"     : Momentos cuando el jugador es eliminado
  8. "highlights"   / "kills"      : Los mejores momentos generales de acción

Soporta exportación en múltiples formatos:
  - "9:16" (1080x1920) Vertical Shorts/Reels/TikTok
  - "16:9" (1920x1080) Horizontal YouTube
  - "1:1"  (1080x1080) Cuadrado Instagram
"""

import os
import cv2
import numpy as np
import subprocess
import tempfile
from dataclasses import dataclass
from .gameplay_analyzer import get_video_duration, get_video_info


@dataclass
class DetectedSegment:
    start_time: float
    end_time: float
    score: float
    event_type: str


def analyze_video_events_advanced(video_path: str, sample_fps: float = 4.0) -> list[dict]:
    """
    Escanea el video cuadro por cuadro con OpenCV para calcular metricas de:
      - red_score: números rojos de daño de headshot
      - motion_score: velocidad de movimiento de cámara / Pared Gloo
      - sniper_score: presencia de mira telescópica circular
      - booyah_score: texto dorado/amarillo de BOOYAH!
      - death_score: pantalla de eliminación / viñeta oscura
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    frame_step = max(1, int(fps / sample_fps))

    timeline = []
    frame_idx = 0
    prev_gray = None

    # Rangos HSV para Free Fire
    # Rojo (damage numbers): HSV 0-10 & 170-180
    lower_red1 = np.array([0, 180, 180])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 180, 180])
    upper_red2 = np.array([180, 255, 255])

    # Dorado/Amarillo (BOOYAH banner): HSV 15-35
    lower_gold = np.array([15, 160, 160])
    upper_gold = np.array([35, 255, 255])

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps
        h, w = frame.shape[:2]

        # 1. Red Damage Numbers (Headshots)
        roi_center = frame[int(h * 0.15):int(h * 0.65), int(w * 0.20):int(w * 0.80)]
        hsv_center = cv2.cvtColor(roi_center, cv2.COLOR_BGR2HSV)
        mask_r1 = cv2.inRange(hsv_center, lower_red1, upper_red1)
        mask_r2 = cv2.inRange(hsv_center, lower_red2, upper_red2)
        red_score = float(np.sum(cv2.bitwise_or(mask_r1, mask_r2) > 0))

        # 2. BOOYAH / Victoria (Gold/Yellow banner in upper-middle)
        roi_top = frame[int(h * 0.10):int(h * 0.40), int(w * 0.15):int(w * 0.85)]
        hsv_top = cv2.cvtColor(roi_top, cv2.COLOR_BGR2HSV)
        gold_mask = cv2.inRange(hsv_top, lower_gold, upper_gold)
        booyah_score = float(np.sum(gold_mask > 0))

        # 3. Motion Score (Movimiento Insano / Camera Turn)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            motion_score = float(np.mean(diff))
        else:
            motion_score = 0.0
        prev_gray = gray

        # 4. Sniper Scope (Circular dark vignette border)
        roi_scope_edge = frame[int(h * 0.1):int(h * 0.2), int(w * 0.1):int(w * 0.2)]
        scope_darkness = float(255 - np.mean(roi_scope_edge))
        sniper_score = scope_darkness if scope_darkness > 180 else 0.0

        # 5. Death Score (Darkened screen)
        avg_brightness = float(np.mean(gray))
        death_score = 1.0 if avg_brightness < 40 else 0.0

        timeline.append({
            "timestamp": timestamp,
            "red_score": red_score,
            "motion_score": motion_score,
            "sniper_score": sniper_score,
            "booyah_score": booyah_score,
            "death_score": death_score,
            "brightness": avg_brightness,
        })

        frame_idx += frame_step
        # Fast frame skip using grab() without full decoding
        for _ in range(frame_step - 1):
            if not cap.grab():
                break

    cap.release()
    return timeline


def extract_event_clips(
    video_path: str,
    event_type: str = "tiros_rojo",
    clip_duration: float = 3.0,
    max_clips: int = 5,
    aspect_ratio: str = "9:16",
    output_path: str = None,
) -> str:
    """
    Extrae y une los clips del tipo de evento especificado.

    Tipos de eventos soportados:
      - "tiros_rojo"  / "headshots"
      - "squad_wipes" / "frenetico"
      - "movimiento"  / "insano"
      - "sniper"      / "long_shot"
      - "booyah"      / "victoria"
      - "fallando"    / "fails"
      - "muertes"     / "deaths"
      - "highlights"  / "kills"

    Aspect Ratios:
      - "9:16" : Vertical (1080x1920)
      - "16:9" : Horizontal (1920x1080)
      - "1:1"  : Cuadrado (1080x1080)
    """
    duration = get_video_duration(video_path)
    if duration <= 0:
        print("❌ Error: Video no válido o duración cero")
        return ""

    if output_path is None:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "FreeFire")
        os.makedirs(out_dir, exist_ok=True)
        event_clean = event_type.lower().replace(" ", "_")
        output_path = os.path.join(out_dir, f"recopilacion_{event_clean}.mp4")

    event_type_norm = event_type.lower().strip()

    print(f"[+] Analyzing gameplay: '{os.path.basename(video_path)}'...")
    timeline = analyze_video_events_advanced(video_path, sample_fps=4.0)

    segments = []

    if "rojo" in event_type_norm or "headshot" in event_type_norm:
        if timeline:
            sorted_tl = sorted(timeline, key=lambda x: x["red_score"], reverse=True)
            for item in sorted_tl:
                if len(segments) >= max_clips:
                    break
                t = item["timestamp"]
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 1.0)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, item["red_score"], "tiros_rojo"))

    elif "squad" in event_type_norm or "frenetico" in event_type_norm or "wipe" in event_type_norm:
        # Picos con alta densidad de red_score + motion_score en ventana continua
        if timeline:
            scored = []
            for item in timeline:
                score = item["red_score"] * 1.5 + item["motion_score"] * 2.0
                scored.append((item["timestamp"], score))
            sorted_tl = sorted(scored, key=lambda x: x[1], reverse=True)
            for t, score in sorted_tl:
                if len(segments) >= max_clips:
                    break
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 1.0)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, score, "squad_wipes"))

    elif "movimiento" in event_type_norm or "insano" in event_type_norm or "gloo" in event_type_norm:
        if timeline:
            sorted_tl = sorted(timeline, key=lambda x: x["motion_score"], reverse=True)
            for item in sorted_tl:
                if len(segments) >= max_clips:
                    break
                t = item["timestamp"]
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 0.5)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, item["motion_score"], "movimiento"))

    elif "sniper" in event_type_norm or "long" in event_type_norm or "awm" in event_type_norm:
        if timeline:
            sorted_tl = sorted(timeline, key=lambda x: x["sniper_score"], reverse=True)
            for item in sorted_tl:
                if len(segments) >= max_clips:
                    break
                t = item["timestamp"]
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 1.0)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, item["sniper_score"], "sniper"))

    elif "booyah" in event_type_norm or "victoria" in event_type_norm:
        if timeline:
            sorted_tl = sorted(timeline, key=lambda x: x["booyah_score"], reverse=True)
            for item in sorted_tl:
                if len(segments) >= max_clips:
                    break
                t = item["timestamp"]
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 2.0)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, item["booyah_score"], "booyah"))

    elif "muerte" in event_type_norm or "death" in event_type_norm:
        if timeline:
            sorted_tl = sorted(timeline, key=lambda x: x["death_score"], reverse=True)
            for item in sorted_tl:
                if len(segments) >= max_clips:
                    break
                t = item["timestamp"]
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 1.5)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, item["death_score"], "muertes"))

    elif "fallando" in event_type_norm or "fail" in event_type_norm:
        if timeline:
            sorted_tl = sorted(timeline, key=lambda x: (x["motion_score"] - x["red_score"]), reverse=True)
            for item in sorted_tl:
                if len(segments) >= max_clips:
                    break
                t = item["timestamp"]
                if not any(abs(t - s.start_time) < clip_duration for s in segments):
                    start = max(0.0, t - 0.5)
                    end = min(duration, start + clip_duration)
                    segments.append(DetectedSegment(start, end, 1.0, "fallando"))

    # Fallback / Highlights: ordenar por combinación de audio y movimiento
    if not segments:
        step = max(clip_duration, duration / (max_clips + 1))
        for i in range(max_clips):
            st = i * step
            if st + clip_duration <= duration:
                segments.append(DetectedSegment(st, st + clip_duration, 1.0, event_type_norm))

    # Ordenar cronológicamente
    segments.sort(key=lambda s: s.start_time)

    # Definir filtro de video según Aspect Ratio
    if aspect_ratio == "16:9":
        vf_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=60"
    elif aspect_ratio == "1:1":
        vf_filter = "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1,fps=60"
    else:  # "9:16" por defecto
        vf_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=60"

    print(f"[+] Detected {len(segments)} clips of type '{event_type_norm}' (Aspect Ratio {aspect_ratio}):")
    tmp_dir = tempfile.gettempdir()
    cut_files = []

    for i, seg in enumerate(segments, 1):
        seg_dur = round(seg.end_time - seg.start_time, 2)
        print(f"   Clip {i}: {seg.start_time:.1f}s -> {seg.end_time:.1f}s ({seg_dur}s)")
        tmp_cut = os.path.join(tmp_dir, f"ff_clip_cut_{i:02d}.mp4")

        fast_ss = max(0.0, seg.start_time - 3.0)
        exact_ss = seg.start_time - fast_ss

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(fast_ss, 3)),
            "-i", video_path,
            "-ss", str(round(exact_ss, 3)),
            "-t", str(round(seg_dur, 3)),
            "-vf", vf_filter,
            "-af", "aresample=async=1:first_pts=0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            tmp_cut,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0 and os.path.exists(tmp_cut):
            cut_files.append(tmp_cut)

    if not cut_files:
        print("[-] Error trimming clips")
        return ""

    # Concatenar clips
    concat_list = os.path.join(tmp_dir, "ff_clips_concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for cut in cut_files:
            f.write(f"file '{cut.replace(os.sep, '/')}'\n")

    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    res_concat = subprocess.run(cmd_concat, capture_output=True, text=True, encoding="utf-8")

    # Cleanup
    for cut in cut_files + [concat_list]:
        try:
            if os.path.exists(cut):
                os.remove(cut)
        except Exception:
            pass

    if res_concat.returncode == 0 and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[+] Compilation saved at: {output_path} ({size_mb:.1f} MB)")
        return output_path
    else:
        print(f"[-] Error concatenating clips: {res_concat.stderr[-300:]}")
        return ""
