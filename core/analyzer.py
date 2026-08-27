"""
core/analyzer.py
=================
Motor de detección de momentos virales y clasificación de Hooks.
Combina análisis de energía de audio, NLP de texto, sentimiento
y clasificación en 15 metodologías de Hook Virales.

Algoritmo de scoring:
    viral_score = (
        0.35 * audio_energy_score
      + 0.25 * keyword_score
      + 0.20 * sentiment_score
      + 0.20 * speech_density_score
    )
    
"""

import os
import re
import math
import tempfile
import warnings
from typing import List, Dict, Optional, Any, Tuple

import numpy as np

warnings.filterwarnings("ignore")

# ═════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE LOS 15 HOOKS VIRALES
# ═════════════════════════════════════════════════════════════════════════════

HOOK_DEFINITIONS = [
    {
        "id": "contracorriente",
        "name": "Contracorriente",
        "emoji": "🌊",
        "desc": "Contradice una creencia popular o convención",
        "regex": r"\b(no es|mentira|falso|mito|nadie sabe|la verdad sobre|never|wrong|myth|realmente no)\b",
    },
    {
        "id": "numero_especifico",
        "name": "Número específico",
        "emoji": "🔢",
        "desc": "Usa una cifra concreta para generar credibilidad",
        "regex": r"(\$\d+|\d+\s*%|\b\d+\s*(dólares|pesos|puntos|días|horas|veces|k|m)\b|\b\d{2,}\b)",
    },
    {
        "id": "error",
        "name": "Error común",
        "emoji": "❌",
        "desc": "Señala un error frecuente que comete la audiencia",
        "regex": r"\b(error|fallo|equivocad|haciendo mal|no hagas|peor|mistake|wrong|fail)\b",
    },
    {
        "id": "promesa",
        "name": "Promesa clara",
        "emoji": "🎯",
        "desc": "Anticipa un resultado claro y altamente deseable",
        "regex": r"\b(cómo|te enseño|lograr|conseguir|ganar|resultado|how to|learn)\b",
    },
    {
        "id": "transformacion",
        "name": "Transformación personal",
        "emoji": "🔄",
        "desc": "Parte de una historia de cambio o experiencia propia",
        "regex": r"\b(yo solía|mi historia|cuando empecé|cambió mi|hace \d+|hice esto|i used to|my)\b",
    },
    {
        "id": "secreto",
        "name": "Secreto revelado",
        "emoji": "🤫",
        "desc": "Insinúa información oculta o poco conocida",
        "regex": r"\b(secreto|truco|oculto|nadie te dice|pocos saben|secret|hidden|nobody)\b",
    },
    {
        "id": "pregunta",
        "name": "Pregunta inducida",
        "emoji": "❓",
        "desc": "Pregunta que fuerza a la audiencia a responder mentalmente",
        "regex": r"(\?|¿|\b(sabías|alguna vez|te has|por qué|qué pasaría|ever wondered|did you know)\b)",
    },
    {
        "id": "lista",
        "name": "Lista / Enumeración",
        "emoji": "📋",
        "desc": "Anuncia una lista ordenada (3 cosas, top 5, etc.)",
        "regex": r"\b(\d+\s*(cosas|razones|formas|pasos|tips|trucos|top|ways|reasons))\b",
    },
    {
        "id": "contraste",
        "name": "Contraste comparativo",
        "emoji": "⚖️",
        "desc": "Comparación directa: antes/después, X vs Y",
        "regex": r"\b(vs|versus|diferencia|antes y después|mientras que|en vez de|instead)\b",
    },
    {
        "id": "advertencia",
        "name": "Advertencia urgente",
        "emoji": "⚠️",
        "desc": "Alerta sobre un peligro o consecuencia negativa",
        "regex": r"\b(cuidado|peligro|advertencia|alerta|evita|riesgo|warning|danger|stop|no cometas)\b",
    },
    {
        "id": "caso_real",
        "name": "Caso real",
        "emoji": "📖",
        "desc": "Se apoya en un ejemplo o historia real concreta",
        "regex": r"\b(mira este|este chico|esta persona|caso real|historia real|ejemplo|pasó cuando)\b",
    },
    {
        "id": "atractivo",
        "name": "Atractivo / Aspiración",
        "emoji": "🌟",
        "desc": "Apela al deseo, estatus, excelencia o aspiración",
        "regex": r"\b(increíble|brutal|locura|el mejor|increible|perfecto|amazing|insane|best|epic)\b",
    },
    {
        "id": "vulnerable",
        "name": "Vulnerable / Confesión",
        "emoji": "💔",
        "desc": "Abre con una confesión o debilidad personal",
        "regex": r"\b(tengo que confesar|perdí|mi mayor miedo|fracasé|me equivoqué|admito|confess|failed)\b",
    },
    {
        "id": "prediccion",
        "name": "Predicción futura",
        "emoji": "🔮",
        "desc": "Anticipa lo que va a pasar a futuro",
        "regex": r"\b(en el futuro|esto va a pasar|lo que viene|próximo año|futuro|future|will happen)\b",
    },
    {
        "id": "provocacion",
        "name": "Provocación polémica",
        "emoji": "🔥",
        "desc": "Declaración polémica que genera debate o incomoda",
        "regex": r"\b(te va a enojar|la dura verdad|me van a odiar|polémic|opinión impopular|unpopular)\b",
    },
]


