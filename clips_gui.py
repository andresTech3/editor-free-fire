"""
clips_gui.py
=============
GUI Dedicada para el Recopilador de Clips de Free Fire v2.0.

Permite seleccionar:
  - Video de Gameplay (input/IMG_0930.MOV u otro)
  - 8 Categorías de eventos de gameplay (Tiros todo rojo, Squad wipes, Movimiento, Sniper, Booyah, Fallando, Muertes, Highlights)
  - Aspect Ratio (9:16 Vertical, 16:9 Horizontal, 1:1 Cuadrado)
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

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from freefire.clip_extractor import extract_event_clips
    from freefire.presets import OUTPUT_DIR
except ImportError as e:
    print(f"Error importando módulos: {e}")
    OUTPUT_DIR = BASE_DIR / "output" / "FreeFire"


class ClipExtractorGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🎯 Recopilador de Clips — Free Fire Edition")
        self.geometry("780x700")
        self.resizable(False, False)

        self.bg_color = "#12121e"
        self.card_bg = "#1e1e2f"
        self.fg_color = "#ffffff"
        self.accent_red = "#ff0055"
        self.accent_cyan = "#00f0ff"
        self.text_dim = "#a0a0c0"

        self.configure(bg=self.bg_color)
        self._set_styles()

        self.video_path_var = tk.StringVar(value="")
        self.event_type_var = tk.StringVar(value="tiros_rojo")
        self.aspect_ratio_var = tk.StringVar(value="9:16")
        self.max_clips_var = tk.IntVar(value=5)
        self.clip_dur_var = tk.DoubleVar(value=3.0)
        self.is_processing = False

        input_dir = BASE_DIR / "input"
        if input_dir.exists():
            vids = [f for f in input_dir.iterdir() if f.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}]
            if vids:
                self.video_path_var.set(str(vids[0]))

        self._build_ui()

    def _set_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")

    def _build_ui(self):
        header_frame = tk.Frame(self, bg=self.bg_color, pady=12)
        header_frame.pack(fill="x", padx=20)

        lbl_title = tk.Label(
            header_frame,
            text="🎯 RECOPILADOR DE CLIPS — FREE FIRE",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_color,
            fg=self.accent_red,
        )
        lbl_title.pack(anchor="w")

        # ── SECCIÓN 1: Selección de Video ─────────────────────────────────
        card_video = tk.Frame(self, bg=self.card_bg, bd=0, padx=15, pady=10)
        card_video.pack(fill="x", padx=20, pady=6)

        lbl_v_title = tk.Label(card_video, text="📹 Video de Gameplay (Input)", font=("Segoe UI", 11, "bold"), bg=self.card_bg, fg=self.accent_cyan)
        lbl_v_title.pack(anchor="w", pady=(0, 4))

        entry_frame = tk.Frame(card_video, bg=self.card_bg)
        entry_frame.pack(fill="x")

        txt_video = tk.Entry(
            entry_frame,
            textvariable=self.video_path_var,
            font=("Segoe UI", 9),
            bg="#2a2a40",
            fg="#ffffff",
            insertbackground="white",
            bd=1,
            relief="solid",
        )
        txt_video.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 10))

        btn_browse = tk.Button(
            entry_frame, text="📁 Buscar...", command=self._browse_video,
            bg="#3a3a55", fg="#ffffff", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=4, cursor="hand2"
        )
        btn_browse.pack(side="right")

        # ── SECCIÓN 2: Tipo de Recopilación (8 Modos) ─────────────────────
        card_type = tk.Frame(self, bg=self.card_bg, bd=0, padx=15, pady=10)
        card_type.pack(fill="x", padx=20, pady=6)

        lbl_t_title = tk.Label(card_type, text="🎯 Selecciona la Categoría de Evento", font=("Segoe UI", 11, "bold"), bg=self.card_bg, fg=self.accent_cyan)
        lbl_t_title.pack(anchor="w", pady=(0, 6))

        types_frame = tk.Frame(card_type, bg=self.card_bg)
        types_frame.pack(fill="x")

        options = [
            ("🔴 Tiros Todo Rojo (Headshots)", "tiros_rojo"),
            ("⚡ Squad Wipes / Kills (1vs4)", "squad_wipes"),
            ("🏎️ Movimiento Insano / Gloo", "movimiento"),
            ("🎯 Tiros Sniper / AWM", "sniper"),
            ("🏆 Momento BOOYAH! / Victoria", "booyah"),
            ("❌ Fallando Tiros / Fails", "fallando"),
            ("💀 Muertes / Eliminaciones", "muertes"),
            ("🔥 Highlights Generales", "highlights"),
        ]

        for i, (text, val) in enumerate(options):
            rb = tk.Radiobutton(
                types_frame, text=text, value=val, variable=self.event_type_var,
                font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color,
                selectcolor="#2a2a40", activebackground=self.card_bg, activeforeground=self.accent_cyan,
                cursor="hand2"
            )
            rb.grid(row=i // 2, column=i % 2, sticky="w", pady=3, padx=8)

        # ── SECCIÓN 3: Opciones Ajustes & Aspect Ratio ────────────────────
        card_opts = tk.Frame(self, bg=self.card_bg, bd=0, padx=15, pady=10)
        card_opts.pack(fill="x", padx=20, pady=6)

        opts_row = tk.Frame(card_opts, bg=self.card_bg)
        opts_row.pack(fill="x")

        lbl_c = tk.Label(opts_row, text="Max Jugadas:", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color)
        lbl_c.pack(side="left", padx=(0, 4))

        spin_clips = tk.Spinbox(opts_row, from_=1, to=20, textvariable=self.max_clips_var, width=5, font=("Segoe UI", 9), bg="#2a2a40", fg="white", bd=1)
        spin_clips.pack(side="left", padx=(0, 15))

        lbl_d = tk.Label(opts_row, text="Duración (seg):", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color)
        lbl_d.pack(side="left", padx=(0, 4))

        spin_dur = tk.Spinbox(opts_row, from_=1.5, to=10.0, increment=0.5, textvariable=self.clip_dur_var, width=5, font=("Segoe UI", 9), bg="#2a2a40", fg="white", bd=1)
        spin_dur.pack(side="left", padx=(0, 15))

        lbl_ar = tk.Label(opts_row, text="Formato:", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.fg_color)
        lbl_ar.pack(side="left", padx=(0, 4))

        cb_ar = ttk.Combobox(opts_row, textvariable=self.aspect_ratio_var, values=["9:16", "16:9", "1:1"], width=6, state="readonly")
        cb_ar.pack(side="left")

        # ── SECCIÓN 4: Botón de Generación y Logs ────────────────────────
        btn_frame = tk.Frame(self, bg=self.bg_color, pady=8)
        btn_frame.pack(fill="x", padx=20)

        self.btn_generate = tk.Button(
            btn_frame,
            text="🚀 GENERAR RECOPILACIÓN AHORA",
            command=self._start_generation,
            font=("Segoe UI", 12, "bold"),
            bg=self.accent_red, fg="#ffffff",
            activebackground="#cc0044", activeforeground="#ffffff",
            bd=0, pady=8, cursor="hand2",
        )
        self.btn_generate.pack(fill="x")

        log_frame = tk.Frame(self, bg=self.card_bg, padx=10, pady=8)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        lbl_log = tk.Label(log_frame, text="📋 Registro de Procesamiento:", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.text_dim)
        lbl_log.pack(anchor="w", pady=(0, 4))

        self.txt_log = tk.Text(
            log_frame, height=5, font=("Consolas", 9),
            bg="#0d0d17", fg="#00ffcc", bd=0, wrap="word"
        )
        self.txt_log.pack(fill="both", expand=True)

    def _browse_video(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Video de Gameplay",
            filetypes=[("Archivos de Video", "*.mp4 *.mov *.avi *.mkv *.webm"), ("Todos los archivos", "*.*")],
        )
        if file_path:
            self.video_path_var.set(file_path)

    def _log(self, text: str):
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")

    def _start_generation(self):
        video_path = self.video_path_var.get().strip()

        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error de Archivo", "Por favor selecciona un archivo de video válido (.mp4 o .mov).")
            return

        if self.is_processing:
            return

        self.is_processing = True
        self.btn_generate.config(state="disabled", bg="#555566", text="⏳ PROCESANDO RECOPILACIÓN...")
        self.txt_log.delete("1.0", "end")

        event_type = self.event_type_var.get()
        max_clips = self.max_clips_var.get()
        clip_duration = self.clip_dur_var.get()
        aspect_ratio = self.aspect_ratio_var.get()

        thread = threading.Thread(
            target=self._run_extraction_process,
            args=(video_path, event_type, max_clips, clip_duration, aspect_ratio),
            daemon=True,
        )
        thread.start()

    def _run_extraction_process(self, video_path: str, event_type: str, max_clips: int, clip_duration: float, aspect_ratio: str):
        try:
            self._log(f"🚀 Iniciando recopilación para: '{event_type}'")
            self._log(f"📹 Video: {os.path.basename(video_path)}")
            self._log(f"📐 Formato: {aspect_ratio} | {max_clips} jugadas de {clip_duration}s c/u\n")

            out_dir = OUTPUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)

            event_clean = event_type.lower().strip().replace(" ", "_")
            out_name = f"recopilacion_{event_clean}.mp4"
            output_file = str(out_dir / out_name)

            res_path = extract_event_clips(
                video_path=video_path,
                event_type=event_type,
                clip_duration=clip_duration,
                max_clips=max_clips,
                aspect_ratio=aspect_ratio,
                output_path=output_file,
            )

            if res_path and os.path.exists(res_path):
                size_mb = os.path.getsize(res_path) / (1024 * 1024)
                self._log("\n" + "=" * 50)
                self._log(f"🎉 ¡RECOPILACIÓN CREADA CON ÉXITO!")
                self._log(f"📁 Guardado en: {res_path}")
                self._log(f"📦 Tamaño: {size_mb:.1f} MB")
                self._log("=" * 50)

                self.after(0, lambda: self._on_success(res_path))
            else:
                self._log("\n❌ Error: No se pudo generar el video recopilatorio.")

        except Exception as e:
            self._log(f"\n❌ Excepción durante el proceso: {e}")
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_generate.config(state="normal", bg=self.accent_red, text="🚀 GENERAR RECOPILACIÓN AHORA"))

    def _on_success(self, file_path: str):
        ans = messagebox.askyesno(
            "¡Recopilación Lista!",
            f"El video recopilatorio se ha generado con éxito:\n\n{os.path.basename(file_path)}\n\n¿Deseas abrir la carpeta de salida ahora?",
        )
        if ans:
            folder = os.path.dirname(file_path)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])


if __name__ == "__main__":
    app = ClipExtractorGUI()
    app.mainloop()
