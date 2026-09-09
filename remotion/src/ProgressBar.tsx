/**
 * ProgressBar.tsx
 * Barra de progreso delgada en la parte INFERIOR del Short.
 * Técnica de retención: el espectador inconscientemente sigue el progreso
 * y tiende a ver hasta el final. Usada por los creadores de YouTube Shorts
 * con mayor watch-time (Overtime, MrBeast, Jesser).
 *
 * Diseño: línea de 4px, color degradado del brand (rojo YouTube → dorado),
 * con pill redondeada. Posición: sobre el safe-zone inferior, ENCIMA de los subtítulos
 * para no confundirse con ellos.
 */
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

type ProgressBarProps = {
  totalFrames: number;
  color?: string;         // color de la barra (default: gradiente rojo-dorado)
  height?: number;        // altura en px (default: 5)
  bottomOffset?: number;  // px desde el borde inferior (default: 12)
  opacity?: number;
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
  totalFrames,
  color,
  height = 5,
  bottomOffset = 12,
  opacity = 0.85,
}) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();

  const progress = Math.min(frame / totalFrames, 1);
  const barWidth = progress * width;

  return (
    <div
      style={{
        position: "absolute",
        bottom: bottomOffset,
        left: 0,
        width: "100%",
        height: height,
        pointerEvents: "none",
        zIndex: 30,
        opacity,
      }}
    >
      {/* Track (fondo oscuro semitransparente) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: height,
          backgroundColor: "rgba(0,0,0,0.35)",
        }}
      />
      {/* Barra de progreso con gradiente */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: barWidth,
          height: "100%",
          borderRadius: height,
          background: color ?? "linear-gradient(90deg, #FF0000 0%, #FF4500 40%, #FFD700 100%)",
          boxShadow: "0 0 8px rgba(255, 80, 0, 0.7)",
          transition: "width 0ms",
        }}
      />
    </div>
  );
};
