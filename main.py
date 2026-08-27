"""
ViralClip Maker
===============
Convertidor de videos largos a Shorts virales.
Clon gratuito de Opus Clip usando Python + herramientas open-source.

Uso:
    python main.py input/video.mp4
    python main.py input/video.mp4 --clips 7
    python main.py input/video.mp4 --split-screen --style neon_blue
    python main.py input/video.mp4 --no-zoom --no-subtitles
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional

# Forzar UTF-8 en Windows para soportar emojis en la terminal
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich import print as rprint
from rich.live import Live
from rich.layout import Layout

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import toml

app = typer.Typer(
    name="viralclip",
    help="Convierte videos largos en Shorts virales automaticamente (gratis, 100% local).",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def load_config(config_path: str = "config.toml") -> dict:
    """Carga la configuración desde config.toml."""
    if Path(config_path).exists():
        return toml.load(config_path)
    else:
        console.print(f"[yellow]⚠ config.toml no encontrado, usando valores por defecto[/yellow]")
        return {}


def print_banner():
    """Imprime el banner ASCII de la aplicación."""
    banner = Text()
    console.print()
    console.print(Panel.fit(
        """[bold cyan]
 ██╗   ██╗██╗██████╗  █████╗ ██╗      ██████╗██╗     ██╗██████╗ 
 ██║   ██║██║██╔══██╗██╔══██╗██║     ██╔════╝██║     ██║██╔══██╗
 ██║   ██║██║██████╔╝███████║██║     ██║     ██║     ██║██████╔╝
 ╚██╗ ██╔╝██║██╔══██╗██╔══██║██║     ██║     ██║     ██║██╔═══╝ 
  ╚████╔╝ ██║██║  ██║██║  ██║███████╗╚██████╗███████╗██║██║     
   ╚═══╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚══════╝╚═╝╚═╝     [/bold cyan]
[bold magenta]         🎬 M A K E R  —  Tu Opus Clip Gratuito 🔥[/bold magenta]
[dim]    Powered by Whisper · OpenCV · Remotion · FFmpeg · Librosa[/dim]""",
        title="[bold white]🚀 ViralClip[/bold white]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()


def print_analysis_table(clips_data: list):
    """Imprime una tabla con el análisis de clips virales y su metodología de Hook."""
    table = Table(
        title="📊 Análisis de Momentos Virales & Metodología de Hook",
        show_header=True,
        header_style="bold magenta",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="bold white", width=3)
    table.add_column("⏱ Inicio", style="cyan", width=9)
    table.add_column("⏱ Fin", style="cyan", width=9)
    table.add_column("⌛ Duración", style="green", width=9)
    table.add_column("🔥 Score", style="bold yellow", width=10)
    table.add_column("🎣 Metodología de Hook", style="bold cyan", width=22)
    table.add_column("💬 Preview del Texto", style="white", min_width=25)

    for i, clip in enumerate(clips_data, 1):
        duration = clip.get("end", 0) - clip.get("start", 0)
        score = clip.get("viral_score", 0)
        text_preview = clip.get("text", "")[:45] + ("..." if len(clip.get("text", "")) > 45 else "")
        hook_str = f"{clip.get('hook_emoji', '🎬')} {clip.get('hook_name', 'General')}"

        # Color del score
        if score >= 0.75:
            score_str = f"[bold red]🔥 {score:.2f}[/bold red]"
        elif score >= 0.50:
            score_str = f"[bold yellow]⚡ {score:.2f}[/bold yellow]"
        else:
            score_str = f"[green]✓ {score:.2f}[/green]"

        table.add_row(
            str(i),
            f"{clip.get('start', 0):.1f}s",
            f"{clip.get('end', 0):.1f}s",
            f"{duration:.1f}s",
            score_str,
            hook_str,
            text_preview,
        )

    console.print(table)
    console.print()


def print_completion_summary(clips_saved: list, output_dir: Path, elapsed: float):
    """Imprime el resumen final de clips generados."""
    table = Table(
        title="✅ Clips Generados Exitosamente",
        show_header=True,
        header_style="bold green",
        border_style="green",
        show_lines=True,
    )
    table.add_column("#", style="bold white", width=4)
    table.add_column("📁 Archivo", style="cyan", min_width=30)
    table.add_column("📏 Tamaño", style="yellow", width=12)
    table.add_column("🔥 Score", style="magenta", width=10)

    total_size = 0
    for i, clip_info in enumerate(clips_saved, 1):
        path = Path(clip_info["path"])
        size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        total_size += size_mb
        table.add_row(
            str(i),
            path.name,
            f"{size_mb:.1f} MB",
            f"🔥 {clip_info.get('score', 0):.2f}",
        )

    console.print(table)
    console.print()
    console.print(Panel(
        f"[bold green]🎉 ¡{len(clips_saved)} clips virales generados![/bold green]\n\n"
        f"[cyan]📁 Carpeta de salida:[/cyan] {output_dir}\n"
        f"[cyan]💾 Tamaño total:[/cyan] {total_size:.1f} MB\n"
        f"[cyan]⏱ Tiempo total:[/cyan] {elapsed:.1f}s ({elapsed/60:.1f} min)\n\n"
        "[dim]💡 Tip: Revisa los clips y súbelos directamente a TikTok, Instagram Reels o YouTube Shorts[/dim]",
        title="[bold white]🏁 Proceso Completado[/bold white]",
        border_style="green",
    ))


def format_time(seconds: float) -> str:
    """Formatea segundos a mm:ss."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


