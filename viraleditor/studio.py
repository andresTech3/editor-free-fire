"""
viraleditor/studio.py
=====================
Motor principal de producción — procesa videos de inicio a fin.

Flujo:
  1. Recibe lista de videos + configuración de campaña
  2. Extrae audio y transcribe con Whisper
  3. Detecta los mejores momentos virales
  4. Aplica el preset de efectos a cada momento
  5. Renderiza los Shorts con FFmpeg
  6. Genera el copy de redes sociales por clip
  7. Reporta progreso via callback (para GUI)

Uso programático:
    studio = Studio(
        videos=["video1.mp4", "video2.mp4"],
        campaign="TheCapTable",
        preset=Preset.PODCAST_VIRAL,
        clips=5,
        output_dir="output/TheCapTable",
        progress_cb=my_callback,
    )
    results = studio.run()
"""

from __future__ import annotations
import os
import re
import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field

from .clip       import Clip, Caption
from .renderer   import Renderer
from .analyzer   import VoiceAnalyzer, ViralMoment
from .presets    import PresetConfig, get_preset, Preset, PRESETS
from .transcription import WhisperClient

__all__ = ["Studio", "ClipResult", "CampaignConfig"]


# ─────────────────────────────────────────────────────────────────────────────
#  SOCIAL COPY GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

_HOOK_WORDS = {
    "copied", "million", "billion", "fight", "raised", "fired", "quit",
    "secret", "crazy", "insane", "nobody", "stole", "lawsuit", "betrayed",
    "free", "never", "always", "first", "only", "worst", "best",
}

def _extract_keywords_and_hashtags(text: str, campaign_name: str, preset_name: str) -> tuple[list[str], str]:
    """Extract key topic words from spoken text and build optimized hashtags."""
    words = [w.strip(".,!?\"'()[]{}").lower() for w in text.split() if len(w) > 3]
    stopwords = {
        "para", "como", "esta", "esto", "este", "estos", "estas", "pero", "sobre",
        "hacer", "hace", "hacerlo", "todo", "toda", "todos", "todas", "donde", "cuando",
        "quien", "porque", "entonces", "luego", "bien", "tambien", "tenia", "tienen",
        "that", "this", "with", "from", "they", "them", "what", "when", "where", "have",
        "been", "would", "could", "should", "about", "there", "their", "will", "just",
    }
    keywords = [w for w in words if w not in stopwords]

    tags = set()
    text_lower = text.lower()
    camp_lower = campaign_name.lower()

    # Gaming keywords
    if any(k in text_lower or k in camp_lower for k in ["kill", "racha", "eliminacion", "game", "free fire", "cod", "pubg", "fortnite", "clutch", "headshot", "disparo"]):
        tags.update(["#gaming", "#gamer", "#gameplay", "#headshot", "#clutch", "#highlights", "#shorts"])
        if "free fire" in camp_lower or "free fire" in text_lower:
            tags.update(["#freefire", "#freefirelatam", "#freefireclips", "#freefirehighlight"])
        elif "cod" in text_lower or "warzone" in text_lower:
            tags.update(["#callofduty", "#codm", "#warzone"])
    # Business / Startup / Money
    elif any(k in text_lower for k in ["million", "billion", "raised", "funding", "startup", "ai", "money", "dinero", "empresa", "negocio", "invertir"]):
        tags.update(["#negocios", "#emprendimiento", "#startup", "#dinero", "#inversiones", "#finanzas", "#ia", "#shorts"])
    # Reaction / Comedy
    elif any(k in text_lower for k in ["lmao", "lol", "wtf", "omg", "risa", "gracioso", "humor"]):
        tags.update(["#humor", "#risas", "#comedia", "#viral", "#reaccion", "#clips", "#shorts"])
    else:
        tags.update(["#viral", "#trending", "#fyp", "#foryou", "#shorts"])

    # Add top extracted keywords as hashtags
    for kw in keywords[:4]:
        if len(kw) >= 4 and kw.isalnum():
            tags.add(f"#{kw}")

    hashtags_str = " ".join(list(tags)[:10])
    return keywords, hashtags_str


