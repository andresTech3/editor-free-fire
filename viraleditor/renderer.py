"""
viraleditor/renderer.py
=======================
Pipeline FFmpeg — construye y ejecuta el comando de renderizado.

FilterChain gestiona capas ordenadas:
  LAYER 0 — layout  : crop, scale, pad (SIEMPRE PRIMERO)
  LAYER 1 — color   : grade, vignette, eq, brightness
  LAYER 2 — motion  : zoompan, ken burns, shake
  LAYER 3 — fx      : flash, glitch, rgbashift
  LAYER 4 — overlay : drawbox backgrounds, progress bar, letterbox
  LAYER 5 — text    : drawtext (hook, captions, lower-third — SIEMPRE ÚLTIMO)
"""

from __future__ import annotations
import subprocess
import json
import os
import sys
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
#  FONT RESOLVER
# ─────────────────────────────────────────────────────────────────────────────

_FONTS = {
    "bold":    ["C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/ariblk.ttf",
                "C:/Windows/Fonts/verdanab.ttf"],
    "regular": ["C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf"],
    "black":   ["C:/Windows/Fonts/ariblk.ttf",
                "C:/Windows/Fonts/arialbd.ttf"],
}

_font_cache: dict[str, str] = {}


def find_font(style: str = "bold") -> str:
    if style in _font_cache:
        return _font_cache[style]
    for path in _FONTS.get(style, _FONTS["bold"]):
        if Path(path).exists():
            p = str(Path(path).as_posix())
            if len(p) > 1 and p[1] == ":":
                p = p[0] + "\\:" + p[2:]
            _font_cache[style] = p
            return p
    _font_cache[style] = ""
    return ""


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT ESCAPE
# ─────────────────────────────────────────────────────────────────────────────

def esc(text: str) -> str:
    """Escapes text for FFmpeg drawtext=text='...'"""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("'",  "\u2019")
        .replace(":",  "\\:")
        .replace(",",  "\\,")
        .replace("[",  "\\[")
        .replace("]",  "\\]")
        .replace("%",  "\\%")
        .replace("$",  "\\$")
        .replace("@",  "\\@")
        .replace("#",  "")
        .replace("!",  "\\!")
        .replace('"',  '\\"')
        .replace("\n", " ")
    )


# ─────────────────────────────────────────────────────────────────────────────
#  FILTER CHAIN
# ─────────────────────────────────────────────────────────────────────────────

class FilterChain:
    """
    Ordered FFmpeg video filter builder.

    Maintains 6 layers to ensure correct filter ordering.
    Call .build() to get the final comma-joined -vf string.
    """

    N_LAYERS = 6
    LAYER_LAYOUT     = 0   # crop, scale, pad
    LAYER_COLOR      = 1   # color grade, vignette, eq
    LAYER_MOTION     = 2   # zoompan, ken burns
    LAYER_FX         = 3   # flash, glitch
    LAYER_OVERLAY    = 4   # drawbox bg, progress bar, bars
    LAYER_TEXT       = 5   # drawtext (always last)

    def __init__(self, out_w: int = 1080, out_h: int = 1920,
                 fps: int = 30, clip_dur: float = 60.0):
        self.out_w    = out_w
        self.out_h    = out_h
        self.fps      = fps
        self.clip_dur = clip_dur
        self._layers: list[list[str]] = [[] for _ in range(self.N_LAYERS)]

    def add(self, layer: int, f: str):
        """Add a single filter string to the specified layer."""
        if f:
            self._layers[layer].append(f)

    def build(self) -> str:
        """Return the final -vf filter chain string."""
        all_filters = []
        for layer in self._layers:
            all_filters.extend(layer)
        return ",".join(all_filters) if all_filters else "null"

    def count(self) -> int:
        return sum(len(layer) for layer in self._layers)

    # ── Convenience helpers ───────────────────────────────────────────────────

    def drawtext(
        self,
        text:      str,
        x:         str  = "(w-text_w)/2",
        y:         str  = "(h-text_h)/2",
        fontsize:  int  = 60,
        color:     str  = "white",
        font:      str  = "bold",
        shadow:    bool = True,
        box:       bool = False,
        boxcolor:  str  = "black@0.45",
        t0:        Optional[float] = None,
        t1:        Optional[float] = None,
    ) -> str:
        font_arg  = f"fontfile='{find_font(font)}':" if find_font(font) else ""
        parts = [
            f"drawtext=text='{esc(text)}'",
            font_arg + f"fontsize={fontsize}",
            f"fontcolor={color}",
            f"x={x}",
            f"y={y}",
        ]
        if shadow:
            parts.append("shadowcolor=black@0.75:shadowx=3:shadowy=3")
        if box:
            parts.append(f"box=1:boxcolor={boxcolor}:boxborderw=14")
        if t0 is not None and t1 is not None:
            parts.append(f"enable='between(t,{t0:.3f},{t1:.3f})'")
        elif t0 is not None:
            parts.append(f"enable='gte(t,{t0:.3f})'")
        return ":".join(parts)

    def drawbox(
        self,
        x: str = "0", y: str = "0",
        w: str = "iw", h: str = "100",
        color: str = "black@0.6",
        t0: Optional[float] = None,
        t1: Optional[float] = None,
    ) -> str:
        enable = ""
        if t0 is not None and t1 is not None:
            enable = f":enable='between(t,{t0:.3f},{t1:.3f})'"
        return f"drawbox=x={x}:y={y}:w={w}:h={h}:color={color}:t=fill{enable}"


# ─────────────────────────────────────────────────────────────────────────────
#  RENDERER
# ─────────────────────────────────────────────────────────────────────────────

