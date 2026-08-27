"""
render_captable_v2.py
=====================
Renderiza 5 clips profesionales del episodio The Cap Table
usando timestamps REALES del transcript de Whisper.
Recorta a ventanas de 35-50s (ideal para Shorts virales).
"""
import sys, os, json, time, subprocess, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from viraleditor.clip      import Clip, Caption
from viraleditor.renderer  import Renderer
from viraleditor.transcription import WhisperClient

# ── Paths ──────────────────────────────────────────────────────────────────────
SRC_VIDEO  = "input/YTDown.com_YouTube_A-31M-Startup-Copied-Him-He-Fought-Back-_Media_bwiC59nWs1U_001_1080p.mp4"
TRANSCRIPT = r"C:/Users/SnyX/.gemini/antigravity-ide/brain/82918e55-2455-45ed-8abc-55d39319b46c/scratch/transcript.json"
OUTPUT_DIR = Path("output/TheCapTable")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Real viral clips (from Whisper analysis, trimmed to 35-50s windows) ────────
# Each clip picks the most impactful 35-50 seconds within the detected window
CLIPS = [
    {
        "id":    1,
        "start": 635.0,   # "You raised I think what 9 million total for Kled?"
        "end":   675.0,   # 40s — fundraising topic
        "hook1": "He raised $9M for",
        "hook2": "his AI startup Kled",
        "kw":    ["raised", "million", "9", "team", "Kled"],
        "tiktok":    "This founder raised $9M after pivoting from SideShift 👀 @thecaptabletv",
        "ig":        "From SideShift to Kled AI — Avi Patel raised $9M to build AI agents @thecaptable.tv",
        "yt":        "Avi Patel — Raising $9M for Kled AI | The Cap Table @TheCapTableTV",
        "tags":      "#startup #founder #ai #fundraising #thecaptable #sideshift",
    },
    {
        "id":    2,
        "start": 877.0,   # "I still greatly respect that guy..."
        "end":   917.0,   # 40s — conflict/drama about the copycat
        "hook1": "He RESPECTED the guy",
        "hook2": "who copied his startup",
        "kw":    ["respect", "guy", "copied", "won't", "talk"],
        "tiktok":    "He found out someone cloned his startup... and still respected them 😤 @thecaptabletv",
        "ig":        "The SideShift founder's reaction when his startup was copied — @thecaptable.tv",
        "yt":        "When your startup gets copied — Avi Patel's reaction | The Cap Table @TheCapTableTV",
        "tags":      "#startup #drama #founder #sideshift #thecaptable",
    },
    {
        "id":    3,
        "start": 1078.0,  # "I don't even know what the word CA was..."
        "end":   1120.0,  # 42s — legal/conflict moment
        "hook1": "He didn't even know",
        "hook2": "what a CA was",
        "kw":    ["CA", "legal", "know", "what", "happened"],
        "tiktok":    "A first-time founder facing legal threats — this is wild 👀 @thecaptabletv",
        "ig":        "First-time founder vs legal drama — Avi Patel on @thecaptable.tv",
        "yt":        "First-time founder faces legal battle | The Cap Table @TheCapTableTV",
        "tags":      "#founder #startup #legal #thecaptable #sideshift",
    },
    {
        "id":    4,
        "start": 1432.0,  # "Like Bobby runs Duke. They raised like 20 million..."
        "end":   1472.0,  # 40s — competitive landscape
        "hook1": "His competitor raised",
        "hook2": "$20M+ and he had nothing",
        "kw":    ["million", "raised", "compete", "Duke", "Bobby"],
        "tiktok":    "His competitor had $20M... he had basically nothing 💀 @thecaptabletv",
        "ig":        "Competing against a $20M funded startup with zero capital — @thecaptable.tv",
        "yt":        "Competing with zero money vs $20M funding | The Cap Table @TheCapTableTV",
        "tags":      "#startup #competition #founder #thecaptable #sideshift",
    },
    {
        "id":    5,
        "start": 2322.0,  # "Oh no way, way worse. Oh my God. And it's crazy..."
        "end":   2365.0,  # 43s — emotional / reaction moment
        "hook1": "It got way worse",
        "hook2": "than you think",
        "kw":    ["worse", "crazy", "God", "insane", "agree"],
        "tiktok":    "It got way worse than anyone expected 😱 @thecaptabletv #SideShift",
        "ig":        "The moment things got way worse for SideShift — full story @thecaptable.tv",
        "yt":        "Things got way worse than expected — Avi Patel | The Cap Table @TheCapTableTV",
        "tags":      "#startup #drama #founder #thecaptable #sideshift",
    },
]

