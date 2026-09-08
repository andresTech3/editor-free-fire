import os
import sys
import json
import whisper
import subprocess

# Set utf-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

memes_dir = os.path.abspath(r"assets/Recurso video Freefire/PACK DE MEMES")
files = [f for f in sorted(os.listdir(memes_dir)) if f.endswith(".mp4") and not f.startswith(".")]

print(f"Loading Whisper model to index {len(files)} clips...")
model = whisper.load_model("tiny")

catalog = []
for i, f in enumerate(files):
    fp = os.path.join(memes_dir, f)
    # duration via ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", fp
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    dur = 0.0
    try:
        dur = round(float(res.stdout.strip()), 2)
    except:
        pass

    # Whisper transcribe
    try:
        t_res = model.transcribe(fp, fp16=False)
        speech_text = t_res.get("text", "").strip()
    except Exception as e:
        speech_text = ""

    item = {
        "id": i + 1,
        "filename": f,
        "duration": dur,
        "speech": speech_text,
    }
    catalog.append(item)
    print(f"[{i+1}/{len(files)}] {f} ({dur}s): \"{speech_text}\"")

out_path = os.path.abspath(r"core/pack_de_memes_transcripts.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(catalog)} items to {out_path}")
