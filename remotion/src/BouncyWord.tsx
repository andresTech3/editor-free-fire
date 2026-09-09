import React from "react";
import { spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

// ─────────────────────────────────────────────────────────────────────────────
// CAPTION WORD — componente atómico de una sola palabra
// Estilos: active (resaltada), past (desvanecida), impact (explosiva)
// ─────────────────────────────────────────────────────────────────────────────

type WordStatus = "active" | "past" | "upcoming" | "impact";

const STYLES: Record<string, React.CSSProperties> = {
  active: {
    color: "#FFFFFF",
    WebkitTextStroke: "3px #000000",
    textShadow: [
      "0 0 0px #000",
      "3px 3px 0px #000",
      "-3px -3px 0px #000",
      "3px -3px 0px #000",
      "-3px 3px 0px #000",
      "0 6px 20px rgba(0,0,0,0.9)",
    ].join(", "),
    filter: "none",
  },
  impact: {
    color: "#FFD700",            // Amarillo MrBeast signature
    WebkitTextStroke: "4px #000000",
    textShadow: [
      "0 0 30px rgba(255,215,0,0.8)",
      "3px 3px 0px #000",
      "-3px -3px 0px #000",
      "3px -3px 0px #000",
      "-3px 3px 0px #000",
      "0 0 60px rgba(255,165,0,0.5)",
    ].join(", "),
    filter: "brightness(1.15)",
  },
  past: {
    color: "rgba(255,255,255,0.35)",
    WebkitTextStroke: "2px rgba(0,0,0,0.3)",
    textShadow: "none",
    filter: "none",
  },
  upcoming: {
    color: "rgba(255,255,255,0.0)",
    WebkitTextStroke: "0px transparent",
    textShadow: "none",
    filter: "none",
  },
};

export const CaptionWord: React.FC<{
  word: string;
  status: WordStatus;
  wordStartFrame: number;
  isImpact: boolean;
}> = ({ word, status, wordStartFrame, isImpact }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = frame - wordStartFrame;
  const effectiveStatus = isImpact && status === "active" ? "impact" : status;

  // Scale spring — solo cuando la palabra "entra" (active/impact)
  const scale = spring({
    fps,
    frame: relFrame,
    config: {
      damping: isImpact ? 8 : 14,
      stiffness: isImpact ? 200 : 160,
      mass: isImpact ? 0.6 : 0.4,
    },
    from: status === "active" || status === "impact" ? 0.6 : 1.0,
    to: 1.0,
  });

  // Slight rotation para palabras de impacto
  const rotation = isImpact && status === "active"
    ? interpolate(relFrame, [0, 4, 8], [-3, 3, 0], { extrapolateRight: "clamp" })
    : 0;

  const styleOverride = STYLES[effectiveStatus] || STYLES.active;

  return (
    <span
      style={{
        display: "inline-block",
        fontFamily: "'Montserrat', 'Inter', 'Arial Black', sans-serif",
        fontWeight: 900,
        fontSize: isImpact && status === "active" ? 88 : 80,
        letterSpacing: "1px",
        textTransform: "uppercase",
        lineHeight: 1.1,
        margin: "0 6px",
        transform: `scale(${scale}) rotate(${rotation}deg)`,
        transition: "color 0.06s ease, opacity 0.06s ease",
        ...styleOverride,
      }}
    >
      {word}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BOUNCY WORD — compatibilidad con ViralComposition existente (una sola palabra)
// ─────────────────────────────────────────────────────────────────────────────

export const BouncyWord: React.FC<{
  word: string;
  startFrame: number;
  endFrame: number;
  styleName: string;
}> = ({ word, startFrame, styleName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isImpact = styleName === "viral_yellow";
  const scale = spring({
    fps,
    frame: frame - startFrame,
    config: { damping: 10, stiffness: 180, mass: 0.5 },
    from: 0.5,
    to: 1.0,
  });

  const color = isImpact ? "#FFD700" : "#FFFFFF";
  const textShadow = isImpact
    ? "3px 3px 0px #000, -3px -3px 0px #000, 0 0 30px rgba(255,215,0,0.6)"
    : "3px 3px 0px #000, -3px -3px 0px #000";

  const rotation = interpolate(
    frame - startFrame,
    [0, 3, 6],
    [-2, 2, 0],
    { extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${scale}) rotate(${rotation}deg)`,
      }}
    >
      <h1
        style={{
          fontFamily: "'Montserrat', 'Arial Black', sans-serif",
          fontWeight: 900,
          fontSize: 110,
          color,
          textShadow,
          textTransform: "uppercase",
          textAlign: "center",
          margin: 0,
          lineHeight: 1,
          WebkitTextStroke: "3px black",
        }}
      >
        {word}
      </h1>
    </div>
  );
};
