/**
 * ViralComposition.tsx
 * =====================
 * Composición principal 9:16 adaptativa con 5 Arquetipos de Diseño Visual
 * extraídos directamente de los videos de referencia.
 */

import React from "react";
import {
  AbsoluteFill,
  useVideoConfig,
  useCurrentFrame,
  OffthreadVideo,
  Img,
  interpolate,
  spring,
  staticFile,
} from "remotion";
import type { ViralProps } from "./Root";
import { BouncyWord }   from "./BouncyWord";
import { CaptionTrack } from "./CaptionTrack";
import type { CaptionChunk } from "./CaptionTrack";
import { FilmGrain }    from "./FilmGrain";
import { ImpactFlash }  from "./ImpactFlash";
import { ProgressBar }  from "./ProgressBar";
import { ColorGrade, getVideoFilter } from "./ColorGrade";

// ─────────────────────────────────────────────────────────────────────────────
// Tipos
// ─────────────────────────────────────────────────────────────────────────────

type ExtendedViralProps = ViralProps & {
  captionChunks?: CaptionChunk[];
  impactMoments?: Array<{ time: number; word: string; intensity: number }>;
};

// ─────────────────────────────────────────────────────────────────────────────
// Punch zoom helper
// ─────────────────────────────────────────────────────────────────────────────

