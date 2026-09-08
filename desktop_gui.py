"""
desktop_gui.py — Modern Interactive Studio GUI for Free Fire Short Video Generator (v24.1)
===========================================================================================
Layout v24.1: 2-COLUMN WIDE layout (1180x580) to avoid vertical overflow on screen.
  - Left column:  Audio, Formato, Destino/Nombre
  - Right column: Musica/Speed, Hook, Formato/Boton
"""

import os
import sys
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
        font=("Segoe UI", 10, "bold"), fg=color, bg=CARD,
        bd=1, relief="solid", padx=10, pady=6, **kw
    )

def lbl(parent, text, fg=SUB):
    return tk.Label(parent, text=text, font=("Segoe UI", 9), fg=fg, bg=CARD)

def entry(parent, var, fg=WHITE, font=("Consolas", 9)):
    return tk.Entry(
        parent, textvariable=var, font=font,
        bg=ENTRY, fg=fg, insertbackground=WHITE, bd=1, relief="flat"
    )

def btn(parent, text, cmd, bg=BTN_DIM, fg=WHITE, abg=GOLD, afg="#000"):
    return tk.Button(
        parent, text=text, font=("Segoe UI", 9, "bold"),
        bg=bg, fg=fg, activebackground=abg, activeforeground=afg,
        bd=0, padx=10, pady=3, cursor="hand2", command=cmd
    )


class FreeFireEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Codigo Headshot Studio — Free Fire Viral Editor v24.1")
        self.geometry("1180x680")
        self.resizable(True, True)
        self.configure(bg=BG)

        # State vars
        self.audio_path_var   = tk.StringVar()
        self.gameplay_file_var = tk.StringVar()
        self.resources_dir_var = tk.StringVar(value=str(JUGADAS_DIR))
        self.bgm_enable_var   = tk.BooleanVar(value=True)
        self.selected_music_var = tk.StringVar(value="Aleatorio")
        self.hook_mode_var    = tk.StringVar(value="Deteccion Automatica")
        self.variation_var    = tk.BooleanVar(value=True)
        self.out_dir_var      = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.out_name_var     = tk.StringVar(value="freefire_headshot_viral.mp4")
        self.speed_ramp_var   = tk.StringVar(value="1.5x Frenetico (Recomendado)")
        self.aspect_var       = tk.StringVar(value="9:16")
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
            self.lbl_resources.config(text=f"OK  {p.name} ({vids} jugadas/videos encontrados)", fg="#10B981")
        else:
            self.lbl_resources.config(text="Carpeta no encontrada", fg="#EF4444")

    # ── UI Build ──────────────────────────────────────────────────────────────
    def _build(self):
        # ── HEADER ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CARD)
        hdr.pack(side="top", fill="x")
        tk.Label(hdr, text="CODIGO HEADSHOT STUDIO — FRENETICO  v26.0",
                 font=("Impact", 22), fg=GOLD, bg=CARD).pack(side="left", padx=20, pady=10)
        tk.Label(hdr, text="Selecciona Tu Video o Carpeta  |  Motor Frenetico  |  Subtítulos & Memes  |  Zoom Impacto",
                 font=("Segoe UI", 10), fg=SUB, bg=CARD).pack(side="left", padx=0, pady=10)

        def open_web_studio():
            import webbrowser
            webbrowser.open("http://localhost:8000")

        tk.Button(
            hdr, text="📱 Abrir Web Studio Móvil",
            font=("Segoe UI", 10, "bold"), bg=RED, fg=WHITE,
            activebackground=GOLD, activeforeground="#000",
            bd=0, padx=12, pady=6, cursor="hand2",
            command=open_web_studio
        ).pack(side="right", padx=20, pady=10)

        # ── BOTTOM: GENERATE BUTTON + STATUS (Anchored at bottom first) ──────
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=18, pady=10)

        self.btn_generate = tk.Button(
            bottom, text="🔥 EDITAR VIDEO SELECCIONADO EN HEADSHOT STUDIO  >>>",
            font=("Impact", 18), bg=RED, fg=WHITE,
            activebackground=GOLD, activeforeground="#000",
            bd=0, pady=10, cursor="hand2", command=self.start_generation
        )
        self.btn_generate.pack(fill="x", pady=(0, 6))

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
            bd=0, padx=14, pady=4, cursor="hand2", command=self.open_final_video
        )

        # ── MAIN 2-COLUMN BODY ───────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(side="top", fill="both", expand=True, padx=18, pady=(8, 4))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        left  = tk.Frame(body, bg=BG)
        right = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ════════ LEFT COLUMN ════════════════════════════════════════════════

        # ── 1. RECURSOS Y VIDEO PRINCIPAL ─────────────────────────────────────
        f_gameplay = lf(left, "1. Video o Carpeta de Jugadas (Gameplays)", RED)
        f_gameplay.pack(fill="x", pady=(0, 8))

        # Opción A: Video Individual
        lbl(f_gameplay, "Opción A: Sube un Video Individual (.mp4, .mov) [Opcional]:").pack(anchor="w")
        row_g = tk.Frame(f_gameplay, bg=CARD); row_g.pack(fill="x", pady=(2, 4))
        entry(row_g, self.gameplay_file_var).pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        btn(row_g, "📁 Seleccionar Video", self.browse_gameplay, abg=RED, afg=WHITE).pack(side="right")
        self.lbl_gameplay = lbl(f_gameplay, "Si no seleccionas uno, usaremos la carpeta de jugadas", fg=SUB)
        self.lbl_gameplay.pack(anchor="w", pady=(0, 4))

        # Opción B: Carpeta de Jugadas
        lbl(f_gameplay, "Opción B: Carpeta de Jugadas (assets/Recurso video Freefire/free fire jugadas):").pack(anchor="w")
        row_r = tk.Frame(f_gameplay, bg=CARD); row_r.pack(fill="x", pady=(2, 4))
        entry(row_r, self.resources_dir_var).pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        btn(row_r, "📂 Cambiar Carpeta", self.browse_resources, abg=GOLD, afg="#000").pack(side="right")
        self.lbl_resources = lbl(f_gameplay, "Cargando jugadas...", fg=SUB)
        self.lbl_resources.pack(anchor="w", pady=(0, 2))
        self._update_resources_count(str(JUGADAS_DIR))

        # ── 1B. AUDIO DE VOZ ──────────────────────────────────────────────────
        f_audio = lf(left, "1B. Audio de Voz / Locución (Opcional)", GOLD)
        f_audio.pack(fill="x", pady=(0, 8))

        lbl(f_audio, "Sube tu audio de voz (si no subes uno, usaremos el audio de tu video o carpeta):").pack(anchor="w")
        row_a = tk.Frame(f_audio, bg=CARD); row_a.pack(fill="x", pady=(3, 0))
        entry(row_a, self.audio_path_var).pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        btn(row_a, "Seleccionar Audio", self.browse_audio, abg=GOLD, afg="#000").pack(side="right")
        self.lbl_audio = lbl(f_audio, "Audio de locución opcional", fg=SUB)
        self.lbl_audio.pack(anchor="w", pady=(3, 0))

        # ── 2. FORMATO DE VIDEO ───────────────────────────────────────────────
        f_fmt = lf(left, "2. Formato de Salida", BLUE)
        f_fmt.pack(fill="x", pady=(0, 8))

        fmt_row = tk.Frame(f_fmt, bg=CARD); fmt_row.pack(fill="x")

        def rb(parent, text, val, col):
            tk.Radiobutton(
                parent, text=text, variable=self.aspect_var, value=val,
                font=("Segoe UI", 10, "bold"), fg=WHITE, bg=CARD,
                selectcolor=RED if val == "9:16" else GOLD,
                activebackground=CARD, cursor="hand2"
            ).pack(side="left", padx=(0, 20))

        rb(fmt_row, "9:16  Vertical  (Shorts / TikTok / Reels)", "9:16", 0)
        rb(fmt_row, "16:9  Horizontal  (YouTube / Facebook)", "16:9", 1)

        # ── 3. DESTINO & NOMBRE ───────────────────────────────────────────────
        f_dest = lf(left, "3. Carpeta de Guardado y Nombre del Video", WHITE)
        f_dest.pack(fill="x", pady=(0, 8))

        lbl(f_dest, "Carpeta de destino:").pack(anchor="w")
        row_d = tk.Frame(f_dest, bg=CARD); row_d.pack(fill="x", pady=(3, 6))
        entry(row_d, self.out_dir_var).pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        btn(row_d, "Cambiar Carpeta", self.browse_output_dir).pack(side="right")

        lbl(f_dest, "Nombre del archivo (.mp4):").pack(anchor="w")
        entry(f_dest, self.out_name_var, fg=GOLD, font=("Consolas", 10, "bold")).pack(
            fill="x", ipady=4, pady=(3, 0))

        # ════════ RIGHT COLUMN ═══════════════════════════════════════════════

        # ── 4. MUSICA & VELOCIDAD ─────────────────────────────────────────────
        f_mus = lf(right, "4. Musica de Fondo y Velocidad", GOLD)
        f_mus.pack(fill="x", pady=(0, 8))

        tk.Checkbutton(
            f_mus, text="Incluir Musica de Fondo  (Bucle Infinito, -18dB)",
            variable=self.bgm_enable_var, font=("Segoe UI", 10, "bold"),
            fg=WHITE, bg=CARD, selectcolor=BG,
            activebackground=CARD, cursor="hand2"
        ).pack(anchor="w", pady=(0, 6))

        g = tk.Frame(f_mus, bg=CARD); g.pack(fill="x")

        lbl(g, "Pista de musica:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cb_track = ttk.Combobox(g, textvariable=self.selected_music_var,
                                     values=self._music_list(), state="readonly", width=28)
        self.cb_track.grid(row=0, column=1, sticky="w")
        tk.Button(g, text="Actualizar", font=("Segoe UI", 8, "bold"),
                  bg=BTN_DIM, fg=WHITE, bd=0, padx=6, pady=2,
                  cursor="hand2", command=self.refresh_music
                  ).grid(row=0, column=2, padx=(6, 0))

        lbl(g, "Speed Ramp:").grid(row=1, column=0, sticky="w", pady=(6, 0), padx=(0, 8))
        ttk.Combobox(
            g, textvariable=self.speed_ramp_var, state="readonly", width=34,
            values=[
                "1.5x Frenetico (Recomendado)",
                "1.8x Extremo (Ultra Rapido)",
                "1.0x Normal (Estandar)"
            ]
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(6, 0))

        # ── 5. HOOK & VARIACION ───────────────────────────────────────────────
        f_hook = lf(right, "5. Modo de Entrada (Hook) y Variacion", WHITE)
        f_hook.pack(fill="x", pady=(0, 8))

        lbl(f_hook, "Primer Clip del Video:").pack(anchor="w")
        ttk.Combobox(
            f_hook, textvariable=self.hook_mode_var, state="readonly", width=46,
            values=[
                "Deteccion Automatica",
                "Forzar Entrada Rojo (Headshot)",
                "Forzar Entrada Amarillo (Fallando)"
            ]
        ).pack(anchor="w", pady=(3, 6))
        tk.Checkbutton(
            f_hook,
            text="Garantizar Variacion Unica & Seleccion Frenetica por Movimiento",
            variable=self.variation_var, font=("Segoe UI", 9, "bold"),
            fg=GOLD, bg=CARD, selectcolor=BG,
            activebackground=CARD, cursor="hand2"
        ).pack(anchor="w")

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
        if d: self.out_dir_var.set(d)

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
            messagebox.showwarning("Atención", f"El archivo de video seleccionado no existe:\n{gameplay_file}")
            return

        if resources_dir and not os.path.exists(resources_dir):
            messagebox.showwarning("Atención", f"La carpeta de recursos seleccionada no existe:\n{resources_dir}")
            return

        if audio_file and not os.path.exists(audio_file):
            messagebox.showwarning("Atención", f"El archivo de audio seleccionado no existe:\n{audio_file}")
            return

        # Si el usuario seleccionó un video pero no subió un audio separado, extraer el audio del video automáticamente
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
            if aspect_flag == "16:9":
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

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and self.last_rendered_file.exists():
                self.after(0, self._on_success)
            else:
                self.after(0, lambda: self._on_error(res.stderr or res.stdout))
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
        messagebox.showerror("Error", f"No se pudo generar el video:\n\n{err[:500]}")


if __name__ == "__main__":
    app = FreeFireEditorApp()
    app.mainloop()
