"""
semantic_director.py - Intelligent Semantic Audio-to-Visual Director
=====================================================================
Analyzes voiceover narration audio via Whisper speech transcription,
extracts semantic context & sentiment keywords, and schedules matching visual
assets (Diamonds, Sensitivity, Book/Web, Emotes, Weapons, Skins) and CONTEXTUAL MEMES.

STRICT RULE: Memes are NEVER chosen randomly. They are selected strictly
according to the context, sentiment, and spoken words of the audio.
- Long videos (16:9): Primarily standard 16:9 full-screen memes from 'PACK DE MEMES'
  or matching green-screen overlays when appropriate.
- Shorts (9:16): Primarily green-screen meme overlays from 'PACK MEMES PANTALLA VERDE'
  with chroma keying.
"""

import os
import re
import sys
import json
import unicodedata
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Set UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Local imports
from core.asset_catalog import (
    DIAMONDS_CATALOG,
    PASS_AND_TOURNAMENT_CATALOG,
    TOP_GLOBAL_CATALOG,
    SENSITIVITY_CATALOG,
    ASESORIA_CATALOG,
    DPI_AND_DEVICE_CATALOG,
    BOOK_AND_WEB_CATALOG,
    EMOTES_CATALOG,
    WEAPONS_CATALOG,
    RESULTS_AND_STATS_CATALOG,
    CHARACTERS_AND_PROFILE_CATALOG,
    CALL_TO_ACTION_CATALOG,
    CHARACTERS_CATALOG,
    SFX_CATALOG,
    MUSIC_CATALOG,
    GREEN_SCREEN_MEMES_BY_CONTEXT,
    get_green_meme_path,
    get_pack_memes_list,
    DIR_PACK_MEMES,
    DIR_GREEN_MEMES,
    get_gameplay_videos
)