def _build_social_copy(
    moment:       ViralMoment,
    campaign:     "CampaignConfig",
    clip_num:     int,
    accent_words: list[str],
) -> dict[str, str]:
    """Generate platform-optimized titles, descriptions, and hashtags with video keywords."""
    raw_text = moment.text.strip()
    clean_text = re.sub(r'\s+', ' ', raw_text)
    snippet = clean_text[:140]

    name       = campaign.campaign_name
    preset     = campaign.preset
    guest      = campaign.guest_name or ""
    mention    = campaign.mention_name or ""

    tiktok_handle = campaign.tiktok_handle or "@viralstudio"
    ig_handle     = campaign.ig_handle     or "@viralstudio.tv"
    yt_handle     = campaign.yt_handle     or "@ViralStudio"

    keywords, dynamic_tags = _extract_keywords_and_hashtags(clean_text, name, preset)
    base_tags = campaign.hashtags.strip() if campaign.hashtags else ""
    all_tags  = f"{base_tags} {dynamic_tags}".strip()
    unique_tags = " ".join(dict.fromkeys(all_tags.split()))

    # Build headline
    if snippet:
        first_sentence = clean_text.split('.')[0].strip()
        hook_headline  = first_sentence if len(first_sentence) < 60 else first_sentence[:55] + "..."
    else:
        hook_headline  = f"{name} — Moment {clip_num}"

    # 1. TIKTOK COPY
    if guest:
        tiktok_lead = f"🔥 {guest} revela esto en {tiktok_handle}: \"{hook_headline}\""
    elif "gaming" in str(preset).lower():
        tiktok_lead = f"🎮 ¡MIRA ESTA JUGADA! 💥 \"{hook_headline}\" en {name}"
    else:
        tiktok_lead = f"😱 \"{hook_headline}\" — No te pierdas esto en {tiktok_handle}"


    if mention:
        tiktok_lead += f" (vía {mention})"

    tiktok_copy = f"{tiktok_lead}\n\n{unique_tags}"

    # 2. INSTAGRAM REELS COPY
    if guest:
        ig_header = f"💬 {guest} en {ig_handle}:"
    else:
        ig_header = f"🔥 Momento imperdible de {name}:"

    ig_copy = (
        f"{ig_header}\n"
        f"\"{snippet}\"\n\n"
        f"👇 ¿Qué opinas de esto? Déjalo en los comentarios.\n"
        f"📌 Sigue a {ig_handle} para más contenido diario.\n\n"
        f"{unique_tags}"
    )

    # 3. YOUTUBE SHORTS COPY
    yt_title = f"{hook_headline[:65]} | {name} #{clip_num}"
    yt_copy = (
        f"🎬 TÍTULO SUGERIDO: {yt_title}\n\n"
        f"DESCRIPCIÓN:\n"
        f"Momentos clave de {name}. Escucha la conversación completa en el canal.\n\n"
        f"📌 Transcripción del momento:\n"
        f"\"{clean_text}\"\n\n"
        f"🔔 Suscríbete a {yt_handle} para no perderte ningún episodio.\n\n"
        f"{unique_tags}"
    )

    return {
        "tiktok":    tiktok_copy.strip(),
        "instagram": ig_copy.strip(),
        "youtube":   yt_copy.strip(),
        "raw_text":  clean_text,
    }



def _captions_from_words(
    client:     WhisperClient,
    transcript: dict,
    start:      float,
    end:        float,
    words_per_line: int = 4,
    highlight_kw:   list[str] | None = None,
) -> list[Caption]:
    """Build Caption list from Whisper word tokens."""
    tokens = client.words_in_range(transcript, start, end)
    if not tokens:
        return []

    highlight_kw = [k.lower() for k in (highlight_kw or [])]
    captions: list[Caption] = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i : i + words_per_line]
        text  = " ".join(t.word for t in chunk)
        t0    = max(0.0, chunk[0].start  - start)
        t1    = max(0.0, chunk[-1].end   - start)
        is_hl = any(kw in text.lower() for kw in highlight_kw)
        captions.append(Caption(text=text, start=t0, end=t1, highlight=is_hl))
        i += words_per_line

    return captions


