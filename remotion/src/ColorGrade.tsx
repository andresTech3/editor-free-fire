/**
 * ColorGrade.tsx
 * Color grading cinematográfico aplicado como overlay CSS.
 *
 * Pipeline de corrección de color:
 *   1. Warmth boost (+tinte naranja-amarillo en highlights)
 *   2. Contrast boost (+20%)
 *   3. Saturation (+15%)
 *   4. Slight crush en negros (crush shadows) via vignette oscurecida
 *
 * Este look es el "Jesser/MrBeast look": vibrante, contrastado,
 * con highlights cálidos — ideal para content deportivo/de acción.
 *
 * Implementado como div overlay con mix-blend-mode para no afectar
 * el rendimiento del render principal.
 */
import React from "react";

type ColorGradeProps = {
  /**
   * Preset de color:
   *  "warm_vibrant" — naranja/dorado vibrante (default, ideal deportes)
   *  "cold_cinematic" — azul frío, look película de acción
   *  "neutral" — solo contraste + saturación sin tinte
   */
  preset?: "warm_vibrant" | "cold_cinematic" | "neutral";
  intensity?: number;  // 0-1, default 0.55
};

const PRESETS = {
  warm_vibrant: {
    // Tinte naranja/dorado sobre los highlights
    overlay: "rgba(255, 140, 30, 0.10)",
    // CSS filter en el wrapper del video (se aplica via prop en ViralComposition)
    filter: "contrast(1.18) saturate(1.20) brightness(1.04)",
  },
  cold_cinematic: {
    overlay: "rgba(30, 80, 180, 0.10)",
    filter: "contrast(1.22) saturate(0.90) brightness(1.0) hue-rotate(-8deg)",
  },
  neutral: {
    overlay: "rgba(0,0,0,0)",
    filter: "contrast(1.15) saturate(1.10)",
  },
};

export const ColorGrade: React.FC<ColorGradeProps> = ({
  preset = "warm_vibrant",
  intensity = 0.55,
}) => {
  const { overlay } = PRESETS[preset];

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundColor: overlay,
        opacity: intensity,
        mixBlendMode: "soft-light",
        pointerEvents: "none",
        zIndex: 2,
      }}
    />
  );
};

/**
 * Devuelve el CSS filter string para aplicar directamente al elemento de video.
 * Usar: style={{ filter: getVideoFilter() }}
 */
export function getVideoFilter(preset: keyof typeof PRESETS = "warm_vibrant"): string {
  return PRESETS[preset].filter;
}
