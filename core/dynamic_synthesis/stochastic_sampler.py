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

        EXCLUDE_FILENAMES = {
            "intro.mp4", "img_1356.mp4", "img_1366.mp4", "emotes.mp4",
            "img_1326.mov", "img_1327.mov", "img_1328.mov", "img_1329.mov",
            "img_1330.mov", "img_1331.mov", "img_1332.mov", "img_1333.mov",
            "img_1334.mov", "img_1335.mov", "img_1336.mov", "img_1355.mp4",
            "img_1372.mp4"
        }

        from core.orientation_helper import is_upright_portrait_video

        seen_gameplays = set()
        if jugadas_dir.exists():
            for ext in ["*.mov", "*.mp4", "*.MOV", "*.MP4", "*.mkv"]:
                for f in jugadas_dir.rglob(ext):
                    name_lower = f.name.lower()
                    if name_lower in EXCLUDE_FILENAMES:
                        continue
                    p_str = str(f.resolve())
                    if name_lower in seen_gameplays:
                        continue
                    if is_upright_portrait_video(p_str):
                        continue
                    seen_gameplays.add(name_lower)
                    # Check training keywords vs pvp
                    if any(kw in name_lower for kw in ["entrenamiento", "training", "tiro", "sala", "1364"]):
                        self.pools["training"].append(p_str)
                    else:
                        self.pools["pvp"].append(p_str)

        # Import persistent history prioritizer
        from core.asset_catalog import prioritize_fresh_gameplay_videos
        self.pools["pvp"] = prioritize_fresh_gameplay_videos(self.pools["pvp"])
        self.pools["training"] = prioritize_fresh_gameplay_videos(self.pools["training"])

        # Guarantee rich variety in training: combine with pvp so both pools have all 19 unique clips
        if len(self.pools["training"]) < 5 and self.pools["pvp"]:
            all_gameplays = list(self.pools["pvp"])
            for t in self.pools["training"]:
                if t not in all_gameplays:
                    all_gameplays.append(t)
            self.pools["training"] = all_gameplays
            self.pools["pvp"] = list(all_gameplays)

        # 2. Memes Pool (Full 16:9 Reaction Memes - NO GREEN SCREEN)
        seen_memes = set()
        memes_pack_dirs = [
            recurso_dir / "PACK DE MEMES",
            self.root / "PACK DE MEMES",
            self.root / "assets" / "Recurso video Freefire" / "PACK DE MEMES",
        ]
        for mpd in memes_pack_dirs:
            if mpd.exists():
                for ext in ["*.mp4", "*.mov", "*.MP4", "*.MOV"]:
                    for f in mpd.rglob(ext):
                        if not f.name.startswith(".") and f.name.lower() not in seen_memes:
                            seen_memes.add(f.name.lower())
                            self.pools["memes"].append(str(f.resolve()))
                if self.pools["memes"]:
                    break

        # 3. Overlays Pool (Sensitivity card, book guide, diamonds, avatars, etc.)
        img_dir = recurso_dir / "Imagenes"
        if img_dir.exists():
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG"]:
                for f in img_dir.rglob(ext):
                    self.pools["overlays"].append(str(f.resolve()))

        print(f"📦 [Stochastic Sampler] Discovered Pools:")
        print(f"   • PVP Gameplay Clips:      {len(self.pools['pvp'])}")
        print(f"   • Training Gameplay Clips: {len(self.pools['training'])}")
        print(f"   • Full-Frame Pack Memes:   {len(self.pools['memes'])}")
        print(f"   • Contextual Overlays:     {len(self.pools['overlays'])}")

    def sample_asset(self, pool_name: str) -> str:
        """
        Samples an asset from pool_name strictly without repetition:
        P(A_i) = 0 if A_i in S_used
        Resets S_used only when all assets in the pool have been exhausted.
        """
        pool = self.pools.get(pool_name, [])
        if not pool:
            return None

        used = self.used_state[pool_name]
        available = [a for a in pool if a not in used]

        if not available:
            # Reset pool state only when all have been shown
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