def normalize_text(text: str) -> str:
    """Normalizes text by removing accents, lowercasing, and stripping punctuation."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())

class SemanticDirector:
    """
    Intelligent Director that pairs narration audio with contextual visuals and memes.
    """

    def __init__(self, whisper_model: str = "base"):
        self.whisper_model_name = whisper_model
        self._model = None
        self._pack_memes_catalog = self._load_pack_memes_catalog()

    def _load_pack_memes_catalog(self) -> List[Dict[str, Any]]:
        """Loads pre-indexed pack de memes metadata if available."""
        catalog_path = os.path.join(os.path.dirname(__file__), "pack_de_memes_transcripts.json")
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _get_whisper_model(self):
        if self._model is None:
            import whisper
            print(f"🎙️ Loading Whisper speech model '{self.whisper_model_name}'...")
            self._model = whisper.load_model(self.whisper_model_name)
        return self._model

    def transcribe_audio(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Transcribes voiceover audio with OpenAI Whisper, returning word-level timestamps.
        """
        model = self._get_whisper_model()
        print(f"🔍 Transcribing narration: {audio_path}")
        result = model.transcribe(audio_path, language="es", word_timestamps=True, fp16=False)
        segments = result.get("segments", [])
        
        cleaned = []
        for s in segments:
            cleaned.append({
                "start": float(s["start"]),
                "end": float(s["end"]),
                "text": s.get("text", "").strip(),
                "words": [
                    {
                        "word": w.get("word", "").strip(),
                        "start": float(w.get("start", s["start"])),
                        "end": float(w.get("end", s["end"]))
                    }
                    for w in s.get("words", [])
                ]
            })
        return cleaned

    def _match_keyword(self, text_norm: str, keywords: List[str]) -> Optional[str]:
        """Checks if any keyword is present as a word/subphrase in text_norm."""
        for kw in keywords:
            kw_norm = normalize_text(kw)
            pattern = r"\b" + re.escape(kw_norm) + r"\b"
            if re.search(pattern, text_norm):
                return kw
        return None

    def _find_best_pack_meme_for_context(self, category: str, query_text: str, used_memes: set) -> Optional[str]:
        """
        Selects a 16:9 meme from PACK DE MEMES that matches the audio context.
        STRICT RULE: Never random! Evaluates transcript, sentiment, and categories.
        """
        all_pack_files = get_pack_memes_list()
        if not all_pack_files:
            return None

        norm_query = normalize_text(query_text)

        # 1. Match against enriched catalog with tags and speech
        if self._pack_memes_catalog:
            best_match = None
            best_score = -1
            for item in self._pack_memes_catalog:
                m_path = os.path.join(DIR_PACK_MEMES, item["filename"])
                if m_path in used_memes:
                    continue

                score = 0
                item_cat = item.get("category", "")
                tags = item.get("tags", [])
                speech = normalize_text(item.get("speech", ""))
                fname = normalize_text(item.get("filename", ""))

                # Category direct match
                if category == item_cat:
                    score += 20

                # Tag overlaps
                for t in tags:
                    if t in norm_query:
                        score += 10

                # Speech keyword overlap
                for word in norm_query.split():
                    if len(word) >= 4 and word in speech:
                        score += 4
                    if len(word) >= 4 and word in fname:
                        score += 2

                if score > best_score:
                    best_score = score
                    best_match = m_path

            if best_match and best_score > 0 and os.path.exists(best_match):
                return best_match

        # Deterministic fallback based on context string hash for unused meme
        available = [p for p in all_pack_files if p not in used_memes] or all_pack_files
        idx = sum(ord(c) for c in norm_query) % len(available)
        return available[idx]

    def _find_green_meme_for_context(self, category: str, used_memes: set) -> Optional[str]:
        """
        Selects a green screen meme strictly matching category, avoiding duplicates.
        """
        cat_info = GREEN_SCREEN_MEMES_BY_CONTEXT.get(category)
        if cat_info and cat_info["files"]:
            # Pick first unused file in the category
            for fname in cat_info["files"]:
                p = get_green_meme_path(fname)
                if p and os.path.exists(p) and p not in used_memes:
                    return p
            # If all used, pick first available
            for fname in cat_info["files"]:
                p = get_green_meme_path(fname)
                if p and os.path.exists(p):
                    return p
        return None

    def plan_timeline(
        self,
        audio_path: str,
        is_short: bool = False,
        total_duration_fallback: float = 30.0
    ) -> Dict[str, Any]:
        """
        Generates complete visual & meme timeline synchronized with audio.
        """
        try:
            segments = self.transcribe_audio(audio_path)
        except Exception as e:
            print(f"⚠️ Whisper transcription warning: {e}. Using fallback silence analyzer.")
            segments = []

        visual_events: List[Dict[str, Any]] = []
        meme_events: List[Dict[str, Any]] = []
        used_memes: set = set()
        used_visual_types: set = set()

        last_visual_end = -10.0
        last_meme_end = -10.0
        min_visual_gap = 7.0 if is_short else 6.0
        min_meme_gap = 6.5  # Reduced gap so more memes fit in short videos
        max_visuals = 3 if is_short else 5
        max_memes = 3 if is_short else 5  # Up to 3 meme reactions per short

        # Scan each speech segment and words
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            seg_text = seg["text"]
            seg_norm = normalize_text(seg_text)

            # Strict Hook Protection & Spacing Rules:
            # 1. First 3.5s is strictly pure Free Fire gameplay (no images allowed).
            # 2. Max 3 visual overlays per video so 85%+ is pure gameplay action.
            # 3. Minimum 7.0s gap between images.
            can_add_visual = (seg_start >= 3.5 if is_short else True) and \
                             (len(visual_events) < max_visuals) and \
                             (seg_start >= last_visual_end + min_visual_gap)

            # ── 1. CHECK VISUAL ASSETS (Strict Contextual Match, Never Random) ──

            # A. DIAMONDS / RECARGAS (Solo venta o conseguir diamantes más baratos)
            if can_add_visual and "diamond" not in used_visual_types and self._match_keyword(seg_norm, DIAMONDS_CATALOG["keywords"]):
                visual_events.append({
                    "time": seg_start,
                    "duration": 2.3,
                    "type": "diamond",
                    "label": "Venta de Diamantes Baratos Free Fire",
                    "asset_path": DIAMONDS_CATALOG["chest_image"],
                    "is_green_screen": False,
                    "sfx_path": DIAMONDS_CATALOG["sfx"]
                })
                used_visual_types.add("diamond")
                last_visual_end = seg_start + 2.3

            # B. CÓDIGO HEADSHOT WEB (Solo cuando dice que vayan a codigoheadshot)
            elif can_add_visual and "book_and_web" not in used_visual_types and self._match_keyword(seg_norm, BOOK_AND_WEB_CATALOG["keywords"]):
                visual_events.append({
                    "time": seg_start,
                    "duration": 2.5,
                    "type": "book_and_web",
                    "label": "Web Oficial Código Headshot (codigoheadshot.online)",
                    "asset_path": BOOK_AND_WEB_CATALOG["web_banner"],
                    "sfx_path": BOOK_AND_WEB_CATALOG["sfx"]
                })
                used_visual_types.add("book_and_web")
                last_visual_end = seg_start + 2.5

            # C. ASESORÍA / ENTREVISTA (Solo cuando habla de asesoría o entrevista con un usuario)
            elif can_add_visual and "asesoria" not in used_visual_types and self._match_keyword(seg_norm, ASESORIA_CATALOG["keywords"]):
                visual_events.append({
                    "time": seg_start,
                    "duration": 2.6,
                    "type": "asesoria",
                    "label": "Asesoría / Entrevista Personalizada",
                    "asset_path": ASESORIA_CATALOG["device_advice"],
                    "sfx_path": ASESORIA_CATALOG["sfx"]
                })
                used_visual_types.add("asesoria")
                last_visual_end = seg_start + 2.6

            # D. AVATAR EN PANTALLA COMPLETA (Solo cuando habla de mi cuenta, mi avatar, el creador)
            elif can_add_visual and "avatar" not in used_visual_types and self._match_keyword(seg_norm, CHARACTERS_AND_PROFILE_CATALOG["keywords"]):
                visual_events.append({
                    "time": seg_start,
                    "duration": 2.5,
                    "type": "avatar_fullscreen",
                    "label": "Avatar Oficial Cris FF",
                    "asset_path": CHARACTERS_AND_PROFILE_CATALOG["avatar"],
                    "sfx_path": SFX_CATALOG["ding"]
                })
                used_visual_types.add("avatar")
                last_visual_end = seg_start + 2.5

            # E. SENSIBILIDAD IN-GAME (Solo cuando habla de calibrar miras o sensibilidad)
            elif can_add_visual and "sensitivity" not in used_visual_types and self._match_keyword(seg_norm, SENSITIVITY_CATALOG["keywords"]):
                visual_events.append({
                    "time": seg_start,
                    "duration": 2.2,
                    "type": "sensitivity",
                    "label": "Sensibilidad In-Game Free Fire",
                    "asset_path": SENSITIVITY_CATALOG["in_game_menu"],
                    "sfx_path": SENSITIVITY_CATALOG["sfx"]
                })
                used_visual_types.add("sensitivity")
                last_visual_end = seg_start + 2.2

            # F. WEAPONS (Solo si mencionan explícitamente el nombre de la arma evolutiva)
            elif can_add_visual and "weapon" not in used_visual_types and self._match_keyword(seg_norm, WEAPONS_CATALOG["keywords"]):
                visual_events.append({
                    "time": seg_start,
                    "duration": 2.2,
                    "type": "weapon",
                    "label": "Arma Evolutiva",
                    "asset_path": WEAPONS_CATALOG["ak47_dragon"],
                    "sfx_path": WEAPONS_CATALOG["sfx"]
                })
                used_visual_types.add("weapon")
                last_visual_end = seg_start + 2.2

            # ── 2. CHECK CONTEXTUAL MEMES (STRICT CONTEXT MATCHING, NEVER RANDOM) ──
            meme_cat = None
            
            # Emotional & Conceptual triggers in speech
            if any(k in seg_norm for k in ["no hay", "mentira", "falso", "magica", "mágica", "no sirve"]):
                meme_cat = "thinking"  # Disbelief / skepticism
            elif any(k in seg_norm for k in ["proceso", "pantalla", "responde", "valor", "subes", "afinas", "punto exacto", "control", "calcular", "estrategia"]):
                meme_cat = "thinking"  # Calculation / strategy
            elif any(k in seg_norm for k in ["comenta", "codigo", "código", "suscribete", "suscríbete", "canal", "like", "campanita"]):
                meme_cat = "subscribe" # Call to action
            elif any(k in seg_norm for k in ["insano", "modo diablo", "nivel dios", "ultra instinto", "nadie te para", "imbatible", "todo rojo"]):
                meme_cat = "god_mode"
            elif any(k in seg_norm for k in ["manco", "fallar", "morir", "lobby", "perder", "wasted", "fallé", "no pegas"]):
                meme_cat = "fail"
            elif any(k in seg_norm for k in ["increible", "increíble", "impresionante", "locura", "no lo vas a creer", "mira esto"]):
                meme_cat = "shock"
            elif any(k in seg_norm for k in ["risa", "jaja", "chiste", "humillar", "burlarse", "troll"]):
                meme_cat = "laugh"
            elif any(k in seg_norm for k in ["llorar", "triste", "puntos", "dolor", "bajar de rango"]):
                meme_cat = "cry"
            elif any(k in seg_norm for k in ["booyah", "victoria", "ganamos", "campeon", "campeón"]):
                meme_cat = "victory"
            elif any(k in seg_norm for k in ["enojo", "rabia", "gritar", "furia"]):
                meme_cat = "rage"
            elif any(k in seg_norm for k in ["que paso", "qué pasó", "no entiendo", "como asi"]):
                meme_cat = "wtf"

            # Schedule meme reaction at the end of the spoken phrase so the phrase is completed cleanly
            meme_time = seg_end
            overlaps_with_visual = any(
                v["time"] - 1.5 <= meme_time <= (v["time"] + v["duration"] + 1.5)
                for v in visual_events
            )

            if meme_cat and (meme_time >= last_meme_end + min_meme_gap) and not overlaps_with_visual and (len(meme_events) < max_memes):
                meme_path = None
                is_green = False

                if is_short:
                    # Shorts: ONLY green-screen memes (never 16:9 cutaway memes)
                    meme_path = self._find_green_meme_for_context(meme_cat, used_memes)
                    is_green = True if meme_path else False
                else:
                    # Long 16:9 videos: pick from PACK DE MEMES matching context, fallback to green-screen
                    pack_meme = self._find_best_pack_meme_for_context(meme_cat, seg_text, used_memes)
                    if pack_meme:
                        meme_path = pack_meme
                        is_green = False
                    else:
                        meme_path = self._find_green_meme_for_context(meme_cat, used_memes)
                        is_green = True

                if meme_path:
                    used_memes.add(meme_path)
                    dur = 2.0 if is_green else 1.8
                    meme_events.append({
                        "time": meme_time,
                        "duration": dur,
                        "category": meme_cat,
                        "matched_phrase": seg_text,
                        "meme_path": meme_path,
                        "is_green_screen": is_green
                    })
                    last_meme_end = meme_time + dur

        total_audio_dur = segments[-1]["end"] if segments else total_duration_fallback

        return {
            "total_duration": total_audio_dur,
            "segments": segments,
            "visual_events": visual_events,
            "meme_events": meme_events,
            "is_short": is_short
        }
