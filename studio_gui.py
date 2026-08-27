"""
studio_gui.py
=============
ViralEditor Studio — Interfaz Gráfica Profesional
Dark mode, modern design usando customtkinter.

Características:
  - Subida de videos (múltiples), documento de campaña y logo
  - Configuración de campaña (nombre, preset, clips)
  - Información de redes sociales (TikTok, IG, YT handles)
  - Barra de progreso y log en tiempo real
  - Resultados con copy de redes sociales por clip
  - Botón copiar al portapapeles para cada plataforma
  - Abre carpeta de output al terminar
"""

from __future__ import annotations
import os
import sys
import threading
import subprocess
import queue
import time
import json
from pathlib import Path
from typing import Optional

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Check / install customtkinter ────────────────────────────────────────────
try:
    import customtkinter as ctk
except ImportError:
    print("Installing customtkinter...")
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "customtkinter", "-q"], check=True)
    import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Studio engine ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from viraleditor.studio  import Studio, CampaignConfig, ClipResult
from viraleditor.presets import Preset, PRESETS

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS & STYLES
# ─────────────────────────────────────────────────────────────────────────────

APP_TITLE   = "ViralEditor Studio"
APP_VERSION = "1.0"
WIN_W, WIN_H = 1020, 780
ACCENT      = "#FFD700"       # gold
BTN_PRIMARY = "#1f6aa5"
BTN_DANGER  = "#c0392b"
BTN_SUCCESS = "#27ae60"

VIDEO_EXTS = (
    ".mp4", ".mov", ".avi", ".mkv", ".m4v",
    ".webm", ".flv", ".wmv",
)
DOC_EXTS   = (".pdf", ".docx", ".doc", ".txt")
IMG_EXTS   = (".png", ".jpg", ".jpeg", ".webp", ".svg")

PRESET_LABELS = {
    "capcut_ultra_viral": "⚡ CapCut Ultra Viral (10M+)",
    "podcast_viral":      "🎙 Podcast Viral",
    "gaming":             "🎮 Gaming",
    "motivational":       "💪 Motivacional",
    "clean_minimal":      "✨ Clean Minimal",
    "pov_cinematic":      "🎬 POV Cinematic",
    "reaction":           "😮 Reaction",
}
PRESET_KEYS = list(PRESET_LABELS.keys())

# ─────────────────────────────────────────────────────────────────────────────
#  DRAG-AND-DROP ZONE WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class DropZone(ctk.CTkFrame):
    """A file upload area with browse button and file list."""

    def __init__(self, master, label: str, exts: tuple,
                 multi: bool = True, **kwargs):
        super().__init__(master, corner_radius=12,
                         border_width=2, border_color="#3a3a3a", **kwargs)
        self.exts  = exts
        self.multi = multi
        self.files: list[str] = []

        # Header label
        self._lbl = ctk.CTkLabel(self, text=label,
                                 font=ctk.CTkFont(size=14, weight="bold"),
                                 text_color="#aaaaaa")
        self._lbl.pack(pady=(14, 4))

        # Icon
        icon = "📹" if "mp4" in " ".join(exts) else ("📄" if "pdf" in " ".join(exts) else "🖼")
        ctk.CTkLabel(self, text=icon,
                     font=ctk.CTkFont(size=36)).pack(pady=(0, 4))

        # Hint
        self._hint = ctk.CTkLabel(
            self,
            text="Drop files here\nor click Browse",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
        )
        self._hint.pack(pady=(0, 8))

        # File list display
        self._list_box = ctk.CTkTextbox(
            self, height=80, state="disabled",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#1a1a1a", text_color="#cccccc",
        )
        self._list_box.pack(fill="x", padx=10, pady=(0, 6))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 12))

        ctk.CTkButton(
            btn_frame, text="Browse...", width=100,
            command=self._browse,
            fg_color=BTN_PRIMARY,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Clear", width=70,
            command=self._clear,
            fg_color="#3a3a3a",
        ).pack(side="left")

    def _browse(self):
        from tkinter import filedialog
        if self.multi:
            paths = filedialog.askopenfilenames(
                filetypes=[("Supported files", " ".join(f"*{e}" for e in self.exts))]
            )
            if paths:
                self.files = list(paths)
        else:
            path = filedialog.askopenfilename(
                filetypes=[("Supported files", " ".join(f"*{e}" for e in self.exts))]
            )
            if path:
                self.files = [path]
        self._refresh()

    def _clear(self):
        self.files.clear()
        self._refresh()

    def _refresh(self):
        self._list_box.configure(state="normal")
        self._list_box.delete("1.0", "end")
        if self.files:
            text = "\n".join(f"✓ {Path(f).name}" for f in self.files)
        else:
            text = "(no files)"
        self._list_box.insert("1.0", text)
        self._list_box.configure(state="disabled")

    def add_file(self, path: str):
        if path and path not in self.files:
            self.files.append(path)
            self._refresh()

    def get(self) -> list[str]:
        return self.files.copy()

    def get_first(self) -> Optional[str]:
        return self.files[0] if self.files else None


