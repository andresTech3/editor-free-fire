"""
viraleditor/transcription/whisper_client.py
============================================
Integración Whisper — transcripción + word timestamps.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional, Callable

__all__ = ["WhisperClient", "WordToken", "load_transcript"]


class WordToken:
    __slots__ = ("word", "start", "end")
    def __init__(self, word: str, start: float, end: float):
        self.word  = word.strip()
        self.start = start
        self.end   = end
    def __repr__(self):
        return f"<Word '{self.word}' {self.start:.2f}s-{self.end:.2f}s>"


class WhisperClient:
    """
    Wraps OpenAI Whisper for audio transcription.

    Usage:
        client = WhisperClient(model="base")
        result = client.transcribe("audio.mp3")
        words  = client.words_in_range(result, 45.0, 105.0)
    """

    def __init__(self, model: str = "base", language: str = "en"):
        self.model_name = model
        self.language   = language
        self._model     = None   # lazy load

    def _load(self, progress_cb: Optional[Callable] = None):
        if self._model is None:
            if progress_cb:
                progress_cb("Loading Whisper model...")
            import whisper
            self._model = whisper.load_model(self.model_name)

    def transcribe(
        self,
        audio_path:   str,
        cache_path:   Optional[str] = None,
        progress_cb:  Optional[Callable] = None,
    ) -> dict:
        """
        Transcribes audio. Returns Whisper result dict with word timestamps.
        If cache_path exists, loads from cache instead.
        """
        if cache_path and Path(cache_path).exists():
            if progress_cb:
                progress_cb(f"Loading cached transcript: {Path(cache_path).name}")
            return load_transcript(cache_path)

        self._load(progress_cb)

        if progress_cb:
            progress_cb(f"Transcribing: {Path(audio_path).name}...")

        # Clean language code: if 'auto', 'en / es / auto', or multi-word, pass None for auto-detection
        lang = self.language.strip().lower() if self.language else None
        if not lang or "auto" in lang or "/" in lang or len(lang) > 3:
            lang = None

        result = self._model.transcribe(
            audio_path,
            language=lang,
            word_timestamps=True,
            verbose=False,
        )

        if cache_path:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            if progress_cb:
                progress_cb(f"Transcript saved: {Path(cache_path).name}")

        return result

    @staticmethod
    def words_in_range(
        transcript: dict,
        start:      float,
        end:        float,
    ) -> list[WordToken]:
        """Returns word tokens within [start, end] seconds."""
        tokens = []
        for seg in transcript.get("segments", []):
            if seg.get("end", 0) < start - 0.5:
                continue
            if seg.get("start", 0) > end + 0.5:
                break
            for w in seg.get("words", []):
                ws = w.get("start", 0)
                we = w.get("end", 0)
                if ws >= start and we <= end:
                    tokens.append(WordToken(w.get("word", ""), ws, we))
        return tokens

    @staticmethod
    def full_text(transcript: dict) -> str:
        """Returns plain text of full transcript."""
        return transcript.get("text", "")

    @staticmethod
    def segments(transcript: dict) -> list[dict]:
        return transcript.get("segments", [])


def load_transcript(path: str) -> dict:
    """Load a cached Whisper transcript JSON."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)
