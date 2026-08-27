"""
core/editor.py
===============
Orquestador de edición: calcula crop, genera captions MrBeast
y delega el renderizado visual a Remotion.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class Editor:
    TARGET_WIDTH = 1080
    TARGET_HEIGHT = 1920

    def __init__(
        self,
        video_path: str,
        output_dir: str,
        config: dict,
        segments: List[Dict],           # Segmentos de Whisper (para captions)
        use_zoom: bool = True,
        use_subtitles: bool = True,
        use_split_screen: bool = False,
        subtitle_style: str = "viral_yellow",
        face_detection: bool = True,
        forced_layout: Optional[str] = None,
        console: Optional[Any] = None,
    ):
        self.video_path = video_path
        self.output_dir = output_dir
        self.config = config
        self.segments = segments
        self.use_zoom = use_zoom
        self.use_subtitles = use_subtitles
        self.subtitle_style = subtitle_style
        self.face_detection = face_detection
        self.forced_layout = forced_layout
        self.console = console

        # Auto-detectar si es video de 'Si te ríes pierdes' o similar para aplicar Ranking List
        video_name_upper = Path(video_path).name.upper()
        if "SI TE RÍES PIERDES" in video_name_upper or "SI TE RIES PIERDES" in video_name_upper or "RISA" in video_name_upper:
            self.forced_layout = "ranking_list"

        effects_cfg = config.get("effects", {})
        advanced_cfg = config.get("advanced", {})
        output_cfg = config.get("output", {})

        self.fps_out = output_cfg.get("fps", 30)
        self.face_smoothing = advanced_cfg.get("face_tracking_smoothing", 0.85)
        self.face_sample_rate = advanced_cfg.get("face_detection_sample_rate", 5)

        self._video_info: Optional[Dict] = None

        # Ruta al proyecto Remotion
        self.remotion_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion"
        )

        # Motor de captions (inicializado una vez, reutilizado por clip)
        from core.caption_engine import CaptionEngine
        self._caption_engine = CaptionEngine(
            chunk_size=3,
            max_chunk_duration=2.5,
            language=config.get("general", {}).get("language", "es"),
        )

    def _log(self, msg: str):
        if self.console:
            self.console.print(f"    [dim cyan]{msg}[/dim cyan]")

    # ──────────────────────────────────────────────────────────────────────────
    # Información del video (cacheada)
    # ──────────────────────────────────────────────────────────────────────────

    def _get_video_info(self) -> Dict:
        if self._video_info is not None:
            return self._video_info

        import cv2
        cap = cv2.VideoCapture(self.video_path)
        info = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": cap.get(cv2.CAP_PROP_FPS) or 30.0,
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "duration": (int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / (cap.get(cv2.CAP_PROP_FPS) or 30.0)),
        }
        cap.release()
        self._video_info = info
        return info

    def _create_ranking_composite_video(self, clip_number: int) -> Tuple[str, float, float, List[Dict]]:
        """
        Para el formato ranking_list:
        1. Omite los primeros 40 segundos (introducción / habla del creador).
        2. Divide la duración útil del video en 5 zonas iguales y encuentra el tramo de mayor energía (meme) en cada zona.
        3. Ensambla (concatena) los 5 memes usando FFmpeg en un nuevo video compuesto sin intro ni tiempos muertos.
        4. Calcula la duración exacta de cada meme y construye ranking_items con sus títulos/emojis sincronizados.
        """
        self._log("✂️ Generando compilación de 5 memes individuales (omitida la introducción)...")

        video_info = self._get_video_info()
        orig_dur = video_info.get("duration", 300.0)

        # Omitir introducción (primeros 40 segundos si el video dura más de 90s)
        valid_start = 40.0 if orig_dur > 90.0 else 0.0
        valid_dur = max(orig_dur - valid_start, 60.0)

        # Dividir el resto del video en 5 zonas
        zone_dur = valid_dur / 5.0
        meme_dur_target = 18.0  # ~18s por meme (total 5 memes x 18s = 90s)

        sub_files = []
        ranking_items = []
        accumulated_time = 0.0
        tmp_dir = tempfile.gettempdir()

        EMOJIS = ["🤣", "🤯", "🌊", "👨‍🦲", "💀", "💣", "💥", "🐶", "🤸"]
        ranks = [5, 4, 3, 2, 1]

        for i, r in enumerate(ranks):
            zone_start = valid_start + i * zone_dur
            zone_end = zone_start + zone_dur

            # Buscar segmentos en esta zona para detectar el meme y su final natural por silencio/pausa
            zone_segs = [seg for seg in self.segments if zone_start <= seg["start"] <= zone_end]
            zone_words = [
                w for seg in self.segments
                for w in seg.get("words", [])
                if zone_start <= w.get("start", 0) <= zone_end
            ]

            if zone_segs:
                m_start = zone_segs[0]["start"]
                m_end = zone_segs[0]["end"]

                for seg in zone_segs[1:]:
                    gap = seg["start"] - m_end
                    if gap > 1.2:  # ¡Pausa/silencio detectado! El meme terminó aquí.
                        break
                    m_end = seg["end"]
                    if (m_end - m_start) >= 16.0:  # Límite máximo para mantener ritmo dinámico
                        break

                m_end = min(m_end + 0.3, zone_end)
            else:
                m_start = zone_start
                m_end = min(zone_start + 14.0, zone_end)

            actual_dur = max(round(m_end - m_start, 2), 8.0)

            # Cortar sub-clip individual con FFmpeg
            sub_file = os.path.join(tmp_dir, f"ranking_sub_{clip_number}_{i}.mp4")
            cmd_cut = [
                "ffmpeg", "-y",
                "-ss", str(round(m_start, 2)),
                "-to", str(round(m_start + actual_dur, 2)),
                "-i", self.video_path,
                "-c", "copy",
                sub_file
            ]
            subprocess.run(cmd_cut, capture_output=True)
            sub_files.append(sub_file)

            # Extraer palabras limpias para el título descriptivo del meme
            clean_kws = [
                w["word"].strip(".,!?\"'").lower() for w in zone_words
                if len(w["word"]) > 3 and w["word"].lower() not in {"este", "esta", "esto", "estos", "para", "pero", "como", "cuando", "porque", "with", "that", "this", "from", "they", "have"}
            ]
            w1 = clean_kws[0] if len(clean_kws) > 0 else "meme"
            w2 = clean_kws[1] if len(clean_kws) > 1 else f"nivel {r}"
            emoji = EMOJIS[i % len(EMOJIS)]

            title_desc = f"{w1} {w2} {emoji}"

            ranking_items.append({
                "rank": r,
                "title": title_desc,
                "subtitle": "Si te ríes pierdes...",
                "start": round(accumulated_time, 2),
                "end": round(accumulated_time + actual_dur, 2),
            })

            accumulated_time += actual_dur

        # Concatenar los 5 sub-clips en un único video con FFmpeg
        concat_list_file = os.path.join(tmp_dir, f"concat_list_{clip_number}.txt")
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for sf in sub_files:
                clean_sf = sf.replace("\\", "/")
                f.write(f"file '{clean_sf}'\n")

        composite_filename = f"ranking_meme_compilation_{clip_number}.mp4"
        public_input_dir = os.path.join(self.remotion_dir, "public", "input")
        os.makedirs(public_input_dir, exist_ok=True)
        composite_path = os.path.join(public_input_dir, composite_filename)

        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_file,
            "-c", "copy",
            composite_path
        ]
        subprocess.run(cmd_concat, capture_output=True)

        self._log(f"✓ Compilación de 5 memes creada ({accumulated_time:.1f}s total)")
        rel_composite_path = f"input/{composite_filename}"
        return rel_composite_path, 0.0, accumulated_time, ranking_items

    # ──────────────────────────────────────────────────────────────────────────
    # Crop params con face tracking
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_crop_params(
        self, clip_data: Dict, video_info: Dict
    ) -> Tuple[List[Dict], Dict]:
        orig_w = video_info["width"]
        orig_h = video_info["height"]

        if self.face_detection:
            try:
                from core.face_tracker import FaceTracker
                tracker = FaceTracker(
                    smoothing=self.face_smoothing,
                    sample_rate=self.face_sample_rate,
                    console=self.console,
                )
                self._log("Detectando caras para smart crop...")
                crop_positions, crop_meta = tracker.analyze_clip(
                    self.video_path,
                    clip_data["start"],
                    clip_data["end"],
                    self.TARGET_WIDTH,
                    self.TARGET_HEIGHT,
                )
                self._log(f"✓ Smart crop calculado ({len(crop_positions)} keyframes)")
                return crop_positions, crop_meta
            except Exception as e:
                self._log(f"⚠ Face tracking falló: {e}. Usando crop centrado.")

        from core.face_tracker import get_simple_crop_params
        simple = get_simple_crop_params(orig_w, orig_h, self.TARGET_WIDTH, self.TARGET_HEIGHT)

        fps = video_info["fps"]
        start_frame = int(clip_data["start"] * fps)
        end_frame = int(clip_data["end"] * fps)
        n_frames = end_frame - start_frame

        crop_positions = [
            {"frame_idx": start_frame + i, **simple, "has_face": False}
            for i in range(n_frames)
        ]
        crop_meta = {
            "orig_width": orig_w,
            "orig_height": orig_h,
            "crop_w": simple["crop_w"],
            "crop_h": simple["crop_h"],
            "fps": fps,
        }
        return crop_positions, crop_meta

    # ──────────────────────────────────────────────────────────────────────────
    # Captions MrBeast (word-by-word con chunks e impactos)
    # ──────────────────────────────────────────────────────────────────────────

    def _build_captions(self, clip_data: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Genera captionChunks e impactMoments para el clip dado.
        Los timestamps son relativos al inicio del clip.
        """
        start = clip_data["start"]
        end = clip_data["end"]

        caption_data = self._caption_engine.process_segments(
            self.segments,
            clip_start_sec=start,
            clip_end_sec=end,
        )

        caption_chunks = caption_data.get("chunks", [])
        impact_moments = caption_data.get("impact_moments", [])

        self._log(
            f"✓ Captions: {len(caption_chunks)} chunks, "
            f"{len(impact_moments)} momentos de impacto"
        )
        return caption_chunks, impact_moments

    # ──────────────────────────────────────────────────────────────────────────
    # Proceso principal de un clip
    # ──────────────────────────────────────────────────────────────────────────

    def process_clip(self, clip_data: Dict, output_path: str, clip_number: int = 1):
        start = clip_data["start"]
        end = clip_data["end"]
        duration = end - start

        self._log(f"📎 Clip {clip_number}: {start:.1f}s → {end:.1f}s ({duration:.1f}s)")

        # 1. Video info
        video_info = self._get_video_info()

        # 2. Crop params
        crop_positions, crop_meta = self._compute_crop_params(clip_data, video_info)

        # 3. Captions word-by-word
        caption_chunks, impact_moments = self._build_captions(clip_data)

        # 4. Palabras del clip (para compatibilidad / fallback en Remotion)
        clip_words = [
            {
                "word": w["word"],
                "start": round(w["start"] - start, 4),
                "end": round(w["end"] - start, 4),
                "confidence": w.get("probability", 1.0),
            }
            for seg in self.segments
            for w in seg.get("words", [])
            if w.get("start", 0) >= start and w.get("end", 0) <= end
        ]

        # Lista de arquetipos de diseño visual — 5 estilos únicos por petición
        LAYOUT_ARCHETYPES = [
            "header_banner",        # 1: Header Title Banner clásico
            "zoom_burst",           # 2: Texto explosivo centrado (super viral)
            "neon_pointer",         # 3: Punteros/Flechas neón con tracking
            "financial_highlight",  # 4: Subtítulos amarillos estilo financiero
            "zoom_burst",           # 5: segunda aparición de zoom_burst con hook diferente
        ]

        layout_style = self.forced_layout if self.forced_layout else LAYOUT_ARCHETYPES[(clip_number - 1) % len(LAYOUT_ARCHETYPES)]

        # Generar un título corto y directo con PALABRAS CLAVE EN MAYÚSCULAS según el clip
        hook_name = clip_data.get("hook_name", "Momento Viral")
        hook_emoji = clip_data.get("hook_emoji", "🔥")
        hook_id = clip_data.get("hook_id", "")
        text = clip_data.get("text", "")

        # Extraer palabras clave principales del texto del clip
        raw_words = [w.strip(".,!?\"'") for w in text.split() if len(w) > 3]
        clean_words = [w.upper() for w in raw_words if w.lower() not in {"este", "esta", "esto", "estos", "para", "pero", "como", "cuando", "porque", "with", "that", "this", "from", "they", "have"}]
        
        kw1 = clean_words[0] if len(clean_words) > 0 else "MOMENT"
        kw2 = clean_words[1] if len(clean_words) > 1 else "INSANE"

        lang_is_en = self.config.get("general", {}).get("language", "es") == "en" or "Jesser" in self.video_path

        # ── Variantes únicas por número de clip (garantiza 5 hooks distintos) ────
        # Cada clip_number 1-5 mapea a un ángulo de hook completamente diferente.
        # Esto anula el fallback genérico y asegura diversidad visual + narrativa.
        HOOK_VARIANTS_EN = [
            # clip 1 — Contracorriente / Verdad oculta
            (f"{hook_emoji} The TRUTH Nobody Tells You About {kw1}",
             f"Everyone Was WRONG About {kw2}"),
            # clip 2 — Número específico / Stats impactantes
            (f"{hook_emoji} INSANE {kw1} Stats That Will BLOW Your Mind",
             f"The Numbers Behind {kw2} Are WILD"),
            # clip 3 — Reacción / Momento real
            (f"{hook_emoji} This {kw1} Moment Left Everyone SPEECHLESS",
             f"Nobody Expected This From {kw2}"),
            # clip 4 — Contraste / VS
            (f"{hook_emoji} {kw1} VS {kw2} — The REAL Difference",
             "Which Side Are YOU On?"),
            # clip 5 — Advertencia / Warning urgente
            (f"{hook_emoji} STOP Sleeping On {kw1}",
             f"This Changes EVERYTHING About {kw2}"),
        ]

        HOOK_VARIANTS_ES = [
            (f"{hook_emoji} La VERDAD que NADIE dice sobre {kw1}",
             f"Todo el mundo estaba EQUIVOCADO con {kw2}"),
            (f"{hook_emoji} Las CIFRAS de {kw1} te dejarán sin palabras",
             f"Los números detrás de {kw2} son LOCOS"),
            (f"{hook_emoji} Este momento de {kw1} dejó a todos BOQUIABIERTOS",
             f"Nadie esperó esto de {kw2}"),
            (f"{hook_emoji} {kw1} VS {kw2} — La DIFERENCIA REAL",
             "¿De qué lado estás tú?"),
            (f"{hook_emoji} DEJA de ignorar {kw1}",
             f"Esto cambia TODO sobre {kw2}"),
        ]

        # Seleccionar variante según clip_number (1-based, rotativo cada 5)
        variant_idx = (clip_number - 1) % 5
        if lang_is_en:
            # Si el hook_id tiene plantilla específica, mezclarla con la variante
            if hook_id in {"contracorriente", "numero_especifico", "error", "promesa",
                           "secreto", "pregunta", "lista", "contraste", "advertencia", "caso_real"}:
                # Generar desde plantilla específica primero
                hook_map_en = {
                    "contracorriente": (f"{hook_emoji} The TRUTH About {kw1}", f"What NOBODY Tells You About {kw2}"),
                    "numero_especifico": (f"{hook_emoji} INSANE STATS on {kw1}", f"Did You Know This About {kw2}?"),
                    "error": (f"{hook_emoji} The WORST MISTAKE With {kw1}", f"Never Do This With {kw2}"),
                    "promesa": (f"{hook_emoji} How To MASTER {kw1} FAST", f"The Ultimate Method For {kw2}"),
                    "secreto": (f"{hook_emoji} The HIDDEN SECRET of {kw1}", f"What They Didn't Tell You About {kw2}"),
                    "pregunta": (f"{hook_emoji} What Happened To {kw1}?", f"The Truth Behind {kw2}"),
                    "lista": (f"{hook_emoji} TOP MOMENT With {kw1}", f"The Best Play In {kw2}"),
                    "contraste": (f"{hook_emoji} {kw1} VS {kw2}", "The Big Difference Explained"),
                    "advertencia": (f"{hook_emoji} WARNING About {kw1}", f"Be Careful With {kw2}"),
                    "caso_real": (f"{hook_emoji} CRAZY MOMENT With {kw1}", f"What Happened To {kw2}"),
                }
                hook_title, hook_header = hook_map_en[hook_id]
            else:
                # Usar variante forzada por clip_number
                hook_title, hook_header = HOOK_VARIANTS_EN[variant_idx]
        else:
            if hook_id in {"contracorriente", "numero_especifico", "error", "promesa",
                           "secreto", "pregunta", "lista", "contraste", "advertencia", "caso_real"}:
                hook_map_es = {
                    "contracorriente": (f"{hook_emoji} La MENTIRA de {kw1}", f"Lo que NADIE TE DICE sobre {kw2}"),
                    "numero_especifico": (f"{hook_emoji} La CIFRA EXACTA de {kw1}", f"¿Sabías esto sobre {kw2}?"),
                    "error": (f"{hook_emoji} ¡El PEOR ERROR con {kw1}!", f"No cometas esto jamás en {kw2}"),
                    "promesa": (f"{hook_emoji} Cómo LOGRAR {kw1} RÁPIDO", f"El método definitivo para {kw2}"),
                    "secreto": (f"{hook_emoji} El SECRETO OCULTO de {kw1}", f"Lo que no querían que sepas de {kw2}"),
                    "pregunta": (f"{hook_emoji} ¿Qué Pasó con {kw1}?", f"La verdad detrás de {kw2}"),
                    "lista": (f"{hook_emoji} TOP 3 Datos sobre {kw1}", f"La lista definitiva de {kw2}"),
                    "contraste": (f"{hook_emoji} {kw1} VS {kw2}", "La gran diferencia explicada"),
                    "advertencia": (f"{hook_emoji} ¡CUIDADO con {kw1}!", f"Advertencia urgente sobre {kw2}"),
                    "caso_real": (f"{hook_emoji} El CASO REAL de {kw1}", f"Lo que le pasó a {kw2}"),
                }
                hook_title, hook_header = hook_map_es[hook_id]
            else:
                hook_title, hook_header = HOOK_VARIANTS_ES[variant_idx]

        # Copiar video a remotion/public/input si no existe
        rel_video_path = f"input/{Path(self.video_path).name}"
        public_input_dir = os.path.join(self.remotion_dir, "public", "input")
        os.makedirs(public_input_dir, exist_ok=True)
        dest_video = os.path.join(public_input_dir, Path(self.video_path).name)
        if not os.path.exists(dest_video):
            import shutil
            shutil.copy2(self.video_path, dest_video)

        # Generar los 5 ítems del ranking con descripciones cortas + emojis AL LADO DE CADA NÚMERO (1. al 5.)
        ranking_items = []
        if layout_style == "ranking_list":
            # Para el formato ranking_list:
            # 1. Omite los primeros 40s (introducción/habla del creador).
            # 2. Extrae 5 memes/momentos de risa de 5 zonas del video.
            # 3. Concatenación con FFmpeg en un nuevo video compuesto sin intro ni tiempos muertos.
            rel_video_path, start, duration, ranking_items = self._create_ranking_composite_video(clip_number)

        remotion_props = {
            "videoPath": rel_video_path,
            "startTime": start,
            "durationInSeconds": duration,
            "fps": self.fps_out,
            "cropMeta": crop_meta,
            "cropPositions": crop_positions,
            "words": clip_words,
            "captionChunks": caption_chunks,
            "impactMoments": impact_moments,
            "viralScore": clip_data.get("viral_score", 0.5),
            "useZoom": self.use_zoom,
            "useSubtitles": self.use_subtitles,
            "subtitleStyle": self.subtitle_style,
            "logoPath": "logo.png",
            "layoutStyle": layout_style,
            "hookTitle": hook_title,
            "hookHeader": hook_header,
            "rankingItems": ranking_items,
        }

        # 6. Guardar props JSON en temp
        tmp_dir = tempfile.gettempdir()
        json_path = os.path.join(tmp_dir, f"viral_props_clip_{clip_number}.json").replace("\\", "/")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(remotion_props, f)

        self._log(f"✓ Props exportados ({Path(json_path).name})")
        self._log("Renderizando con Remotion...")

        # 7. Llamar a Remotion CLI
        cmd = [
            "npx", "remotion", "render",
            "ViralComposition",
            output_path,
            f"--props={json_path}",
            "--browser-executable=C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "--log", "info",
        ]

        result = subprocess.run(
            cmd,
            cwd=self.remotion_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=(os.name == "nt"),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        if result.returncode != 0:
            self._log(f"⚠ Error en Remotion:\n{result.stderr[-800:]}")
            raise RuntimeError("Fallo en render de Remotion")

        self._log(f"✅ Clip {clip_number} completado: {Path(output_path).name}")

        # Limpiar JSON temporal
        try:
            os.remove(json_path)
        except Exception:
            pass
