"""
web_server.py — High-Performance Mobile & Web Backend for Free Fire Video Studio
================================================================================
FastAPI + Uvicorn server providing:
- Mobile-friendly web interface for iOS and Android smartphones.
- REST API for audio/resource uploads, asset investigation, and video generation.
- Real-time job progress tracking and streaming video delivery.
"""

import os
import sys
import time
import uuid
import shutil
import socket
import asyncio
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

# Set UTF-8 encoding on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.asset_investigator import AssetInvestigator

# Project Paths
PROJECT_ROOT = Path(__file__).parent.resolve()
ASSETS_DIR = PROJECT_ROOT / "assets" / "Recurso video Freefire"
OUTPUT_DIR = PROJECT_ROOT / "output"
WEB_STUDIO_DIR = PROJECT_ROOT / "web_studio"
TEMP_UPLOADS_DIR = PROJECT_ROOT / "temp_uploads"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_temp_dir(dir_path: Optional[str]):
    """Safely removes a temporary session directory to prevent disk bloat."""
    if not dir_path:
        return
    try:
        p = Path(dir_path).resolve()
        temp_root = TEMP_UPLOADS_DIR.resolve()
        # Strictly verify it is a subfolder of TEMP_UPLOADS_DIR and not root or assets
        if temp_root in p.parents and p != temp_root and p != PROJECT_ROOT.resolve():
            shutil.rmtree(p, ignore_errors=True)
            print(f"🧹 [Auto-Cleanup] Recursos temporales eliminados del disco: {p.name}")
    except Exception as e:
        print(f"⚠️ [Auto-Cleanup] Error limpiando directorio temporal: {e}")

def cleanup_all_temp_uploads():
    """Cleans leftover directories inside temp_uploads upon server startup."""
    try:
        if TEMP_UPLOADS_DIR.exists():
            for item in TEMP_UPLOADS_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    item.unlink(missing_ok=True)
            print("🧹 [Auto-Cleanup] Carpeta temp_uploads vaciada y lista.")
    except Exception as e:
        print(f"⚠️ [Auto-Cleanup] Error al inicializar temp_uploads: {e}")

# Clean any existing leftover temporary uploads on startup
cleanup_all_temp_uploads()

