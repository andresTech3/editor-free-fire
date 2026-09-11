import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type TopicBadgeOverlayProps = {
  title?: string;
  badge?: string;
  accentColor?: string;
};

export const TopicBadgeOverlay: React.FC<TopicBadgeOverlayProps> = ({
  title = "TODO ROJO ACTIVADO",
  badge = "TRUCO PRO FREE FIRE",
  accentColor = "#FF2E55",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring
  const scale = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 180 },
  });

  // Dynamic glow pulse
  const glow = interpolate(
    Math.sin((frame / fps) * Math.PI * 2),
    [-1, 1],
    [8, 22]
  );

  // Subtle float
  const floatY = Math.sin((frame / fps) * Math.PI) * 4;

  // Exit fade out in the last 15 frames
  const exitOpacity = interpolate(
    frame,
    [105, 120],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "center",
        paddingTop: 140,
        opacity: exitOpacity,
      }}
    >
      <div
        style={{
          transform: `scale(${scale}) translateY(${floatY}px)`,
          background: "linear-gradient(135deg, rgba(14, 18, 27, 0.95), rgba(22, 28, 42, 0.90))",
          border: `2px solid ${accentColor}`,
          boxShadow: `0 0 ${glow}px ${accentColor}88, 0 10px 30px rgba(0,0,0,0.7)`,
          borderRadius: 16,
          padding: "16px 36px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
          maxWidth: 900,
          fontFamily: "'Segoe UI', Roboto, sans-serif",
          backdropFilter: "blur(8px)",
        }}
      >
        {/* Top Mini Badge */}
        <div
          style={{
            background: accentColor,
            color: "#ffffff",
            fontSize: 14,
            fontWeight: 900,
            letterSpacing: 2,
            textTransform: "uppercase",
            padding: "3px 14px",
            borderRadius: 20,
            boxShadow: `0 0 10px ${accentColor}aa`,
          }}
        >
          {badge}
        </div>

        {/* Main Title */}
        <div
          style={{
            color: "#ffffff",
            fontSize: 34,
            fontWeight: 900,
            letterSpacing: 1,
            textTransform: "uppercase",
            textAlign: "center",
            textShadow: "0 2px 8px rgba(0,0,0,0.8)",
          }}
        >
          {title}
        </div>
      </div>
    </AbsoluteFill>
  );
};
