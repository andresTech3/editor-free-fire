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

# Cache default resources investigation
default_investigation_cache = None

def get_default_investigation() -> Dict[str, Any]:
    global default_investigation_cache
    if default_investigation_cache is None:
        inv = AssetInvestigator(str(ASSETS_DIR))
        default_investigation_cache = inv.investigate()
    return default_investigation_cache

# ── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.get("/api/info")
async def get_server_info():
    ip = get_local_ip()
    def_inv = get_default_investigation()
    return {
        "status": "online",
        "local_ip": ip,
        "mobile_url": f"http://{ip}:8000",
        "default_assets": def_inv["summary"]
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

@app.post("/api/upload")
async def upload_files(
    audio: UploadFile = File(...),
    use_default_resources: bool = Form(True),
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

    if use_default_resources or not resources:
        res_dir = ASSETS_DIR
        def_inv = get_default_investigation()
        investigation_summary = {
            "mode": "official_default_pack",
            "message": "Usando el Pack Maestro Oficial Free Fire (37 jugadas, memes verdes, armas, diamantes)",
            "details": def_inv["summary"]
        }
    else:
        # Save custom uploaded resources
        custom_res_dir = session_dir / "custom_resources"
        custom_res_dir.mkdir(parents=True, exist_ok=True)
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

def run_editor_process(job_id: str, cmd: List[str], target_file: Path):
    """Executes editing subprocess, parsing progress from output lines."""
    with jobs_lock:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["step"] = "Iniciando motor de edición profesional..."
        jobs[job_id]["progress"] = 10

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
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
                # Keep last 60 logs
                if len(jobs[job_id]["logs"]) > 60:
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
                elif "Compiling" in clean_line or "FFmpeg render" in clean_line or "Master" in clean_line:
                    jobs[job_id]["progress"] = max(jobs[job_id]["progress"], 85)
                    jobs[job_id]["step"] = "Renderizando video maestro en alta definición (60 FPS)..."

        proc.wait()

        if proc.returncode == 0 and target_file.exists():
            with jobs_lock:
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["progress"] = 100
                jobs[job_id]["step"] = "¡Video generado exitosamente!"
                jobs[job_id]["output_file"] = str(target_file)
                jobs[job_id]["file_size_mb"] = round(os.path.getsize(target_file) / (1024 * 1024), 2)
        else:
            with jobs_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = "Error durante el renderizado. Revisa los registros."
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

@app.post("/api/generate")
async def generate_video(payload: GenerateRequest):
    audio_path = None
    res_dir = None

    if payload.session_id and payload.session_id in sessions:
        session = sessions[payload.session_id]
        audio_path = session.get("audio_path")
        res_dir = session.get("resources_dir")
    
    if not audio_path and payload.audio_path:
        audio_path = payload.audio_path
    
    if not res_dir:
        res_dir = payload.resources_dir or str(ASSETS_DIR)

    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=400, detail="Archivo de audio no encontrado. Sube un audio primero.")

    aspect = payload.aspect or payload.aspect_ratio or "9:16"
    speed = payload.speed or 1.5
    hook_mode = payload.hook_preference or payload.hook_mode or "auto"
    bgm = payload.bgm if payload.bgm is not None else True

    job_id = str(uuid.uuid4())[:8]
    out_filename = f"video_{aspect.replace(':', 'x')}_{job_id}.mp4"
    target_output_file = OUTPUT_DIR / out_filename

    if aspect == "16:9":
        # Launch Master Long Video Engine (YouTube 16:9 widescreen)
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "long_video_engine.py"),
            "--audio", str(audio_path),
            "--gameplay", str(res_dir),
            "--outdir", str(OUTPUT_DIR),
            "--outname", out_filename
        ]
    else:
        # Launch Master Shorts Engine (9:16 Vertical full-screen zoom)
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "desktop_auto_editor.py"),
            "--aspect", "9:16",
            "--audio", str(audio_path),
            "--resdir", str(res_dir),
            "--outdir", str(OUTPUT_DIR),
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
        args=(job_id, cmd, target_output_file),
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