# ─────────────────────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CampaignConfig:
    """Full campaign configuration from the GUI or brief."""
    campaign_name:  str
    preset:         str       = "podcast_viral"
    clips:          int       = 5
    videos:         list[str] = field(default_factory=list)
    doc_path:       str       = ""     # campaign brief PDF/Word
    logo_path:      str       = ""     # optional logo
    output_dir:     str       = ""     # auto-derived if empty
    guest_name:     str       = ""
    host_name:      str       = ""
    client_tag:     str       = ""
    mention_name:   str       = ""
    tiktok_handle:  str       = ""
    ig_handle:      str       = ""
    yt_handle:      str       = ""
    hashtags:       str       = "#shorts #viral #fyp"
    accent_color:   str       = "#FFD700"
    whisper_model:  str       = "base"
    language:       str       = "en"
    max_clip_dur:   float     = 75.0
    min_clip_dur:   float     = 20.0
    words_per_line: int       = 4
    highlight_kw:   list[str] = field(default_factory=list)


@dataclass
class ClipResult:
    """Result of rendering one clip."""
    clip_num:   int
    output_mp4: str
    duration:   float
    size_mb:    float
    moment:     ViralMoment
    captions:   list[Caption]
    social:     dict[str, str]   # tiktok / instagram / youtube
    txt_path:   str              # saved social copy file


# ─────────────────────────────────────────────────────────────────────────────
#  STUDIO
# ─────────────────────────────────────────────────────────────────────────────

