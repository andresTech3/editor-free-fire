"""
freefire_editor.py
===================
🔥 Free Fire Edition — Generador de Shorts Virales estilo "Código Headshot"

Replica exactamente la edición del video de referencia:
  - Hook con título + avatar de fondo
  - Overlay de sensibilidad
  - Cortes rápidos de gameplay con texto overlay
  - CTA sutil: "Comenta CÓDIGO"

Uso:
    python freefire_editor.py generate "El error que comete el 90%" --input input/gameplay.mp4
    python freefire_editor.py generate "SENSIBILIDAD TODO ROJO"
    python freefire_editor.py generate "La mejor config 2024" --duration 25 --clips 2

Pipeline:
    1. Analizar gameplay → mejores momentos
    2. Generar guion (hook/contenido/CTA) a partir del título
    3. Generar voz con edge-tts
    4. Componer video con FFmpeg (avatar + sensibilidad + gameplay + CTA)
    5. Render final con logo watermark
"""

import sys
import os
import time
import tempfile
from pathlib import Path
from typing import Optional

# UTF-8 en Windows
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
from rich.table import Table

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = typer.Typer(
    name="freefire",
    help="🔥 Free Fire Edition — Genera shorts virales estilo Código Headshot.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def print_banner():
    """Banner de Free Fire Edition."""
    console.print()
    console.print(Panel.fit(
        """[bold red]
  ██████╗ ██████╗ ██████╗ ██╗ ██████╗  ██████╗ 
 ██╔════╝██╔═══██╗██╔══██╗██║██╔════╝ ██╔═══██╗
 ██║     ██║   ██║██║  ██║██║██║  ███╗██║   ██║
 ██║     ██║   ██║██║  ██║██║██║   ██║██║   ██║
 ╚██████╗╚██████╔╝██████╔╝██║╚██████╔╝╚██████╔╝
  ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝  ╚═════╝ [/bold red]
[bold yellow]  H E A D S H O T   —   Free Fire Edition 🔥[/bold yellow]
[dim]    Edición automática estilo Código Headshot[/dim]""",
        title="[bold white]🎯 Código Headshot[/bold white]",
        border_style="red",
        padding=(0, 2),
    ))
    console.print()


@app.command()
def generate(
    title: str = typer.Argument(
        ...,
        help="Título del video (determina el guion). Ej: 'El error del 90% al levantar la mira'",
    ),
    input_video: str = typer.Option(
        "input/",
        "--input", "-i",
        help="Video de gameplay (.mp4/.mov) o carpeta con videos",
    ),
    duration: float = typer.Option(
        15.0,
        "--duration", "-d",
        help="Duración target del short (15-30 segundos)",
    ),
    clips: int = typer.Option(
        1,
        "--clips", "-n",
        help="Número de shorts a generar con el mismo título (variaciones)",
    ),
    voice: str = typer.Option(
        "es-MX-JorgeNeural",
        "--voice", "-v",
        help="Voz de edge-tts (es-MX-JorgeNeural / es-MX-DaliaNeural)",
    ),
    rate: str = typer.Option(
        "+15%",
        "--rate",
        help="Velocidad de la voz TTS (+10%, +15%, +20%)",
    ),
):
    """
    🔥 Genera un short viral de Free Fire estilo Código Headshot.

    El video replica exactamente la edición del video de referencia:
    Hook → Sensibilidad → Gameplay frenético → CTA "Comenta CÓDIGO"
    """
    start_time = time.time()
    print_banner()

    # Clamp duration
    duration = max(9.0, min(30.0, duration))

    # ── Imports del módulo ───────────────────────────────────────────────
    try:
        from freefire.script_generator import generate_script, format_script_preview
        from freefire.gameplay_analyzer import select_gameplay_clips, get_video_info
        from freefire.tts_engine import generate_script_audio, concatenate_audio
        from freefire.composer import (
            render_hook_segment,
            render_sensibilidad_segment,
            render_gameplay_segment,
            render_cta_segment,
            compose_final_video,
        )
        from freefire.presets import (
            OUTPUT_DIR, AVATAR_PATH, LOGO_PATH, SENSIBILIDAD_PATH,
            get_segment_durations,
        )
    except ImportError as e:
        console.print(f"[bold red]❌ Error importando módulos:[/bold red] {e}")
        console.print("[dim]Instala las dependencias: pip install edge-tts[/dim]")
        raise typer.Exit(1)

    # ── Resolver video de gameplay ───────────────────────────────────────
    input_path = Path(input_video)
    if input_path.is_dir():
        # Buscar el primer video en la carpeta
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
        videos = [f for f in input_path.iterdir() if f.suffix.lower() in video_exts]
        if not videos:
            console.print(f"[bold red]❌ No se encontraron videos en:[/bold red] {input_path}")
            raise typer.Exit(1)
        gameplay_path = str(videos[0].resolve())
        console.print(f"[cyan]📁 Carpeta de input:[/cyan] {input_path}")
        console.print(f"[cyan]📹 Video seleccionado:[/cyan] {videos[0].name}")
    elif input_path.is_file():
        gameplay_path = str(input_path.resolve())
        console.print(f"[cyan]📹 Video de gameplay:[/cyan] {input_path.name}")
    else:
        console.print(f"[bold red]❌ No se encontró:[/bold red] {input_video}")
        raise typer.Exit(1)

    # Verificar assets
    missing = []
    if not os.path.exists(AVATAR_PATH):
        missing.append(f"Avatar: {AVATAR_PATH}")
    if not os.path.exists(SENSIBILIDAD_PATH):
        missing.append(f"Sensibilidad: {SENSIBILIDAD_PATH}")

    if missing:
        console.print("[bold red]❌ Assets faltantes:[/bold red]")
        for m in missing:
            console.print(f"  • {m}")
        console.print("[dim]Agrega los archivos a assets/video free fire/[/dim]")
        raise typer.Exit(1)

    # ── Mostrar configuración ────────────────────────────────────────────
    config_table = Table(show_header=False, border_style="dim", box=None)
    config_table.add_column("Key", style="dim red", width=22)
    config_table.add_column("Value", style="bold white")
    config_table.add_row("🎬 Título", title)
    config_table.add_row("📹 Gameplay", Path(gameplay_path).name)
    config_table.add_row("⏱ Duración target", f"{duration:.0f}s")
    config_table.add_row("🎯 Clips a generar", str(clips))
    config_table.add_row("🎙 Voz TTS", voice)
    config_table.add_row("⚡ Velocidad", rate)
    config_table.add_row("📁 Output", str(OUTPUT_DIR))

    console.print(Panel(config_table,
                        title="[bold red]⚙ Configuración Free Fire[/bold red]",
                        border_style="red"))
    console.print()

    # ── Crear directorio de output ───────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="ff_edit_")

    # ── Info del gameplay ────────────────────────────────────────────────
    vid_info = get_video_info(gameplay_path)
    console.print(f"[dim]Gameplay: {vid_info['width']}x{vid_info['height']} @ {vid_info['fps']:.0f}fps, {vid_info['duration']:.1f}s[/dim]")
    console.print()

    rendered_clips = []

    for clip_num in range(1, clips + 1):
        console.rule(f"[bold red]🔥 Generando Short {clip_num}/{clips}[/bold red]")
        console.print()

        # ══════════════════════════════════════════════════════════════════
        # PASO 1: GENERAR GUIÓN
        # ══════════════════════════════════════════════════════════════════
        console.print("[bold cyan]📝 Paso 1/5: Generando guión...[/bold cyan]")

        num_scenes = max(3, min(6, int(duration / 3)))  # 3-6 escenas según duración
        script = generate_script(title, num_scenes=num_scenes)

        preview = format_script_preview(script)
        console.print(Panel(preview, title="[bold]Guión Generado[/bold]",
                           border_style="dim", padding=(0, 2)))
        console.print()

        # ══════════════════════════════════════════════════════════════════
        # PASO 2: GENERAR VOZ TTS
        # ══════════════════════════════════════════════════════════════════
        console.print("[bold cyan]🎙 Paso 2/5: Generando voz TTS...[/bold cyan]")

        tts_dir = os.path.join(tmp_dir, f"tts_clip{clip_num}")
        scene_voices = [s.voice_line for s in script.scenes]

        tts_result = generate_script_audio(
            hook_voice=script.hook_voice,
            scene_voices=scene_voices,
            cta_voice=script.cta_voice,
            output_dir=tts_dir,
            voice=voice,
            rate=rate,
        )

        console.print(f"  [green]✓ Hook:[/green] {tts_result['hook'].duration:.1f}s")
        for i, seg in enumerate(tts_result['scenes']):
            console.print(f"  [green]✓ Escena {i+1}:[/green] {seg.duration:.1f}s — \"{seg.text[:40]}\"")
        console.print(f"  [green]✓ CTA:[/green] {tts_result['cta'].duration:.1f}s")
        console.print(f"  [yellow]⏱ Audio total TTS:[/yellow] {tts_result['total_duration']:.1f}s")
        console.print()

        # ══════════════════════════════════════════════════════════════════
        # PASO 3: ANALIZAR GAMEPLAY
        # ══════════════════════════════════════════════════════════════════
        console.print("[bold cyan]🎮 Paso 3/5: Analizando gameplay...[/bold cyan]")

        # Calcular duraciones de segmentos basadas en el TTS real
        hook_dur = tts_result['hook'].duration + 0.3      # +padding
        sensi_dur = max(2.0, hook_dur * 0.8)               # Proporcional al hook
        cta_dur = tts_result['cta'].duration + 0.5         # +padding

        # El gameplay llena el resto
        total_tts = tts_result['total_duration']
        gameplay_dur = max(
            duration - hook_dur - sensi_dur - cta_dur,
            sum(s.duration for s in tts_result['scenes']) + 0.5,
        )

        # Ajustar duración real del video
        actual_duration = hook_dur + sensi_dur + gameplay_dur + cta_dur
        console.print(f"  [dim]Duración real del short: {actual_duration:.1f}s[/dim]")
        console.print(f"    Hook: {hook_dur:.1f}s | Sensi: {sensi_dur:.1f}s | "
                      f"Gameplay: {gameplay_dur:.1f}s | CTA: {cta_dur:.1f}s")

        # Seleccionar clips de gameplay
        gameplay_clips = select_gameplay_clips(
            gameplay_path,
            total_gameplay_duration=gameplay_dur + cta_dur,  # Incluir fondo del CTA
            num_clips=len(script.scenes) + 1,  # +1 para el CTA
        )

        console.print(f"  [green]✓ {len(gameplay_clips)} clips de gameplay seleccionados[/green]")
        for i, (start, dur) in enumerate(gameplay_clips):
            console.print(f"    Clip {i+1}: {start:.1f}s → {start+dur:.1f}s ({dur:.1f}s)")
        console.print()

        # ══════════════════════════════════════════════════════════════════
        # PASO 4: COMPONER SEGMENTOS
        # ══════════════════════════════════════════════════════════════════
        console.print("[bold cyan]🎬 Paso 4/5: Componiendo segmentos...[/bold cyan]")

        segment_paths = []

        # ── Segmento 1: Hook Intro ──
        hook_path = os.path.join(tmp_dir, f"seg_01_hook_{clip_num}.mp4")
        console.print("  [dim]Renderizando hook intro con fondo difuminado...[/dim]")
        if render_hook_segment(script.hook_text, hook_dur, hook_path, gameplay_video=gameplay_path):
            segment_paths.append(hook_path)
            console.print(f"  [green]✓ Hook renderizado ({hook_dur:.1f}s)[/green]")
        else:
            console.print("  [red]❌ Error en hook — continuando...[/red]")

        # ── Segmento 2: Sensibilidad ──
        sensi_path_out = os.path.join(tmp_dir, f"seg_02_sensi_{clip_num}.mp4")
        console.print("  [dim]Renderizando sensibilidad con fondo difuminado...[/dim]")
        if render_sensibilidad_segment(sensi_dur, sensi_path_out, gameplay_video=gameplay_path):
            segment_paths.append(sensi_path_out)
            console.print(f"  [green]✓ Sensibilidad renderizada ({sensi_dur:.1f}s)[/green]")
        else:
            console.print("  [red]❌ Error en sensibilidad — continuando...[/red]")

        # ── Segmentos 3-N: Gameplay ──
        for i, scene in enumerate(script.scenes):
            if i >= len(gameplay_clips):
                break
            gp_start, gp_dur = gameplay_clips[i]
            # Usar la duración del TTS de la escena como guía
            scene_dur = tts_result['scenes'][i].duration + 0.2 if i < len(tts_result['scenes']) else gp_dur
            scene_dur = min(scene_dur, gp_dur)

            gp_path = os.path.join(tmp_dir, f"seg_{i+3:02d}_gameplay_{clip_num}.mp4")
            console.print(f"  [dim]Renderizando gameplay [{scene.overlay_text}]...[/dim]")
            if render_gameplay_segment(gameplay_path, gp_start, scene_dur, scene.overlay_text, gp_path):
                segment_paths.append(gp_path)
                console.print(f"  [green]✓ Gameplay [{scene.overlay_text}] ({scene_dur:.1f}s)[/green]")
            else:
                console.print(f"  [red]❌ Error en gameplay {scene.overlay_text}[/red]")

        # ── Segmento CTA ──
        cta_path_out = os.path.join(tmp_dir, f"seg_cta_{clip_num}.mp4")
        cta_gp_idx = min(len(gameplay_clips) - 1, len(script.scenes))
        cta_gp_start = gameplay_clips[cta_gp_idx][0] if cta_gp_idx < len(gameplay_clips) else 0
        console.print("  [dim]Renderizando CTA...[/dim]")
        if render_cta_segment(gameplay_path, cta_gp_start, cta_dur,
                             script.cta_text, script.cta_badge, cta_path_out):
            segment_paths.append(cta_path_out)
            console.print(f"  [green]✓ CTA renderizado ({cta_dur:.1f}s)[/green]")
        else:
            console.print("  [red]❌ Error en CTA[/red]")

        console.print(f"\n  [bold]Total de segmentos: {len(segment_paths)}[/bold]")
        console.print()

        if not segment_paths:
            console.print("[bold red]❌ No se pudo renderizar ningún segmento[/bold red]")
            continue

        # ══════════════════════════════════════════════════════════════════
        # PASO 5: ENSAMBLAJE FINAL
        # ══════════════════════════════════════════════════════════════════
        console.print("[bold cyan]🎯 Paso 5/5: Ensamblaje final...[/bold cyan]")

        # Concatenar audio TTS
        all_audio = [tts_result['hook'].audio_path]
        for seg in tts_result['scenes']:
            all_audio.append(seg.audio_path)
        all_audio.append(tts_result['cta'].audio_path)

        full_tts_path = os.path.join(tmp_dir, f"tts_full_{clip_num}.wav")
        concatenate_audio(all_audio, full_tts_path, gap=0.15)

        # Output path
        safe_title = "".join(c if c.isalnum() or c in " _-" else "" for c in title)[:40].strip()
        safe_title = safe_title.replace(" ", "_")
        output_mp4 = str(OUTPUT_DIR / f"clip_{clip_num:02d}_{safe_title}.mp4")

        console.print("  [dim]Ensamblando video final con logo...[/dim]")
        ok = compose_final_video(
            segment_paths=segment_paths,
            tts_audio_path=full_tts_path,
            output_path=output_mp4,
        )

        if ok and os.path.exists(output_mp4):
            size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
            rendered_clips.append(output_mp4)
            console.print(f"\n  [bold green]✅ Short creado: {Path(output_mp4).name} ({size_mb:.1f} MB)[/bold green]")

            # Guardar SEO/caption junto al clip
            seo_path = Path(output_mp4).with_suffix(".txt")
            with open(seo_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"🔥 FREE FIRE — CÓDIGO HEADSHOT\n")
                f.write(f"Clip {clip_num}/{clips}\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"📌 TÍTULO:\n{title}\n\n")
                f.write(f"🎣 HOOK:\n{script.hook_voice}\n\n")
                f.write(f"📢 CTA:\n{script.cta_voice}\n\n")
                f.write(f"📝 CAPTION (TikTok / Reels / Shorts):\n")
                f.write("-" * 60 + "\n")
                f.write(f"{title} 🔥🎯\n\n")
                f.write(f'{script.cta_text}\n\n')
                f.write(f"#freefire #freefireclips #headshot #sensibilidad "
                        f"#gaming #codigoheadshot #freefireshorts #viral\n")
                f.write("-" * 60 + "\n")

            console.print(f"  [dim]SEO caption guardado: {seo_path.name}[/dim]")
        else:
            console.print(f"\n  [bold red]❌ Error en ensamblaje final[/bold red]")

        console.print()

    # ── Cleanup tmp ──────────────────────────────────────────────────────
    import shutil
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass

    # ── Resumen final ────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    console.print()
    console.print(Panel(
        f"[bold green]🎉 ¡Proceso completado! ({len(rendered_clips)}/{clips} shorts creados)[/bold green]\n\n"
        f"[cyan]📁 Carpeta de salida:[/cyan] {OUTPUT_DIR}\n"
        f"[cyan]⏱ Tiempo total:[/cyan] {elapsed:.1f}s ({elapsed/60:.1f} min)\n\n"
        f"[dim]Cada clip incluye su .txt con caption lista para TikTok/Reels/Shorts[/dim]\n"
        f"[dim]💡 Tip: Agrega la música de fondo en tu editor favorito[/dim]",
        title="[bold white]🎯 Código Headshot — Free Fire Edition[/bold white]",
        border_style="red",
    ))


@app.command()
def clips(
    event_type: str = typer.Argument(
        "tiros todo rojo",
        help="Tipo de evento a extraer: 'tiros todo rojo' / 'headshots', 'fallando' / 'fails', 'muertes' / 'deaths', 'highlights'",
    ),
    input_video: str = typer.Option(
        "input/",
        "--input", "-i",
        help="Video de gameplay (.mp4/.mov) o carpeta con videos",
    ),
    max_clips: int = typer.Option(
        5,
        "--max-clips", "-n",
        help="Número máximo de jugadas a extraer y unir",
    ),
    clip_duration: float = typer.Option(
        3.0,
        "--duration", "-d",
        help="Duración aproximada de cada jugada recortada (segundos)",
    ),
):
    """
    ✂️ Recorta y une únicamente momentos específicos del gameplay (tiros en rojo, muertes, fallos, highlights).
    """
    start_time = time.time()
    print_banner()

    from freefire.clip_extractor import extract_event_clips
    from freefire.presets import OUTPUT_DIR

    # Resolver video
    input_path = Path(input_video)
    if input_path.is_dir():
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
        videos = [f for f in input_path.iterdir() if f.suffix.lower() in video_exts]
        if not videos:
            console.print(f"[bold red]❌ No se encontraron videos en:[/bold red] {input_path}")
            raise typer.Exit(1)
        gameplay_path = str(videos[0].resolve())
    elif input_path.is_file():
        gameplay_path = str(input_path.resolve())
    else:
        console.print(f"[bold red]❌ No se encontró:[/bold red] {input_video}")
        raise typer.Exit(1)

    console.print(f"[bold cyan]✂️ Extrayendo y uniendo jugadas de tipo:[/bold cyan] [bold yellow]'{event_type}'[/bold yellow]")
    console.print(f"[dim]📹 Input: {Path(gameplay_path).name} | Max jugadas: {max_clips} | Duración/jugada: {clip_duration}s[/dim]\n")

    safe_event = "".join(c if c.isalnum() or c in " _-" else "" for c in event_type)[:30].strip().replace(" ", "_")
    output_mp4 = str(OUTPUT_DIR / f"recopilacion_{safe_event}.mp4")

    res_path = extract_event_clips(
        video_path=gameplay_path,
        event_type=event_type,
        clip_duration=clip_duration,
        max_clips=max_clips,
        output_path=output_mp4,
    )

    elapsed = time.time() - start_time
    if res_path and os.path.exists(res_path):
        size_mb = os.path.getsize(res_path) / (1024 * 1024)
        console.print()
        console.print(Panel(
            f"[bold green]✅ ¡Recopilación de jugadas creada con éxito![/bold green]\n\n"
            f"[cyan]📹 Archivo final:[/cyan] {res_path} ({size_mb:.1f} MB)\n"
            f"[cyan]⏱ Tiempo de procesado:[/cyan] {elapsed:.1f}s\n\n"
            f"[dim]Tip: Puedes pedir recopilaciones de 'tiros en rojo', 'fallando', 'muertes' o 'highlights'[/dim]",
            title="[bold white]🎯 Recopilación Free Fire[/bold white]",
            border_style="green",
        ))
    else:
        console.print("[bold red]❌ Ocurrió un error al recortar y unir los clips.[/bold red]")


if __name__ == "__main__":
    app()