app = FastAPI(title="Codigo Headshot Mobile & Web Studio", version="26.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job State Store
jobs_lock = threading.Lock()
jobs: Dict[str, Dict[str, Any]] = {}
sessions: Dict[str, Dict[str, Any]] = {}

def get_local_ip() -> str:
    """Finds the primary local network IP (e.g. 192.168.1.X) for mobile access."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# Precomputed default official pack summary (prevents blocking the server on startup)
DEFAULT_PACK_SUMMARY = {
    "gameplay_count": 37,
    "memes_count": 282,
    "images_count": 16,
    "audios_count": 12,
    "green_screen_memes_count": 196,
    "transparent_images_count": 7
}

default_investigation_cache = {"summary": DEFAULT_PACK_SUMMARY}

def get_default_investigation() -> Dict[str, Any]:
    global default_investigation_cache
    return default_investigation_cache

# ── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.get("/api/info")
async def get_server_info():
    ip = get_local_ip()
    return {
        "status": "online",
        "local_ip": ip,
        "mobile_url": f"http://{ip}:8000",
        "default_assets": DEFAULT_PACK_SUMMARY
    }

from pydantic import BaseModel

class GenerateRequest(BaseModel):
    session_id: Optional[str] = None
    audio_path: Optional[str] = None
    resources_dir: Optional[str] = None
    aspect_ratio: Optional[str] = "9:16"
    aspect: Optional[str] = None
    speed: Optional[float] = 1.5
    hook_mode: Optional[str] = "auto"
    hook_preference: Optional[str] = None
    bgm: Optional[bool] = True
    outname: Optional[str] = None
    outdir: Optional[str] = None

@app.post("/api/upload")
async def upload_files(
    audio: UploadFile = File(...),
    use_default_resources: Any = Form(True),
    resources: Optional[List[UploadFile]] = File(None)
):
    session_id = str(uuid.uuid4())[:8]
    session_dir = TEMP_UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save audio file
    audio_suffix = Path(audio.filename).suffix or ".mp3"
    audio_path = session_dir / f"voiceover{audio_suffix}"
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    res_dir = None
    investigation_summary = None

    is_default = True
    if isinstance(use_default_resources, bool):
        is_default = use_default_resources
    elif isinstance(use_default_resources, str):
        is_default = use_default_resources.strip().lower() not in ["false", "0", "no"]

    if is_default or not resources:
        res_dir = ASSETS_DIR
        investigation_summary = {
            "mode": "official_default_pack",
            "message": "Usando el Pack Maestro Oficial Free Fire (37 jugadas, memes verdes, armas, diamantes)",
            "details": DEFAULT_PACK_SUMMARY
        }
    else:
        # Save custom uploaded resources
        custom_res_dir = session_dir / "custom_resources"
        custom_res_dir.mkdir(parents=True, exist_ok=True)
        print(f"📥 [Server] Guardando {len(resources)} archivos subidos por el usuario en {custom_res_dir}...")
        for r_file in resources:
            if r_file.filename:
                target_f = custom_res_dir / Path(r_file.filename).name
                with open(target_f, "wb") as f:
                    shutil.copyfileobj(r_file.file, f)
        res_dir = custom_res_dir
        inv = AssetInvestigator(str(custom_res_dir))
        custom_inv = inv.investigate()
        investigation_summary = {
            "mode": "custom_uploaded_pack",
            "message": f"Se investigaron {custom_inv['total_files']} archivos personalizados subidos",
            "details": custom_inv["summary"]
        }

    sessions[session_id] = {
        "session_dir": str(session_dir),
        "audio_path": str(audio_path),
        "audio_name": audio.filename,
        "resources_dir": str(res_dir),
        "use_default": use_default_resources,
        "investigation": investigation_summary
    }

    return {
        "success": True,
        "session_id": session_id,
        "audio_name": audio.filename,
        "audio_path": str(audio_path),
        "resources_dir": str(res_dir),
        "investigation": investigation_summary
    }

def run_editor_process(job_id: str, cmd: List[str], target_file: Path, session_dir: Optional[str] = None):
    """Executes editing subprocess, parsing progress from output lines."""
    with jobs_lock:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["step"] = "Iniciando motor de edición profesional..."
        jobs[job_id]["progress"] = 10

    try:
        proc_env = os.environ.copy()
        proc_env["PYTHONUNBUFFERED"] = "1"
        proc_env["PYTHONIOENCODING"] = "utf-8"

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=proc_env,
            cwd=str(PROJECT_ROOT)
        )

        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            clean_line = line.strip()
            if not clean_line:
                continue

            with jobs_lock:
                jobs[job_id]["logs"].append(clean_line)
                # Keep last 80 logs
                if len(jobs[job_id]["logs"]) > 80:
                    jobs[job_id]["logs"].pop(0)

                # Update progress based on process milestones
                if "Whisper" in clean_line or "Transcribing" in clean_line:
                    jobs[job_id]["progress"] = max(jobs[job_id]["progress"], 25)
                    jobs[job_id]["step"] = "Analizando audio de locución con Whisper..."
                elif "Discovered" in clean_line or "Headshots" in clean_line or "OpenCV" in clean_line or "Investigador" in clean_line:
                    jobs[job_id]["progress"] = max(jobs[job_id]["progress"], 45)
                    jobs[job_id]["step"] = "Investigando jugadas y detectando headshots..."
                elif "Montage" in clean_line or "Contextual Memes" in clean_line or "Memes" in clean_line:
                    jobs[job_id]["progress"] = max(jobs[job_id]["progress"], 65)
                    jobs[job_id]["step"] = "Sincronizando memes contextuales y capas visuales..."
                elif "Compiling" in clean_line or "FFmpeg render" in clean_line or "Master" in clean_line or "Remotion" in clean_line:
                    jobs[job_id]["progress"] = max(jobs[job_id]["progress"], 85)
                    jobs[job_id]["step"] = "Renderizando video maestro en alta definición (60 FPS)..."

        proc.wait()

        # Limpiar automáticamente los archivos temporales subidos por el usuario (audio y clips personalizados)
        if session_dir:
            cleanup_temp_dir(session_dir)

        if proc.returncode == 0 and target_file.exists():
            with jobs_lock:
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["progress"] = 100
                jobs[job_id]["step"] = "¡Video generado exitosamente!"
                jobs[job_id]["output_file"] = str(target_file)
                jobs[job_id]["file_size_mb"] = round(os.path.getsize(target_file) / (1024 * 1024), 2)
        else:
            with jobs_lock:
                last_err_lines = [l for l in jobs[job_id]["logs"][-10:] if "Error" in l or "error" in l or "Exception" in l or "Traceback" in l]
                summary_err = " | ".join(last_err_lines) if last_err_lines else "Fallo durante el renderizado. Revisa los registros."
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = summary_err
                jobs[job_id]["step"] = "Fallo en la generación"
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["step"] = "Fallo en la ejecución"

@app.post("/api/generate")
async def generate_video(payload: GenerateRequest):
    audio_path = None
    res_dir = None
    session_dir = None

    if payload.session_id and payload.session_id in sessions:
        session = sessions[payload.session_id]
        audio_path = session.get("audio_path")
        res_dir = session.get("resources_dir")
        session_dir = session.get("session_dir")
    
    if not audio_path and payload.audio_path:
        audio_path = payload.audio_path
    
    if not session_dir and audio_path:
        try:
            p = Path(audio_path).resolve()
            temp_root = TEMP_UPLOADS_DIR.resolve()
            if temp_root in p.parents:
                for parent in p.parents:
                    if parent.parent == temp_root:
                        session_dir = str(parent)
                        break
        except Exception:
            pass

    if not res_dir:
        res_dir = payload.resources_dir or str(ASSETS_DIR)

    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=400, detail="Archivo de audio no encontrado. Sube un audio primero.")

    aspect = payload.aspect or payload.aspect_ratio or "9:16"
    speed = payload.speed or 1.5
    hook_mode = payload.hook_preference or payload.hook_mode or "auto"
    bgm = payload.bgm if payload.bgm is not None else True

    job_id = str(uuid.uuid4())[:8]
    out_dir_target = OUTPUT_DIR
    if payload.outdir and payload.outdir.strip():
        try:
            out_dir_target = Path(payload.outdir.strip()).resolve()
            out_dir_target.mkdir(parents=True, exist_ok=True)
        except Exception:
            out_dir_target = OUTPUT_DIR

    if payload.outname and payload.outname.strip():
        out_filename = payload.outname.strip()
        if not out_filename.lower().endswith(".mp4"):
            out_filename += ".mp4"
    else:
        out_filename = f"video_{aspect.replace(':', 'x')}_{job_id}.mp4"

    target_output_file = out_dir_target / out_filename

    if aspect == "16:9":
        # Launch Master Long Video Engine (YouTube 16:9 widescreen)
        cmd = [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "long_video_engine.py"),
            "--audio", str(audio_path),
            "--gameplay", str(res_dir),
            "--outdir", str(out_dir_target),
            "--outname", out_filename
        ]
    else:
        # Launch Master Shorts Engine (9:16 Vertical full-screen zoom)
        cmd = [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "desktop_auto_editor.py"),
            "--aspect", "9:16",
            "--audio", str(audio_path),
            "--resdir", str(res_dir),
            "--outdir", str(out_dir_target),
            "--outname", out_filename,
            "--speed", str(speed),
            "--hook", hook_mode,
            "--bgm", "yes" if bgm else "no"
        ]

    with jobs_lock:
        jobs[job_id] = {
            "status": "queued",
            "progress": 5,
            "step": "En cola de procesamiento...",
            "aspect": aspect,
            "logs": [],
            "output_file": None,
            "error": None
        }

    thread = threading.Thread(
        target=run_editor_process,
        args=(job_id, cmd, target_output_file, session_dir),
        daemon=True
    )
    thread.start()

    return {
        "success": True,
        "job_id": job_id,
        "aspect": aspect,
        "out_filename": out_filename
    }

@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
        
        resp = dict(job)
        if job["status"] == "completed":
            resp["video_url"] = f"/api/video/{job_id}"
            resp["download_url"] = f"/api/download/{job_id}"
        return resp

@app.get("/api/video/{job_id}")
async def stream_video(job_id: str, request: Request):
    """Streams the rendered MP4 file supporting HTTP byte ranges for mobile players."""
    job = jobs.get(job_id)
    if not job or not job.get("output_file"):
        raise HTTPException(status_code=404, detail="Video no encontrado.")

    file_path = Path(job["output_file"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="El archivo de video no existe.")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range")

    if not range_header:
        return FileResponse(file_path, media_type="video/mp4")

    # Handle Range Header (e.g. "bytes=0-1048575")
    try:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
    except Exception:
        start = 0
        end = file_size - 1

    length = end - start + 1

    def iterfile():
        with open(file_path, "rb") as f:
            f.seek(start)
            bytes_left = length
            chunk_size = 1024 * 512  # 512KB chunks
            while bytes_left > 0:
                read_bytes = min(chunk_size, bytes_left)
                data = f.read(read_bytes)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)

@app.get("/api/download/{job_id}")
async def download_video(job_id: str):
    job = jobs.get(job_id)
    if not job or not job.get("output_file"):
        raise HTTPException(status_code=404, detail="Video no encontrado.")

    file_path = Path(job["output_file"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="El archivo de video no existe.")

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=f"freefire_viral_{job.get('aspect', 'short').replace(':', 'x')}.mp4"
    )

# ── SERVE WEB APP FRONTEND ────────────────────────────────────────────────────
if WEB_STUDIO_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_STUDIO_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = WEB_STUDIO_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Web Studio está iniciando... Actualiza en un momento.</h1>"

if __name__ == "__main__":
    ip = get_local_ip()
    port = int(os.environ.get("PORT", 7860 if os.environ.get("SPACE_ID") else 8000))
    print("\n" + "═" * 75)
    print("🚀 CODIGO HEADSHOT WEB & MOBILE STUDIO SERVER (v26.0)")
    print("═" * 75)
    print(f"📱 ACCESO DESDE TU CELULAR:  http://{ip}:{port}")
    print(f"🖥️ ACCESO DESDE TU PC:       http://localhost:{port}")
    print("═" * 75 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
