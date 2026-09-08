"""
core/asset_investigator.py — Autonomous Asset Investigator & Classifier
========================================================================
Analyzes custom uploaded resource folders (or project default assets):
- Videos: Dimensions, aspect ratio, duration, orientation rotation needed, green-screen chroma.
- Images: Dimensions, alpha channel transparency, visual categories.
- Audios: Duration, channels, voiceover vs music vs sfx classification.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
from PIL import Image

def get_media_info_fast(filepath: str) -> Dict[str, Any]:
    """Retrieves stream and format information via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", filepath
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
        return json.loads(res.stdout) if res.stdout else {}
    except Exception:
        return {}

def detect_green_screen_ratio(video_path: str) -> bool:
    """Checks if a video clip contains green-screen chroma backdrop."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return False
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (35, 50, 50), (85, 255, 255))
        ratio = np.sum(mask > 0) / (frame.shape[0] * frame.shape[1])
        return ratio >= 0.12
    except Exception:
        return False

def check_image_transparency(img_path: str) -> bool:
    """Checks if a PNG image contains native alpha transparency."""
    try:
        with Image.open(img_path) as im:
            if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                alpha = im.convert('RGBA').split()[-1]
                return alpha.getextrema()[0] < 250
    except Exception:
        pass
    return False

class AssetInvestigator:
    """
    Scans a folder and automatically categorizes all media assets for professional video editing.
    """

    VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
    AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir).resolve()

    def investigate(self) -> Dict[str, Any]:
        """
        Recursively scans directory and compiles an intelligent asset report.
        """
        report = {
            "root": str(self.target_dir),
            "total_files": 0,
            "gameplays": [],
            "memes": [],
            "images": [],
            "audios": [],
            "summary": {
                "gameplay_count": 0,
                "memes_count": 0,
                "images_count": 0,
                "audios_count": 0,
                "green_screen_memes_count": 0,
                "transparent_images_count": 0
            }
        }

        if not self.target_dir.exists():
            return report

        all_files = [p for p in self.target_dir.rglob("*") if p.is_file() and not p.name.startswith(".")]
        report["total_files"] = len(all_files)

        for file_path in all_files:
            ext = file_path.suffix.lower()
            rel_name = file_path.name
            path_str = str(file_path)

            if ext in self.VIDEO_EXTS:
                self._classify_video(path_str, rel_name, report)
            elif ext in self.IMAGE_EXTS:
                self._classify_image(path_str, rel_name, report)
            elif ext in self.AUDIO_EXTS:
                self._classify_audio(path_str, rel_name, report)

        report["summary"]["gameplay_count"] = len(report["gameplays"])
        report["summary"]["memes_count"] = len(report["memes"])
        report["summary"]["images_count"] = len(report["images"])
        report["summary"]["audios_count"] = len(report["audios"])
        report["summary"]["green_screen_memes_count"] = sum(1 for m in report["memes"] if m["is_green_screen"])
        report["summary"]["transparent_images_count"] = sum(1 for img in report["images"] if img["is_transparent"])

        return report

    def _classify_video(self, path: str, name: str, report: Dict[str, Any]):
        info = get_media_info_fast(path)
        v_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
        w = int(v_stream.get("width", 0))
        h = int(v_stream.get("height", 0))
        dur = float(info.get("format", {}).get("duration", 0.0))

        # Check rotation metadata
        rot = None
        side_data = v_stream.get("side_data_list", [])
        for sd in side_data:
            if "rotation" in sd:
                rot = sd["rotation"]
        if rot is None and "tags" in v_stream and "rotate" in v_stream["tags"]:
            try: rot = int(v_stream["tags"]["rotate"])
            except Exception: pass

        is_green = detect_green_screen_ratio(path)
        lower_path = path.lower()

        # Is this a meme or a gameplay clip?
        is_meme = "meme" in lower_path or is_green or ("auron" in lower_path or "chavo" in lower_path or "wasted" in lower_path)
        is_intro = "intro" in lower_path

        # Check orientation
        # Raw files recorded horizontally inside portrait container (1290x2796)
        is_sideways = (w == 1290 and h == 2796 and rot is None) or (w == 720 and h == 1280 and "sideway" in lower_path)
        rot_filter = "transpose=2," if is_sideways else ""

        entry = {
            "path": path,
            "filename": name,
            "width": w,
            "height": h,
            "duration": round(dur, 2),
            "rotation": rot,
            "is_sideways": is_sideways,
            "rot_filter": rot_filter,
            "is_green_screen": is_green,
            "is_intro": is_intro
        }

        if is_meme:
            report["memes"].append(entry)
        else:
            report["gameplays"].append(entry)

    def _classify_image(self, path: str, name: str, report: Dict[str, Any]):
        try:
            with Image.open(path) as im:
                w, h = im.size
        except Exception:
            w, h = 0, 0

        is_trans = check_image_transparency(path)
        lower_name = name.lower()

        cat = "general"
        if "diamant" in lower_name: cat = "diamonds"
        elif "asesoria" in lower_name or "dpi" in lower_name: cat = "dpi"
        elif "sencibilidad" in lower_name or "sensi" in lower_name: cat = "sensitivity"
        elif "codigo" in lower_name or "headshot" in lower_name: cat = "web_banner"
        elif "arma" in lower_name or "dragon" in lower_name or "groza" in lower_name or "m16" in lower_name: cat = "weapon"
        elif "top" in lower_name or "maestro" in lower_name or "torneo" in lower_name: cat = "rank"
        elif "like" in lower_name or "sub" in lower_name: cat = "cta"

        report["images"].append({
            "path": path,
            "filename": name,
            "width": w,
            "height": h,
            "is_transparent": is_trans,
            "category": cat
        })

    def _classify_audio(self, path: str, name: str, report: Dict[str, Any]):
        info = get_media_info_fast(path)
        dur = float(info.get("format", {}).get("duration", 0.0))
        lower_name = name.lower()

        atype = "audio"
        if "sfx" in lower_name or "ding" in lower_name or "boom" in lower_name or "punch" in lower_name:
            atype = "sfx"
        elif "music" in lower_name or "phonk" in lower_name or "bgm" in lower_name:
            atype = "music"
        else:
            atype = "voiceover"

        report["audios"].append({
            "path": path,
            "filename": name,
            "duration": round(dur, 2),
            "type": atype
        })

if __name__ == "__main__":
    import sys
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "assets/Recurso video Freefire/free fire jugadas"
    inv = AssetInvestigator(test_dir)
    res = inv.investigate()
    print("Summary:", res["summary"])
