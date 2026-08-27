"""
core/transcriber.py
====================
Transcripción de audio con OpenAI Whisper (100% gratuito, local).
Extrae texto con timestamps precisos a nivel de palabra.
"""

import os
import tempfile
import warnings
from pathlib import Path
from typing import List, Dict, Optional, Any

warnings.filterwarnings("ignore")


class Transcriber:
    """
    Transcribe el audio de un video usando Whisper y devuelve
    segmentos con timestamps de inicio/fin.
    """

    def __init__(
        self,
        model_name: str = "base",
        language: str = "es",
        console: Optional[Any] = None,
    ):
        self.model_name = model_name
        self.language = None if language == "auto" else language
        self.console = console
        self.model = None
        self._audio_path = None

    def _log(self, msg: str):
        if self.console:
            self.console.print(f"  [dim]{msg}[/dim]")
        else:
            print(f"  {msg}")

    def _load_model(self):
        """Carga el modelo de Whisper (se descarga automáticamente la primera vez)."""
        if self.model is not None:
            return

        self._log(f"Cargando modelo Whisper '{self.model_name}'...")
        self._log("(La primera vez descarga el modelo, puede tardar unos minutos)")

        import whisper
        self.model = whisper.load_model(self.model_name)
        self._log(f"✓ Modelo '{self.model_name}' cargado")

    def _extract_audio(self, video_path: str) -> str:
        """Extrae el audio del video a un archivo WAV temporal via FFmpeg."""
        self._log("Extrayendo audio del video...")

        import subprocess
        tmp_dir = tempfile.gettempdir()
        audio_path = os.path.join(tmp_dir, "viralclip_audio.wav")

        result = subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-ar", "16000", "-ac", "1", "-f", "wav", audio_path
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error al extraer audio: {result.stderr[-500:]}")

        self._log(f"✓ Audio extraído: {audio_path}")
        self._audio_path = audio_path
        return audio_path

    def transcribe(self, video_path: str) -> List[Dict]:
        """
        Transcribe el video y devuelve lista de segmentos.

        Returns:
            Lista de dicts con:
                - start (float): tiempo de inicio en segundos
                - end (float): tiempo de fin en segundos
                - text (str): texto transcrito
                - words (list): lista de palabras con timestamps individuales
        """
        self._load_model()
        audio_path = self._extract_audio(video_path)

        self._log(f"Iniciando transcripción (modelo: {self.model_name})...")

        import whisper

        # Opciones de transcripción
        options = {
            "task": "transcribe",
            "word_timestamps": True,  # timestamps por palabra
            "verbose": False,
        }
        if self.language:
            options["language"] = self.language

        result = self.model.transcribe(audio_path, **options)

        segments = self._process_segments(result["segments"])
        self._log(f"✓ Transcripción completada: {len(segments)} segmentos")

        # Limpiar temporal
        try:
            os.remove(audio_path)
        except Exception:
            pass

        return segments

    def _process_segments(self, raw_segments: list) -> List[Dict]:
        """
        Procesa los segmentos crudos de Whisper y los normaliza.
        Combina segmentos muy cortos con el siguiente.
        """
        segments = []

        for seg in raw_segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            # Extraer palabras con timestamps
            words = []
            if "words" in seg and seg["words"]:
                for w in seg["words"]:
                    words.append({
                        "word": w.get("word", "").strip(),
                        "start": float(w.get("start", seg["start"])),
                        "end": float(w.get("end", seg["end"])),
                        "probability": float(w.get("probability", 1.0)),
                    })

            segments.append({
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "text": text,
                "words": words,
                "duration": float(seg["end"]) - float(seg["start"]),
            })

        return segments

    def get_full_text(self, segments: List[Dict]) -> str:
        """Concatena todos los segmentos en texto completo."""
        return " ".join(s["text"] for s in segments)

    def get_words_at_time(
        self, segments: List[Dict], time_start: float, time_end: float
    ) -> List[Dict]:
        """
        Devuelve todas las palabras que caen dentro del rango de tiempo.

        Args:
            segments: Segmentos de Whisper
            time_start: Tiempo de inicio
            time_end: Tiempo de fin

        Returns:
            Lista de palabras con timestamps normalizados al inicio del clip
        """
        words_in_range = []
        for seg in segments:
            if seg["end"] < time_start or seg["start"] > time_end:
                continue
            for word in seg.get("words", []):
                if word["start"] >= time_start and word["end"] <= time_end:
                    # Normalizar timestamps al inicio del clip
                    words_in_range.append({
                        "word": word["word"],
                        "start": word["start"] - time_start,
                        "end": word["end"] - time_start,
                        "probability": word.get("probability", 1.0),
                    })
        return words_in_range
