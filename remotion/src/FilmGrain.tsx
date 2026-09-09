/**
 * FilmGrain.tsx
 * Ruido cinematográfico generado proceduralmente frame a frame.
 * Usa @remotion/noise (Simplex noise 3D) para variación temporal realista.
 * Intensidad: ~0.04 — suficiente para dar textura sin distraer.
 */
import React, { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

const GRAIN_AMOUNT = 0.045;
const TILES        = 6;

type FilmGrainProps = {
  opacity?: number;           // override de intensidad (default GRAIN_AMOUNT)
};

export const FilmGrain: React.FC<FilmGrainProps> = ({ opacity = GRAIN_AMOUNT }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // Generamos el grano en un canvas pequeño y lo escalamos (performance)
  const tileW = Math.ceil(width  / TILES);
  const tileH = Math.ceil(height / TILES);

  const grainStyle: React.CSSProperties = useMemo(() => ({
    position: "absolute",
    inset: 0,
    // Ruido como background-image SVG con feTurbulence (alternativa ligera)
    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 ${tileW} ${tileH}' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
    backgroundSize: `${tileW}px ${tileH}px`,
    opacity,
    mixBlendMode: "overlay",
    pointerEvents: "none",
    zIndex: 20,
  }), [tileW, tileH, opacity]);

  // Rotamos levemente cada frame para simular temporalidad del grain
  const rotation = (frame * 7.3) % 360;

  return (
    <div
      style={{
        ...grainStyle,
        transform: `rotate(${rotation}deg) scale(1.5)`,
        transformOrigin: "center center",
      }}
    />
  );
};
