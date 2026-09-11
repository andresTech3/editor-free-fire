"""
desktop_gui.py — Modern Interactive Studio GUI for Free Fire Short Video Generator (v26.2)
===========================================================================================
Layout v26.2: 2-COLUMN WIDE layout (1280x820) with Tab panel on right column.
  - Left column (scrollable):  Recursos, Audio, Formato, Destino/Nombre
  - Right column (Notebook tabs): Música/Speed | Hook | Motor de Edición
  - All sections always visible, no overflow.
"""

import os
import sys

# Set UTF-8 encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Project Paths
PROJECT_ROOT = Path(__file__).parent.resolve()
PROJECT_RECURSO_DIR = PROJECT_ROOT / "assets" / "Recurso video Freefire"
JUGADAS_DIR = PROJECT_RECURSO_DIR / "free fire jugadas"
GENERATE_VIDEO_DIR = PROJECT_RECURSO_DIR / "Generar Video"
MUSICA_DIR = PROJECT_RECURSO_DIR / "musica"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

# ── Styling Constants ────────────────────────────────────────────────────────
BG      = "#0D0F12"
CARD    = "#161920"
RED     = "#FF2E55"
GOLD    = "#FFC700"
BLUE    = "#3B82F6"
WHITE   = "#FFFFFF"
SUB     = "#94A3B8"
ENTRY   = "#0D0F12"
BTN_DIM = "#2A2E3D"

def lf(parent, title, color=WHITE, **kw):
    """Helper: styled LabelFrame."""
    return tk.LabelFrame(
        parent, text=f" {title} ",
        font=("Segoe UI", 9, "bold"), fg=color, bg=CARD,
        bd=1, relief="solid", padx=8, pady=4, **kw
    )

def lbl(parent, text, fg=SUB):
    return tk.Label(parent, text=text, font=("Segoe UI", 8), fg=fg, bg=CARD)

def entry(parent, var, fg=WHITE, font=("Consolas", 9)):
    return tk.Entry(
        parent, textvariable=var, font=font,
        bg=ENTRY, fg=fg, insertbackground=WHITE, bd=1, relief="flat"
    )

def btn(parent, text, cmd, bg=BTN_DIM, fg=WHITE, abg=GOLD, afg="#000"):
    return tk.Button(
        parent, text=text, font=("Segoe UI", 8, "bold"),
        bg=bg, fg=fg, activebackground=abg, activeforeground=afg,
        bd=0, padx=8, pady=3, cursor="hand2", command=cmd
    )


