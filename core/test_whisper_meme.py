import os
import whisper

model = whisper.load_model("tiny")
memes_dir = os.path.abspath(r"assets/Recurso video Freefire/PACK DE MEMES")
files = [f for f in sorted(os.listdir(memes_dir)) if f.endswith(".mp4") and not f.startswith(".")][:5]

for f in files:
    fp = os.path.join(memes_dir, f)
    res = model.transcribe(fp, fp16=False)
    print(f, "-->", res.get("text", "").strip())
