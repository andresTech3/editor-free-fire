"""
core/caption_engine.py
======================
Motor de captions word-by-word estilo MrBeast / Opus Clip.
- Extrae timestamps exactos por palabra desde segmentos de Whisper
- Agrupa palabras en "chunks" de 2-4 palabras para mostrar en pantalla
- Detecta palabras de alto impacto para animación especial
- Exporta JSON compatible con Remotion y CapCut
- Idioma: inglés (language="en")
"""

import re
from typing import List, Dict, Optional, Tuple


# Palabras de alto impacto que reciben animación especial (más grande, color diferente)
IMPACT_WORDS_EN = {
    "insane", "crazy", "wild", "unbelievable", "impossible", "never",
    "always", "win", "lose", "money", "million", "billion", "thousand",
    "dollar", "free", "beat", "destroy", "survive", "die", "dead",
    "win", "won", "lost", "broke", "rich", "poor", "sick", "hurt",
    "amazing", "incredible", "shocking", "huge", "massive", "tiny",
    "everyone", "nobody", "nothing", "everything", "best", "worst",
    "fastest", "slowest", "hardest", "easiest", "first", "last",
    "challenge", "impossible", "record", "world", "ever", "never",
    "minutes", "hours", "days", "seconds", "finally", "literally",
    "actually", "honestly", "seriously", "wait", "stop", "go", "run",
    "wow", "omg", "bro", "dude", "man", "fire", "cold", "hot", "pain",
}

# Conectores y palabras funcionales que NO deben ser el highlight activo
FILLER_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those", "what", "which", "who", "when",
    "where", "how", "if", "because", "so", "as", "just", "also",
    "about", "up", "out", "like", "then", "than", "now", "more", "all",
}


