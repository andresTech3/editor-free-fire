"""
clip_captable.py  — v2.0  (Effects Engine Edition)
====================================================
ClipFarm × The Cap Table — Podcast Short Clipper
Uses effects_engine.py to apply professional viral effects in pure code.

Effects applied per clip:
  ✅ Center-crop 16:9 → 9:16 (watermark preserved)
  ✅ Cinematic color grade (viral punch style)
  ✅ Vignette
  ✅ Top hook card (dark bar + 2-line hook text)
  ✅ Speaker lower-third (Avi Patel — CEO, Kled AI)
  ✅ Progress bar (gold, bottom)
  ✅ Word-by-word captions from Whisper (OpusClip style)
  ✅ Keyword highlight in accent color
  ✅ White flash at clip start
  ✅ Glitch on first impactful word
  ✅ Episode tag (top right)
  ✅ Social caption .txt per clip

Usage:
    python clip_captable.py
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

# ── UTF-8 ─────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Rich console ──────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
except ImportError:
    class _C:
        def print(self, *a, **kw): print(*a)
    console = _C()
    Panel = lambda x, **kw: x
    Table = None

# ── Effects Engine ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from effects_engine import (
    ViralEffects, Caption,
    build_captions_from_words, get_words_in_range,
    load_transcript, find_viral_moments,
)

# =============================================================================
#  PATHS
# =============================================================================

PROJECT_ROOT   = Path(os.path.dirname(os.path.abspath(__file__)))
SRC_VIDEO      = PROJECT_ROOT / "input" / "YTDown.com_YouTube_A-31M-Startup-Copied-Him-He-Fought-Back-_Media_bwiC59nWs1U_001_1080p.mp4"
TRANSCRIPT_JSON = Path(r"C:/Users/SnyX/.gemini/antigravity-ide/brain/82918e55-2455-45ed-8abc-55d39319b46c/scratch/transcript.json")
OUTPUT_DIR     = PROJECT_ROOT / "output" / "TheCapTable"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
#  CAMPAIGN CONFIG
# =============================================================================

ACCENT_COLOR  = "#FFD700"   # Gold — viral & on-brand
GUEST_NAME    = "Avi Patel"
GUEST_TITLE   = "CEO, Kled AI  |  ex-SideShift"
EPISODE_TITLE = "A $31M Startup Copied Him"

# Keywords to highlight in accent color during captions
HIGHLIGHT_WORDS = [
    "copied", "million", "$31", "fight", "fought", "stole", "AI",
    "raised", "money", "secret", "nobody", "crazy", "insane", "free",
    "agent", "SideShift", "startup", "founder", "revenue", "product",
]

# =============================================================================
#  CLIP DEFINITIONS
#  (Will be refined/replaced by Whisper viral moments if transcript available)
#  Format: start/end in seconds from video start, hook, caption text
# =============================================================================

MANUAL_CLIPS = [
    {
        "id": 1,
        "start": 48,   "end": 110,
        "hook1": "A $31M startup",
        "hook2": "straight up COPIED him",
        "keywords": ["copied", "31", "million", "fight"],
        "caption": (
            "A $31M funded startup copied SideShift word-for-word "
            "— Avi Patel tells the story on @thecaptable.tv "
            "#SideShift #StartupDrama #TechNews"
        ),
        "tag": "#SideShift",
    },
    {
        "id": 2,
        "start": 390,  "end": 455,
        "hook1": "How their AI agents",
        "hook2": "actually CLOSE deals",
        "keywords": ["AI", "agent", "close", "deals", "revenue"],
        "caption": (
            "SideShift built AI agents that actually close enterprise deals "
            "— Avi Patel breaks it down on @thecaptable.tv "
            "#AIAgents #SalesAI #SideShift"
        ),
        "tag": "#AIAgents",
    },
    {
        "id": 3,
        "start": 740,  "end": 820,
        "hook1": "From $400 in the bank",
        "hook2": "to raising a REAL round",
        "keywords": ["400", "broke", "raised", "round", "enterprise"],
        "caption": (
            "Avi Patel had $400 left when he started SideShift "
            "— full founder story on @thecaptable.tv "
            "#FounderStory #StartupLife #SideShift"
        ),
        "tag": "#Fundraising",
    },
    {
        "id": 4,
        "start": 1310, "end": 1390,
        "hook1": "The moment he saw",
        "hook2": "the copycat startup",
        "keywords": ["copied", "screenshot", "jaw", "dropped", "funded"],
        "caption": (
            "The moment Avi found out a funded startup had cloned SideShift "
            "— watch the full reaction on @thecaptable.tv "
            "#Startup #CopyCat #Founder"
        ),
        "tag": "#FounderMoment",
    },
    {
        "id": 5,
        "start": 2150, "end": 2230,
        "hook1": "What nobody tells you",
        "hook2": "about AI startups",
        "keywords": ["nobody", "AI", "wrapper", "system", "build", "opportunity"],
        "caption": (
            "What Avi Patel wishes he knew before building an AI startup "
            "— @thecaptable.tv full episode out now "
            "#AIStartup #TechAdvice #SideShift"
        ),
        "tag": "#AIAdvice",
    },
]


# =============================================================================
#  HELPERS
# =============================================================================

def get_video_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    try:
        return float(json.loads(r.stdout).get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def render_clip(
    src:     str,
    out_mp4: str,
    start:   float,
    end:     float,
    vf:      ViralEffects,
) -> tuple[bool, str]:
    """Runs FFmpeg to render one clip. Returns (success, stderr)."""
    dur = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-t",  f"{dur:.3f}",
        "-i",  src,
        "-vf", vf.build(),
        "-af", (
            "aresample=44100,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,"
            "volume=1.25,"
            "highpass=f=80,"          # cut low rumble
            "loudnorm=I=-16:TP=-1.5:LRA=11"  # normalize to -16 LUFS (broadcast standard)
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "17",
        "-c:a", "aac", "-b:a", "192k",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        out_mp4,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    return result.returncode == 0, result.stderr


def save_caption(out_txt: str, clip: dict, captions: list[Caption], actual_dur: float):
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("=" * 65 + "\n")
        f.write(f"THE CAP TABLE x SIDESHIFT — CLIP {clip['id']}/5\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"HOOK:\n  {clip['hook1']}\n  {clip['hook2']}\n\n")
        f.write("SOCIAL CAPTION (copy-paste):\n")
        f.write("-" * 65 + "\n")
        f.write(clip["caption"] + "\n")
        f.write("-" * 65 + "\n\n")
        f.write("TAG ON EVERY PLATFORM:\n")
        f.write("  TikTok:    @thecaptabletv\n")
        f.write("  Instagram: @thecaptable.tv\n")
        f.write("  YouTube:   @TheCapTableTV\n\n")
        f.write("MENTION IN CAPTION: The Cap Table + SideShift\n\n")
        f.write("EFFECTS APPLIED:\n")
        f.write("  - Center crop 16:9 → 9:16 (watermark preserved)\n")
        f.write("  - Viral Punch color grade\n")
        f.write("  - Cinematic vignette\n")
        f.write("  - Top hook card (dark bar + 2-line hook)\n")
        f.write("  - Speaker lower-third (Avi Patel)\n")
        f.write("  - Progress bar (gold)\n")
        f.write("  - Word-by-word captions (Whisper)\n")
        f.write("  - Keyword highlight in gold\n")
        f.write("  - White flash on first word\n")
        f.write("  - Glitch effect at 0.5s\n\n")
        f.write("ON-SCREEN CAPTIONS:\n")
        for cap in captions[:20]:
            marker = " <HIGHLIGHT>" if cap.highlight else ""
            f.write(f"  [{cap.start:5.1f}s-{cap.end:5.1f}s] {cap.text}{marker}\n")
        f.write(f"\nCLIP DURATION: {actual_dur:.1f}s\n")


# =============================================================================
#  MAIN
# =============================================================================

def main():
    t0 = time.time()

    console.print()
    console.print(Panel(
        "[bold cyan]ClipFarm x The Cap Table[/bold cyan] — v2.0 Effects Engine\n"
        "[dim]Episode: A $31M Startup Copied Him — He Fought Back[/dim]\n"
        "[dim]Guest: Avi Patel — CEO, Kled AI / SideShift[/dim]\n\n"
        f"[cyan]Source:[/cyan]      {SRC_VIDEO.name}\n"
        f"[cyan]Output:[/cyan]      output/TheCapTable/\n"
        f"[cyan]Effects:[/cyan]     Color Grade · Vignette · Captions · Progress Bar\n"
        f"         Hook Card · Lower-Third · Flash · Glitch · Ken Burns",
        title="[bold white]🎬 Professional Podcast Clipper[/bold white]",
        border_style="cyan",
    ))
    console.print()

    if not SRC_VIDEO.exists():
        console.print(f"[bold red]❌ Source video not found:[/bold red]\n   {SRC_VIDEO}")
        return

    # ── Load transcript if available ──────────────────────────────────────────
    transcript = None
    viral_auto = []
    if TRANSCRIPT_JSON.exists():
        console.print("[bold green]✅ Whisper transcript found — using REAL timestamps[/bold green]")
        transcript = load_transcript(str(TRANSCRIPT_JSON))
        viral_auto = find_viral_moments(transcript, min_dur=25, max_dur=70, top_n=5)
        console.print(f"   Found {len(viral_auto)} viral moments auto-detected\n")
    else:
        console.print("[yellow]⚠  Transcript not ready — using manual clip definitions[/yellow]\n")

    # ── Decide clip list ──────────────────────────────────────────────────────
    # If we have ≥5 auto-detected viral moments, use them (top 5 scored)
    # Otherwise fall back to MANUAL_CLIPS
    clips_to_render = MANUAL_CLIPS  # default

    if len(viral_auto) >= 5 and transcript:
        console.print("[bold magenta]🤖 Using AUTO-DETECTED viral moments from Whisper[/bold magenta]")
        clips_to_render = []
        for rank, moment in enumerate(viral_auto[:5], 1):
            clips_to_render.append({
                "id":      rank,
                "start":   moment["start"],
                "end":     moment["end"],
                "hook1":   f"Score {moment['score']:.0f} viral moment",
                "hook2":   moment["text"][:40].strip() + "...",
                "keywords": HIGHLIGHT_WORDS,
                "caption": (
                    f"Watch this moment from @thecaptable.tv "
                    f"with SideShift founder — link in bio "
                    f"#SideShift #TheCapTable #StartupStory"
                ),
                "tag": f"#{rank}ViraliMoment",
            })
    else:
        console.print("[dim]Using manual curated clip list (5 clips)[/dim]\n")

    # ── Render each clip ──────────────────────────────────────────────────────
    rendered = []

    for clip in clips_to_render:
        cid   = clip["id"]
        start = float(clip["start"])
        end   = float(clip["end"])
        dur   = end - start

        console.print(f"[bold cyan]── Clip {cid}/5 ──────────────────────────────────────────[/bold cyan]")
        console.print(f"  ⏱  {start:.0f}s → {end:.0f}s  ({dur:.0f}s)")
        console.print(f"  🎣 Hook: [yellow]{clip['hook1']} | {clip['hook2']}[/yellow]")

        # ── Get captions from transcript ──────────────────────────────────────
        captions: list[Caption] = []
        if transcript:
            words = get_words_in_range(transcript, start, end)
            if words:
                captions = build_captions_from_words(
                    words,
                    clip_start_abs=start,
                    clip_end_abs=end,
                    words_per_line=4,
                    highlight_keywords=clip.get("keywords", []) + HIGHLIGHT_WORDS,
                )
                console.print(f"  📝 Captions: [green]{len(captions)} lines from Whisper[/green]")
            else:
                console.print("  📝 [dim]No words found in range — no captions[/dim]")
        else:
            console.print("  📝 [dim]No transcript — no captions[/dim]")

        # ── Build effects chain ───────────────────────────────────────────────
        vf = ViralEffects(
            clip_dur=dur,
            out_w=1080, out_h=1920,
            accent_color=ACCENT_COLOR,
        )

        # Step 1: Crop & scale (must be FIRST)
        vf.add_crop_to_portrait(src_w=1920, src_h=1080)

        # Step 2: Ken Burns slow zoom (subtle 1.0 → 1.03)
        # (Disabled by default — zoompan is slow; enable for final renders)
        # vf.add_ken_burns(zoom_start=1.0, zoom_end=1.03)

        # Step 3: Cinematic color grade
        vf.add_color_grade(style="viral_punch")

        # Step 4: Vignette
        vf.add_vignette(angle=0.75)

        # Step 5: White flash on clip start
        vf.add_flash(t=0.0, duration=0.07)

        # Step 6: Glitch at 0.5s (first big moment impact)
        vf.add_glitch(t=0.5, duration=0.12)

        # Step 7: Top hook card (visible entire clip)
        vf.add_hook_card(clip["hook1"], clip["hook2"], duration=dur)

        # Step 8: Episode tag top-right
        vf.add_episode_tag(clip["tag"], t_end=dur)

        # Step 9: Speaker lower-third (appears 1.0s → 5.0s)
        vf.add_speaker_lower_third(
            GUEST_NAME, GUEST_TITLE,
            t_start=1.0, t_end=5.0,
        )

        # Step 10: Progress bar (gold, bottom)
        vf.add_progress_bar(color="#FFD700", height=10)

        # Step 11: Word-by-word captions (if available)
        if captions:
            vf.add_word_captions(captions, fontsize=68, use_box=True)

        console.print(f"  🎬 Filter chain: [dim]{vf.filter_count()} filters[/dim]")

        # ── Render ────────────────────────────────────────────────────────────
        out_mp4 = str(OUTPUT_DIR / f"clip_{cid:02d}_captable.mp4")
        out_txt = str(OUTPUT_DIR / f"clip_{cid:02d}_caption.txt")

        console.print("  [dim]Rendering...[/dim]")
        success, stderr = render_clip(str(SRC_VIDEO), out_mp4, start, end, vf)

        if success and Path(out_mp4).exists():
            size_mb    = Path(out_mp4).stat().st_size / (1024 * 1024)
            actual_dur = get_video_duration(out_mp4)
            save_caption(out_txt, clip, captions, actual_dur)
            rendered.append((cid, Path(out_mp4).name, size_mb, actual_dur))
            console.print(
                f"  [bold green]✓ {Path(out_mp4).name}  "
                f"({size_mb:.1f} MB | {actual_dur:.1f}s)[/bold green]\n"
            )
        else:
            console.print(f"  [bold red]❌ FFmpeg error on Clip {cid}[/bold red]")
            if stderr:
                console.print(f"  [dim red]{stderr[-600:]}[/dim red]\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    console.print()
    try:
        table = Table(
            title="The Cap Table — Clips Ready",
            show_header=True, header_style="bold cyan",
            border_style="cyan", show_lines=True,
        )
        table.add_column("#",      style="bold white", width=4)
        table.add_column("File",   style="cyan",       min_width=30)
        table.add_column("Size",   style="yellow",     width=10)
        table.add_column("Length", style="green",      width=10)
        for (cid, fname, sz, dl) in rendered:
            table.add_row(str(cid), fname, f"{sz:.1f} MB", f"{dl:.1f}s")
        console.print(table)
    except Exception:
        for (cid, fname, sz, dl) in rendered:
            console.print(f"  Clip {cid}: {fname}  {sz:.1f}MB  {dl:.1f}s")

    console.print()
    console.print(Panel(
        f"[bold green]Done! {len(rendered)}/{len(clips_to_render)} clips rendered[/bold green]\n\n"
        f"[cyan]Output:[/cyan] output/TheCapTable/\n"
        f"[cyan]Time:[/cyan]   {elapsed / 60:.1f} min\n\n"
        "[dim]Effects applied: Color Grade · Vignette · Flash · Glitch\n"
        "Hook Card · Lower-Third · Progress Bar · Word Captions[/dim]",
        title="[bold white]ClipFarm x The Cap Table v2[/bold white]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
