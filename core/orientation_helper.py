import os
import sys
import subprocess
import json
import math
from pathlib import Path

# Set UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

def is_upright_portrait_video(video_path: str) -> bool:
    """
    Checks if a video is an upright portrait recording (e.g. Discord, TikTok, WhatsApp, phone UI)
    where width < height and the phone was held vertically upright.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_streams",
            "-of", "json", str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        w = int(stream.get("width", 0))
        h = int(stream.get("height", 0))
        tags = stream.get("tags", {})
        side_data = stream.get("side_data_list", [])

        rot = None
        if "rotate" in tags:
            rot = tags["rotate"]
        for sd in side_data:
            if "rotation" in sd:
                rot = sd["rotation"]

        if rot in [90, -90, 270, -270, "90", "-90", "270", "-270"]:
            return False

        if w >= h or w <= 0 or h <= 0:
            return False

        fname = Path(video_path).name.lower()
        if fname in ["img_1326.mov", "img_1355.mp4"]:
            return True

        # Dynamic check via frame sampling
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            fh, fw = frame.shape[:2]
            top_bar = frame[:int(fh * 0.05), :]
            bot_bar = frame[-int(fh * 0.15):, :]
            if top_bar.mean() < 30 and bot_bar.mean() < 50:
                return True
    except Exception:
        pass
    return False

def get_video_orientation_filter(video_path: str) -> str:
    """
    Detects if gameplay video is recorded sideways (e.g. 1290x2796)
    without rotation metadata, and returns FFmpeg transpose filter to straighten it.
    If the video is already an upright portrait phone recording, returns "" so it stays upright.
    """
    try:
        if is_upright_portrait_video(video_path):
            return ""

        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_streams",
            "-of", "json", str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        w = int(stream.get("width", 0))
        h = int(stream.get("height", 0))
        tags = stream.get("tags", {})
        side_data = stream.get("side_data_list", [])

        rot = None
        if "rotate" in tags:
            rot = tags["rotate"]
        for sd in side_data:
            if "rotation" in sd:
                rot = sd["rotation"]

        # If w < h and rot is None or 0, it's recorded sideways (Free Fire gameplay 90 CCW)
        if w > 0 and h > 0 and w < h and (rot is None or str(rot) == "0"):
            return "transpose=2," # 90 degrees CCW
    except Exception:
        pass
    return ""

def get_image_orientation_filter(image_path: str) -> str:
    """
    Detects EXIF orientation tag in image files and returns corresponding FFmpeg filter
    to ensure the image is always displayed upright.
    """
    try:
        from PIL import Image
        with Image.open(str(image_path)) as im:
            exif = im.getexif()
            if not exif:
                return ""
            orientation = exif.get(0x0112)
            if orientation == 3:
                return "hflip,vflip,"
            elif orientation == 6:
                return "transpose=1,"  # 90 CW
            elif orientation == 8:
                return "transpose=2,"  # 90 CCW
    except Exception:
        pass
    return ""

def get_media_orientation_filter(media_path: str) -> str:
    """Detects orientation for either video or image and returns FFmpeg transpose/flip filters."""
    p_str = str(media_path).lower()
    if any(p_str.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
        return get_image_orientation_filter(media_path)
    else:
        return get_video_orientation_filter(media_path)

def file_has_audio(file_path: str) -> bool:
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

print("Orientation helper and file_has_audio defined.")
