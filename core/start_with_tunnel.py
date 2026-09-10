"""
start_with_tunnel.py — Connects local rendering engine to Vercel automatically.
"""
import os
import sys
import time
import re
import socket
import subprocess
import webbrowser
from pathlib import Path

# Fix Windows console encoding for UTF-8 and Emojis
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def main():
    local_ip = get_local_ip()
    print("=" * 75)
    print("🚀 INICIANDO SERVIDOR Y CONEXIÓN PÚBLICA MUNDIAL A VERCEL")
    print("=" * 75)
    print("Iniciando motor de renderizado local...")
    
    server_proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "web_server.py")],
        cwd=str(PROJECT_ROOT)
    )

    print(f"📡 Servidor local activo en: http://localhost:8000 (Móvil en Wi-Fi: http://{local_ip}:8000)")
    print("Generando túnel seguro HTTPS para Vercel...")
    tunnel_cmd = "npx --yes localtunnel --port 8000"
    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT)
    )

    tunnel_url = None
    start_time = time.time()
    try:
        while time.time() - start_time < 30:
            line = tunnel_proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str:
                print(f"  [Túnel] {line_str}")
            match = re.search(r"https://[a-zA-Z0-9-]+\.loca\.lt", line_str)
            if match:
                tunnel_url = match.group(0)
                break
    except Exception as e:
        print(f"Aviso leyendo túnel: {e}")

    if tunnel_url:
        vercel_link = f"https://editor-free-fire.vercel.app?api={tunnel_url}"
        print("\n" + "═" * 75)
        print("🎉 ¡CONEXIÓN GLOBAL EXITOSA!")
        print("Cualquier persona en el mundo (en celular o PC) puede crear videos en:")
        print(f"👉  {vercel_link}")
        print("═" * 75 + "\n")
        time.sleep(2)
        try:
            webbrowser.open(vercel_link)
        except Exception:
            pass
    else:
        print("\n⚠️ No se pudo obtener el túnel público automáticamente.")
        print(f"👉 Puedes acceder localmente en: http://localhost:8000 o desde tu celular en http://{local_ip}:8000")
        try:
            webbrowser.open("http://localhost:8000")
        except Exception:
            pass

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        server_proc.terminate()
        try:
            tunnel_proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()

