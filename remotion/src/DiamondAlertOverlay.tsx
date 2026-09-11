import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type DiamondAlertOverlayProps = {
  amount?: string;
  subtitle?: string;
};

export const DiamondAlertOverlay: React.FC<DiamondAlertOverlayProps> = ({
  amount = "+5,000",
  subtitle = "RECARGA DE DIAMANTES FREE FIRE",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Bouncy entrance
  const scale = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 220 },
  });

  // Diamond pulse
  const pulse = interpolate(
    Math.sin((frame / fps) * Math.PI * 3),
    [-1, 1],
    [0.96, 1.04]
  );

  // Gold / Cyan Glow
  const glow = interpolate(frame, [0, 15, 30], [0, 25, 12], {
    extrapolateRight: "clamp",
  });

  // Fade out near end (4s duration = 120 frames @ 30fps or 240 @ 60fps)
  const fadeOut = interpolate(
    frame,
    [fps * 3.5, fps * 4.0],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "center",
        paddingTop: 180,
        opacity: fadeOut,
      }}
    >
      <div
        style={{
          transform: `scale(${scale * pulse})`,
          background: "linear-gradient(135deg, rgba(12, 16, 28, 0.95), rgba(20, 28, 48, 0.92))",
          border: "2px solid #00E5FF",
          boxShadow: `0 0 ${glow}px #00E5FFaa, 0 10px 40px rgba(0,0,0,0.8)`,
          borderRadius: 20,
          padding: "20px 42px",
          display: "flex",
          alignItems: "center",
          gap: 20,
          fontFamily: "'Segoe UI', Roboto, sans-serif",
          backdropFilter: "blur(10px)",
        }}
      >
        {/* Diamond Icon SVG */}
        <div
          style={{
            width: 70,
            height: 70,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "radial-gradient(circle, rgba(0,229,255,0.3) 0%, rgba(0,0,0,0) 70%)",
          }}
        >
          <svg viewBox="0 0 24 24" width="60" height="60" fill="#00E5FF">
            <path d="M12 2L4.5 9.5L12 22L19.5 9.5L12 2ZM6.7 9L12 3.7L17.3 9H6.7ZM12 19.3L7.1 10.5H16.9L12 19.3Z" />
          </svg>
        </div>

        {/* Text Details */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              color: "#FFC700",
              fontSize: 13,
              fontWeight: 900,
              letterSpacing: 2,
              textTransform: "uppercase",
            }}
          >
            {subtitle}
          </div>
          <div
            style={{
              color: "#ffffff",
              fontSize: 48,
              fontWeight: 900,
              letterSpacing: 1,
              lineHeight: 1.1,
              textShadow: "0 0 16px rgba(0,229,255,0.6)",
            }}
          >
            {amount}{" "}
            <span style={{ fontSize: 26, color: "#00E5FF", fontWeight: 800 }}>
              DIAMANTES
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
