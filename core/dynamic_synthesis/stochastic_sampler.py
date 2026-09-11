"""
stochastic_sampler.py — Stochastic Asset Selection Engine (No Repetition)
========================================================================
Implements:
1. Dynamic Asset Pool Discovery:
   - POOL_CLIPS_PVP
   - POOL_CLIPS_TRAINING
   - POOL_MEMES
   - POOL_OVERLAYS
2. Dynamic Sampler Algorithm:
   - Tracks S_used set
   - P(A_i) = 0 if A_i in S_used
   - Resets S_used only when |S_used| >= 0.8 * |S_pool|
3. Sub-Clip Slicing:
   - Delta t_cut in [1.8s, 3.5s]
   - Safe start slice avoiding motionless spawn areas
"""

import os
import sys

# UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import random
import time as _time
from pathlib import Path
import cv2


class StochasticAssetSampler:
    def __init__(self, assets_root: str):
        self.root = Path(assets_root).resolve()
        self.pools = {
            "pvp": [],
            "training": [],
            "memes": [],
            "overlays": []
        }
        self.used_state = {
            "pvp": set(),
            "training": set(),
            "memes": set(),
            "overlays": set()
        }
        self.clip_durations = {}
        # Entropy seed: each instantiation yields a unique shuffle order
        _seed = int(_time.time() * 1e6) % (2**31)
        random.seed(_seed)
        self._session_seed = _seed
        self._discover_pools()

    def _discover_pools(self):
        """Scans directories and classifies assets into pools."""
        recurso_dir = self.root / "Recurso video Freefire" if (self.root / "Recurso video Freefire").exists() else self.root

        # 1. Gameplay PVP & Training Pools
        jugadas_dir = recurso_dir / "free fire jugadas"
        if not jugadas_dir.exists():
            jugadas_dir = self.root / "gameplay"

        if jugadas_dir.exists():
            for ext in ["*.mov", "*.mp4", "*.MOV", "*.MP4", "*.mkv"]:
                for f in jugadas_dir.rglob(ext):
                    name_lower = f.name.lower()
                    if "intro" in name_lower:
                        continue
                    if any(ex in name_lower for ex in ["intro", "img_1356", "img_1366"]):
                        continue
                    p_str = str(f.resolve())
                    # Check training keywords vs pvp
                    if any(kw in name_lower for kw in ["entrenamiento", "training", "tiro", "sala", "1364"]):
                        self.pools["training"].append(p_str)
                    else:
                        self.pools["pvp"].append(p_str)

        # Import persistent history prioritizer
        from core.asset_catalog import prioritize_fresh_gameplay_videos
        self.pools["pvp"] = prioritize_fresh_gameplay_videos(self.pools["pvp"])
        self.pools["training"] = prioritize_fresh_gameplay_videos(self.pools["training"])

        # Fallback if training is empty
        if not self.pools["training"] and self.pools["pvp"]:
            self.pools["training"] = list(self.pools["pvp"])
        elif not self.pools["pvp"] and self.pools["training"]:
            self.pools["pvp"] = list(self.pools["training"])

        # 2. Memes Pool (Green screen memes prioritized for Shorts)
        memes_green_dir = recurso_dir / "PACK MEMES PANTALLA VERDE 1 (manuDT)"
        if memes_green_dir.exists():
            for ext in ["*.mp4", "*.mov", "*.MP4", "*.MOV"]:
                for f in memes_green_dir.rglob(ext):
                    self.pools["memes"].append(str(f.resolve()))

        # 3. Overlays Pool (Sensitivity card, book guide, diamonds, avatars, etc.)
        img_dir = recurso_dir / "Imagenes"
        if img_dir.exists():
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG"]:
                for f in img_dir.rglob(ext):
                    self.pools["overlays"].append(str(f.resolve()))

        print(f"📦 [Stochastic Sampler] Discovered Pools:")
        print(f"   • PVP Gameplay Clips:      {len(self.pools['pvp'])}")
        print(f"   • Training Gameplay Clips: {len(self.pools['training'])}")
        print(f"   • Green Screen Memes:      {len(self.pools['memes'])}")
        print(f"   • Contextual Overlays:     {len(self.pools['overlays'])}")

    def sample_asset(self, pool_name: str) -> str:
        """
        Samples an asset from pool_name without repetition:
        P(A_i) = 0 if A_i in S_used
        Resets S_used when |S_used| >= 0.8 * |S_pool|
        """
        pool = self.pools.get(pool_name, [])
        if not pool:
            return None

        used = self.used_state[pool_name]
        available = [a for a in pool if a not in used]

        if not available or (len(used) >= 0.8 * len(pool)):
            # Reset pool state
            self.used_state[pool_name].clear()
            available = list(pool)

        chosen = random.choice(available)
        self.used_state[pool_name].add(chosen)
        return chosen

    def get_clip_duration(self, video_path: str) -> float:
        """Cached duration query using OpenCV."""
        if video_path in self.clip_durations:
            return self.clip_durations[video_path]
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 150
        cap.release()
        dur = max(1.0, n_frames / fps)
        self.clip_durations[video_path] = dur
        return dur

    def slice_sub_clip(self, video_path: str, min_dur: float = 1.8, max_dur: float = 3.5) -> dict:
        """
        Randomly samples sub-clip start and duration:
        Delta t_cut in [min_dur, max_dur]
        t_start in U(2.0, T_clip - Delta t_cut) avoiding spawn cages.
        """
        t_total = self.get_clip_duration(video_path)
        clip_dur = round(random.uniform(min_dur, min(max_dur, max(min_dur, t_total))), 2)

        safe_min = 2.0 if t_total >= 5.0 else 0.0
        max_start = max(safe_min, t_total - clip_dur)

        if max_start > safe_min:
            t_start = round(random.uniform(safe_min, max_start), 2)
        else:
            t_start = 0.0

        return {
            "path": video_path,
            "start": t_start,
            "duration": clip_dur,
            "end": t_start + clip_dur
        }
