import os
import subprocess
import json
from pathlib import Path
import cv2

ROOT = Path("assets/Recurso video Freefire")

def probe_file(p):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:stream_tags=rotate:side_data=rotation",
        "-of", "json", str(p)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None
        st = streams[0]
        w = st.get("width")
        h = st.get("height")
        tags = st.get("tags", {})
        rot = tags.get("rotate")
        side_data_list = st.get("side_data_list", [])
        for sd in side_data_list:
            if "rotation" in sd:
                rot = sd["rotation"]
        return {"width": w, "height": h, "rotation": rot}
    except Exception as e:
        return None

def main():
    print("--- GAMEPLAY VIDEOS ---")
    for f in (ROOT / "free fire jugadas").glob("*.*"):
        if f.suffix.lower() in [".mp4", ".mov"]:
            info = probe_file(f)
            print(f"{f.name}: {info}")

    print("\n--- IMAGES ---")
    for f in (ROOT / "Imagenes").glob("*.*"):
        if f.suffix.lower() in [".jpg", ".png", ".jpeg"]:
            img = cv2.imread(str(f))
            if img is not None:
                h, w = img.shape[:2]
                print(f"{f.name}: {w}x{h}")

if __name__ == "__main__":
    main()
