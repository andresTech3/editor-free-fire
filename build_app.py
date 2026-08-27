"""
build_app.py
============
Script de compilación y empaquetado para generar el ejecutable (.exe)
de "Código Headshot — Free Fire Studio".

Características:
  - Compila con PyInstaller en un archivo/carpeta independiente (.exe)
  - Incluye todos los assets (avatar, sensibilidad, logos, ranking, sfx)
  - Copia ejecutables binarios de FFmpeg si existen localmente
  - Genera un archivo ZIP de distribución portable listo para compartir.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "assets"

APP_NAME = "CodigoHeadshotStudio"
ZIP_NAME = "CodigoHeadshot_FreeFireEdition_v1.0"


def check_pyinstaller():
    try:
        import PyInstaller
        print("[+] PyInstaller is installed:", PyInstaller.__version__)
    except ImportError:
        print("[+] Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def locate_ffmpeg_binaries():
    """Busca los binarios de FFmpeg y FFprobe para empaquetado si existen."""
    ffmpeg_exe = shutil.which("ffmpeg")
    ffprobe_exe = shutil.which("ffprobe")

    bins = []
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        bins.append((ffmpeg_exe, "."))
        print(f"[+] FFmpeg binary found: {ffmpeg_exe}")
    if ffprobe_exe and os.path.exists(ffprobe_exe):
        bins.append((ffprobe_exe, "."))
        print(f"[+] FFprobe binary found: {ffprobe_exe}")

    return bins


def build_executable():
    print("\n[+] Starting PyInstaller build...")
    check_pyinstaller()

    # Construir argumento add-data para assets
    assets_src = PROJECT_ROOT / "assets"
    add_data_args = []
    if assets_src.exists():
        add_data_args.extend(["--add-data", f"{assets_src};assets"])

    # Buscar FFmpeg
    ffmpeg_bins = locate_ffmpeg_binaries()
    add_binary_args = []
    for b_path, b_dest in ffmpeg_bins:
        add_binary_args.extend(["--add-binary", f"{b_path};{b_dest}"])

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", APP_NAME,
        "--onedir",
    ] + add_data_args + add_binary_args + [
        "--hidden-import", "edge_tts",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--hidden-import", "typer",
        "--hidden-import", "rich",
        str(PROJECT_ROOT / "freefire_studio_app.py")
    ]

    print("Executing PyInstaller command:")
    print(" ".join(pyinstaller_cmd))
    print("-" * 60)

    res = subprocess.run(pyinstaller_cmd, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        print("[-] Error in PyInstaller build.")
        sys.exit(1)

    print("\n[+] Build successful at:", DIST_DIR / APP_NAME)


def create_distribution_zip():
    app_dir = DIST_DIR / APP_NAME
    if not app_dir.exists():
        print("[-] Compiled directory not found.")
        return

    # Crear carpetas por defecto dentro del directorio compilado
    (app_dir / "input").mkdir(exist_ok=True)
    (app_dir / "output" / "FreeFire").mkdir(parents=True, exist_ok=True)

    # Crear un README explicativo
    readme_path = app_dir / "INSTRUCCIONES_USO.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("=" * 65 + "\n")
        f.write("CODIGO HEADSHOT - FREE FIRE STUDIO v1.0 (PORTABLE)\n")
        f.write("=" * 65 + "\n\n")
        f.write("COMO EJECUTAR LA APLICACION:\n")
        f.write(f"1. Haz doble clic en '{APP_NAME}.exe'.\n")
        f.write("2. Selecciona tu video de gameplay en la casilla 'Input Video'.\n")
        f.write("3. Elige tu tipo de Short o Recopilacion de Clips y presiona GENERAR.\n\n")
        f.write("CARPETAS:\n")
        f.write("  - /input/  : Coloca aqui tus videos de gameplay (.mp4 / .mov)\n")
        f.write("  - /output/ : Aqui se guardaran tus shorts virales renderizados\n\n")
        f.write("Desarrollado para creacion masiva de contenido de Free Fire.\n")

    # Crear archivo ZIP listo para compartir
    zip_path = DIST_DIR / ZIP_NAME
    print(f"\n[+] Creating distribution ZIP package: {zip_path}.zip...")
    shutil.make_archive(str(zip_path), "zip", root_dir=str(DIST_DIR), base_dir=APP_NAME)

    zip_file = Path(str(zip_path) + ".zip")
    if zip_file.exists():
        size_mb = zip_file.stat().st_size / (1024 * 1024)
        print(f"[+] PACKAGE CREATED SUCCESSFULLY! ({size_mb:.1f} MB)")
        print(f"[+] File ready to share: {zip_file}")


if __name__ == "__main__":
    build_executable()
    create_distribution_zip()