# ─────────────────────────────────────────────────────────────────────────────
#  RESULTS PANEL (shows clips + social copy after render)
# ─────────────────────────────────────────────────────────────────────────────

class ResultsPanel(ctk.CTkScrollableFrame):
    """Displays clip results with social copy and copy-to-clipboard buttons."""

    def __init__(self, master, **kwargs):
        super().__init__(master, label_text="📋 Results — Social Copy",
                         label_font=ctk.CTkFont(size=14, weight="bold"),
                         **kwargs)

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def add_result(self, result: ClipResult):
        card = ctk.CTkFrame(self, corner_radius=10,
                            border_width=1, border_color="#2a2a2a",
                            fg_color="#1e1e1e")
        card.pack(fill="x", padx=8, pady=6)

        # Header
        hdr = ctk.CTkFrame(card, fg_color="#252525", corner_radius=8)
        hdr.pack(fill="x", padx=8, pady=(8, 0))

        ctk.CTkLabel(
            hdr,
            text=f"  🎬 Clip {result.clip_num:02d}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=8, pady=6)

        ctk.CTkLabel(
            hdr,
            text=f"{result.duration:.1f}s  |  {result.size_mb:.1f} MB",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
        ).pack(side="right", padx=8, pady=6)

        # Moment text preview
        moment_text = result.moment.text[:100] + "..."
        ctk.CTkLabel(
            card,
            text=f'"{moment_text}"',
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#777777",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(6, 2))

        # Social tabs
        social = result.social
        platforms = [
            ("📱 TikTok",    social.get("tiktok", "")),
            ("📸 Instagram", social.get("instagram", "")),
            ("▶ YouTube",   social.get("youtube", "")),
        ]

        for platform, copy_text in platforms:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)

            ctk.CTkLabel(
                row, text=platform,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#aaaaaa", width=110, anchor="w",
            ).pack(side="left")

            txt_box = ctk.CTkTextbox(
                row, height=54,
                font=ctk.CTkFont(family="Consolas", size=10),
                fg_color="#161616", text_color="#dddddd",
            )
            txt_box.insert("1.0", copy_text)
            txt_box.configure(state="disabled")
            txt_box.pack(side="left", fill="x", expand=True, padx=(4, 4))

            def make_copy_cmd(t=copy_text):
                return lambda: self._copy(t)

            ctk.CTkButton(
                row, text="Copy", width=60,
                font=ctk.CTkFont(size=11),
                fg_color=BTN_SUCCESS,
                command=make_copy_cmd(),
            ).pack(side="right")

        # Open file button
        def open_mp4(p=result.output_mp4):
            os.startfile(p) if sys.platform == "win32" else subprocess.Popen(["xdg-open", p])

        ctk.CTkButton(
            card, text="▶ Open Clip",
            font=ctk.CTkFont(size=11),
            width=120, height=28,
            fg_color="#2a2a2a",
            command=open_mp4,
        ).pack(anchor="e", padx=10, pady=(4, 10))

    def _copy(self, text: str):
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.after(500, r.destroy)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class ViralStudioApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(900, 680)
        self.configure(fg_color="#141414")

        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._results: list[ClipResult] = []

        self._build_ui()
        self._poll_queue()

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Title bar ──────────────────────────────────────────────────────
        title_bar = ctk.CTkFrame(self, height=56, fg_color="#0d0d0d",
                                 corner_radius=0)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        ctk.CTkLabel(
            title_bar,
            text=f"  🎬  {APP_TITLE}",
            font=ctk.CTkFont(family="Arial", size=20, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(
            title_bar,
            text="Professional Short Editor — No CapCut Needed",
            font=ctk.CTkFont(size=12),
            text_color="#555555",
        ).pack(side="left")

        # ── Tab view ───────────────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(self, corner_radius=10,
                                   fg_color="#181818",
                                   segmented_button_fg_color="#1e1e1e",
                                   segmented_button_selected_color=BTN_PRIMARY)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=10)

        self.tabs.add("📁 Setup")
        self.tabs.add("⚙️ Campaign")
        self.tabs.add("🚀 Produce")
        self.tabs.add("📋 Results")

        self._build_setup_tab()
        self._build_campaign_tab()
        self._build_produce_tab()
        self._build_results_tab()

    # ── Tab: Setup ────────────────────────────────────────────────────────────

    def _build_setup_tab(self):
        tab = self.tabs.tab("📁 Setup")

        ctk.CTkLabel(
            tab,
            text="Upload your materials — videos, campaign brief, logo (optional)",
            font=ctk.CTkFont(size=13),
            text_color="#888888",
        ).pack(pady=(10, 14))

        # 3-column grid for upload zones
        grid = ctk.CTkFrame(tab, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1, 2), weight=1, uniform="col")

        # Videos zone
        self.zone_videos = DropZone(
            grid, "📹 Source Videos",
            exts=VIDEO_EXTS, multi=True,
            fg_color="#1a1a1a",
        )
        self.zone_videos.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        # Campaign doc zone
        self.zone_doc = DropZone(
            grid, "📄 Campaign Brief (optional)",
            exts=DOC_EXTS, multi=False,
            fg_color="#1a1a1a",
        )
        self.zone_doc.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")

        # Logo zone
        self.zone_logo = DropZone(
            grid, "🖼 Logo (optional)",
            exts=IMG_EXTS, multi=False,
            fg_color="#1a1a1a",
        )
        self.zone_logo.grid(row=0, column=2, padx=6, pady=6, sticky="nsew")

        # Next button
        ctk.CTkButton(
            tab,
            text="Next → Configure Campaign",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color=BTN_PRIMARY,
            command=lambda: self.tabs.set("⚙️ Campaign"),
        ).pack(pady=12, padx=20, fill="x")

    # ── Tab: Campaign ─────────────────────────────────────────────────────────

    def _build_campaign_tab(self):
        tab = self.tabs.tab("⚙️ Campaign")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def section(label: str):
            ctk.CTkLabel(scroll, text=label,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=ACCENT).pack(anchor="w", padx=20, pady=(16, 4))

        def field(label: str, var, placeholder: str = "", width: int = 340):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(row, text=label, width=180, anchor="w",
                         font=ctk.CTkFont(size=12),
                         text_color="#bbbbbb").pack(side="left")
            ent = ctk.CTkEntry(row, textvariable=var,
                               placeholder_text=placeholder, width=width)
            ent.pack(side="left")
            return ent

        # ── Basic settings ────────────────────────────────────────────────
        section("📋 Basic Settings")

        self.var_campaign    = ctk.StringVar(value="MyCampaign")
        self.var_clips       = ctk.StringVar(value="5")
        self.var_output_dir  = ctk.StringVar(value="")

        field("Campaign name:", self.var_campaign, "e.g. TheCapTable")
        field("Number of clips:", self.var_clips, "5")

        # Preset picker
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(row, text="Editing preset:", width=180, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color="#bbbbbb").pack(side="left")

        self.var_preset = ctk.StringVar(value=PRESET_KEYS[0])
        ctk.CTkOptionMenu(
            row,
            values=list(PRESET_LABELS.values()),
            variable=ctk.StringVar(value=list(PRESET_LABELS.values())[0]),
            width=260,
            command=self._on_preset_select,
        ).pack(side="left")

        self._preset_desc = ctk.CTkLabel(
            scroll, text="", font=ctk.CTkFont(size=11),
            text_color="#666666", wraplength=700, justify="left",
        )
        self._preset_desc.pack(anchor="w", padx=200, pady=0)
        self._on_preset_select(list(PRESET_LABELS.values())[0])

        # ── Guest / Show info ─────────────────────────────────────────────
        section("🎙 Guest & Show Info")

        self.var_guest  = ctk.StringVar()
        self.var_host   = ctk.StringVar()
        self.var_client = ctk.StringVar()
        self.var_mention = ctk.StringVar()

        field("Guest name:",   self.var_guest,   "e.g. Avi Patel")
        field("Show / host:",  self.var_host,    "e.g. The Cap Table")
        field("Client brand:", self.var_client,  "e.g. SideShift")
        field("Mention:",      self.var_mention, "e.g. SideShift AI")

        # ── Social handles ────────────────────────────────────────────────
        section("📱 Social Media Handles")

        self.var_tiktok = ctk.StringVar(value="@thecaptabletv")
        self.var_ig     = ctk.StringVar(value="@thecaptable.tv")
        self.var_yt     = ctk.StringVar(value="@TheCapTableTV")
        self.var_tags   = ctk.StringVar(value="#shorts #viral #fyp #startup")

        field("TikTok handle:",   self.var_tiktok, "@yourhandle")
        field("Instagram handle:", self.var_ig,    "@yourhandle")
        field("YouTube handle:",  self.var_yt,     "@yourhandle")
        field("Hashtags:",        self.var_tags,   "#shorts #viral")

        # ── Advanced ──────────────────────────────────────────────────────
        section("🔧 Advanced")

        self.var_whisper  = ctk.StringVar(value="base")
        self.var_accent   = ctk.StringVar(value="#FFD700")
        self.var_lang     = ctk.StringVar(value="en")
        self.var_min_dur  = ctk.StringVar(value="20")
        self.var_max_dur  = ctk.StringVar(value="75")

        row_w = ctk.CTkFrame(scroll, fg_color="transparent")
        row_w.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(row_w, text="Whisper model:", width=180, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color="#bbbbbb").pack(side="left")
        ctk.CTkOptionMenu(
            row_w,
            values=["tiny", "base", "small", "medium"],
            variable=self.var_whisper,
            width=180,
        ).pack(side="left")

        field("Accent color:",  self.var_accent,  "#FFD700")
        field("Language:",      self.var_lang,     "en / es / auto")
        field("Min clip (sec):", self.var_min_dur, "20")
        field("Max clip (sec):", self.var_max_dur, "75")

        # Next
        ctk.CTkButton(
            scroll,
            text="Next → Start Production",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44, fg_color=BTN_PRIMARY,
            command=lambda: self.tabs.set("🚀 Produce"),
        ).pack(pady=18, padx=20, fill="x")

    def _on_preset_select(self, label: str):
        key = PRESET_KEYS[list(PRESET_LABELS.values()).index(label)] if label in PRESET_LABELS.values() else PRESET_KEYS[0]
        self.var_preset.set(key)
        from viraleditor.presets import get_preset
        cfg = get_preset(key)
        self._preset_desc.configure(text=f"ℹ  {cfg.description}")

    # ── Tab: Produce ──────────────────────────────────────────────────────────

    def _build_produce_tab(self):
        tab = self.tabs.tab("🚀 Produce")

        # Summary card
        self._summary = ctk.CTkFrame(tab, fg_color="#1a1a1a",
                                     corner_radius=10, border_width=1,
                                     border_color="#2a2a2a")
        self._summary.pack(fill="x", padx=16, pady=(12, 8))
        self._summary_lbl = ctk.CTkLabel(
            self._summary,
            text="Configure your campaign and press Start Production",
            font=ctk.CTkFont(size=12),
            text_color="#777777",
            wraplength=860,
            justify="left",
        )
        self._summary_lbl.pack(padx=16, pady=12)

        # Progress bar
        prog_frame = ctk.CTkFrame(tab, fg_color="transparent")
        prog_frame.pack(fill="x", padx=16, pady=(0, 4))

        self._progress_bar = ctk.CTkProgressBar(prog_frame, height=16,
                                                 progress_color=ACCENT,
                                                 fg_color="#1e1e1e")
        self._progress_bar.pack(fill="x")
        self._progress_bar.set(0)

        self._progress_lbl = ctk.CTkLabel(
            tab, text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
        )
        self._progress_lbl.pack(anchor="w", padx=16)

        # Log output
        ctk.CTkLabel(tab, text="Production Log",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#555555").pack(anchor="w", padx=16, pady=(8, 2))

        self._log = ctk.CTkTextbox(
            tab, height=340,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0f0f0f",
            text_color="#b0b0b0",
            scrollbar_button_color="#2a2a2a",
        )
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Buttons row
        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        self._btn_start = ctk.CTkButton(
            btn_row,
            text="🚀  Start Production",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50, fg_color=BTN_SUCCESS,
            hover_color="#219a52",
            command=self._start_production,
        )
        self._btn_start.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._btn_open = ctk.CTkButton(
            btn_row,
            text="📁 Open Output",
            font=ctk.CTkFont(size=13),
            height=50, width=160,
            fg_color="#2a2a2a",
            command=self._open_output,
            state="disabled",
        )
        self._btn_open.pack(side="left")

    # ── Tab: Results ──────────────────────────────────────────────────────────

    def _build_results_tab(self):
        tab = self.tabs.tab("📋 Results")
        self._results_panel = ResultsPanel(tab, fg_color="#141414")
        self._results_panel.pack(fill="both", expand=True, padx=10, pady=8)

    # ── Production Engine ─────────────────────────────────────────────────────

    def _build_config(self) -> CampaignConfig:
        """Build CampaignConfig from current UI values."""
        videos = self.zone_videos.get()
        doc    = self.zone_doc.get_first() or ""
        logo   = self.zone_logo.get_first() or ""
        name   = self.var_campaign.get().strip() or "Campaign"

        try:
            clips = int(self.var_clips.get())
        except ValueError:
            clips = 5

        try:
            min_dur = float(self.var_min_dur.get())
        except ValueError:
            min_dur = 20.0

        try:
            max_dur = float(self.var_max_dur.get())
        except ValueError:
            max_dur = 75.0

        out_dir = str(
            Path(os.path.dirname(os.path.abspath(__file__)))
            / "output" / name
        )

        return CampaignConfig(
            campaign_name  = name,
            preset         = self.var_preset.get(),
            clips          = clips,
            videos         = videos,
            doc_path       = doc,
            logo_path      = logo,
            output_dir     = out_dir,
            guest_name     = self.var_guest.get().strip(),
            host_name      = self.var_host.get().strip(),
            client_tag     = self.var_client.get().strip(),
            mention_name   = self.var_mention.get().strip(),
            tiktok_handle  = self.var_tiktok.get().strip(),
            ig_handle      = self.var_ig.get().strip(),
            yt_handle      = self.var_yt.get().strip(),
            hashtags       = self.var_tags.get().strip(),
            accent_color   = self.var_accent.get().strip() or "#FFD700",
            whisper_model  = self.var_whisper.get(),
            language       = self.var_lang.get().strip() or "en",
            min_clip_dur   = min_dur,
            max_clip_dur   = max_dur,
        )

    def _update_summary(self, cfg: CampaignConfig):
        videos_str = f"{len(cfg.videos)} video(s)" if cfg.videos else "⚠ No videos"
        doc_str    = Path(cfg.doc_path).name if cfg.doc_path else "None"
        logo_str   = Path(cfg.logo_path).name if cfg.logo_path else "None"
        preset_lbl = PRESET_LABELS.get(cfg.preset, cfg.preset)
        self._summary_lbl.configure(
            text=(
                f"📹 Videos: {videos_str}   |   📄 Brief: {doc_str}   |   "
                f"🖼 Logo: {logo_str}\n"
                f"🎬 Campaign: {cfg.campaign_name}   |   Preset: {preset_lbl}   |   "
                f"Clips: {cfg.clips}   |   Output: output/{cfg.campaign_name}/"
            ),
            text_color="#aaaaaa",
        )

    def _start_production(self):
        if self._running:
            return

        cfg = self._build_config()
        self._update_summary(cfg)

        if not cfg.videos:
            self._log_append("❌ No videos selected. Go to Setup tab and add videos.")
            return

        self._running = True
        self._btn_start.configure(state="disabled", text="⏳ Producing...")
        self._progress_bar.set(0)
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._results_panel.clear()
        self._results.clear()
        self._btn_open.configure(state="disabled")

        self._out_dir = cfg.output_dir

        def run_studio():
            try:
                def progress_cb(msg: str, pct: float):
                    self._queue.put(("progress", msg, pct))

                def clip_done_cb(result):
                    self._queue.put(("result", result))

                studio = Studio(cfg, progress_cb=progress_cb, clip_done_cb=clip_done_cb)
                results = studio.run()

                self._queue.put(("done", len(results), cfg.clips))
            except Exception as e:
                import traceback
                self._queue.put(("error", str(e), traceback.format_exc()))

        thread = threading.Thread(target=run_studio, daemon=True)
        thread.start()

    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    _, msg, pct = item
                    self._progress_lbl.configure(text=msg)
                    self._progress_bar.set(max(0.0, min(1.0, pct)))
                    self._log_append(f"  {msg}")

                elif kind == "result":
                    _, result = item
                    self._results.append(result)
                    self._results_panel.add_result(result)
                    self._log_append(
                        f"  Clip {result.clip_num:02d} ready — "
                        f"{result.duration:.1f}s | {result.size_mb:.1f} MB"
                    )
                    # Switch to Results tab on first clip so user sees it immediately
                    if len(self._results) == 1:
                        self.tabs.set("📋 Results")

                elif kind == "done":
                    _, n_ok, n_total = item
                    self._progress_bar.set(1.0)
                    self._progress_lbl.configure(text=f"✅ Done! {n_ok}/{n_total} clips created")
                    self._log_append(f"\n🎉 Production complete! {n_ok}/{n_total} clips")
                    self._btn_start.configure(state="normal", text="🚀  Start Production")
                    self._btn_open.configure(state="normal")
                    self._running = False
                    self.tabs.set("📋 Results")

                elif kind == "error":
                    _, err, tb = item
                    self._log_append(f"\n❌ ERROR: {err}")
                    self._log_append(f"\n{tb}")
                    self._progress_lbl.configure(text=f"❌ Error: {err[:60]}")
                    self._btn_start.configure(state="normal", text="🚀  Start Production")
                    self._running = False

        except queue.Empty:
            pass

        self.after(150, self._poll_queue)

    def _log_append(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _open_output(self):
        if hasattr(self, "_out_dir") and Path(self._out_dir).exists():
            if sys.platform == "win32":
                os.startfile(self._out_dir)
            else:
                subprocess.Popen(["xdg-open", self._out_dir])


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ViralStudioApp()
    app.mainloop()
