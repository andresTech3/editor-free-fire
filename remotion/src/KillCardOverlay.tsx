import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const KillCardOverlay: React.FC<{ headshots?: number; playerTag?: string }> = ({
  headshots = 3,
  playerTag = "CODIGO HEADSHOT PRO",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { damping: 12, stiffness: 200 } });
  const glow = interpolate(frame, [0, 15, 30], [0, 25, 5], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          transform: `scale(${scale})`,
          border: "2px solid #ff3b30",
          boxShadow: `0px 0px ${glow}px #ff3b30`,
          backgroundColor: "rgba(10, 10, 15, 0.85)",
          padding: "16px 36px",
          borderRadius: "12px",
          textAlign: "center",
          fontFamily: "'Space Grotesk', 'Outfit', sans-serif",
        }}
      >
        <span style={{ color: "#ff3b30", fontSize: 24, fontWeight: 900, letterSpacing: "1px" }}>
          HEADSHOT COMBO
        </span>
        <h1 style={{ color: "#ffffff", fontSize: 56, margin: "4px 0", fontWeight: 900 }}>
          x{headshots}
        </h1>
        <p style={{ color: "#8b949e", fontSize: 18, margin: 0, fontWeight: 600 }}>
          {playerTag}
        </p>
      </div>
    </AbsoluteFill>
  );
};