class Studio:
    """
    End-to-end video production engine.

    Usage:
        studio = Studio(config, progress_cb=lambda msg, pct: ...)
        results = studio.run()
    """

    def __init__(
        self,
        config:       CampaignConfig,
        progress_cb:  Optional[Callable[[str, float], None]] = None,
        clip_done_cb: Optional[Callable] = None,
    ):
        self.cfg        = config
        self._progress  = progress_cb or (lambda msg, pct: None)
        self._on_clip_done = clip_done_cb or (lambda result: None)
        self.renderer   = Renderer(gpu=False)
        self.whisper    = WhisperClient(
            model=config.whisper_model,
            language=config.language,
        )
        self.analyzer   = VoiceAnalyzer()

        # Derive output dir
        if config.output_dir:
            self.out_dir = Path(config.output_dir)
        else:
            self.out_dir = (
                Path(os.path.dirname(os.path.abspath(__file__))).parent
                / "output" / config.campaign_name
            )
        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> list[ClipResult]:
        """Run the full pipeline. Returns list of ClipResult."""
        t0 = time.time()
        cfg = self.cfg

        self._progress("Starting production...", 0.0)

        # 1. Validate inputs
        valid_videos = self._validate_videos(cfg.videos)
        if not valid_videos:
            raise ValueError("No valid video files found.")

        # 2. Extract audio and transcribe
        self._progress("Transcribing audio with Whisper...", 0.05)
        transcripts = self._transcribe_all(valid_videos)

        # 3. Find viral moments
        self._progress("Detecting viral moments...", 0.20)
        moments = self._find_moments(transcripts, cfg)

        if not moments:
            raise ValueError(
                "No viral moments detected. Try longer videos or smaller min_clip_dur."
            )

        # Pick top N
        moments = moments[:cfg.clips]
        self._progress(f"Found {len(moments)} viral moments. Rendering...", 0.25)

        # 4. Render each clip
        results: list[ClipResult] = []
        preset_cfg = get_preset(cfg.preset)
        # Override accent from campaign config
        preset_cfg.accent_color = cfg.accent_color

        for i, moment in enumerate(moments):
            clip_num  = i + 1
            pct_start = 0.25 + (i / len(moments)) * 0.70
            pct_end   = 0.25 + ((i + 1) / len(moments)) * 0.70
            self._progress(
                f"Rendering clip {clip_num}/{len(moments)}...",
                pct_start,
            )

            result = self._render_moment(
                moment   = moment,
                clip_num = clip_num,
                preset   = preset_cfg,
                transcript_map = transcripts,
                pct_end  = pct_end,
            )
            if result:
                results.append(result)
                # Notify GUI about finished clip immediately
                self._on_clip_done(result)

        elapsed = time.time() - t0
        self._progress(
            f"Done! {len(results)}/{len(moments)} clips in {elapsed/60:.1f} min",
            1.0,
        )
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    def _validate_videos(self, paths: list[str]) -> list[str]:
        valid = []
        for p in paths:
            if Path(p).exists():
                info = self.renderer.probe(p)
                if info["duration"] > 5:
                    valid.append(p)
        return valid

    def _audio_path(self, video: str) -> str:
        import hashlib
        v_path = Path(video).resolve()
        path_hash = hashlib.md5(str(v_path).encode("utf-8")).hexdigest()[:8]
        base = v_path.stem[:30]
        return str(self.out_dir / f"_audio_{base}_{path_hash}.mp3")

    def _transcript_cache(self, video: str) -> str:
        import hashlib
        v_path = Path(video).resolve()
        path_hash = hashlib.md5(str(v_path).encode("utf-8")).hexdigest()[:8]
        base = v_path.stem[:30]
        return str(self.out_dir / f"_transcript_{base}_{path_hash}.json")

    def _extract_audio(self, video: str) -> str:
        out = self._audio_path(video)
        if Path(out).exists():
            return out
        subprocess.run(
            ["ffmpeg", "-y", "-i", video,
             "-vn", "-ar", "16000", "-ac", "1", "-q:a", "0", out],
            capture_output=True,
        )
        return out

    def _transcribe_all(
        self, videos: list[str]
    ) -> dict[str, dict]:
        """Returns {video_path: transcript_dict}"""
        result = {}
        for v in videos:
            self._progress(f"Extracting audio: {Path(v).name}", 0.06)
            audio = self._extract_audio(v)
            cache = self._transcript_cache(v)
            self._progress(f"Transcribing: {Path(v).name}", 0.10)
            tr = self.whisper.transcribe(
                audio,
                cache_path  = cache,
                progress_cb = lambda msg: self._progress(msg, 0.12),
            )
            # Inject real video duration so fallback time-slicer works correctly
            video_dur = self.renderer.probe_duration(v)
            if video_dur > 0:
                tr["duration"] = video_dur
            result[v] = tr
        return result

    def _find_moments(
        self,
        transcripts:  dict[str, dict],
        cfg:          CampaignConfig,
    ) -> list[ViralMoment]:
        """Find and rank all viral moments across all videos."""
        all_moments: list[ViralMoment] = []
        for video, tr in transcripts.items():
            # Auto-adapt min_clip_dur: never request clips longer than half the video
            video_dur = float(tr.get("duration", 0)) or self.renderer.probe_duration(video)
            effective_min = min(cfg.min_clip_dur, max(5.0, video_dur * 0.4))
            effective_max = min(cfg.max_clip_dur, max(effective_min + 5.0, video_dur * 0.9))

            moments = self.analyzer.find_moments(
                tr,
                min_dur   = effective_min,
                max_dur   = effective_max,
                top_n     = cfg.clips * 3,   # over-generate then trim
            )
            # Tag each moment with its source video
            for m in moments:
                m.reason = f"{Path(video).name} | {m.reason}"
            all_moments.extend(moments)

        # Re-rank combined list
        all_moments.sort(key=lambda m: m.score, reverse=True)

        # Deduplicate by overlap within same video
        selected: list[ViralMoment] = []
        seen_video_ranges: list[tuple[str, float]] = []
        for m in all_moments:
            src = m.reason.split(" | ")[0]
            too_close = any(
                v == src and abs(m.start - s) < 20
                for v, s in seen_video_ranges
            )
            if not too_close:
                selected.append(m)
                seen_video_ranges.append((src, m.start))

        return selected

    def _build_clip(
        self,
        video:     str,
        moment:    ViralMoment,
        clip_num:  int,
        preset:    PresetConfig,
        captions:  list[Caption],
        hook1:     str,
        hook2:     str,
    ) -> Clip:
        """Build a Clip object with the full effect chain."""
        clip = Clip(
            src      = video,
            start    = moment.start,
            end      = moment.end,
            meta     = {"clip_num": clip_num},
        )

        # ── Probe source video dimensions for exact crop math ─────────────────
        info = self.renderer.probe(video)
        src_w = info.get("width", 1920) or 1920
        src_h = info.get("height", 1080) or 1080

        # ── Layout selection ─────────────────────────────────────────────────
        is_capcut_ultra = "capcut" in preset.name.lower() or preset.name.lower().startswith("capcut")
        is_gaming = "gaming" in preset.name.lower() or getattr(preset, "pov_hook_mode", False)
        layout_mode = getattr(preset, "layout_mode", "portrait" if is_gaming else "auto")

        if is_gaming:
            if layout_mode == "full_169_blur":
                clip.layout.full_169_blur(src_w=src_w, src_h=src_h, blur_sigma=28)
            else:
                # Full 9:16 Vertical Crop (fills 100% of 1080x1920 canvas vertically)
                clip.layout.portrait(src_w=src_w, src_h=src_h)
        elif is_capcut_ultra:
            if clip_num % 3 == 1:
                clip.layout.split_2up(top_x=1380, bottom_x=420, divider_color=preset.accent_color)
            elif clip_num % 3 == 2:
                clip.layout.full_169_blur(src_w=src_w, src_h=src_h, blur_sigma=32)
            else:
                clip.layout.portrait_autoface(src_w=src_w, src_h=src_h)
        elif preset.crop_portrait:
            clip.layout.portrait_autoface(src_w=src_w, src_h=src_h)

        # ── Color grade ──────────────────────────────────────────────────────
        if preset.color_grade != "flat":
            clip.fx.color_grade(preset.color_grade)

        # ── Vignette ─────────────────────────────────────────────────────────
        if preset.vignette > 0:
            clip.fx.vignette(preset.vignette)

        # ── Gaming frenetic effects ──────────────────────────────────────────
        if is_gaming:
            dur = moment.duration
            n_flashes = getattr(preset, "frenetic_flashes", 3)
            n_zooms   = getattr(preset, "zoom_punches", 2)

            # Spread flash cuts evenly but avoid t=0 (already has opening flash)
            import random as _rand
            flash_times = []
            if dur > 4:
                step = dur / (n_flashes + 1)
                for k in range(1, n_flashes + 1):
                    t = step * k
                    # Add slight random jitter for organic feel
                    t += _rand.uniform(-step * 0.15, step * 0.15)
                    t = max(0.5, min(t, dur - 0.5))
                    flash_times.append(round(t, 2))
                    clip.fx.flash(at=t, dur=0.07)

            # Opening flash (1 frame brightness burst)
            clip.fx.flash(at=0.0, dur=0.09)

            # Glitch effect at ~30% into clip
            clip.fx.glitch(at=round(dur * 0.30, 2), dur=0.14)
            # Second glitch near climax (~70%)
            if dur > 8:
                clip.fx.glitch(at=round(dur * 0.70, 2), dur=0.12)

            # Zoom punches spread across clip
            if dur > 5:
                zoom_step = dur / (n_zooms + 1)
                for k in range(1, n_zooms + 1):
                    zt = zoom_step * k + _rand.uniform(-0.5, 0.5)
                    zt = max(1.0, min(zt, dur - 1.5))
                    clip.fx.zoom_punch(at=round(zt, 2), strength=0.14, dur=0.35)

        # ── Preset-specific SFX & FX scheduling ──────────────────────────────
        dur = moment.duration
        sfx_events: list[dict] = []

        if is_gaming and getattr(preset, "gaming_sfx", False):
            # Kill ding at start
            sfx_events.append({"type": "kill_ding", "t": 0.05, "vol": 0.85})
            # Whoosh at flash cuts
            for ft in flash_times[:2]:
                sfx_events.append({"type": "whoosh", "t": max(0.0, ft - 0.08), "vol": 0.70})
            if dur > 6:
                sfx_events.append({"type": "triple_kill", "t": round(dur * 0.35, 2), "vol": 0.80})
            if dur > 10:
                sfx_events.append({"type": "frenetic", "t": round(dur * 0.65, 2), "vol": 0.75})
            if dur > 8:
                sfx_events.append({"type": "impact", "t": round(dur * 0.80, 2), "vol": 0.85})
            clip.meta["sfx_events"] = sfx_events

        elif "motivational" in preset.name.lower():
            # Deep sub-bass impact drop at hook
            sfx_events.append({"type": "impact", "t": 0.40, "vol": 0.90})
            if dur > 10:
                sfx_events.append({"type": "whoosh", "t": round(dur * 0.50, 2), "vol": 0.65})
            clip.meta["sfx_events"] = sfx_events

        elif "reaction" in preset.name.lower():
            # High-energy reaction emojis & SFX
            from .effects.capcut_pack import CapCutFXPack
            reaction_emojis = ["😱", "🤯", "🤣", "🚨", "💀"]
            CapCutFXPack.emoji_popup(clip, reaction_emojis[(clip_num - 1) % len(reaction_emojis)], at=1.8, dur=1.2)
            sfx_events.append({"type": "glitch", "t": 0.30, "vol": 0.75})
            if dur > 6:
                sfx_events.append({"type": "impact", "t": round(dur * 0.60, 2), "vol": 0.85})
            clip.meta["sfx_events"] = sfx_events

        elif is_capcut_ultra:
            from .effects.capcut_pack import CapCutFXPack
            CapCutFXPack.light_leak(clip, at=1.5, dur=0.25)
            emojis = ["💰", "😤", "🚨", "📈", "😱", "🔥", "⚡"]
            emoji = emojis[(clip_num - 1) % len(emojis)]
            CapCutFXPack.emoji_popup(clip, emoji, at=2.0, dur=1.2)
            sfx_events.append({"type": "whoosh", "t": 1.40, "vol": 0.75})
            sfx_events.append({"type": "pop", "t": 1.95, "vol": 0.70})
            clip.meta["sfx_events"] = sfx_events

        # ── Ken Burns ────────────────────────────────────────────────────────
        if preset.ken_burns:
            clip.fx.ken_burns(zoom_from=preset.ken_from, zoom_to=preset.ken_to)

        # ── Letterbox ────────────────────────────────────────────────────────
        if preset.letterbox:
            clip.layout.letterbox(bar_pct=preset.letterbox_pct)

        # ── Hook text ────────────────────────────────────────────────────────
        if is_gaming and getattr(preset, "pov_hook_mode", False):
            # Single clean POV hook at top — no text wall
            hook_text = hook1.strip() or hook2.strip() or self.cfg.campaign_name
            clip.text.pov_gaming_hook(
                hook_text,
                accent=preset.accent_color,
                duration=getattr(preset, "pov_hook_dur", 4.5),
            )
        elif "pov" in preset.name.lower():
            # POV style tag badge at top
            pov_text = f"POV: {hook1[:40]}"
            clip.text.pov_gaming_hook(pov_text, accent=preset.accent_color, duration=5.0)
        elif preset.hook_card:
            clip.text.hook_card(hook1, hook2, accent=preset.accent_color)


        # ── Lower third ──────────────────────────────────────────────────────
        if preset.lower_third and self.cfg.guest_name:
            title = self.cfg.host_name or "The Cap Table"
            clip.text.lower_third(
                self.cfg.guest_name, title,
                t0=1.0, t1=5.5,
                accent=preset.accent_color,
                y_pct=preset.lower_third_y,
            )

        # ── Progress bar ─────────────────────────────────────────────────────
        if preset.progress_bar:
            clip.text.progress_bar(color=preset.progress_color)

        # ── Episode tag ──────────────────────────────────────────────────────
        clip.text.episode_tag(
            f"#{self.cfg.campaign_name}",
            dur=moment.duration,
        )

        # ── Word captions (non-gaming only) ──────────────────────────────────
        if preset.word_captions and captions and not is_gaming:
            clip.text.word_captions(
                captions,
                fontsize = preset.caption_size,

                accent   = preset.accent_color,
                y_expr   = preset.caption_y,
                use_box  = preset.caption_box,
            )

        return clip

    def _render_moment(
        self,
        moment:         ViralMoment,
        clip_num:       int,
        preset:         PresetConfig,
        transcript_map: dict[str, dict],
        pct_end:        float = 0.0,
    ) -> Optional[ClipResult]:
        """Render a single viral moment to a Short."""
        cfg = self.cfg

        # Find source video for this moment (by checking timestamp ranges)
        video = cfg.videos[0]   # fallback
        for v, tr in transcript_map.items():
            dur = self.renderer.probe_duration(v)
            if moment.start <= dur:
                video = v
                break

        # Build captions
        transcript = transcript_map.get(video, {})
        captions   = _captions_from_words(
            self.whisper, transcript,
            start       = moment.start,
            end         = moment.end,
            words_per_line = cfg.words_per_line,
            highlight_kw   = cfg.highlight_kw + list(_HOOK_WORDS),
        )

        # Auto-generate hook from moment text
        text_words = moment.text.split()
        hook1 = " ".join(text_words[:6]) if text_words else cfg.campaign_name
        hook2 = " ".join(text_words[6:12]) + "..." if len(text_words) > 6 else ""
        hook1 = hook1[:45]
        hook2 = hook2[:45]

        # Build clip with effects
        clip = self._build_clip(
            video    = video,
            moment   = moment,
            clip_num = clip_num,
            preset   = preset,
            captions = captions,
            hook1    = hook1,
            hook2    = hook2,
        )

        # Paths
        out_mp4 = str(self.out_dir / f"clip_{clip_num:02d}_{cfg.campaign_name.lower()}.mp4")
        out_txt = str(self.out_dir / f"clip_{clip_num:02d}_social_copy.txt")

        # Render — wire gaming SFX events if present
        raw_sfx = clip.meta.get("sfx_events", [])
        sfx_events = []
        if raw_sfx:
            from .audio.sfx import ensure_sfx_library
            sfx_lib = ensure_sfx_library()
            for ev in raw_sfx:
                sfx_path = sfx_lib.get(ev.get("type", ""))
                if sfx_path:
                    sfx_events.append({
                        "path": sfx_path,
                        "t":    ev.get("t", 0.0),
                        "vol":  ev.get("vol", 0.80),
                    })

        ok, stderr = self.renderer.render(
            src        = video,
            out        = out_mp4,
            start      = moment.start,
            duration   = moment.duration,
            vf         = clip._fc,
            crf        = preset.crf,
            audio_vol  = preset.audio_vol,
            sfx_events = sfx_events or None,
        )


        if not ok or not Path(out_mp4).exists() or Path(out_mp4).stat().st_size < 1000:
            err_msg = stderr[-400:] if stderr else "Unknown FFmpeg error"
            self._progress(f"ERROR clip {clip_num}: {err_msg}", pct_end)
            return None

        size_mb    = Path(out_mp4).stat().st_size / (1024 * 1024)
        actual_dur = self.renderer.probe_duration(out_mp4)

        # Social copy
        social = _build_social_copy(moment, cfg, clip_num, cfg.highlight_kw)

        # Save social copy txt
        self._save_social_txt(out_txt, clip_num, hook1, hook2, social, captions, actual_dur)

        self._progress(
            f"OK clip_{clip_num:02d} — {actual_dur:.1f}s | {size_mb:.1f} MB",
            pct_end,
        )

        return ClipResult(
            clip_num   = clip_num,
            output_mp4 = out_mp4,
            duration   = actual_dur,
            size_mb    = size_mb,
            moment     = moment,
            captions   = captions,
            social     = social,
            txt_path   = out_txt,
        )

    def _save_social_txt(
        self,
        path:       str,
        clip_num:   int,
        hook1:      str,
        hook2:      str,
        social:     dict,
        captions:   list[Caption],
        dur:        float,
    ):
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 65 + "\n")
            f.write(f"  {self.cfg.campaign_name.upper()} — CLIP {clip_num}\n")
            f.write("=" * 65 + "\n\n")

            f.write("HOOK (on-screen text):\n")
            f.write(f"  Line 1: {hook1}\n")
            f.write(f"  Line 2: {hook2}\n\n")

            f.write("─" * 65 + "\n")
            f.write("📱 TIKTOK CAPTION\n")
            f.write("─" * 65 + "\n")
            f.write(social.get("tiktok", "") + "\n\n")

            f.write("─" * 65 + "\n")
            f.write("📸 INSTAGRAM CAPTION\n")
            f.write("─" * 65 + "\n")
            f.write(social.get("instagram", "") + "\n\n")

            f.write("─" * 65 + "\n")
            f.write("▶ YOUTUBE CAPTION\n")
            f.write("─" * 65 + "\n")
            f.write(social.get("youtube", "") + "\n\n")

            f.write("─" * 65 + "\n")
            f.write(f"Clip duration: {dur:.1f}s\n")
            f.write(f"On-screen captions: {len(captions)} lines\n")
