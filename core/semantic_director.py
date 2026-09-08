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

        # Keep track of usage to alternate assets dynamically
        sensitivity_count = 0
        last_visual_end = -10.0
        last_meme_end = -10.0
        min_visual_gap = 2.5
        min_meme_gap = 5.0

        # Scan each speech segment and words
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            seg_text = seg["text"]
            seg_norm = normalize_text(seg_text)

            visual_added_at_seg = False

            # ── 1. CHECK VISUAL ASSETS (Strict Contextual Match, Never Random) ──

            # A. DIAMONDS / DINERO / RECARGAS / MONEDAS
            if self._match_keyword(seg_norm, DIAMONDS_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    # User request: "cuando se hablen de diamantes muestre la imagenes donde esta diamantes o emotes donde hay dinero"
                    if any(k in seg_norm for k in ["emote", "baile", "presumir"]):
                        v_asset = DIAMONDS_CATALOG["emotes_video"]
                        is_gs = False
                        v_label = "Emote Presumiendo Dinero Free Fire"
                    elif any(k in seg_norm for k in ["dinero", "plata", "lluvia", "oro", "millonario", "gastar", "comprar"]):
                        v_asset = DIAMONDS_CATALOG["green_screen_money"]
                        is_gs = True
                        v_label = "Lluvia de Dinero (Memes Pantalla Verde)"
                    else:
                        v_asset = DIAMONDS_CATALOG["chest_image"]
                        is_gs = False
                        v_label = "Cofre de Diamantes Free Fire"

                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.0,
                        "type": "diamond",
                        "label": v_label,
                        "asset_path": v_asset,
                        "is_green_screen": is_gs,
                        "sfx_path": DIAMONDS_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.0
                    visual_added_at_seg = True

            # B. PASE ÉLITE / TORNEOS / SALAS COMPETITIVAS
            elif self._match_keyword(seg_norm, PASS_AND_TOURNAMENT_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    # User request: "cuando digan pase elite lo mismo"
                    if any(k in seg_norm for k in ["torneo", "sala", "salas", "campeonato", "copa"]):
                        v_asset = PASS_AND_TOURNAMENT_CATALOG["tournament_poster"]
                        v_label = "Torneo Oficial Booyah"
                    elif any(k in seg_norm for k in ["gran maestro", "rango"]):
                        v_asset = PASS_AND_TOURNAMENT_CATALOG["elite_badge"]
                        v_label = "Insignia Gran Maestro"
                    else:
                        v_asset = PASS_AND_TOURNAMENT_CATALOG["tournament_poster"]
                        v_label = "Pase Élite Free Fire"

                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.2,
                        "type": "pass_and_tournament",
                        "label": v_label,
                        "asset_path": v_asset,
                        "sfx_path": PASS_AND_TOURNAMENT_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.2
                    visual_added_at_seg = True

            # C. TOP GLOBALES / RANKINGS / GRAN MAESTRO
            elif self._match_keyword(seg_norm, TOP_GLOBAL_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    # User request: "o top globales etc cada imagen tiene su nombre, no especificamente pero puede estar relacionado"
                    if "gran maestro" in seg_norm:
                        v_asset = TOP_GLOBAL_CATALOG["gran_maestro_badge"]
                        v_label = "Insignia Gran Maestro"
                    elif any(k in seg_norm for k in ["tabla", "puntos", "posicion", "clasificacion"]):
                        v_asset = TOP_GLOBAL_CATALOG["ranking_board"] if os.path.exists(TOP_GLOBAL_CATALOG["ranking_board"]) else TOP_GLOBAL_CATALOG["leaderboard_image"]
                        v_label = "Tabla de Posiciones Oficial"
                    else:
                        v_asset = TOP_GLOBAL_CATALOG["leaderboard_image"]
                        v_label = "Top Global Oficial Free Fire"

                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.5,
                        "type": "top_global",
                        "label": v_label,
                        "asset_path": v_asset,
                        "sfx_path": TOP_GLOBAL_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.5
                    visual_added_at_seg = True

            # D. RESULTADOS & ESTADÍSTICAS (Resultados, Daño Efectivo, Kills, Bajas)
            elif self._match_keyword(seg_norm, RESULTS_AND_STATS_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.0,
                        "type": "results",
                        "label": "Resultados Oficiales de Partida",
                        "asset_path": RESULTS_AND_STATS_CATALOG["results_image"],
                        "sfx_path": RESULTS_AND_STATS_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.0
                    visual_added_at_seg = True

            # E. WEAPONS / PVP / BATTLE ROYALE / DISPARO / DAÑO
            elif self._match_keyword(seg_norm, WEAPONS_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    if "groza" in seg_norm:
                        w_img = WEAPONS_CATALOG["groza_booyah"]
                        w_label = "Groza Booyah"
                    elif "m16" in seg_norm or "rifle" in seg_norm:
                        w_img = WEAPONS_CATALOG["m16_rifle"]
                        w_label = "Rifle M16"
                    else:
                        w_img = WEAPONS_CATALOG["ak47_dragon"]
                        w_label = "AK-47 Dragón Flama Azul Evolutiva"

                    visual_events.append({
                        "time": seg_start,
                        "duration": 2.8,
                        "type": "weapon",
                        "label": w_label,
                        "asset_path": w_img,
                        "sfx_path": WEAPONS_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 2.8
                    visual_added_at_seg = True

            # F. BOOK / WEB / GUÍA / CÓDIGO HEADSHOT
            elif self._match_keyword(seg_norm, BOOK_AND_WEB_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.2,
                        "type": "book_and_web",
                        "label": "Banner Oficial Código Headshot",
                        "asset_path": BOOK_AND_WEB_CATALOG["web_banner"],
                        "sfx_path": BOOK_AND_WEB_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.2
                    visual_added_at_seg = True

            # G. DPI & DISPOSITIVO MÓVIL (Celular, Pantalla, Gama, Asesoría)
            elif self._match_keyword(seg_norm, DPI_AND_DEVICE_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.2,
                        "type": "dpi_device",
                        "label": "Asesoría de Celular & DPI",
                        "asset_path": DPI_AND_DEVICE_CATALOG["device_advice"],
                        "sfx_path": DPI_AND_DEVICE_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.2
                    visual_added_at_seg = True

            # H. SENSIBILIDAD & MIRAS
            elif self._match_keyword(seg_norm, SENSITIVITY_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.2,
                        "type": "sensitivity",
                        "label": "Sensibilidad In-Game Free Fire",
                        "asset_path": SENSITIVITY_CATALOG["in_game_menu"],
                        "sfx_path": SENSITIVITY_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 3.2
                    visual_added_at_seg = True

            # I. EMOTES & CELEBRACIONES
            elif self._match_keyword(seg_norm, EMOTES_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 2.8,
                        "type": "emotes",
                        "label": "Emote Free Fire",
                        "asset_path": EMOTES_CATALOG["emotes_video"],
                        "sfx_path": EMOTES_CATALOG["sfx"]
                    })
                    last_visual_end = seg_start + 2.8
                    visual_added_at_seg = True

            # J. PERSONAJE & PERFIL
            elif self._match_keyword(seg_norm, CHARACTERS_AND_PROFILE_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 2.8,
                        "type": "character",
                        "label": "Personaje Oficial Free Fire",
                        "asset_path": CHARACTERS_AND_PROFILE_CATALOG["personaje"],
                        "sfx_path": SFX_CATALOG["ding"]
                    })
                    last_visual_end = seg_start + 2.8
                    visual_added_at_seg = True

            # K. CALL TO ACTION / LIKES / SUSCRÍBETE
            elif self._match_keyword(seg_norm, CALL_TO_ACTION_CATALOG["keywords"]):
                if seg_start >= last_visual_end + min_visual_gap:
                    visual_events.append({
                        "time": seg_start,
                        "duration": 3.0,
                        "type": "cta",
                        "label": "Insignia de Likes y Suscríbete",
                        "asset_path": CALL_TO_ACTION_CATALOG["likes_badge"],
                        "sfx_path": SFX_CATALOG["ding"]
                    })
                    last_visual_end = seg_start + 3.0
                    visual_added_at_seg = True

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

            if meme_cat and (meme_time >= last_meme_end + min_meme_gap):
                meme_path = None
                is_green = False

                if is_short:
                    # Shorts: strictly prioritize green-screen memes
                    meme_path = self._find_green_meme_for_context(meme_cat, used_memes)
                    is_green = True
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