function getPunchZoomScale(
  impactMoments: Array<{ time: number; intensity: number }>,
  currentTimeSec: number,
  fps: number,
  frame: number
): number {
  for (const impact of impactMoments) {
    const dt = currentTimeSec - impact.time;
    if (dt >= -0.05 && dt <= 0.6) {
      const relFrame       = frame - Math.round(impact.time * fps);
      const punchInFrames  = Math.round(fps * 0.18);
      const holdFrames     = Math.round(fps * 0.10);
      const punchOutFrames = Math.round(fps * 0.45);

      if (relFrame <= punchInFrames) {
        const t = relFrame / punchInFrames;
        return 1.0 + 0.10 * impact.intensity * (1 - Math.pow(1 - t, 3));
      } else if (relFrame <= punchInFrames + holdFrames) {
        return 1.0 + 0.10 * impact.intensity;
      } else {
        const t = Math.min((relFrame - punchInFrames - holdFrames) / punchOutFrames, 1.0);
        return 1.0 + 0.10 * impact.intensity * (1 - t);
      }
    }
  }
  return 1.0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constantes de layout
// ─────────────────────────────────────────────────────────────────────────────

const FADE_FRAMES  = 12;           // 0.4s @ 30fps
const LOGO_WIDTH   = 560;          // px en canvas 1080px (prominente)
const LOGO_ASPECT  = 1320 / 495;   // ratio del PNG original
const LOGO_HEIGHT  = Math.round(LOGO_WIDTH / LOGO_ASPECT); // ≈210px
const LOGO_TOP     = 36;           // px desde borde superior

// ─────────────────────────────────────────────────────────────────────────────
// SUB-COMPONENTES DE ARQUETIPOS EXTRAÍDOS DE LAS REFERENCIAS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Header Banner estilo referencia (dinámico para cada clip y campaña)
 */
const HeaderBannerOverlay: React.FC<{ title?: string; header?: string; topPos?: number }> = ({
  title,
  header,
  topPos,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const displayDurationFrames = fps * 5; // 5 segundos exactos
  const fadeOutFrames = 12; // 0.4s fade out

  if (frame > displayDurationFrames + fadeOutFrames) {
    return null;
  }

  const opacity = interpolate(
    frame,
    [0, 8, displayDurationFrames, displayDurationFrames + fadeOutFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const scale = spring({
    fps,
    frame,
    config: { damping: 14, stiffness: 180 },
    from: 0.85,
    to: 1.0,
  });

  const mainTitle = title || "JUGADA ÉPICA";

  return (
    <div
      style={{
        position: "absolute",
        top: topPos ?? (LOGO_TOP + LOGO_HEIGHT + 14),
        left: 24,
        right: 24,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 30,
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          background: "rgba(0, 0, 0, 0.82)",
          border: "3px solid #FFD700",
          borderRadius: 18,
          padding: "10px 22px",
          textAlign: "center",
          boxShadow: "0 8px 24px rgba(0,0,0,0.9), 0 0 15px rgba(255,215,0,0.4)",
          backdropFilter: "blur(6px)",
        }}
      >
        <span
          style={{
            display: "block",
            fontFamily: "'Montserrat', 'Arial Black', sans-serif",
            fontWeight: 900,
            fontSize: 32,
            color: "#FFD700",
            textTransform: "uppercase",
            letterSpacing: 1.5,
            textShadow: "3px 3px 0px #000, 0 0 12px rgba(255,215,0,0.8)",
            marginBottom: 2,
          }}
        >
          {mainTitle}
        </span>
        {header && (
          <span
            style={{
              display: "block",
              fontFamily: "'Inter', sans-serif",
              fontWeight: 800,
              fontSize: 24,
              color: "#FFFFFF",
              lineHeight: 1.2,
              textShadow: "2px 2px 0px #000",
            }}
          >
            {header}
          </span>
        )}
      </div>
    </div>
  );
};

/**
 * Arquetipo 3: Puntero Neón (Estilo Gavi & Princess Leonor)
 * Aparece únicamente en el hook inicial (primeros 4.5s) y sigue a la persona detectada.
 */
const NeonPointerOverlay: React.FC<{
  label?: string;
  targetX?: number;
  targetY?: number;
  hasFace?: boolean;
}> = ({ label = "JUGADA ÉPICA", targetX = 540, targetY = 700, hasFace = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Mostrar únicamente en los primeros 4.5s (hook inicial) y si hay cara detectada
  const maxDisplayFrames = Math.round(fps * 4.5);
  const fadeOutFrames = 15;

  if (frame > maxDisplayFrames + fadeOutFrames || hasFace === false) {
    return null;
  }

  const opacity = interpolate(
    frame,
    [0, 8, maxDisplayFrames, maxDisplayFrames + fadeOutFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const bounce = Math.sin(frame * 0.18) * 10;
  const pulse = interpolate(Math.sin(frame * 0.25), [-1, 1], [0.95, 1.10]);

  // Limitar coordenadas dentro del lienzo 1080x1920
  const clampedX = Math.max(180, Math.min(900, targetX));
  const clampedY = Math.max(220, Math.min(1350, targetY - 70));

  return (
    <div
      style={{
        position: "absolute",
        left: clampedX,
        top: clampedY,
        transform: `translate(-50%, ${bounce}px) scale(${pulse})`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        zIndex: 35,
        pointerEvents: "none",
        opacity,
        transition: "left 0.08s ease-out, top 0.08s ease-out",
      }}
    >
      <div
        style={{
          fontFamily: "'Montserrat', 'Arial Black', sans-serif",
          fontWeight: 900,
          fontSize: 34,
          color: "#00FF66",
          WebkitTextStroke: "2.5px #000",
          textShadow: "0 0 25px rgba(0,255,102,1.0), 3px 3px 0px #000",
          textTransform: "uppercase",
          letterSpacing: 2,
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 48,
          color: "#00FF66",
          textShadow: "0 0 25px rgba(0,255,102,1.0), 3px 3px 0px #000",
          marginTop: -8,
        }}
      >
        ▼
      </div>
    </div>
  );
};

/**
 * Arquetipo 4: Contador de Lista Lateral Replicado Exacto
 * Lista vertical (1. 2. 3. 4. 5.) con TITULO AL LADO DE CADA NUMERO
 */
const RankingListOverlay: React.FC<{
  currentTimeSec: number;
  totalDurationSec: number;
  items?: Array<{ rank: number; title: string; subtitle?: string; start: number; end: number }>;
  title?: string;
  header?: string;
}> = ({ currentTimeSec, totalDurationSec, items, title, header }) => {
  const defaultItems = [
    { rank: 1, title: "momento #1 🔥", start: 0, end: totalDurationSec * 0.2 },
    { rank: 2, title: "momento #2 🤯", start: totalDurationSec * 0.2, end: totalDurationSec * 0.4 },
    { rank: 3, title: "momento #3 🌊", start: totalDurationSec * 0.4, end: totalDurationSec * 0.6 },
    { rank: 4, title: "momento #4 ⚡", start: totalDurationSec * 0.6, end: totalDurationSec * 0.8 },
    { rank: 5, title: "momento #5 🤣", start: totalDurationSec * 0.8, end: totalDurationSec },
  ];

  const rankingList = (items && items.length > 0) ? items : defaultItems;

  const currentActive = rankingList.find(
    (it) => currentTimeSec >= it.start && currentTimeSec <= it.end
  ) || rankingList[0];

  return (
    <>
      {/* Header Banner superior especifico del clip */}
      {title && <HeaderBannerOverlay title={title} header={header} topPos={35} />}

      {/* Lista lateral izquierda 1. 2. 3. 4. 5. con título al lado de cada número */}
      <div
        style={{
          position: "absolute",
          top: "24%",
          left: 28,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          zIndex: 32,
          pointerEvents: "none",
        }}
      >
        {[1, 2, 3, 4, 5].map((num) => {
          const item = rankingList.find((it) => it.rank === num);
          const isActive = currentActive && currentActive.rank === num;
          const hasPlayed = item && currentTimeSec >= item.start;

          return (
            <div
              key={num}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                fontFamily: "'Montserrat', 'Arial Black', sans-serif",
                fontWeight: 900,
                fontSize: isActive ? 44 : 36,
                transition: "all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
              }}
            >
              <span
                style={{
                  color: isActive ? "#FF0033" : "#FFFFFF",
                  WebkitTextStroke: "2.5px #000",
                  textShadow: isActive
                    ? "0 0 20px rgba(255,0,51,0.9), 3px 3px 0 #000"
                    : "2.5px 2.5px 0 #000",
                }}
              >
                {num}.
              </span>

              {hasPlayed && item && (
                <span
                  style={{
                    fontSize: isActive ? 34 : 28,
                    fontWeight: 900,
                    color: isActive ? "#FFD700" : "#FFFFFF",
                    WebkitTextStroke: "1.8px #000",
                    textShadow: isActive
                      ? "0 0 16px rgba(255,215,0,0.9), 2px 2px 0 #000"
                      : "2px 2px 0 #000",
                    textTransform: "lowercase",
                  }}
                >
                  {item.title}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
};

/**
 * Arquetipo 5: Zoom Burst — Texto explosivo centrado (estilo super viral)
 * Aparece en los primeros 6s con crash-in dramático, neon glow y letterbox cinematográfico.
 * Ideal para hooks de alto impacto que paran el scroll.
 */
const ZoomBurstOverlay: React.FC<{ title?: string; header?: string }> = ({
  title = "INSANE MOMENT",
  header,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const displayFrames  = Math.round(fps * 6);   // 6s máximo
  const fadeOutFrames  = Math.round(fps * 0.5);

  if (frame > displayFrames + fadeOutFrames) return null;

  const opacity = interpolate(
    frame,
    [0, 6, displayFrames, displayFrames + fadeOutFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Crash-in: escala enorme → 1 en los primeros 0.35s
  const crashScale = spring({
    fps,
    frame,
    config: { damping: 10, stiffness: 280, mass: 0.6 },
    from: 3.2,
    to: 1.0,
  });

  // Shake horizontal sólo en el crash (primeros 8 frames)
  const shakeX = frame < 8 ? Math.sin(frame * 3.8) * (8 - frame) * 2.5 : 0;

  // Blur de entrada: va de 12px a 0 en 10 frames
  const blurPx = Math.max(0, interpolate(frame, [0, 10], [12, 0], { extrapolateRight: "clamp" }));

  // Pulsación de brillo neón
  const glowPulse = interpolate(Math.sin(frame * 0.22), [-1, 1], [0.7, 1.3]);

  // Letras del título — divididas en líneas cortas si es largo
  const words = title.toUpperCase().split(" ");
  const line1 = words.slice(0, Math.ceil(words.length / 2)).join(" ");
  const line2 = words.slice(Math.ceil(words.length / 2)).join(" ");

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 40, opacity }}>

      {/* Barras de letterbox cinematográfico */}
      <div style={{
        position: "absolute", top: 0, left: 0, width: "100%",
        height: 110, background: "rgba(0,0,0,0.88)", zIndex: 41,
      }} />
      <div style={{
        position: "absolute", bottom: 0, left: 0, width: "100%",
        height: 110, background: "rgba(0,0,0,0.88)", zIndex: 41,
      }} />

      {/* Overlay oscuro central */}
      <div style={{
        position: "absolute", top: 110, left: 0,
        width: "100%", height: height - 220,
        background: "linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.0) 40%, rgba(0,0,0,0.0) 60%, rgba(0,0,0,0.45) 100%)",
        zIndex: 41,
      }} />

      {/* Contenedor del texto principal */}
      <div style={{
        position: "absolute",
        top: 0, left: 0, width: "100%", height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        transform: `scale(${crashScale}) translateX(${shakeX}px)`,
        filter: `blur(${blurPx}px)`,
      }}>

        {/* Línea 1 */}
        <span style={{
          display: "block",
          fontFamily: "'Montserrat', 'Arial Black', Impact, sans-serif",
          fontWeight: 900,
          fontSize: 118,
          lineHeight: 0.95,
          color: "#FFFFFF",
          textAlign: "center",
          WebkitTextStroke: "4px #000",
          textShadow: [
            `0 0 ${30 * glowPulse}px rgba(255,60,60,1.0)`,
            `0 0 ${60 * glowPulse}px rgba(255,60,60,0.7)`,
            "6px 6px 0px #000",
          ].join(", "),
          letterSpacing: -2,
          paddingLeft: 24, paddingRight: 24,
        }}>
          {line1}
        </span>

        {/* Línea 2 si existe */}
        {line2 && (
          <span style={{
            display: "block",
            fontFamily: "'Montserrat', 'Arial Black', Impact, sans-serif",
            fontWeight: 900,
            fontSize: 118,
            lineHeight: 0.95,
            color: "#FF3C3C",
            textAlign: "center",
            WebkitTextStroke: "4px #000",
            textShadow: [
              `0 0 ${30 * glowPulse}px rgba(255,60,60,1.0)`,
              `0 0 ${60 * glowPulse}px rgba(255,60,60,0.6)`,
              "6px 6px 0px #000",
            ].join(", "),
            letterSpacing: -2,
            paddingLeft: 24, paddingRight: 24,
          }}>
            {line2}
          </span>
        )}

        {/* Sub-header */}
        {header && (
          <span style={{
            display: "block",
            marginTop: 18,
            fontFamily: "'Inter', sans-serif",
            fontWeight: 700,
            fontSize: 36,
            color: "#FFD700",
            textAlign: "center",
            WebkitTextStroke: "1.5px #000",
            textShadow: "2px 2px 0 #000, 0 0 14px rgba(255,215,0,0.8)",
            letterSpacing: 1,
            paddingLeft: 32, paddingRight: 32,
          }}>
            {header}
          </span>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSICIÓN PRINCIPAL
// ─────────────────────────────────────────────────────────────────────────────

export const ViralComposition: React.FC<ExtendedViralProps> = ({
  videoPath,
  startTime,
  durationInSeconds,
  fps,
  cropMeta,
  cropPositions,
  words,
  useZoom,
  useSubtitles,
  subtitleStyle,
  captionChunks   = [],
  impactMoments   = [],
  logoPath,
  layoutStyle     = "header_banner",
  hookTitle,
  hookHeader,
  rankingItems,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const currentTimeSec = frame / fps;
  const totalFrames    = Math.round(durationInSeconds * fps);

  // ── Face tracking ──────────────────────────────────────────────────────
  const globalFrameIdx = Math.round(startTime * fps) + frame;
  let crop = cropPositions.find((p) => p.frame_idx === globalFrameIdx);
  if (!crop && cropPositions.length > 0) {
    crop = cropPositions.reduce((prev, curr) =>
      Math.abs(curr.frame_idx - globalFrameIdx) < Math.abs(prev.frame_idx - globalFrameIdx)
        ? curr : prev
    );
  }
  const cx = crop ? crop.crop_x : (cropMeta.orig_width  - cropMeta.crop_w) / 2;
  const cy = crop ? crop.crop_y : (cropMeta.orig_height - cropMeta.crop_h) / 2;

  // ── Ken Burns + Punch zoom ────────────────────────────────────────────
  const kenBurnsZoom = interpolate(frame, [0, totalFrames], [1.0, 1.08], {
    extrapolateRight: "clamp",
  });
  const punchScale = getPunchZoomScale(impactMoments, currentTimeSec, fps, frame);
  const finalZoom  = useZoom ? kenBurnsZoom * punchScale : punchScale;

  // ── Escala y traslación ────────────────────────────────────────────────
  const scale      = height / cropMeta.crop_h;
  const translateX = -cx * scale;
  const translateY = -cy * scale;

  // ── Fade-in / Fade-out global ──────────────────────────────────────────
  const fadeOpacity = interpolate(
    frame,
    [0, FADE_FRAMES, totalFrames - FADE_FRAMES, totalFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // ── Coordenadas de tracking dinámico para Puntero Neón ────────────────
  const scaleX = width / cropMeta.crop_w;
  const scaleY = height / cropMeta.crop_h;

  const faceX = crop?.face_x ?? (cx + cropMeta.crop_w / 2);
  const faceY = crop?.face_y ?? (cy + cropMeta.crop_h / 3);

  const targetCanvasX = (faceX - cx) * scaleX;
  const targetCanvasY = (faceY - cy) * scaleY;

  // ── Logo posición horizontal centrada ─────────────────────────────────
  const logoLeft = Math.round((width - LOGO_WIDTH) / 2);

  let captionPositionY = 0.70;

  return (
    <AbsoluteFill style={{ backgroundColor: "black", opacity: fadeOpacity }}>

      {/* ── CAPA 1: Video Principal 9:16 Nítido (Smart Crop con Tracking) ── */}
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            width: "100%",
            height: "100%",
            transformOrigin: "center center",
            transform: `scale(${finalZoom})`,
          }}
        >
          <div
            style={{
              position: "absolute",
              width:  cropMeta.orig_width  * scale,
              height: cropMeta.orig_height * scale,
              transform: `translate(${translateX}px, ${translateY}px)`,
            }}
          >
            <OffthreadVideo
              src={staticFile(videoPath)}
              startFrom={Math.round(startTime * fps)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                filter: getVideoFilter(layoutStyle === "financial_highlight" ? "neutral" : "warm_vibrant"),
              }}
            />
          </div>
        </div>
      </AbsoluteFill>

      {/* ── CAPA 2: Color grade overlay ────────────────────────────────── */}
      <ColorGrade preset={layoutStyle === "financial_highlight" ? "neutral" : "warm_vibrant"} intensity={0.50} />

      {/* ── CAPA 3: Viñeta cinematográfica ─────────────────────────────── */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.65) 100%)",
          pointerEvents: "none",
          zIndex: 3,
        }}
      />

      {/* ── CAPA 4: Impact flash ───────────────────────────────────────── */}
      <ImpactFlash impactMoments={impactMoments} fps={fps} />

      {/* ── CAPA 5: Film grain ─────────────────────────────────────────── */}
      <FilmGrain opacity={0.04} />

      {/* ── CAPA 6: Logo permanente de la Campaña ───────────────────────── */}
      {logoPath && (
        <AbsoluteFill style={{ pointerEvents: "none", zIndex: 25 }}>
          <Img
            src={staticFile(logoPath)}
            style={{
              position: "absolute",
              top:    LOGO_TOP,
              left:   logoLeft,
              width:  LOGO_WIDTH,
              height: LOGO_HEIGHT,
              objectFit: "contain",
              opacity: 0.92,
              filter: "drop-shadow(0px 2px 10px rgba(0,0,0,0.80))",
            }}
          />
        </AbsoluteFill>
      )}

      {/* ── CAPAS DE ARQUETIPOS VISUALES ESPECÍFICOS ───────────────────── */}
      {layoutStyle === "header_banner" && (
        <HeaderBannerOverlay title={hookTitle} header={hookHeader} />
      )}

      {layoutStyle === "neon_pointer" && (
        <NeonPointerOverlay
          label={hookTitle || "JUGADA ÉPICA"}
          targetX={targetCanvasX}
          targetY={targetCanvasY}
          hasFace={crop?.has_face ?? false}
        />
      )}

      {layoutStyle === "zoom_burst" && (
        <ZoomBurstOverlay title={hookTitle} header={hookHeader} />
      )}

      {/* ── CAPA 7: Captions MrBeast word-by-word ───────────────────────── */}
      {useSubtitles && captionChunks.length > 0 && (
        <CaptionTrack chunks={captionChunks} positionY={captionPositionY} />
      )}

      {/* ── CAPA 7b: Fallback una palabra ───────────────────────────────── */}
      {useSubtitles && captionChunks.length === 0 && (() => {
        const activeWord = words.find(
          (w) => currentTimeSec >= w.start && currentTimeSec <= w.end + 0.1
        );
        if (!activeWord) return null;
        return (
          <AbsoluteFill
            style={{
              justifyContent: "center",
              alignItems: "flex-end",
              paddingBottom: height * 0.28,
              zIndex: 26,
            }}
          >
            <BouncyWord
              word={activeWord.word.toUpperCase()}
              startFrame={Math.round((activeWord.start - startTime) * fps)}
              endFrame={Math.round((activeWord.end   - startTime) * fps)}
              styleName={subtitleStyle}
            />
          </AbsoluteFill>
        );
      })()}

      {/* ── CAPA 8: Progress bar de retención ──────────────────────────── */}
      <ProgressBar totalFrames={totalFrames} bottomOffset={14} height={5} opacity={0.80} />

    </AbsoluteFill>
  );
};
