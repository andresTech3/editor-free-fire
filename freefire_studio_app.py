"""
freefire_studio_app.py
======================
🎮 Recopilador Inteligente de Clips — Free Fire Edition v2.0.

Aplicación de escritorio especializada exclusivamente en extraer y unir
clips de gameplay por categoría de evento (8 modos seleccionables),
ajuste de formato (9:16 Vertical, 16:9 Horizontal, 1:1 Cuadrado) y renderizado rápido.
"""

import sys
import os
import tempfile
import shutil
import threading
import subprocess
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Directorio raíz del proyecto y soporte PyInstaller _MEIPASS
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = PROJECT_ROOT

try:
    from freefire.presets import OUTPUT_DIR, AVATAR_CUTOUT_PATH, SENSIBILIDAD_CROPPED_PATH, LOGO_PATH
    from freefire.clip_extractor import extract_event_clips
    from freefire.gameplay_analyzer import get_video_info
except Exception as e:
    print(f"Advertencia al importar módulos: {e}")
    OUTPUT_DIR = PROJECT_ROOT / "output" / "FreeFire"


class FreeFireStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🎯 Recopilador de Clips — Free Fire Edition v2.0")
        self.geometry("880x720")
        self.minsize(820, 660)

        # Temática Dark Gaming
        self.bg_color = "#0e0e18"
        self.card_bg = "#18182a"
        self.card_bg_select = "#252540"
        self.fg_color = "#ffffff"
        self.accent_red = "#ff0055"
        self.accent_cyan = "#00f0ff"
        self.accent_gold = "#ffd700"
        self.text_dim = "#9595b8"

        self.configure(bg=self.bg_color)

        # Variables de la App
        self.input_video_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value=str(OUTPUT_DIR.resolve()))
        self.event_type_var = tk.StringVar(value="tiros_rojo")
        self.aspect_ratio_var = tk.StringVar(value="9:16")
        self.max_clips_var = tk.IntVar(value=5)
        self.clip_dur_var = tk.DoubleVar(value=3.0)
        self.is_processing = False

        # Auto-detectar video en input/
        input_folder = PROJECT_ROOT / "input"
        if input_folder.exists():
            vids = [f for f in input_folder.iterdir() if f.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}]
            if vids:
                self.input_video_var.set(str(vids[0]))

        self._set_styles()
        self._build_ui()

    def _set_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg)

        # Estilo de Notebook Pestañas
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.card_bg,
            foreground=self.text_dim,
            font=("Segoe UI", 10, "bold"),
            padding=[20, 9],
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.accent_red)],
            foreground=[("selected", "#ffffff")],
        )

    def _build_ui(self):
        # ── HEADER BANNER ──────────────────────────────────────────────────
        header = tk.Frame(self, bg=self.bg_color, pady=12, padx=20)
        header.pack(fill="x")

        lbl_logo = tk.Label(
            header,
            text="🎯 RECOPILADOR DE CLIPS — FREE FIRE EDITION",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_color,
            fg=self.accent_red,
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = tk.Label(
            header,
            text="Extrae y une automáticamente tus mejores jugadas por categoría de evento",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_dim,
        )
        lbl_sub.pack(anchor="w")

        # ── BARRA GLOBAL DE INPUT VIDEO ────────────────────────────────────
        input_card = tk.Frame(self, bg=self.card_bg, padx=15, pady=10)
        input_card.pack(fill="x", padx=20, pady=(0, 10))

        lbl_inp = tk.Label(
            input_card, text="📹 Video de Gameplay Original (Input):",
            font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.accent_cyan
        )
        lbl_inp.pack(anchor="w", pady=(0, 4))

        inp_row = tk.Frame(input_card, bg=self.card_bg)
        inp_row.pack(fill="x")

        entry_inp = tk.Entry(
            inp_row, textvariable=self.input_video_var,
            font=("Segoe UI", 9), bg="#222236", fg="#ffffff",
            bd=1, relief="solid", insertbackground="white"
        )
        entry_inp.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        btn_browse = tk.Button(
            inp_row, text="📁 Seleccionar Video...",
            command=self._browse_video, bg="#33334d", fg="#ffffff",
            font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=4, cursor="hand2"
        )
        btn_browse.pack(side="right")

        # ── NOTEBOOK PESTAÑAS ──────────────────────────────────────────────
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20)

        # Tab 1: Selector de Eventos de Clips
        self.tab_events = tk.Frame(self.notebook, bg=self.bg_color, pady=10)
        self.notebook.add(self.tab_events, text="✂️ Recopilador Inteligente")
        self._build_tab_events()

        # Tab 2: Formato & Resolución
        self.tab_format = tk.Frame(self.notebook, bg=self.bg_color, pady=10)
        self.notebook.add(self.tab_format, text="🎬 Formato & Edición")
        self._build_tab_format()

        # Tab 3: Ajustes
        self.tab_settings = tk.Frame(self.notebook, bg=self.bg_color, pady=10)
        self.notebook.add(self.tab_settings, text="⚙️ Ajustes & Recursos")
        self._build_tab_settings()

        # ── CONSOLA DE LOGS EN VIVO (Bottom) ──────────────────────────────
        console_card = tk.Frame(self, bg=self.card_bg, padx=12, pady=8)
        console_card.pack(fill="x", padx=20, pady=10)

        c_header = tk.Frame(console_card, bg=self.card_bg)
        c_header.pack(fill="x", pady=(0, 4))

        lbl_console = tk.Label(c_header, text="📋 Registro de Avance en Vivo:", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.text_dim)
        lbl_console.pack(side="left")

        btn_open_out = tk.Button(
            c_header, text="📂 Abrir Carpeta Final", command=self._open_output_folder,
            bg=self.accent_cyan, fg="#000000", font=("Segoe UI", 8, "bold"), bd=0, padx=8, pady=2, cursor="hand2"
        )
        btn_open_out.pack(side="right")

        self.txt_log = tk.Text(
            console_card, height=5, font=("Consolas", 9),
            bg="#0a0a12", fg="#00ffcc", bd=0, wrap="word"
        )
        self.txt_log.pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # PESTAÑA 1: RECOPILADOR INTELIGENTE (8 EVENTOS)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_events(self):
        card = tk.Frame(self.tab_events, bg=self.card_bg, padx=15, pady=12)
        card.pack(fill="x", pady=5)

        lbl_t = tk.Label(card, text="🎯 Selecciona la Categoría de Jugadas a Extraer:", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_gold)
        lbl_t.pack(anchor="w", pady=(0, 8))

        grid_frame = tk.Frame(card, bg=self.card_bg)
        grid_frame.pack(fill="x")

        # 8 Modos de Eventos organizados en 2 columnas
        modes = [
            ("🔴 Tiros Todo Rojo (Headshots / One Taps)", "tiros_rojo"),
            ("⚡ Squad Wipes / Kills Frenéticas (1vs4)", "squad_wipes"),
            ("🏎️ Movimiento Insano / Paredes Gloo", "movimiento"),
            ("🎯 Tiros Sniper / AWM / Barrett", "sniper"),
            ("🏆 Momento BOOYAH! / Victorias", "booyah"),
            ("❌ Fallando Tiros / Fails / Pecheadas", "fallando"),
            ("💀 Muertes / Eliminaciones", "muertes"),
            ("🔥 Highlights Generales de Acción", "highlights"),
        ]

        for i, (text, val) in enumerate(modes):
            row = i // 2
            col = i % 2
            rb = tk.Radiobutton(
                grid_frame, text=text, value=val, variable=self.event_type_var,
                font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color,
                selectcolor="#222238", activebackground=self.card_bg, activeforeground=self.accent_cyan,
                cursor="hand2"
            )
            rb.grid(row=row, column=col, sticky="w", pady=4, padx=10)

        # Fila Ajustes
        row_c = tk.Frame(card, bg=self.card_bg)
        row_c.pack(fill="x", pady=(12, 0))

        lbl_cnt = tk.Label(row_c, text="Max Jugadas:", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color)
        lbl_cnt.pack(side="left", padx=(0, 4))

        spin_cnt = tk.Spinbox(row_c, from_=1, to=20, textvariable=self.max_clips_var, width=5, font=("Segoe UI", 9), bg="#222238", fg="white", bd=1)
        spin_cnt.pack(side="left", padx=(0, 20))

        lbl_cdur = tk.Label(row_c, text="Duración/jugada (seg):", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color)
        lbl_cdur.pack(side="left", padx=(0, 4))

        spin_cdur = tk.Spinbox(row_c, from_=1.5, to=10.0, increment=0.5, textvariable=self.clip_dur_var, width=5, font=("Segoe UI", 9), bg="#222238", fg="white", bd=1)
        spin_cdur.pack(side="left")

        # Botón de Acción Principal
        self.btn_gen_clips = tk.Button(
            self.tab_events,
            text="✂️ RENDERIZAR RECOPILACIÓN AHORA",
            command=self._start_clip_extraction,
            font=("Segoe UI", 12, "bold"),
            bg=self.accent_red, fg="#ffffff",
            activebackground="#cc0044", activeforeground="#ffffff",
            bd=0, pady=10, cursor="hand2"
        )
        self.btn_gen_clips.pack(fill="x", pady=10)

    # ─────────────────────────────────────────────────────────────────────────
    # PESTAÑA 2: FORMATO & EDICIÓN
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_format(self):
        card = tk.Frame(self.tab_format, bg=self.card_bg, padx=15, pady=12)
        card.pack(fill="x", pady=5)

        lbl_f = tk.Label(card, text="📐 Formato / Aspect Ratio del Video Final:", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_cyan)
        lbl_f.pack(anchor="w", pady=(0, 8))

        fmt_frame = tk.Frame(card, bg=self.card_bg)
        fmt_frame.pack(fill="x")

        formats = [
            ("📱 9:16 Vertical (Shorts / Reels / TikTok — 1080x1920)", "9:16"),
            ("🖥️ 16:9 Horizontal (YouTube / Twitch — 1920x1080)", "16:9"),
            ("🔲 1:1 Cuadrado (Instagram / Post — 1080x1080)", "1:1"),
        ]

        for text, val in formats:
            rb = tk.Radiobutton(
                fmt_frame, text=text, value=val, variable=self.aspect_ratio_var,
                font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.fg_color,
                selectcolor="#222238", activebackground=self.card_bg, activeforeground=self.accent_cyan,
                cursor="hand2"
            )
            rb.pack(anchor="w", pady=4)

    # ─────────────────────────────────────────────────────────────────────────
    # PESTAÑA 3: AJUSTES & DIAGNÓSTICO
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_settings(self):
        card = tk.Frame(self.tab_settings, bg=self.card_bg, padx=15, pady=12)
        card.pack(fill="x", pady=5)

        lbl_s = tk.Label(card, text="📂 Carpeta de Salida para Videos Renderizados:", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.accent_cyan)
        lbl_s.pack(anchor="w", pady=(0, 4))

        row_out = tk.Frame(card, bg=self.card_bg)
        row_out.pack(fill="x", pady=(0, 10))

        entry_out = tk.Entry(row_out, textvariable=self.output_dir_var, font=("Segoe UI", 9), bg="#222238", fg="white", bd=1, relief="solid")
        entry_out.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        btn_b_out = tk.Button(
            row_out, text="📁 Cambiar...", command=self._browse_output,
            bg="#33334d", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2"
        )
        btn_b_out.pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODOS Y ACCIONES
    # ─────────────────────────────────────────────────────────────────────────
    def _browse_video(self):
        f = filedialog.askopenfilename(
            title="Seleccionar Video de Gameplay Input",
            filetypes=[("Archivos de Video", "*.mp4 *.mov *.avi *.mkv *.webm"), ("Todos los archivos", "*.*")]
        )
        if f:
            self.input_video_var.set(f)

    def _browse_output(self):
        d = filedialog.askdirectory(title="Seleccionar Carpeta de Salida")
        if d:
            self.output_dir_var.set(d)

    def _log(self, text: str):
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")

    def _open_output_folder(self):
        folder = self.output_dir_var.get()
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])

    def _start_clip_extraction(self):
        video_path = self.input_video_var.get().strip()

        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Video no Encontrado", "Por favor selecciona un video de gameplay (.mp4 o .mov).")
            return

        if self.is_processing:
            return

        self.is_processing = True
        self.btn_gen_clips.config(state="disabled", text="⏳ EXTRAYENDO Y UNIENDO CLIPS...")
        self.txt_log.delete("1.0", "end")

        threading.Thread(
            target=self._run_clip_extraction,
            args=(video_path, self.event_type_var.get(), self.max_clips_var.get(), self.clip_dur_var.get(), self.aspect_ratio_var.get()),
            daemon=True
        ).start()

    def _run_clip_extraction(self, video_path: str, event_type: str, max_clips: int, clip_duration: float, aspect_ratio: str):
        try:
            self._log(f"✂️ Iniciando extracción de clips: '{event_type}'")
            self._log(f"📹 Video Input: {os.path.basename(video_path)}")
            self._log(f"📐 Aspect Ratio: {aspect_ratio} | {max_clips} jugadas de {clip_duration}s c/u\n")

            out_dir = Path(self.output_dir_var.get())
            out_dir.mkdir(parents=True, exist_ok=True)

            event_clean = event_type.lower().strip().replace(" ", "_")
            out_file = str(out_dir / f"recopilacion_{event_clean}.mp4")

            res_path = extract_event_clips(
                video_path=video_path, event_type=event_type,
                clip_duration=clip_duration, max_clips=max_clips,
                aspect_ratio=aspect_ratio, output_path=out_file
            )

            if res_path and os.path.exists(res_path):
                size_mb = os.path.getsize(res_path) / (1024 * 1024)
                self._log("\n" + "=" * 50)
                self._log(f"🎉 ¡RECOPILACIÓN DE CLIPS CREADA CON ÉXITO!")
                self._log(f"📁 Video: {res_path} ({size_mb:.1f} MB)")
                self._log("=" * 50)
                self.after(0, lambda: self._on_success(res_path))
            else:
                self._log("\n❌ Ocurrió un error extrayendo los clips.")

        except Exception as ex:
            self._log(f"\n❌ Excepción durante extracción: {ex}")
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_gen_clips.config(state="normal", text="✂️ RENDERIZAR RECOPILACIÓN AHORA"))

    def _on_success(self, file_path: str):
        ans = messagebox.askyesno(
            "¡Proceso Completado!",
            f"La recopilación de clips se ha generado con éxito:\n\n{os.path.basename(file_path)}\n\n¿Deseas abrir la carpeta de salida ahora?"
        )
        if ans:
            self._open_output_folder()


if __name__ == "__main__":
    app = FreeFireStudioApp()
    app.mainloop()
