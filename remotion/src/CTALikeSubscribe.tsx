import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type CTALikeSubscribeProps = {
  channelName?: string;
};

export const CTALikeSubscribe: React.FC<CTALikeSubscribeProps> = ({
  channelName = "Código Headshot",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring animation
  const entrance = spring({
    frame,
    fps,
    config: { damping: 10, mass: 0.7, stiffness: 120 },
  });

  const scale = interpolate(entrance, [0, 1], [0.4, 1]);
  const opacity = interpolate(entrance, [0, 1], [0, 1]);

  // Click animation (subscribing state transition at frame 70)
  const isSubscribed = frame > 70;
  const clickSpring = spring({
    frame: frame - 70,
    fps,
    config: { damping: 8, stiffness: 200 },
  });
  const clickScale = isSubscribed ? interpolate(clickSpring, [0, 0.5, 1], [1, 0.85, 1]) : 1;

  // Bell ringing vibration around frame 90
  const bellRinging = frame > 90 && frame < 130 ? Math.sin((frame - 90) * 0.8) * 15 : 0;

  return (
    <AbsoluteFill className="justify-end items-center pb-24 bg-transparent font-sans">
      <div
        style={{
          transform: `scale(${scale * clickScale})`,
          opacity,
        }}
        className="bg-slate-950/95 border-2 border-red-600/90 px-8 py-5 rounded-full shadow-[0_0_40px_rgba(220,38,38,0.5)] backdrop-blur-md flex items-center gap-6 text-white"
      >
        {/* Channel Info */}
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-fuchsia-600 p-0.5 shadow-lg">
            <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center font-black text-amber-400 text-lg">
              🎯
            </div>
          </div>
          <div>
            <h3 className="font-black text-lg tracking-wide text-white drop-shadow">{channelName}</h3>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">SUSCRÍBETE Y DEJA TU LIKE</p>
          </div>
        </div>

        {/* Subscribe Button */}
        <div
          className={`px-6 py-2.5 rounded-full font-black text-sm tracking-wider uppercase transition-all duration-300 shadow-md ${
            isSubscribed
              ? "bg-slate-800 text-slate-300 border border-slate-700"
              : "bg-red-600 hover:bg-red-500 text-white animate-pulse"
          }`}
        >
          {isSubscribed ? "✓ SUSCRITO" : "SUSCRIBIRSE"}
        </div>

        {/* Bell Icon */}
        <div
          style={{ transform: `rotate(${bellRinging}deg)` }}
          className={`text-2xl p-2 rounded-full ${
            frame > 90 ? "bg-amber-500/20 text-amber-400 border border-amber-400/50" : "text-slate-500"
          }`}
        >
          🔔
        </div>
      </div>
    </AbsoluteFill>
  );
};