@app.command()
def main(
    video_path: str = typer.Argument(..., help="Ruta al video largo de entrada"),
    clips: int = typer.Option(None, "--clips", "-n", help="Número de clips a generar"),
    zoom: bool = typer.Option(None, "--zoom/--no-zoom", help="Activar efecto zoom"),
    subtitles: bool = typer.Option(None, "--subtitles/--no-subtitles", help="Activar subtítulos"),
    style: Optional[str] = typer.Option(None, "--style", "-s", help="Estilo de subtítulos: viral_yellow / neon_blue / fire_orange / white_bold"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Modelo Whisper: tiny / base / small"),
    language: Optional[str] = typer.Option(None, "--lang", help="Idioma: es / en / auto"),
    layout: Optional[str] = typer.Option(None, "--layout", "-l", help="Forzar formato visual: ranking_list / header_banner / split_screen / neon_pointer / financial_highlight"),
    config_file: str = typer.Option("config.toml", "--config", "-c", help="Archivo de configuración"),
):
    """
    🎬 Convierte un video largo en Shorts virales automáticamente.

    Ejemplos:\n
        python main.py input/video.mp4\n
        python main.py input/video.mp4 --clips 7 --split-screen\n
        python main.py input/video.mp4 --style neon_blue --model small\n
    """
    start_time = time.time()
    print_banner()

    # ── Cargar configuración ─────────────────────────────
    config = load_config(config_file)
    general = config.get("general", {})
    effects_cfg = config.get("effects", {})
    output_cfg = config.get("output", {})
    analysis_cfg = config.get("analysis", {})
    advanced_cfg = config.get("advanced", {})

    # ── Aplicar overrides de CLI ─────────────────────────
    num_clips = clips or general.get("num_clips", 5)
    use_zoom = zoom if zoom is not None else effects_cfg.get("enable_zoom", True)
    use_subs = subtitles if subtitles is not None else effects_cfg.get("enable_subtitles", True)
    sub_style = style or effects_cfg.get("subtitle_style", "viral_yellow")
    whisper_model = model or analysis_cfg.get("whisper_model", "base")
    lang = language or general.get("language", "es")
    max_dur = general.get("max_clip_duration", 60)
    min_dur = general.get("min_clip_duration", 20)

    # ── Validar input ────────────────────────────────────
    video_file = Path(video_path)
    if not video_file.exists():
        console.print(f"[bold red]❌ Error: No se encontró el archivo:[/bold red] {video_path}")
        raise typer.Exit(1)

    # Forzar duración de 2.5 a 3 minutos (150s - 180s) para formato ranking_list o videos de risa
    is_comedy_video = "SI TE RÍES PIERDES" in video_file.name.upper() or "RISA" in video_file.name.upper()
    if layout == "ranking_list" or is_comedy_video:
        max_dur = 180
        min_dur = 150
    face_det = analysis_cfg.get("face_detection", True)

    if video_file.suffix.lower() not in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]:
        console.print(f"[bold red]❌ Formato no soportado:[/bold red] {video_file.suffix}")
        console.print("[dim]Formatos soportados: .mp4 .mov .avi .mkv .webm .m4v[/dim]")
        raise typer.Exit(1)

    # ── Preparar directorio de salida ────────────────────
    output_base = output_cfg.get("output_folder", "output")
    output_dir = Path(output_base) / video_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Detectar especificaciones de Campaña Whop / Marcas ──
    try:
        from core.campaign import CampaignManager
        campaign_mgr = CampaignManager(input_dir=str(video_file.parent))
        campaign = campaign_mgr.detect_campaign()
        if campaign.get("subtitle_style") and not style:
            sub_style = campaign["subtitle_style"]
    except Exception:
        campaign = {"brand_name": "Campaña Viral", "logo_path": None, "source_doc": None}

    # ── Mostrar configuración ────────────────────────────
    config_table = Table(show_header=False, border_style="dim", box=None)
    config_table.add_column("Key", style="dim cyan", width=22)
    config_table.add_column("Value", style="bold white")

    config_table.add_row("📹 Video", str(video_file.name))
    config_table.add_row("🎯 Campaña / Marca", campaign.get("brand_name", "General"))
    if campaign.get("source_doc"):
        config_table.add_row("📄 Doc Requerimientos", Path(campaign["source_doc"]).name)
    if campaign.get("logo_path"):
        config_table.add_row("🖼️ Logo de Cliente", Path(campaign["logo_path"]).name)
    config_table.add_row("🎯 Clips a generar", str(num_clips))
    config_table.add_row("⏱ Duración máx/mín", f"{max_dur}s / {min_dur}s")
    config_table.add_row("🧠 Modelo Whisper", whisper_model)
    config_table.add_row("🌍 Idioma", lang)
    config_table.add_row("🔍 Zoom (Ken Burns)", "✅ Activado" if use_zoom else "❌ Desactivado")
    config_table.add_row("💬 Subtítulos", f"✅ {sub_style}" if use_subs else "❌ Desactivado")
    config_table.add_row("👤 Face Detection", "✅ Activado" if face_det else "❌ Desactivado")
    config_table.add_row("📁 Salida", str(output_dir))

    console.print(Panel(config_table, title="[bold cyan]⚙ Configuración de Campaña[/bold cyan]", border_style="cyan"))
    console.print()

    

    # ── Importar módulos del pipeline ────────────────────
    try:
        from core.transcriber import Transcriber
        from core.analyzer import ViralAnalyzer
        from core.editor import Editor
    except ImportError as e:
        console.print(f"[bold red]Error importando módulos:[/bold red] {e}")
        console.print("[dim]Ejecuta setup.bat primero para instalar las dependencias.[/dim]")
        raise typer.Exit(1)

    # ══════════════════════════════════════════════════════
    # PASO 1: Transcripción con Whisper
    # ══════════════════════════════════════════════════════
    console.rule("[bold cyan]Paso 1 de 4: Transcripción de Audio[/bold cyan]")
    console.print()

    transcriber = Transcriber(
        model_name=whisper_model,
        language=lang,
        console=console,
    )

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("🎙 Transcribiendo audio...", total=None)
        segments = transcriber.transcribe(str(video_file))
        progress.update(task, completed=True, description="[green]✅ Transcripción completada[/green]")

    console.print(f"[green]✅ {len(segments)} segmentos de texto extraídos[/green]")
    console.print()

    # ══════════════════════════════════════════════════════
    # PASO 2: Análisis de Momentos Virales
    # ══════════════════════════════════════════════════════
    console.rule("[bold cyan]Paso 2 de 4: Análisis de Viralidad[/bold cyan]")
    console.print()

    keywords = analysis_cfg.get(f"viral_keywords_{lang}", analysis_cfg.get("viral_keywords_es", []))
    weights = {
        "audio_energy": analysis_cfg.get("weight_audio_energy", 0.35),
        "keywords": analysis_cfg.get("weight_keywords", 0.25),
        "sentiment": analysis_cfg.get("weight_sentiment", 0.20),
        "speech_density": analysis_cfg.get("weight_speech_density", 0.20),
    }

    analyzer = ViralAnalyzer(
        video_path=str(video_file),
        segments=segments,
        viral_keywords=keywords,
        weights=weights,
        max_clip_duration=max_dur,
        min_clip_duration=min_dur,
        console=console,
    )

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("📊 Analizando momentos virales...", total=None)
        top_clips = analyzer.get_top_clips(n=num_clips)
        progress.update(task, completed=True, description="[green]✅ Análisis completado[/green]")

    console.print(f"[green]✅ {len(top_clips)} momentos virales detectados[/green]")
    console.print()
    print_analysis_table(top_clips)

    # ══════════════════════════════════════════════════════
    # PASO 3 & 4: Edición y Renderizado de Clips
    # ══════════════════════════════════════════════════════
    console.rule("[bold cyan]Pasos 3 & 4: Edición y Renderizado[/bold cyan]")
    console.print()

    editor = Editor(
        video_path=str(video_file),
        output_dir=str(output_dir),
        config=config,
        segments=segments,
        use_zoom=use_zoom,
        use_subtitles=use_subs,
        subtitle_style=sub_style,
        face_detection=face_det,
        forced_layout=layout,
        console=console,
    )

    clips_saved = []
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        overall_task = progress.add_task(
            f"🎬 Procesando {len(top_clips)} clips...", total=len(top_clips)
        )

        for i, clip_data in enumerate(top_clips, 1):
            progress.update(
                overall_task,
                description=f"🎬 Procesando clip {i}/{len(top_clips)}: {format_time(clip_data['start'])} → {format_time(clip_data['end'])}",
            )

            output_path = output_dir / f"clip_{i:02d}_score{clip_data['viral_score']:.2f}.mp4"

            try:
                editor.process_clip(
                    clip_data=clip_data,
                    output_path=str(output_path.resolve()),
                    clip_number=i,
                )
                clips_saved.append({
                    "path": str(output_path),
                    "score": clip_data["viral_score"],
                })
                console.print(f"  [green]✅ Clip {i} guardado:[/green] {output_path.name}")
            except Exception as e:
                console.print(f"  [red]❌ Error en clip {i}:[/red] {e}")

            progress.advance(overall_task)

    # Guardar reporte
    report_path = output_dir / "report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("ViralClip Maker — Reporte de Análisis\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Video original: {video_file.name}\n")
        f.write(f"Clips generados: {len(clips_saved)}\n\n")
        for i, clip in enumerate(top_clips, 1):
            f.write(f"Clip {i:02d}:\n")
            f.write(f"  Tiempo: {clip['start']:.1f}s → {clip['end']:.1f}s\n")
            f.write(f"  Duración: {clip['end'] - clip['start']:.1f}s\n")
            f.write(f"  Viral Score: {clip['viral_score']:.3f}\n")
            f.write(f"  Metodología Hook: {clip.get('hook_emoji', '')} {clip.get('hook_name', '')} ({clip.get('hook_desc', '')})\n")
            f.write(f"  Texto: {clip.get('text', '')[:200]}\n\n")

    # Fin
    elapsed = time.time() - start_time
    console.print()
    print_completion_summary(clips_saved, output_dir, elapsed)


if __name__ == "__main__":
    app()
