import os
import subprocess
import json

memes_dir = os.path.abspath(r"assets/Recurso video Freefire/PACK DE MEMES")
files = [f for f in sorted(os.listdir(memes_dir)) if f.endswith(".mp4")]

print(f"Analyzing {len(files)} files in PACK DE MEMES...")

# Let's inspect each clip: duration, audio presence
results = []
for f in files:
    fp = os.path.join(memes_dir, f)
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
        "-of", "json", fp
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    dur = 0.0
    w, h = 0, 0
    has_audio = False
    try:
        data = json.loads(res.stdout)
        dur = float(data.get("format", {}).get("duration", 0))
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                w = s.get("width", 0)
                h = s.get("height", 0)
            elif s.get("codec_type") == "audio":
                has_audio = True
    except Exception as e:
        pass
    results.append({"file": f, "dur": dur, "res": f"{w}x{h}", "audio": has_audio})

print(f"Sample 10: {results[:10]}")
