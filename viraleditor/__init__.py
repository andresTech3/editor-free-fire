"""
viraleditor/__init__.py
=======================
Motor de Edición Viral — API pública.

Uso mínimo:
    from viraleditor import Studio
    Studio.run("input/mi_video.mp4", clips=5, preset="podcast")
"""

from .clip        import Clip, Caption
from .renderer    import FilterChain, Renderer
from .presets     import Preset, PRESETS
from .analyzer    import VoiceAnalyzer
from .studio      import Studio

__all__ = ["Clip", "Caption", "FilterChain", "Renderer",
           "Preset", "PRESETS", "VoiceAnalyzer", "Studio"]

__version__ = "1.0.0"
