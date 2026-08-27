"""
render_captable_final.py
========================
Usa la transcripcion real de Whisper para encontrar los mejores
momentos virales del episodio The Cap Table y renderizar 5 Shorts
con todos los efectos profesionales del motor viraleditor.
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from viraleditor.studio   import Studio, CampaignConfig
from viraleditor.presets  import Preset

# ── Paths ──────────────────────────────────────────────────────────────────────
SRC_VIDEO      = "input/YTDown.com_YouTube_A-31M-Startup-Copied-Him-He-Fought-Back-_Media_bwiC59nWs1U_001_1080p.mp4"
TRANSCRIPT_JSON = r"C:/Users/SnyX/.gemini/antigravity-ide/brain/82918e55-2455-45ed-8abc-55d39319b46c/scratch/transcript.json"
AUDIO_MP3      = r"C:/Users/SnyX/.gemini/antigravity-ide/brain/82918e55-2455-45ed-8abc-55d39319b46c/scratch/captable_audio.mp3"

# ── Campaign Config ─────────────────────────────────────────────────────────────
cfg = CampaignConfig(
    campaign_name  = "TheCapTable",
    preset         = "podcast_viral",
    clips          = 5,
    videos         = [SRC_VIDEO],
    output_dir     = "output/TheCapTable",
    guest_name     = "Avi Patel",
    host_name      = "CEO, Kled AI  |  SideShift",
    client_tag     = "SideShift",
    mention_name   = "SideShift",
    tiktok_handle  = "@thecaptabletv",
    ig_handle      = "@thecaptable.tv",
    yt_handle      = "@TheCapTableTV",
    hashtags       = "#shorts #startup #ai #fyp #thecaptable #sideshift",
    accent_color   = "#FFD700",
    whisper_model  = "base",
    language       = "en",
    min_clip_dur   = 22.0,
    max_clip_dur   = 70.0,
    words_per_line = 4,
    highlight_kw   = [
        "copied", "million", "31", "fight", "fought",
        "AI", "agent", "raised", "crazy", "insane",
        "secret", "nobody", "free", "startup", "founder",
        "revenue", "product", "copied", "stole", "lawsuit",
    ],
)

# ── Progress callback ──────────────────────────────────────────────────────────
def progress(msg: str, pct: float):
    bar_len = 30
    filled  = int(bar_len * pct)
    bar     = "█" * filled + "░" * (bar_len - filled)
    print(f"  [{bar}] {pct*100:.0f}%  {msg}")

# ── Run ────────────────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("  ClipFarm × The Cap Table — Rendering 5 Viral Shorts")
print("  Episode: A $31M Startup Copied Him — He Fought Back")
print("  Guest:   Avi Patel (CEO, Kled AI / SideShift)")
print("=" * 65)
print()

# Pre-copy transcript to output dir so Studio finds it as cache
out_dir = Path("output/TheCapTable")
out_dir.mkdir(parents=True, exist_ok=True)

# Copy transcript cache to output dir where Studio looks for it
import shutil
cached = out_dir / "_transcript_YTDown.com_YouTube_A-31M-Startup-Copied-Him-H.json"
if Path(TRANSCRIPT_JSON).exists() and not cached.exists():
    shutil.copy(TRANSCRIPT_JSON, cached)
    print(f"  Copied transcript cache → {cached.name}")

# Copy audio to output dir as well for Studio's audio extractor
audio_cached = out_dir / "_audio_YTDown.com_YouTube_A-31M-Startup-Copied-Him-He-.mp3"
if Path(AUDIO_MP3).exists() and not audio_cached.exists():
    shutil.copy(AUDIO_MP3, audio_cached)
    print(f"  Copied audio cache → {audio_cached.name}")

print()
t0 = time.time()

try:
    studio  = Studio(cfg, progress_cb=progress)
    results = studio.run()

    print()
    print("=" * 65)
    print(f"  DONE — {len(results)}/5 clips created in {(time.time()-t0)/60:.1f} min")
    print("=" * 65)
    for r in results:
        print(f"  Clip {r.clip_num:02d}: {Path(r.output_mp4).name}  {r.duration:.1f}s  {r.size_mb:.1f}MB")
    print()
    print(f"  Output: {out_dir.resolve()}")
    print()

except Exception as e:
    import traceback
    print(f"\n  ERROR: {e}")
    traceback.print_exc()
