/**
 * ImpactFlash.tsx
 * Destello de luz blanca sincronizado con las palabras de impacto.
 * Técnica usada en MrBeast, Yes Theory y canales virales de alto presupuesto.
 * El flash dura ~6 frames (0.2s), muy intenso al inicio y decae rápido.
 */
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

type ImpactMoment = {
  time: number;
  word: string;
  intensity: number;
};

type ImpactFlashProps = {
  impactMoments: ImpactMoment[];
  fps: number;
};

const FLASH_DURATION_FRAMES = 8;

export const ImpactFlash: React.FC<ImpactFlashProps> = ({ impactMoments, fps }) => {
  const frame = useCurrentFrame();
  useVideoConfig(); // needed for Remotion context

  // Encontrar si estamos dentro de un flash
  let flashOpacity = 0;
  let flashColor = "white";

  for (const impact of impactMoments) {
    const impactFrame = Math.round(impact.time * fps);
    const relFrame    = frame - impactFrame;

    if (relFrame >= 0 && relFrame < FLASH_DURATION_FRAMES) {
      // Curva: instantáneo al impacto, decae exponencialmente
      const t = relFrame / FLASH_DURATION_FRAMES;
      flashOpacity = impact.intensity * 0.55 * Math.pow(1 - t, 2.5);
      // Palabras muy intensas → flash levemente amarillo (como explosión)
      flashColor = impact.intensity > 0.8 ? "rgba(255, 240, 180, 1)" : "rgba(255, 255, 255, 1)";
      break;
    }
  }

  if (flashOpacity < 0.01) return null;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundColor: flashColor,
        opacity: flashOpacity,
        pointerEvents: "none",
        zIndex: 15,
        mixBlendMode: "screen",
      }}
    />
  );
};
