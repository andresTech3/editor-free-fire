"""
core/fish_audio_service.py - Fish Audio API Integration with Smart Fallback
===========================================================================
Connects to Fish Audio API (https://api.fish.audio/v1/tts) to generate high-fidelity
neural voiceover audio from text.

Includes seamless fallback to Microsoft Azure Neural (edge-tts) if Fish Audio
returns 402 (Insufficient API credit) or network timeout, ensuring generation
never fails.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Set UTF-8 Encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Default user Fish Audio API Key
DEFAULT_FISH_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "sk-fish-BFpY4iWJsh5MZHlRIZYFhhyeqHLa_t700vFiD8uKwyw")
FISH_TTS_ENDPOINT = "https://api.fish.audio/v1/tts"

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_TTS_DIR = PROJECT_ROOT / "assets" / "Recurso video Freefire" / "Generar Video"


class FishAudioService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DEFAULT_FISH_API_KEY

    def generate_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_id: Optional[str] = None,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Synthesizes text into speech.
        Attempts Fish Audio API first; if unavailable or credit exhausted (402),
        transparently falls back to edge-tts.
        """
        text = text.strip()
        if not text:
            raise ValueError("El texto para generar voz no puede estar vacío.")

        if not output_path:
            DEFAULT_TTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(DEFAULT_TTS_DIR / "locucion_ia.mp3")

        output_path = str(Path(output_path).resolve())
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        print(f"\n🎙️ [Fish Audio TTS] Solicitando síntesis de voz...")
        print(f"📝 Texto ({len(text)} caracteres): \"{text[:70]}...\"")

        # 1. Try Fish Audio API
        fish_success, fish_message = self._call_fish_audio_api(text, output_path, voice_id)
        if fish_success:
            print(f"✅ [Fish Audio TTS] Audio generado exitosamente con Fish Audio API: {output_path}")
            return {
                "success": True,
                "engine": "fish_audio",
                "audio_path": output_path,
                "message": "Generado exitosamente con Fish Audio API."
            }

        # 2. Fallback to Microsoft Azure Neural (edge-tts)
        print(f"⚠️ [Fish Audio TTS] {fish_message}")
        print("🔄 Activando respaldo con Microsoft Azure Neural (edge-tts)...")
        fallback_success, fb_message = self._call_edge_tts(text, output_path)
        if fallback_success:
            print(f"✅ [Respaldo TTS] Audio generado con éxito vía Azure Neural: {output_path}")
            return {
                "success": True,
                "engine": "azure_neural_fallback",
                "audio_path": output_path,
                "notice": f"Fish Audio notice: {fish_message}",
                "message": "Audio generado correctamente (usando motor de voz de alta fidelidad)."
            }

        return {
            "success": False,
            "engine": "none",
            "audio_path": None,
            "message": f"Error en síntesis: {fish_message} | Respaldo: {fb_message}"
        }

    def _call_fish_audio_api(self, text: str, output_path: str, voice_id: Optional[str]) -> tuple[bool, str]:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "format": "mp3",
            "latency": "normal"
        }
        if voice_id:
            payload["reference_id"] = voice_id

        try:
            resp = requests.post(FISH_TTS_ENDPOINT, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 100:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return True, "OK"
            elif resp.status_code == 402:
                msg = "Crédito de API de Fish Audio insuficiente (402). Recarga en https://fish.audio/app/developers"
                return False, msg
            else:
                return False, f"Fish Audio API HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            return False, f"Error de conexión con Fish Audio: {e}"

    def _call_edge_tts(self, text: str, output_path: str) -> tuple[bool, str]:
        try:
            import edge_tts
            import concurrent.futures

            communicate = edge_tts.Communicate(text, voice="es-MX-JorgeNeural", rate="+12%")

            # Run in worker thread to prevent event loop collision in FastAPI / uvicorn
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(asyncio.run, communicate.save(output_path)).result()

            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                return True, "OK"
            return False, "Archivo generado vacío"
        except Exception as e:
            # Last resort: gTTS
            try:
                from gtts import gTTS
                tts = gTTS(text=text, lang="es", slow=False)
                tts.save(output_path)
                return True, "OK (gTTS)"
            except Exception as e2:
                return False, f"edge-tts error: {e}, gTTS error: {e2}"


# Global instance
fish_audio_service = FishAudioService()


def text_to_speech(text: str, output_path: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    svc = FishAudioService(api_key=api_key) if api_key else fish_audio_service
    return svc.generate_speech(text, output_path=output_path)
