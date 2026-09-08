"""
start_with_tunnel.py — Connects local rendering engine to Vercel automatically.
"""
import sys
import time
import re
import subprocess
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def main():
    print("=" * 75)
    print("🚀 INICIANDO SERVIDOR Y CONEXIÓN PÚBLICA MUNDIAL A VERCEL")
    print("=" * 75)
    print("Iniciando motor de renderizado local...")
    
    server_proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "web_server.py")],
        cwd=str(PROJECT_ROOT)
    )

    print("Generando túnel seguro HTTPS para Vercel...")
    tunnel_cmd = "npx --yes localtunnel --port 8000"
    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(PROJECT_ROOT)
    )

    tunnel_url = None
    for line in iter(tunnel_proc.stdout.readline, ""):
        if not line:
            break
        print(line.strip())
        match = re.search(r"https://[a-zA-Z0-9-]+\.loca\.lt", line)
        if match:
            tunnel_url = match.group(0)
            break

    if tunnel_url:
        vercel_link = f"https://editor-free-fire.vercel.app?api={tunnel_url}"
        print("\n" + "═" * 75)
        print("🎉 ¡CONEXIÓN GLOBAL EXITOSA!")
        print("Cualquier persona en el mundo (en celular o PC) puede crear videos en:")
        print(f"👉  {vercel_link}")
        print("═" * 75 + "\n")
        time.sleep(2)
        webbrowser.open(vercel_link)
    else:
        print("No se pudo obtener el túnel automático. Abriendo enlace local...")
        webbrowser.open("http://localhost:8000")

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        server_proc.terminate()
        tunnel_proc.terminate()

if __name__ == "__main__":
    main()