def classify_hook(text: str) -> Dict[str, str]:
    """
    Clasifica el texto inicial de un clip en uno de los 15 Hooks Virales.
    Si no coincide con ningún patrón específico, asigna 'Atractivo' o 'Caso real'.
    """
    text_lower = text.lower() if text else ""

    # Tomar los primeros 120 caracteres para el análisis del Hook (los primeros 3-5 segundos)
    hook_sample = text_lower[:120]

    best_hook = None
    max_matches = 0

    for hook in HOOK_DEFINITIONS:
        matches = len(re.findall(hook["regex"], hook_sample, re.IGNORECASE))
        if matches > max_matches:
            max_matches = matches
            best_hook = hook

    if not best_hook:
        # Fallback de clasificación según estructura general
        if "?" in hook_sample or "¿" in hook_sample:
            best_hook = HOOK_DEFINITIONS[6]  # Pregunta inducida
        elif any(c.isdigit() for c in hook_sample):
            best_hook = HOOK_DEFINITIONS[1]  # Número específico
        else:
            best_hook = HOOK_DEFINITIONS[11] # Atractivo / Aspiración

    return best_hook


class ViralAnalyzer:
    """
    Analiza segmentos de texto + audio y asigna un Viral Score
    e identifica el Hook para cada clip corto.
    """

    def __init__(
        self,
        video_path: str,
        segments: List[Dict],
        viral_keywords: List[str] = None,
        weights: Dict[str, float] = None,
        max_clip_duration: float = 60.0,
        min_clip_duration: float = 20.0,
        console: Optional[Any] = None,
    ):
        self.video_path = video_path
        self.segments = segments
        self.viral_keywords = [kw.lower() for kw in (viral_keywords or [])]
        self.weights = weights or {
            "audio_energy": 0.35,
            "keywords": 0.25,
            "sentiment": 0.20,
            "speech_density": 0.20,
        }
        self.max_clip_duration = max_clip_duration
        self.min_clip_duration = min_clip_duration
        self.console = console
        self._audio_energy_cache: Optional[Dict] = None

    def _log(self, msg: str):
        if self.console:
            self.console.print(f"  [dim]{msg}[/dim]")

    # ═══════════════════════════════════════════════════════
    # Análisis de Energía de Audio
    # ═══════════════════════════════════════════════════════

    def _compute_audio_energy(self) -> Dict[float, float]:
        if self._audio_energy_cache is not None:
            return self._audio_energy_cache

        self._log("Calculando energía de audio...")

        try:
            import librosa
            import subprocess

            tmp_path = os.path.join(tempfile.gettempdir(), "viralclip_energy.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", self.video_path,
                "-ar", "22050", "-ac", "1", "-f", "wav", tmp_path
            ], capture_output=True)

            y, sr = librosa.load(tmp_path, sr=22050, mono=True)
            frame_length = int(sr * 0.5)
            hop_length = frame_length

            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

            rms_min, rms_max = rms.min(), rms.max()
            rms_normalized = (rms - rms_min) / (rms_max - rms_min) if rms_max > rms_min else rms * 0
            energy_map = {float(t): float(e) for t, e in zip(times, rms_normalized)}

            try:
                os.remove(tmp_path)
            except Exception:
                pass

            self._audio_energy_cache = energy_map
            self._log(f"✓ Energía calculada: {len(energy_map)} puntos")
            return energy_map

        except Exception as e:
            self._log(f"⚠ No se pudo calcular energía de audio: {e}")
            return {}

    def _get_segment_energy(self, start: float, end: float) -> float:
        energy_map = self._compute_audio_energy()
        if not energy_map:
            return 0.5

        energies = [v for t, v in energy_map.items() if start <= t <= end]
        return float(np.mean(energies)) if energies else 0.0

    # ═══════════════════════════════════════════════════════
    # Análisis de Palabras Clave
    # ═══════════════════════════════════════════════════════

    def _keyword_score(self, text: str) -> float:
        if not text:
            return 0.0

        text_lower = text.lower()
        score = 0.0
        total_words = max(len(text.split()), 1)

        keyword_hits = sum(1 for kw in self.viral_keywords if kw in text_lower)
        score += min(keyword_hits * 0.15, 0.6)

        patterns = [
            (r'\?', 0.10),
            (r'!', 0.08),
            (r'\b\d+\b', 0.08),
            (r'\d+\s*%', 0.12),
            (r'\b(ahora|hoy|ya|inmediato|urgente|now|today|immediately)\b', 0.10),
            (r'\b(nunca|jamás|siempre|todo|nada|nadie|todos|never|always|everyone|nobody)\b', 0.08),
            (r'\b(pero|sin embargo|aunque|resulta|actually|however|but)\b', 0.05),
            (r'\b(primero|segundo|tercero|uno|dos|tres|first|second|third)\b', 0.07),
        ]

        for pattern, weight in patterns:
            if re.search(pattern, text_lower):
                score += weight

        if total_words > 0:
            density_bonus = min(keyword_hits / total_words * 2, 0.2)
            score += density_bonus

        return min(score, 1.0)

    # ═══════════════════════════════════════════════════════
    # Análisis de Sentimiento
    # ═══════════════════════════════════════════════════════

    def _sentiment_score(self, text: str) -> float:
        if not text:
            return 0.0

        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            sia = SentimentIntensityAnalyzer()
            scores = sia.polarity_scores(text)

            compound = abs(scores["compound"])
            positive_peak = scores["pos"]
            negative_peak = scores["neg"]

            intensity = max(compound, positive_peak * 1.5, negative_peak * 1.2)
            return min(intensity, 1.0)

        except Exception:
            exclamations = text.count("!")
            questions = text.count("?")
            caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
            return min((exclamations * 0.15 + questions * 0.10 + caps_words * 0.10), 1.0)

    # ═══════════════════════════════════════════════════════
    # Densidad de Discurso
    # ═══════════════════════════════════════════════════════

    def _speech_density_score(self, text: str, duration: float) -> float:
        if duration <= 0 or not text:
            return 0.0

        words = text.split()
        wps = len(words) / duration

        if wps < 0.5:
            return 0.1
        elif wps < 2.0:
            return 0.3 + (wps - 0.5) / 1.5 * 0.3
        elif wps <= 4.5:
            return 0.6 + (1 - abs(wps - 3.0) / 2.5) * 0.4
        else:
            return max(0.4, 1.0 - (wps - 4.5) / 5.0)

    # ═══════════════════════════════════════════════════════
    # Scoring Principal
    # ═══════════════════════════════════════════════════════

    def _compute_viral_score(self, candidate: Dict) -> Tuple[float, Dict]:
        text = candidate.get("text", "")
        start = candidate["start"]
        end = candidate["end"]
        duration = end - start

        e_energy = self._get_segment_energy(start, end)
        e_keyword = self._keyword_score(text)
        e_sentiment = self._sentiment_score(text)
        e_density = self._speech_density_score(text, duration)

        w = self.weights
        score = (
            w.get("audio_energy", 0.35) * e_energy
            + w.get("keywords", 0.25) * e_keyword
            + w.get("sentiment", 0.20) * e_sentiment
            + w.get("speech_density", 0.20) * e_density
        )

        return round(min(score, 1.0), 4), {
            "audio_energy": round(e_energy, 3),
            "keyword": round(e_keyword, 3),
            "sentiment": round(e_sentiment, 3),
            "density": round(e_density, 3),
        }

    # ═══════════════════════════════════════════════════════
    # Construcción de Candidatos y Diversidad de Hooks
    # ═══════════════════════════════════════════════════════

    def _build_candidates(self) -> List[Dict]:
        if not self.segments:
            return []

        candidates = []
        n = len(self.segments)

        # Pase 1: Candidatos basados en acumulación de segmentos con tolerancia de pausa de 12s
        for i in range(n):
            seg = self.segments[i]
            start = seg["start"]
            end = seg["end"]
            text = seg["text"]
            words = seg.get("words", [])
            duration = end - start

            j = i + 1
            while j < n and (self.segments[j]["end"] - start) <= self.max_clip_duration:
                next_seg = self.segments[j]
                gap = next_seg["start"] - end
                if gap > 12.0:  # Permitir pausas de risa/efectos hasta 12 segundos
                    break
                end = next_seg["end"]
                text += " " + next_seg["text"]
                words += next_seg.get("words", [])
                duration = end - start
                j += 1

            if duration >= self.min_clip_duration:
                hook_info = classify_hook(text)
                candidates.append({
                    "start": start,
                    "end": end,
                    "text": text.strip(),
                    "words": words,
                    "duration": duration,
                    "segment_idx": i,
                    "hook_id": hook_info["id"],
                    "hook_name": hook_info["name"],
                    "hook_emoji": hook_info["emoji"],
                    "hook_desc": hook_info["desc"],
                })

        # Pase 2: Fallback por ventana deslizante si los segmentos son muy dispersos (ej. videos de risa)
        if len(candidates) < 3:
            total_duration = self.segments[-1]["end"] if self.segments else 180.0
            clip_len = min(45.0, self.max_clip_duration)
            step = 25.0
            t = 0.0
            while t + clip_len <= total_duration:
                # Buscar palabras en este rango de tiempo
                sub_words = [w for seg in self.segments for w in seg.get("words", []) if t <= w.get("start", 0) <= t + clip_len]
                sample_text = " ".join(w["word"] for w in sub_words) if sub_words else f"Momento divertido {int(t)}s"
                hook_info = classify_hook(sample_text)
                candidates.append({
                    "start": t,
                    "end": t + clip_len,
                    "text": sample_text,
                    "words": sub_words,
                    "duration": clip_len,
                    "segment_idx": int(t),
                    "hook_id": hook_info["id"],
                    "hook_name": hook_info["name"],
                    "hook_emoji": hook_info["emoji"],
                    "hook_desc": hook_info["desc"],
                })
                t += step

        return candidates

    def _remove_overlapping_clips_with_hook_diversity(
        self, sorted_clips: List[Dict], n: int
    ) -> List[Dict]:
        """
        Selecciona los top N clips promoviendo DIVERSIDAD DE HOOKS:
        Intenta que cada clip seleccionado use una metodología de Hook distinta.
        """
        selected = []
        remaining = sorted_clips.copy()
        used_hooks = set()

        # Pase 1: Seleccionar clips con hooks únicos sin solapamiento
        for c in list(remaining):
            if len(selected) >= n:
                break
            # Verificar solapamiento con los ya seleccionados
            overlap = any(
                not (c["end"] <= s["start"] or c["start"] >= s["end"])
                for s in selected
            )
            if not overlap and c["hook_id"] not in used_hooks:
                selected.append(c)
                used_hooks.add(c["hook_id"])
                remaining.remove(c)

        # Pase 2: Si no alcanzamos N, rellenar con los de mayor score sin solapamiento
        for c in list(remaining):
            if len(selected) >= n:
                break
            overlap = any(
                not (c["end"] <= s["start"] or c["start"] >= s["end"])
                for s in selected
            )
            if not overlap:
                selected.append(c)

        selected.sort(key=lambda x: x["start"])
        return selected

    # ═══════════════════════════════════════════════════════
    # API Pública
    # ═══════════════════════════════════════════════════════

    def get_top_clips(self, n: int = 5) -> List[Dict]:
        self._log("Construyendo candidatos de segmentos y clasificando Hooks...")
        candidates = self._build_candidates()
        self._log(f"✓ {len(candidates)} candidatos a evaluar")

        if not candidates:
            return self._fallback_clips(n)

        self._log("Calculando Viral Score y asignando metodologías de Hook...")
        scored = []
        for candidate in candidates:
            score, sub_scores = self._compute_viral_score(candidate)
            candidate["viral_score"] = score
            candidate["audio_energy"] = sub_scores["audio_energy"]
            candidate["keyword_score"] = sub_scores["keyword"]
            candidate["sentiment_score"] = sub_scores["sentiment"]
            candidate["density_score"] = sub_scores["density"]
            scored.append(candidate)

        scored.sort(key=lambda x: x["viral_score"], reverse=True)
        top_n = self._remove_overlapping_clips_with_hook_diversity(scored, n)

        self._log(f"✓ {len(top_n)} clips seleccionados con metodologías de Hook diversas")
        return top_n

    def _fallback_clips(self, n: int) -> List[Dict]:
        clip_dur = self.max_clip_duration
        clips = []
        for i in range(n):
            hook_info = HOOK_DEFINITIONS[i % len(HOOK_DEFINITIONS)]
            clips.append({
                "start": i * clip_dur,
                "end": (i + 1) * clip_dur,
                "text": f"Segmento {i+1}",
                "words": [],
                "duration": clip_dur,
                "viral_score": 0.5,
                "audio_energy": 0.5,
                "hook_id": hook_info["id"],
                "hook_name": hook_info["name"],
                "hook_emoji": hook_info["emoji"],
                "hook_desc": hook_info["desc"],
            })
        return clips[:n]