class Renderer:
    """
    Executes FFmpeg to render a clip with a FilterChain.

    Supports:
      - GPU acceleration (NVENC) if available
      - Audio: normalize, highpass, loudnorm
      - Web-ready output: H.264 + AAC, faststart
    """

    def __init__(self, gpu: bool = False):
        self.gpu = gpu and self._has_nvenc()

    @staticmethod
    def _has_nvenc() -> bool:
        r = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return "h264_nvenc" in r.stdout

    @staticmethod
    def probe(path: str) -> dict:
        """Returns dict with 'duration', 'width', 'height', 'fps' for a video."""
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        try:
            d = json.loads(r.stdout)
        except Exception:
            return {"duration": 0.0, "width": 0, "height": 0, "fps": 30.0}

        info = {"duration": 0.0, "width": 1920, "height": 1080, "fps": 30.0}
        fmt = d.get("format", {})
        info["duration"] = float(fmt.get("duration", 0))

        for s in d.get("streams", []):
            if s.get("codec_type") == "video":
                info["width"]  = int(s.get("width",  1920))
                info["height"] = int(s.get("height", 1080))
                fps_str = s.get("r_frame_rate", "30/1")
                try:
                    num, den = fps_str.split("/")
                    info["fps"] = float(num) / float(den)
                except Exception:
                    info["fps"] = 30.0
                break
        return info

    def render(
        self,
        src:        str,
        out:        str,
        start:      float,
        duration:   float,
        vf:         FilterChain,
        af:         str = "",
        crf:        int = 17,
        audio_vol:  float = 1.25,
        sfx_events: list = None,     # list of {path, t, vol} dicts for SFX injection
    ) -> tuple[bool, str]:
        """
        Renders a clip. Returns (success: bool, stderr: str).
        Uses -filter_script:v to avoid Windows 8191-char command-line limit.
        When sfx_events is provided, injects SFX audio using FFmpeg amix.
        """
        import tempfile

        vcodec = "h264_nvenc" if self.gpu else "libx264"
        preset  = "p4" if self.gpu else "fast"

        default_af = (
            f"aresample=44100,"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={audio_vol},"
            f"highpass=f=80,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11"
        )
        audio_filter = af if af else default_af

        # Write filter chain to a temp .txt so we bypass Windows 8191-char limit
        vf_chain = vf.build()

        is_complex = "split=2" in vf_chain or "[v_" in vf_chain
        if is_complex and not vf_chain.startswith("["):
            vf_chain = "[0:v]" + vf_chain

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False,
            encoding="utf-8", errors="replace"
        ) as tmp:
            tmp.write(vf_chain)
            filter_script = tmp.name

        try:
            filter_flag = "-filter_complex_script" if is_complex else "-filter_script:v"

            # ── SFX audio injection via FFmpeg amix ─────────────────────────
            if sfx_events:
                valid_sfx = [e for e in sfx_events if os.path.exists(e.get("path", ""))]
            else:
                valid_sfx = []

            if valid_sfx:
                # Build multi-input FFmpeg command with filter_complex for audio mixing
                sfx_inputs = []
                for ev in valid_sfx:
                    sfx_inputs += ["-i", ev["path"]]

                # Audio filter_complex: delay each SFX + amix everything
                n_inputs = 1 + len(valid_sfx)   # 1 video source + N sfx
                parts = [f"[0:a]{audio_filter}[main_a]"]
                for idx, ev in enumerate(valid_sfx):
                    delay_ms = int(ev.get("t", 0.0) * 1000)
                    vol       = ev.get("vol", 0.8)
                    sfx_idx   = idx + 1
                    parts.append(
                        f"[{sfx_idx}:a]"
                        f"adelay={delay_ms}|{delay_ms},"
                        f"volume={vol:.2f},"
                        f"aresample=44100,"
                        f"aformat=sample_fmts=fltp:channel_layouts=stereo"
                        f"[sfx{idx}]"
                    )
                mix_inputs = "[main_a]" + "".join(f"[sfx{i}]" for i in range(len(valid_sfx)))
                parts.append(f"{mix_inputs}amix=inputs={n_inputs}:duration=first:dropout_transition=0[out_a]")
                fc_audio = ";".join(parts)

                # Use filter_complex for both video and audio mixing
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix="_audio.txt", delete=False,
                    encoding="utf-8", errors="replace"
                ) as atmp:
                    atmp.write(fc_audio)
                    audio_fc_script = atmp.name

                cmd = [
                    "ffmpeg", "-y",
                    "-ss", f"{start:.3f}",
                    "-t",  f"{duration:.3f}",
                    "-i",  src,
                ] + sfx_inputs + [
                    filter_flag, filter_script,
                    "-filter_complex_script", audio_fc_script,
                    "-map", "0:v",
                    "-map", "[out_a]",
                    "-c:v", vcodec,
                    "-preset", preset,
                    "-crf", str(crf),
                    "-c:a", "aac", "-b:a", "192k",
                    "-avoid_negative_ts", "make_zero",
                    "-movflags", "+faststart",
                    out,
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace"
                )
                try:
                    os.unlink(audio_fc_script)
                except Exception:
                    pass

                if result.returncode == 0:
                    return True, result.stderr

                # SFX mixing failed — fallback to no-SFX render
            # ── Standard render (no SFX or SFX failed) ──────────────────────
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start:.3f}",
                "-t",  f"{duration:.3f}",
                "-i",  src,
                filter_flag, filter_script,
                "-af", audio_filter,
                "-c:v", vcodec,
                "-preset", preset,
                "-crf", str(crf),
                "-c:a", "aac", "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                "-movflags", "+faststart",
                out,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            return result.returncode == 0, result.stderr
        finally:
            try:
                os.unlink(filter_script)
            except Exception:
                pass

    def probe_duration(self, path: str) -> float:
        return self.probe(path)["duration"]