class CaptionEngine:
    """
    Convierte los segmentos de Whisper en una pista de captions
    estilo MrBeast: grupos de 2-4 palabras, con highlight de la
    palabra activa, animación de impacto en palabras clave.
    """

    def __init__(
        self,
        chunk_size: int = 3,          # Palabras por grupo en pantalla
        max_chunk_duration: float = 2.5,  # Máx segundos que puede durar un grupo
        min_word_duration: float = 0.05,  # Mínimo de frames para una palabra
        language: str = "en",
    ):
        self.chunk_size = chunk_size
        self.max_chunk_duration = max_chunk_duration
        self.min_word_duration = min_word_duration
        self.language = language

    def extract_words(self, segments: List[Dict]) -> List[Dict]:
        """
        Extrae todos los timestamps de palabras individuales desde
        los segmentos de Whisper.

        Whisper devuelve palabras en seg["words"] = [
            {"word": "Hello", "start": 0.5, "end": 0.8, "probability": 0.95}
        ]
        Si el segmento no tiene palabras, se estima la distribución uniformemente.
        """
        all_words = []

        for seg in segments:
            seg_start = seg.get("start", 0.0)
            seg_end = seg.get("end", seg_start + 1.0)
            seg_words = seg.get("words", [])

            if seg_words:
                # Whisper devolvió timestamps por palabra — usarlos directamente
                for w in seg_words:
                    word_text = w.get("word", "").strip()
                    # Limpiar puntuación del borde pero mantener apóstrofes internos
                    word_clean = re.sub(r"^[^\w']+|[^\w']+$", "", word_text)
                    if not word_clean:
                        continue

                    all_words.append({
                        "word": word_clean.upper(),   # MrBeast usa mayúsculas
                        "word_raw": word_text,
                        "start": float(w.get("start", seg_start)),
                        "end": float(w.get("end", seg_end)),
                        "probability": float(w.get("probability", 0.8)),
                        "is_impact": word_clean.lower() in IMPACT_WORDS_EN,
                        "is_filler": word_clean.lower() in FILLER_WORDS,
                    })
            else:
                # Sin timestamps por palabra: distribuir uniformemente
                text = seg.get("text", "").strip()
                words_in_seg = text.split()
                if not words_in_seg:
                    continue

                seg_duration = seg_end - seg_start
                word_dur = seg_duration / len(words_in_seg)

                for j, word_text in enumerate(words_in_seg):
                    word_clean = re.sub(r"^[^\w']+|[^\w']+$", "", word_text)
                    if not word_clean:
                        continue
                    w_start = seg_start + j * word_dur
                    w_end = w_start + word_dur

                    all_words.append({
                        "word": word_clean.upper(),
                        "word_raw": word_text,
                        "start": w_start,
                        "end": w_end,
                        "probability": 0.75,
                        "is_impact": word_clean.lower() in IMPACT_WORDS_EN,
                        "is_filler": word_clean.lower() in FILLER_WORDS,
                    })

        return all_words

    def build_caption_chunks(self, words: List[Dict]) -> List[Dict]:
        """
        Agrupa las palabras en "chunks" de 2-4 palabras para mostrar
        en pantalla al mismo tiempo, estilo MrBeast.

        Reglas de agrupación:
        - Máximo chunk_size palabras por grupo
        - Si el grupo duraría más de max_chunk_duration segundos, cortar antes
        - Cortar en puntuación final (., !, ?)
        - Cortar en silencios >0.4s entre palabras
        """
        if not words:
            return []

        chunks = []
        i = 0

        while i < len(words):
            chunk_words = []
            chunk_start = words[i]["start"]

            while i < len(words):
                w = words[i]
                chunk_words.append(w)

                # Detectar condiciones de corte
                chunk_dur = w["end"] - chunk_start
                is_sentence_end = re.search(r"[.!?]", w.get("word_raw", ""))
                is_max_size = len(chunk_words) >= self.chunk_size
                is_too_long = chunk_dur >= self.max_chunk_duration

                # Silencio antes de la siguiente palabra
                next_gap = 0.0
                if i + 1 < len(words):
                    next_gap = words[i + 1]["start"] - w["end"]

                i += 1

                if is_sentence_end or is_max_size or is_too_long or next_gap > 0.4:
                    break

            if chunk_words:
                chunk_end = chunk_words[-1]["end"]
                # La palabra activa inicial es la primera no-filler si existe
                primary_idx = next(
                    (j for j, cw in enumerate(chunk_words) if not cw["is_filler"]),
                    0
                )
                chunks.append({
                    "words": chunk_words,
                    "start": chunk_start,
                    "end": chunk_end,
                    "duration": chunk_end - chunk_start,
                    "primary_idx": primary_idx,
                    "has_impact": any(cw["is_impact"] for cw in chunk_words),
                    "text": " ".join(cw["word"] for cw in chunk_words),
                })

        return chunks

    def get_silence_cut_points(self, words: List[Dict], min_silence: float = 0.35) -> List[float]:
        """
        Detecta puntos de corte ideales: silencios >min_silence segundos entre palabras.
        Returns: lista de timestamps donde es óptimo cortar el video.
        """
        cut_points = []
        for i in range(len(words) - 1):
            gap = words[i + 1]["start"] - words[i]["end"]
            if gap >= min_silence:
                # El corte ocurre en el punto medio del silencio
                cut_time = words[i]["end"] + gap * 0.3  # 30% del silencio = más natural
                cut_points.append(round(cut_time, 3))
        return cut_points

    def get_impact_moments(self, words: List[Dict]) -> List[Dict]:
        """
        Detecta momentos de alto impacto para trigger de punch-zoom.
        Returns: lista de {time, word, intensity}
        """
        impact_events = []
        for w in words:
            if w["is_impact"] and not w["is_filler"]:
                impact_events.append({
                    "time": w["start"],
                    "word": w["word"],
                    "intensity": min(1.0, w["probability"] + 0.2),  # boost por ser impact word
                })
        return impact_events

    def to_remotion_json(
        self,
        chunks: List[Dict],
        words: List[Dict],
        clip_start_sec: float = 0.0,
    ) -> Dict:
        """
        Exporta el JSON de captions listo para Remotion.
        Los timestamps son relativos al inicio del clip.
        """
        def rel(t: float) -> float:
            return round(t - clip_start_sec, 4)

        return {
            "language": self.language,
            "style": "mrbeast",
            "words": [
                {
                    "word": w["word"],
                    "start": rel(w["start"]),
                    "end": rel(w["end"]),
                    "probability": w["probability"],
                    "is_impact": w["is_impact"],
                    "is_filler": w["is_filler"],
                }
                for w in words
            ],
            "chunks": [
                {
                    "text": ch["text"],
                    "words": [
                        {
                            "word": cw["word"],
                            "start": rel(cw["start"]),
                            "end": rel(cw["end"]),
                            "is_impact": cw["is_impact"],
                        }
                        for cw in ch["words"]
                    ],
                    "start": rel(ch["start"]),
                    "end": rel(ch["end"]),
                    "has_impact": ch["has_impact"],
                    "primary_idx": ch["primary_idx"],
                }
                for ch in chunks
            ],
            "silence_cuts": self.get_silence_cut_points(words),
            "impact_moments": self.get_impact_moments(words),
        }

    def process_segments(
        self,
        segments: List[Dict],
        clip_start_sec: float = 0.0,
        clip_end_sec: float = None,
    ) -> Dict:
        """
        Pipeline completo: segmentos Whisper → JSON de captions MrBeast.
        """
        # Filtrar segmentos del clip
        clip_segs = [
            s for s in segments
            if s.get("end", 0) >= clip_start_sec
            and (clip_end_sec is None or s.get("start", 0) <= clip_end_sec)
        ]

        words = self.extract_words(clip_segs)

        # Filtrar palabras fuera del clip
        if clip_end_sec is not None:
            words = [w for w in words if w["start"] >= clip_start_sec and w["end"] <= clip_end_sec]

        chunks = self.build_caption_chunks(words)
        return self.to_remotion_json(chunks, words, clip_start_sec)
