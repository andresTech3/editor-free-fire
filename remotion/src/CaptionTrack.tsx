import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  AbsoluteFill,
} from "remotion";
import { CaptionWord } from "./BouncyWord";

// ─────────────────────────────────────────────────────────────────────────────
// Tipos
// ─────────────────────────────────────────────────────────────────────────────

export type CaptionChunkWord = {
  word: string;
  start: number;   // segundos relativos al inicio del clip
  end: number;
  is_impact: boolean;
};

export type CaptionChunk = {
  words: CaptionChunkWord[];
  start: number;
  end: number;
  has_impact: boolean;
  primary_idx: number;
  text: string;
};

type CaptionTrackProps = {
  chunks: CaptionChunk[];
  positionY?: number;    // 0.0 (top) → 1.0 (bottom) — default 0.72 (bottom 1/3)
  maxCharsPerLine?: number;
};

// ─────────────────────────────────────────────────────────────────────────────
// Helper: obtener el chunk activo en el frame actual
// ─────────────────────────────────────────────────────────────────────────────

function getActiveChunk(
  chunks: CaptionChunk[],
  currentTimeSec: number
): { chunk: CaptionChunk; chunkIdx: number } | null {
  for (let i = 0; i < chunks.length; i++) {
    const ch = chunks[i];
    if (currentTimeSec >= ch.start && currentTimeSec <= ch.end + 0.12) {
      return { chunk: ch, chunkIdx: i };
    }
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// CAPTION CHUNK ROW — renderiza un grupo de 2-4 palabras
// ─────────────────────────────────────────────────────────────────────────────

const ChunkRow: React.FC<{
  chunk: CaptionChunk;
  currentTimeSec: number;
  chunkEnterFrame: number;
}> = ({ chunk, currentTimeSec, chunkEnterFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrada del grupo completo: slide up + fade in
  const enterProgress = spring({
    fps,
    frame: frame - chunkEnterFrame,
    config: { damping: 18, stiffness: 200, mass: 0.4 },
    from: 0,
    to: 1,
  });
  const translateY = interpolate(enterProgress, [0, 1], [30, 0]);
  const groupOpacity = interpolate(enterProgress, [0, 1], [0, 1]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "center",
        gap: "0px 2px",
        transform: `translateY(${translateY}px)`,
        opacity: groupOpacity,
        paddingLeft: 24,
        paddingRight: 24,
      }}
    >
      {chunk.words.map((w, idx) => {

        let status: "active" | "past" | "upcoming" | "impact" = "upcoming";
        if (currentTimeSec >= w.end) {
          status = "past";
        } else if (currentTimeSec >= w.start) {
          status = w.is_impact ? "impact" : "active";
        }

        const wordEnterFrame = Math.round(
          (w.start - chunk.start) * fps
        ) + chunkEnterFrame;

        return (
          <CaptionWord
            key={idx}
            word={w.word}
            status={status}
            wordStartFrame={wordEnterFrame}
            isImpact={w.is_impact}
          />
        );
      })}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// CAPTION BACKGROUND PILL — fondo semitransparente detrás del texto
// ─────────────────────────────────────────────────────────────────────────────

const CaptionBackground: React.FC<{
  hasImpact: boolean;
  enterProgress: number;
}> = ({ hasImpact, enterProgress }) => {
  const bgOpacity = interpolate(enterProgress, [0, 1], [0, hasImpact ? 0.55 : 0.45]);

  return (
    <div
      style={{
        position: "absolute",
        inset: "-16px -20px",
        borderRadius: 18,
        background: hasImpact
          ? `rgba(0, 0, 0, ${bgOpacity})`
          : `rgba(0, 0, 0, ${bgOpacity})`,
        backdropFilter: "blur(2px)",
        zIndex: 0,
      }}
    />
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// CAPTION TRACK — componente principal que se monta sobre el video
// ─────────────────────────────────────────────────────────────────────────────

export const CaptionTrack: React.FC<CaptionTrackProps> = ({
  chunks,
  positionY = 0.72,
}) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();

  const currentTimeSec = frame / fps;
  const activeResult = getActiveChunk(chunks, currentTimeSec);

  if (!activeResult) return null;

  const { chunk } = activeResult;

  // Frame de inicio del chunk activo
  const chunkEnterFrame = Math.round(chunk.start * fps);

  // Progreso de entrada del chunk para el background
  const enterProgress = spring({
    fps,
    frame: frame - chunkEnterFrame,
    config: { damping: 18, stiffness: 200, mass: 0.4 },
    from: 0,
    to: 1,
  });

  const topPx = height * positionY;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: topPx,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 10,
        }}
      >
        <div style={{ position: "relative", display: "inline-flex" }}>
          {/* Fondo semitransparente */}
          <CaptionBackground
            hasImpact={chunk.has_impact}
            enterProgress={enterProgress}
          />
          {/* Palabras del chunk */}
          <ChunkRow
            chunk={chunk}
            currentTimeSec={currentTimeSec}
            chunkEnterFrame={chunkEnterFrame}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
