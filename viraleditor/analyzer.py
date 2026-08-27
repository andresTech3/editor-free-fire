"""
viraleditor/analyzer.py
========================
Detección automática de momentos virales en transcripciones Whisper.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

__all__ = ["ViralMoment", "VoiceAnalyzer"]


@dataclass
class ViralMoment:
    """A candidate viral clip segment."""
    start:   float
    end:     float
    score:   float
    text:    str
    reason:  str   # what triggered the high score

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __repr__(self):
        return (
            f"<ViralMoment [{self.start:.0f}s-{self.end:.0f}s] "
            f"({self.duration:.0f}s) score={self.score:.1f} | "
            f"{self.text[:60]}>"
        )


class VoiceAnalyzer:
    """
    Scores transcript segments by virality potential.

    Scoring criteria:
    - Hook words (copied, million, raised, secret, fight...)
    - Energy markers (crazy, insane, nobody, always, never)
    - Financial markers ($, million, billion, %)
    - Conflict markers (vs, against, fired, quit, war)
    - Question openers (how did, why did, what if, did you)
    """

    # Base scores
    HOOK_WORDS: dict[str, float] = {
        # Drama / conflict
        "copied":    3.0, "stole":    3.0, "plagiarized": 3.0,
        "fight":     2.0, "fought":   2.0, "war":         1.8,
        "fired":     2.5, "quit":     2.0, "left":        1.5,
        "betrayed":  2.5, "lied":     2.0, "cheated":     2.0,
        "sued":      2.5, "lawsuit":  2.5,
        # Money
        "million":   2.0, "billion":  2.5, "raised":      1.8,
        "funding":   1.5, "revenue":  1.5, "valuation":   1.5,
        "money":     1.2, "profit":   1.5, "loss":        1.5,
        # Emotion / energy
        "crazy":     1.8, "insane":   1.8, "unbelievable":1.8,
        "nobody":    1.5, "everyone": 1.2, "secret":      2.0,
        "never":     1.3, "always":   1.2, "worst":       1.5,
        "best":      1.0, "first":    1.2, "only":        1.3,
        # Question openers
        "why":       0.8, "how":      0.8, "what":        0.6,
        "when":      0.5, "who":      0.5,
        # Tech / startup
        "ai":        1.5, "startup":  1.2, "founder":     1.2,
        "product":   0.8, "company":  0.8, "team":        0.6,
        "launch":    1.0, "ship":     1.0, "build":       0.8,
        # ── Gaming kill / streak events ──────────────────────────────────
        "kill":      2.0, "killed":   2.0, "killing":     1.8,
        "double":    2.5, "triple":   3.5, "quadruple":   4.0,
        "quintuple": 4.5, "multikill":4.0, "ace":         4.5,
        "dominating":3.5, "unstoppable":4.0, "legendary": 4.0,
        "godlike":   4.5, "rampage":  3.5, "massacre":    3.5,
        "annihilation":3.5, "flawless":3.0,
        "clutch":    3.5, "headshot": 2.5, "sniper":      2.0,
        "wipeout":   3.0, "eliminated":2.0, "eliminated": 2.0,
        "overkill":  3.5, "savage":   2.5, "slayer":      2.5,
        # ── Gaming emotion / reaction ─────────────────────────────────────
        "bro":       1.5, "omg":      2.0, "no way":      2.5,
        "lmao":      2.5, "lol":      1.5, "wtf":         2.5,
        "oh":        0.8, "wow":      1.5, "dude":        1.2,
        "dios":      1.5, "uff":      1.2, "ay":          0.8,
        "jaja":      1.5, "haha":     1.5, "nooo":        2.0,
        "lets go":   2.5, "vamos":    2.0, "yeah":        1.2,
        # ── Spanish gaming terms ──────────────────────────────────────────
        "matar":     1.8, "mato":     1.8, "murieron":    1.8,
        "disparar":  1.5, "rachazo":  3.5, "racha":       3.0,
        "eliminacion":2.5, "eliminaciones":3.0,
        "dominando": 3.5, "imparable":3.5, "legendario":  3.5,
        "triple":    3.5, "doble":    2.5, "cuadruple":   4.0,
    }


    # Multipliers for specific patterns
    PATTERN_BOOST: list[tuple[str, float]] = [
        ("$",       1.5),   # money reference
        ("%",       1.2),   # percentage = specific stat
        ("?",       1.3),   # question = hook
        ("!",       1.2),   # exclamation = energy
        ("...",     0.8),   # trailing thought
    ]

    def find_moments(
        self,
        transcript:     dict,
        min_dur:        float = 20.0,
        max_dur:        float = 75.0,
        top_n:          int   = 10,
        overlap_guard:  float = 25.0,  # min seconds between selections
    ) -> list[ViralMoment]:
        """
        Scans the transcript and returns the top-n viral moments.

        Each moment is a window of segments totaling min_dur–max_dur seconds.
        Moments are deduplicated so they don't overlap heavily.
        """
        segments = transcript.get("segments", [])
        candidates: list[ViralMoment] = []

        if segments:
            for i, seg in enumerate(segments):
                seg_start = float(seg.get("start", 0))

                # Build a window of segments up to max_dur
                window_segs: list[dict] = []
                window_text = ""
                j = i
                while j < len(segments):
                    s = segments[j]
                    window_dur = float(s.get("end", 0)) - seg_start
                    if window_dur > max_dur:
                        break
                    window_segs.append(s)
                    window_text += " " + s.get("text", "")
                    j += 1

                if not window_segs:
                    continue

                actual_dur = float(window_segs[-1].get("end", seg_start)) - seg_start
                if actual_dur < min_dur:
                    continue

                end_sec = float(window_segs[-1].get("end", seg_start + actual_dur))
                score, reason = self._score(window_text)

                # Penalty for clips much longer than 45s
                if actual_dur > 50:
                    score *= 0.80

                candidates.append(ViralMoment(
                    start=seg_start,
                    end=end_sec,
                    score=round(score, 2),
                    text=window_text.strip()[:250],
                    reason=reason,
                ))

        # Fallback 1: If min_dur filtered out short segments, relax min_dur constraint
        if not candidates and segments:
            seg_start = float(segments[0].get("start", 0))
            seg_end = float(segments[-1].get("end", seg_start + 20.0))
            dur = seg_end - seg_start
            full_text = " ".join(s.get("text", "") for s in segments)
            score, reason = self._score(full_text)
            candidates.append(ViralMoment(
                start=seg_start,
                end=seg_end,
                score=max(5.0, score),
                text=full_text[:250].strip() or "Highlight clip",
                reason=reason or "full transcript",
            ))

        # Fallback 2: If no speech/transcript detected at all (e.g. gaming without commentary), slice video uniformly
        if not candidates:
            duration = float(transcript.get("duration", 120.0))
            if duration <= 10.0:
                candidates.append(ViralMoment(
                    start=0.0, end=duration, score=5.0,
                    text="Gaming Highlight", reason="full video"
                ))
            else:
                chunk_dur = min(max_dur, max(min_dur, 30.0))
                step = max(chunk_dur, duration / max(1, top_n))
                curr = 0.0
                while curr < duration and len(candidates) < top_n:
                    end_t = min(duration, curr + chunk_dur)
                    if end_t - curr >= 5.0:
                        candidates.append(ViralMoment(
                            start=round(curr, 2),
                            end=round(end_t, 2),
                            score=5.0,
                            text=f"Gaming Action Clip ({curr:.0f}s - {end_t:.0f}s)",
                            reason="gameplay highlight",
                        ))
                    curr += step

        # Sort by score descending
        candidates.sort(key=lambda m: m.score, reverse=True)

        # Deduplicate (no overlapping windows)
        selected: list[ViralMoment] = []
        for cand in candidates:
            too_close = any(
                abs(cand.start - sel.start) < overlap_guard
                for sel in selected
            )
            if not too_close:
                selected.append(cand)
            if len(selected) >= top_n:
                break

        return selected if selected else candidates[:top_n]

    def _score(self, text: str) -> tuple[float, str]:
        """Score a block of text. Returns (score, reason_string)."""
        lower   = text.lower()
        words   = lower.split()
        score   = 0.0
        reasons: list[str] = []

        for word in words:
            clean = word.strip(".,!?\"'();:-")
            if clean in self.HOOK_WORDS:
                s = self.HOOK_WORDS[clean]
                score += s
                if s >= 2.0:
                    reasons.append(f"'{clean}'({s:.1f})")

        for pattern, mult in self.PATTERN_BOOST:
            count = text.count(pattern)
            if count:
                bonus = mult * count
                score += bonus

        reason = ", ".join(reasons[:4]) if reasons else "general content"
        return score, reason