# ── Setup ──────────────────────────────────────────────────────────────────────
renderer  = Renderer(gpu=False)
whisper_c = WhisperClient()
transcript = whisper_c.transcribe(SRC_VIDEO, cache_path=TRANSCRIPT)

ACCENT    = "#FFD700"
GUEST     = "Avi Patel"
GUEST_TTL = "CEO, Kled AI  |  ex-SideShift"

print()
print("=" * 65)
print("  ClipFarm x The Cap Table — 5 Professional Shorts")
print("=" * 65)
t0 = time.time()

rendered = []
for clip_def in CLIPS:
    cid   = clip_def["id"]
    start = clip_def["start"]
    end   = clip_def["end"]
    dur   = end - start

    print(f"\n  ── Clip {cid}/5 ──────────────────────────────────────")
    print(f"  Hook: {clip_def['hook1']} / {clip_def['hook2']}")
    print(f"  Range: {start:.0f}s → {end:.0f}s  ({dur:.0f}s)")

    # Get real word captions from Whisper
    words = whisper_c.words_in_range(transcript, start, end)
    captions: list[Caption] = []
    kws = [k.lower() for k in clip_def.get("kw", [])]
    i = 0
    while i < len(words):
        chunk = words[i : i + 4]
        text  = " ".join(t.word for t in chunk)
        t0_c  = max(0.0, chunk[0].start  - start)
        t1_c  = max(0.0, chunk[-1].end   - start)
        is_hl = any(k in text.lower() for k in kws)
        captions.append(Caption(text=text, start=t0_c, end=t1_c, highlight=is_hl))
        i += 4
    print(f"  Captions: {len(captions)} lines from Whisper")

    # Build clip with effects based on 10M+ Ultra-Viral Engine
    clip = Clip(SRC_VIDEO, start=start, end=end)

    # Layer 0 — Ultra-Dynamic Timeline Multi-Layout (Within Single Short)
    pov_text = f"{clip_def['hook1']} {clip_def['hook2']}"
    clip.layout.auto_dynamic_mix(
        top_x=1380, bottom_x=420,
        divider_color=ACCENT, pov_text=pov_text
    )

    # Layer 1 — Color Grade & Vignette
    clip.fx.color_grade("viral_punch")
    clip.fx.vignette(0.75)

    # Layer 3 — CapCut Ultra FX & Transitions
    clip.fx.flash(at=0.0, dur=0.07)
    from viraleditor.effects.capcut_pack import CapCutFXPack
    if cid == 2 or cid == 5:
        CapCutFXPack.light_leak(clip, at=1.5, dur=0.25)
    if cid == 3 or cid == 5:
        CapCutFXPack.glitch_shake(clip, at=0.5, dur=0.20)

    # Emoji Popups (10M+ Retention Boosters)
    if cid == 1:
        CapCutFXPack.emoji_popup(clip, "💰", at=2.0, dur=1.2)
    elif cid == 2:
        CapCutFXPack.emoji_popup(clip, "😤", at=2.5, dur=1.2)
    elif cid == 3:
        CapCutFXPack.emoji_popup(clip, "🚨", at=2.0, dur=1.2)
    elif cid == 4:
        CapCutFXPack.emoji_popup(clip, "📈", at=2.0, dur=1.2)
    elif cid == 5:
        CapCutFXPack.emoji_popup(clip, "😱", at=2.0, dur=1.2)

    # Layer 4 — Overlay: hook card, progress bar, lower-third, episode tag
    clip.text.hook_card(clip_def["hook1"], clip_def["hook2"], accent=ACCENT)
    clip.text.progress_bar(color=ACCENT, height=10)
    clip.text.lower_third(GUEST, GUEST_TTL, t0=1.0, t1=5.5, accent=ACCENT)
    clip.text.episode_tag("#TheCapTable", dur=dur)

    # Layer 5 — Captions
    if captions:
        clip.text.word_captions(captions, fontsize=68, accent=ACCENT, use_box=True)

    print(f"  Filters: {clip.filter_count()}")

    out_mp4 = str(OUTPUT_DIR / f"clip_{cid:02d}_captable.mp4")
    out_txt = str(OUTPUT_DIR / f"clip_{cid:02d}_social_copy.txt")

    print(f"  Rendering → {Path(out_mp4).name}...")
    ok, stderr = renderer.render(
        src=SRC_VIDEO, out=out_mp4,
        start=start, duration=dur,
        vf=clip._fc,
        crf=17, audio_vol=1.25,
    )

    if ok and Path(out_mp4).exists():
        size_mb = Path(out_mp4).stat().st_size / (1024 * 1024)
        actual_dur = renderer.probe_duration(out_mp4)
        rendered.append((cid, Path(out_mp4).name, size_mb, actual_dur))
        print(f"  OK  {Path(out_mp4).name}  {actual_dur:.1f}s  {size_mb:.1f}MB")

        # Save social copy
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("=" * 65 + "\n")
            f.write(f"  THE CAP TABLE x SIDESHIFT — CLIP {cid}/5\n")
            f.write("=" * 65 + "\n\n")
            f.write(f"HOOK:\n  Line 1: {clip_def['hook1']}\n  Line 2: {clip_def['hook2']}\n\n")
            f.write("-" * 65 + "\n")
            f.write("TIKTOK  (tag: @thecaptabletv)\n")
            f.write("-" * 65 + "\n")
            f.write(clip_def["tiktok"] + "\n" + clip_def["tags"] + "\n\n")
            f.write("-" * 65 + "\n")
            f.write("INSTAGRAM  (tag: @thecaptable.tv)\n")
            f.write("-" * 65 + "\n")
            f.write(clip_def["ig"] + "\n" + clip_def["tags"] + "\n\n")
            f.write("-" * 65 + "\n")
            f.write("YOUTUBE  (tag: @TheCapTableTV)\n")
            f.write("-" * 65 + "\n")
            f.write(clip_def["yt"] + "\n" + clip_def["tags"] + "\n\n")
            f.write(f"CLIP DURATION: {actual_dur:.1f}s\n")
            f.write(f"ON-SCREEN CAPTIONS: {len(captions)} lines (from Whisper)\n\n")
            f.write("REMEMBER TO TAG:\n")
            f.write("  TikTok:    @thecaptabletv\n")
            f.write("  Instagram: @thecaptable.tv\n")
            f.write("  YouTube:   @TheCapTableTV\n")
            f.write("  Mention:   SideShift (in every caption)\n")
        print(f"  Social copy → {Path(out_txt).name}")
    else:
        print(f"  FAIL  FFmpeg error:")
        if stderr:
            print(f"  {stderr[-400:]}")

elapsed = time.time() - t0
print()
print("=" * 65)
print(f"  DONE — {len(rendered)}/5 clips in {elapsed/60:.1f} min")
print("=" * 65)
for cid, fname, sz, dl in rendered:
    print(f"  {cid:02d}  {fname}  {dl:.1f}s  {sz:.1f}MB")
print()
print(f"  Output: {OUTPUT_DIR.resolve()}")