class ScrollableFrame(tk.Frame):
    """A vertically scrollable frame container."""
    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.inner.bind("<MouseWheel>", self._on_mousewheel)

    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._win, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class FreeFireEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Codigo Headshot Studio — Free Fire Viral Editor v26.2")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.resizable(True, True)
        self.configure(bg=BG)

        # Style notebook
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BTN_DIM, foreground=WHITE,
                         font=("Segoe UI", 9, "bold"), padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", GOLD)])

        # State vars
        self.audio_path_var    = tk.StringVar()
        self.gameplay_file_var = tk.StringVar()
        self.resources_dir_var = tk.StringVar(value=str(JUGADAS_DIR))
        self.bgm_enable_var    = tk.BooleanVar(value=True)
        self.selected_music_var = tk.StringVar(value="Aleatorio")
        self.hook_mode_var     = tk.StringVar(value="Deteccion Automatica")
        self.variation_var     = tk.BooleanVar(value=True)
        self.out_dir_var       = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.out_name_var      = tk.StringVar(value="freefire_headshot_viral.mp4")
        self.speed_ramp_var    = tk.StringVar(value="1.5x Frenetico (Recomendado)")
        self.aspect_var        = tk.StringVar(value="9:16")
        self.engine_mode_var   = tk.StringVar(value="Clasico (Fluido y Seguro - Recomendado)")
        self.last_rendered_file = None

        self._build()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _music_list(self):
        tracks = ["Aleatorio"]
        if MUSICA_DIR.exists():
            tracks += [f.name for f in MUSICA_DIR.glob("*.*")
                       if f.suffix.lower() in (".mp3", ".wav", ".m4a")]
        return tracks

    def refresh_music(self):
        tracks = self._music_list()
        self.cb_track["values"] = tracks
        if self.selected_music_var.get() not in tracks:
            self.selected_music_var.set("Aleatorio")

    def _update_resources_count(self, d):
        if d and os.path.exists(d):
            p = Path(d)
            vids = sum(len(list(p.rglob(f"*{e}"))) + len(list(p.rglob(f"*{e.upper()}"))) for e in [".mp4",".mov",".avi",".mkv"])
            self.lbl_resources.config(text=f"OK  {p.name} ({vids} videos)", fg="#10B981")
        else:
            self.lbl_resources.config(text="Carpeta no encontrada", fg="#EF4444")

    # ── UI Build ──────────────────────────────────────────────────────────────
    def _build(self):
        # ── HEADER ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CARD)
        hdr.pack(side="top", fill="x")

        tk.Label(hdr, text="CODIGO HEADSHOT STUDIO  v26.2",
                 font=("Impact", 20), fg=GOLD, bg=CARD).pack(side="left", padx=16, pady=8)
        tk.Label(hdr, text="Video | Audio | Motor | Formato | Destino",
                 font=("Segoe UI", 9), fg=SUB, bg=CARD).pack(side="left", padx=0, pady=8)

        def open_web_studio():
            import webbrowser
            webbrowser.open("http://localhost:8000")

        tk.Button(
            hdr, text="📱 Web Studio Movil",
            font=("Segoe UI", 9, "bold"), bg=RED, fg=WHITE,
            activebackground=GOLD, activeforeground="#000",
            bd=0, padx=10, pady=5, cursor="hand2",
            command=open_web_studio
        ).pack(side="right", padx=16, pady=8)

        # ── BOTTOM: DESTINO Y SALIDA DEL VIDEO FINAL + GENERATE BUTTON + STATUS ──
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=16, pady=8)

        # Dedicated Output Destination Box (Always visible above the generate button)
        box_out = tk.LabelFrame(
            bottom, text=" 💾 DESTINO Y SALIDA DEL VIDEO FINAL ",
            font=("Segoe UI", 9, "bold"), fg=GOLD, bg=CARD, bd=1, relief="solid", padx=10, pady=8
        )
        box_out.pack(fill="x", pady=(0, 8))

        # Row 0: Formato del Video (9:16 Shorts vs 16:9 YouTube)
        row_fmt = tk.Frame(box_out, bg=CARD)
        row_fmt.pack(fill="x", pady=(0, 8))

        tk.Label(
            row_fmt, text="📐 Formato del Video:",
            font=("Segoe UI", 10, "bold"), fg=GOLD, bg=CARD, width=22, anchor="w"
        ).pack(side="left")

        tk.Radiobutton(
            row_fmt, text="📱 9:16 Vertical (Shorts / TikTok / Reels)",
            variable=self.aspect_var, value="9:16",
            font=("Segoe UI", 10, "bold"), fg=WHITE, bg=CARD,
            selectcolor=RED, activebackground=CARD, cursor="hand2"
        ).pack(side="left", padx=(0, 24))

        tk.Radiobutton(
            row_fmt, text="🖥️ 16:9 Horizontal (YouTube / Facebook Largo)",
            variable=self.aspect_var, value="16:9",
            font=("Segoe UI", 10, "bold"), fg=WHITE, bg=CARD,
            selectcolor=GOLD, activebackground=CARD, cursor="hand2"
        ).pack(side="left")

        # Row 1: Output directory selection
        row_dir = tk.Frame(box_out, bg=CARD)
        row_dir.pack(fill="x", pady=(0, 6))

        tk.Label(
            row_dir, text="📁 Carpeta de Guardado:",
            font=("Segoe UI", 9, "bold"), fg=WHITE, bg=CARD, width=22, anchor="w"
        ).pack(side="left")
        tk.Entry(
            row_dir, textvariable=self.out_dir_var,
            font=("Consolas", 9), bg="#1A1D27", fg=WHITE, insertbackground=WHITE,
            bd=1, relief="solid"
        ).pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 6))
        tk.Button(
            row_dir, text="📁 Cambiar Carpeta", font=("Segoe UI", 9, "bold"),
            bg=GOLD, fg="#000", bd=0, padx=10, pady=3, cursor="hand2",
            command=self.browse_output_dir
        ).pack(side="left", padx=(0, 4))
        tk.Button(
            row_dir, text="📂 Abrir", font=("Segoe UI", 9),
            bg=BTN_DIM, fg=WHITE, bd=0, padx=8, pady=3, cursor="hand2",
            command=self.open_output_dir
        ).pack(side="left")

        # Row 2: Output filename
        row_name = tk.Frame(box_out, bg=CARD)
        row_name.pack(fill="x")

        tk.Label(
            row_name, text="🏷️ Nombre del Video (.mp4):",
            font=("Segoe UI", 9, "bold"), fg=GOLD, bg=CARD, width=22, anchor="w"
        ).pack(side="left")
        tk.Entry(
            row_name, textvariable=self.out_name_var,
            font=("Consolas", 10, "bold"), bg="#1A1D27", fg=GOLD, insertbackground=GOLD,
            bd=1, relief="solid"
        ).pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 8))
        tk.Label(
            row_name, text="(automáticamente se guarda aquí)",
            font=("Segoe UI", 8), fg=SUB, bg=CARD
        ).pack(side="left")

        self.btn_generate = tk.Button(
            bottom, text="🔥 EDITAR VIDEO EN HEADSHOT STUDIO  >>>",
            font=("Impact", 17), bg=RED, fg=WHITE,
            activebackground=GOLD, activeforeground="#000",
            bd=0, pady=8, cursor="hand2", command=self.start_generation
        )
        self.btn_generate.pack(fill="x", pady=(0, 4))

        row_status = tk.Frame(bottom, bg=BG)
        row_status.pack(fill="x")

        self.lbl_status = tk.Label(
            row_status,
            text="Listo — Usando jugadas de assets/Recurso video Freefire/free fire jugadas",
            font=("Segoe UI", 9, "italic"), fg=SUB, bg=BG
        )
        self.lbl_status.pack(side="left")

        self.btn_open_video = tk.Button(
            row_status, text="Abrir Video Final",
            font=("Segoe UI", 9, "bold"), bg=BTN_DIM, fg=GOLD,
            bd=0, padx=12, pady=4, cursor="hand2", command=self.open_final_video
        )

        # ── MAIN 2-COLUMN BODY ───────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(side="top", fill="both", expand=True, padx=16, pady=(6, 2))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Left: scrollable
        left_wrap = ScrollableFrame(body, bg=BG)
        left_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left = left_wrap.inner

        # Right: static (notebook)
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # ════════ LEFT COLUMN ════════════════════════════════════════════════

        # ── 1. RECURSOS Y VIDEO PRINCIPAL ─────────────────────────────────────
        f_gameplay = lf(left, "1. Video o Carpeta de Jugadas (Gameplays)", RED)
        f_gameplay.pack(fill="x", pady=(0, 6))

        lbl(f_gameplay, "Opcion A: Video Individual (.mp4 / .mov) [Opcional]:").pack(anchor="w")
        row_g = tk.Frame(f_gameplay, bg=CARD)
        row_g.pack(fill="x", pady=(2, 3))
        entry(row_g, self.gameplay_file_var).pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 5))
        btn(row_g, "📁 Seleccionar Video", self.browse_gameplay, abg=RED, afg=WHITE).pack(side="right")
        self.lbl_gameplay = lbl(f_gameplay, "Si no seleccionas uno, usaremos la carpeta de jugadas", fg=SUB)
        self.lbl_gameplay.pack(anchor="w", pady=(0, 3))

        lbl(f_gameplay, "Opcion B: Carpeta de Jugadas:").pack(anchor="w")
        row_r = tk.Frame(f_gameplay, bg=CARD)
        row_r.pack(fill="x", pady=(2, 3))
        entry(row_r, self.resources_dir_var).pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 5))
        btn(row_r, "📂 Cambiar Carpeta", self.browse_resources, abg=GOLD, afg="#000").pack(side="right")
        self.lbl_resources = lbl(f_gameplay, "Cargando jugadas...", fg=SUB)
        self.lbl_resources.pack(anchor="w", pady=(0, 2))
        self._update_resources_count(str(JUGADAS_DIR))

        # ── 1B. AUDIO DE VOZ ──────────────────────────────────────────────────
        f_audio = lf(left, "1B. Audio de Voz / Locucion (Opcional)", GOLD)
        f_audio.pack(fill="x", pady=(0, 6))

        lbl(f_audio, "Audio de locución (si no subes, usaremos el audio del video):").pack(anchor="w")
        row_a = tk.Frame(f_audio, bg=CARD)
        row_a.pack(fill="x", pady=(2, 0))
        entry(row_a, self.audio_path_var).pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 5))
        btn(row_a, "Seleccionar Audio", self.browse_audio, abg=GOLD, afg="#000").pack(side="right")
        self.lbl_audio = lbl(f_audio, "Audio de locucion opcional", fg=SUB)
        self.lbl_audio.pack(anchor="w", pady=(2, 0))

        # ── 2. FORMATO DE VIDEO ───────────────────────────────────────────────
        f_fmt = lf(left, "2. Formato de Salida", BLUE)
        f_fmt.pack(fill="x", pady=(0, 6))

        fmt_row = tk.Frame(f_fmt, bg=CARD)
        fmt_row.pack(fill="x")

        def rb(parent, text, val):
            tk.Radiobutton(
                parent, text=text, variable=self.aspect_var, value=val,
                font=("Segoe UI", 9, "bold"), fg=WHITE, bg=CARD,
                selectcolor=RED if val == "9:16" else GOLD,
                activebackground=CARD, cursor="hand2"
            ).pack(side="left", padx=(0, 18))

        rb(fmt_row, "9:16  Vertical  (Shorts / TikTok / Reels)", "9:16")
        rb(fmt_row, "16:9  Horizontal  (YouTube / Facebook)", "16:9")

        # ── 3. DESTINO & NOMBRE ───────────────────────────────────────────────
        f_dest = lf(left, "3. Carpeta de Guardado y Nombre", WHITE)
        f_dest.pack(fill="x", pady=(0, 6))

        lbl(f_dest, "Carpeta de destino:").pack(anchor="w")
        row_d = tk.Frame(f_dest, bg=CARD)
        row_d.pack(fill="x", pady=(2, 5))
        entry(row_d, self.out_dir_var).pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 5))
        btn(row_d, "Cambiar", self.browse_output_dir).pack(side="right")

        lbl(f_dest, "Nombre del archivo (.mp4):").pack(anchor="w")
        entry(f_dest, self.out_name_var, fg=GOLD, font=("Consolas", 9, "bold")).pack(
            fill="x", ipady=3, pady=(2, 0))

        # ════════ RIGHT COLUMN — Notebook Tabs ══════════════════════════════

        nb = ttk.Notebook(right)
        nb.pack(fill="both", expand=True)

        # ── Tab A: Música & Velocidad ─────────────────────────────────────────
        tab_mus = tk.Frame(nb, bg=CARD, padx=10, pady=8)
        nb.add(tab_mus, text="🎵  Música & Velocidad")

        tk.Checkbutton(
            tab_mus, text="Incluir Musica de Fondo  (Bucle Infinito, -18dB)",
            variable=self.bgm_enable_var, font=("Segoe UI", 9, "bold"),
            fg=WHITE, bg=CARD, selectcolor=BG,
            activebackground=CARD, cursor="hand2"
        ).pack(anchor="w", pady=(0, 8))

        g = tk.Frame(tab_mus, bg=CARD)
        g.pack(fill="x")

        lbl(g, "Pista de musica:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cb_track = ttk.Combobox(g, textvariable=self.selected_music_var,
                                     values=self._music_list(), state="readonly", width=28)
        self.cb_track.grid(row=0, column=1, sticky="w")
        tk.Button(g, text="Actualizar", font=("Segoe UI", 8, "bold"),
                  bg=BTN_DIM, fg=WHITE, bd=0, padx=6, pady=2,
                  cursor="hand2", command=self.refresh_music
                  ).grid(row=0, column=2, padx=(6, 0))

        lbl(g, "Speed Ramp:").grid(row=1, column=0, sticky="w", pady=(8, 0), padx=(0, 8))
        ttk.Combobox(
            g, textvariable=self.speed_ramp_var, state="readonly", width=34,
            values=[
                "1.5x Frenetico (Recomendado)",
                "1.8x Extremo (Ultra Rapido)",
                "1.0x Normal (Estandar)"
            ]
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(8, 0))

        # ── Tab B: Hook & Variación ───────────────────────────────────────────
        tab_hook = tk.Frame(nb, bg=CARD, padx=10, pady=8)
        nb.add(tab_hook, text="🎣  Hook & Variacion")

        lbl(tab_hook, "Primer Clip del Video (Hook de Entrada):").pack(anchor="w")
        ttk.Combobox(
            tab_hook, textvariable=self.hook_mode_var, state="readonly", width=44,
            values=[
                "Deteccion Automatica",
                "Forzar Entrada Rojo (Headshot)",
                "Forzar Entrada Amarillo (Fallando)"
            ]
        ).pack(anchor="w", pady=(4, 10))

        tk.Checkbutton(
            tab_hook,
            text="Garantizar Variacion Unica & Seleccion Frenetica por Movimiento",
            variable=self.variation_var, font=("Segoe UI", 9, "bold"),
            fg=GOLD, bg=CARD, selectcolor=BG,
            activebackground=CARD, cursor="hand2"
        ).pack(anchor="w")

        lbl(tab_hook, "\nEsta opcion asegura que cada video tenga clips y jugadas distintas.", fg=SUB).pack(anchor="w")

        # ── Tab C: Motor de Edición ───────────────────────────────────────────
        tab_eng = tk.Frame(nb, bg=CARD, padx=10, pady=8)
        nb.add(tab_eng, text="⚙️  Motor de Edicion")

        lbl(tab_eng, "Selecciona el motor de edicion a utilizar:", fg=WHITE).pack(anchor="w")

        engine_frame = tk.Frame(tab_eng, bg=CARD)
        engine_frame.pack(fill="x", pady=(6, 0))

        engines = [
            ("Clasico (Fluido y Seguro - Recomendado)",
             "Motor probado. Cortes fluidos al ritmo de la voz.\nIdeal para la mayoria de videos.",
             GOLD),
            ("Sintesis Dinamica (Whisper + Librosa Beat Sync + 3D Hook)",
             "Motor avanzado. Analiza la voz con IA (Whisper),\nsincroniza cortes con la musica (Librosa) y aplica efectos 3D.",
             BLUE),
        ]

        self._engine_btns = []
        for eng_val, eng_desc, eng_color in engines:
            frm = tk.Frame(engine_frame, bg=BTN_DIM, bd=1, relief="solid")
            frm.pack(fill="x", pady=4)

            top_row = tk.Frame(frm, bg=BTN_DIM)
            top_row.pack(fill="x", padx=8, pady=(6, 0))

            rb_eng = tk.Radiobutton(
                top_row, text=eng_val, variable=self.engine_mode_var, value=eng_val,
                font=("Segoe UI", 9, "bold"), fg=eng_color, bg=BTN_DIM,
                selectcolor=BG, activebackground=BTN_DIM, cursor="hand2"
            )
            rb_eng.pack(side="left")

            tk.Label(frm, text=eng_desc,
                     font=("Segoe UI", 8), fg=SUB, bg=BTN_DIM,
                     justify="left").pack(anchor="w", padx=26, pady=(2, 6))

        lbl(tab_eng, "\n🛡️ Rollback: Si el motor dinamico no te convence, cambia de vuelta al Clasico.", fg="#10B981").pack(anchor="w")

    # ── Actions ───────────────────────────────────────────────────────────────
    def browse_audio(self):
        p = filedialog.askopenfilename(
            title="Seleccionar Audio de Locucion Opcional",
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.ogg"), ("Todos", "*.*")]
        )
        if p:
            self.audio_path_var.set(p)
            mb = os.path.getsize(p) / (1024 * 1024)
            self.lbl_audio.config(text=f"OK  {Path(p).name} ({mb:.1f} MB)", fg="#10B981")

    def browse_gameplay(self):
        p = filedialog.askopenfilename(
            title="Seleccionar Video de Gameplay a Procesar",
            filetypes=[("Video", "*.mp4 *.mov *.avi *.mkv *.webm"), ("Todos", "*.*")]
        )
        if p:
            self.gameplay_file_var.set(p)
            mb = os.path.getsize(p) / (1024 * 1024)
            self.lbl_gameplay.config(text=f"OK  {Path(p).name} ({mb:.1f} MB)", fg="#10B981")

    def browse_resources(self):
        d = filedialog.askdirectory(title="Seleccionar Carpeta de Recursos de Gameplay", initialdir=self.resources_dir_var.get())
        if d:
            self.resources_dir_var.set(d)
            self._update_resources_count(d)

    def browse_output_dir(self):
        d = filedialog.askdirectory(title="Carpeta de Destino", initialdir=self.out_dir_var.get())
        if d:
            self.out_dir_var.set(d)

    def open_output_dir(self):
        d = self.out_dir_var.get().strip() or str(DEFAULT_OUTPUT_DIR)
        p = Path(d)
        p.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(p))
        except Exception:
            messagebox.showinfo("Carpeta de Salida", f"Ubicación:\n{p}")

    def open_final_video(self):
        target = (self.last_rendered_file
                  if self.last_rendered_file and self.last_rendered_file.exists()
                  else Path(self.out_dir_var.get()) / self.out_name_var.get())
        if target.exists():
            os.startfile(str(target)) if sys.platform == "win32" else subprocess.run(["open", str(target)])
        else:
            messagebox.showerror("Error", "El video aun no ha sido generado.")

    def start_generation(self):
        gameplay_file = self.gameplay_file_var.get().strip()
        resources_dir = self.resources_dir_var.get().strip() or str(JUGADAS_DIR)
        audio_file    = self.audio_path_var.get().strip()

        if gameplay_file and not os.path.exists(gameplay_file):
            messagebox.showwarning("Atencion", f"El archivo de video seleccionado no existe:\n{gameplay_file}")
            return

        if resources_dir and not os.path.exists(resources_dir):
            messagebox.showwarning("Atencion", f"La carpeta de recursos seleccionada no existe:\n{resources_dir}")
            return

        if audio_file and not os.path.exists(audio_file):
            messagebox.showwarning("Atencion", f"El archivo de audio seleccionado no existe:\n{audio_file}")
            return

        # Si el usuario selecciono un video pero no subio audio separado, extraer audio del video
        if gameplay_file and not audio_file:
            try:
                import tempfile
                tmp_audio = os.path.join(tempfile.gettempdir(), "extracted_gameplay_voice.wav")
                cmd_ext = [
                    "ffmpeg", "-y", "-i", gameplay_file,
                    "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                    tmp_audio
                ]
                subprocess.run(cmd_ext, capture_output=True)
                if os.path.exists(tmp_audio):
                    audio_file = tmp_audio
            except Exception:
                pass

        out_dir  = self.out_dir_var.get().strip() or str(DEFAULT_OUTPUT_DIR)
        out_name = self.out_name_var.get().strip() or "freefire_headshot_viral.mp4"
        if not out_name.lower().endswith(".mp4"):
            out_name += ".mp4"
        self.last_rendered_file = Path(out_dir) / out_name

        speed_str = self.speed_ramp_var.get()
        speed_val = "1.8" if "1.8x" in speed_str else ("1.0" if "1.0x" in speed_str else "1.5")

        hook_val  = self.hook_mode_var.get()
        hook_flag = "red" if "Rojo" in hook_val else ("yellow" if "Amarillo" in hook_val else "auto")

        aspect_flag  = "16:9" if "16:9" in self.aspect_var.get() else "9:16"
        music_choice = self.selected_music_var.get()

        self.btn_generate.config(state="disabled", bg="#4A5568",
                                 text=f"Procesando Video ({aspect_flag})... ESPERA")
        display_name = Path(gameplay_file).name if gameplay_file else Path(resources_dir).name
        self.lbl_status.config(
            text=f"Procesando: {display_name}  |  Formato: {aspect_flag}", fg=GOLD)
        self.btn_open_video.pack_forget()

        threading.Thread(
            target=self._run,
            args=(audio_file, gameplay_file, resources_dir, hook_flag, out_dir, out_name, speed_val, music_choice, aspect_flag),
            daemon=True
        ).start()

    def _run(self, audio_file, gameplay_file, resources_dir, hook_flag, out_dir, out_name, speed_val, music_choice, aspect_flag):
        try:
            eng = self.engine_mode_var.get()
            if "Sintesis" in eng or "Dinámica" in eng or "Dinamica" in eng:
                # Always pass the PROJECT assets root so generate_video.py
                # can locate musica/, PACK MEMES, etc. regardless of what
                # the user selected as gameplay folder.
                cmd = [
                    sys.executable,
                    str(PROJECT_ROOT / "generate_video.py"),
                    "--aspect",    aspect_flag,
                    "--outdir",    out_dir,
                    "--outname",   out_name,
                    "--assets_dir", str(PROJECT_ROOT / "assets"),
                ]
                if audio_file and os.path.exists(audio_file):
                    cmd.extend(["--audio", audio_file])
                # Optional: specific gameplay subfolder
                if resources_dir and os.path.exists(resources_dir):
                    cmd.extend(["--gamedir", resources_dir])
            elif aspect_flag == "16:9":
                cmd = [
                    sys.executable,
                    str(PROJECT_ROOT / "long_video_engine.py"),
                    "--outdir",  out_dir,
                    "--outname", out_name,
                ]
                if audio_file and os.path.exists(audio_file):
                    cmd.extend(["--audio", audio_file])
                if gameplay_file and os.path.exists(gameplay_file):
                    cmd.extend(["--gameplay", os.path.dirname(gameplay_file)])
                elif resources_dir and os.path.exists(resources_dir):
                    cmd.extend(["--gameplay", resources_dir])
            else:
                cmd = [
                    sys.executable,
                    str(PROJECT_ROOT / "desktop_auto_editor.py"),
                    "--bgm",     "yes" if self.bgm_enable_var.get() else "no",
                    "--hook",    hook_flag,
                    "--outdir",  out_dir,
                    "--outname", out_name,
                    "--speed",   speed_val,
                    "--music",   music_choice,
                    "--aspect",  aspect_flag,
                ]
                if audio_file and os.path.exists(audio_file):
                    cmd.extend(["--audio", audio_file])
                if gameplay_file and os.path.exists(gameplay_file):
                    cmd.extend(["--video", gameplay_file])
                if resources_dir and os.path.exists(resources_dir):
                    cmd.extend(["--resdir", resources_dir])

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and self.last_rendered_file.exists():
                self.after(0, self._on_success)
            else:
                err_msg = (res.stderr or "") + (res.stdout or "")
                err_msg = err_msg.strip() or "El proceso termino sin mensaje de error."
                self.after(0, lambda m=err_msg: self._on_error(m))
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _on_success(self):
        self.btn_generate.config(state="normal", bg=RED,
                                 text="GENERAR OTRO VIDEO FRENETICO  >>>")
        self.lbl_status.config(
            text=f"Listo!  Guardado en: {self.last_rendered_file}", fg="#10B981")
        self.btn_open_video.pack(side="right")
        messagebox.showinfo("Video Listo!",
                            f"Video generado exitosamente!\n\n{self.last_rendered_file}")

    def _on_error(self, err):
        self.btn_generate.config(state="normal", bg=RED, text="REINTENTAR  >>>")
        self.lbl_status.config(text="Error durante el renderizado.", fg="#EF4444")
        # Safely convert to string and truncate for display
        err_str = str(err) if err is not None else "Error desconocido (sin mensaje)."
        messagebox.showerror("Error de Render", f"No se pudo generar el video:\n\n{err_str[:600]}")


if __name__ == "__main__":
    app = FreeFireEditorApp()
    app.mainloop()
