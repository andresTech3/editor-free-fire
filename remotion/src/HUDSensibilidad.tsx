import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type HUDSensibilidadProps = {
  playerName?: string;
  generalVal?: number;
  redDotVal?: number;
  scope2xVal?: number;
  scope4xVal?: number;
  dpiVal?: number;
  buttonSizeVal?: number;
};

export const HUDSensibilidad: React.FC<HUDSensibilidadProps> = ({
  playerName = "CODIGO HEADSHOT PRO",
  generalVal = 100,
  redDotVal = 98,
  scope2xVal = 95,
  scope4xVal = 100,
  dpiVal = 580,
  buttonSizeVal = 42,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Spring entrance animation
  const cardEntrance = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.8, stiffness: 100 },
  });

  const cardScale = interpolate(cardEntrance, [0, 1], [0.7, 1]);
  const cardOpacity = interpolate(cardEntrance, [0, 1], [0, 1]);

  // Animated progress bar springs
  const barProgress = spring({
    frame: frame - 15,
    fps,
    config: { damping: 14, stiffness: 80 },
  });

  const stats = [
    { label: "GENERAL", val: generalVal, color: "from-amber-400 to-red-500" },
    { label: "MIRA DE PUNTO ROJO", val: redDotVal, color: "from-yellow-300 to-amber-500" },
    { label: "MIRA 2X", val: scope2xVal, color: "from-cyan-400 to-blue-600" },
    { label: "MIRA 4X", val: scope4xVal, color: "from-fuchsia-400 to-purple-600" },
  ];

  return (
    <AbsoluteFill className="justify-center items-center bg-transparent font-sans">
      <div
        style={{
          transform: `scale(${cardScale})`,
          opacity: cardOpacity,
        }}
        className="w-[850px] bg-slate-950/90 border-2 border-amber-500/80 rounded-3xl p-8 shadow-[0_0_50px_rgba(245,158,11,0.4)] backdrop-blur-xl text-white relative overflow-hidden"
      >
        {/* Top Header Badge */}
        <div className="flex justify-between items-center border-b border-slate-800 pb-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="flex h-4 w-4 rounded-full bg-red-500 animate-ping" />
            <h2 className="text-2xl font-black tracking-wider text-amber-400 uppercase drop-shadow">
              {playerName}
            </h2>
          </div>
          <div className="bg-amber-500/20 border border-amber-400/50 px-4 py-1.5 rounded-full text-xs font-extrabold text-amber-300 tracking-widest uppercase">
            CONFIGURACIÓN SENSIBILIDAD VIP
          </div>
        </div>

        {/* Bars Container */}
        <div className="space-y-4">
          {stats.map((item, idx) => {
            const currentVal = Math.round(
              interpolate(barProgress, [0, 1], [0, item.val], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
            );
            return (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-sm font-extrabold tracking-wide text-slate-300">
                  <span>{item.label}</span>
                  <span className="text-amber-400 font-mono text-base">{currentVal}%</span>
                </div>
                <div className="w-full h-4 bg-slate-900 rounded-full overflow-hidden p-0.5 border border-slate-800">
                  <div
                    style={{ width: `${currentVal}%` }}
                    className={`h-full rounded-full bg-gradient-to-r ${item.color} shadow-[0_0_12px_rgba(245,158,11,0.6)] transition-all`}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Extra Specs (DPI & Boton Disparo) */}
        <div className="grid grid-cols-2 gap-4 mt-6 pt-4 border-t border-slate-800/80">
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-3 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-400">DPI RECOMENDADO</span>
            <span className="text-lg font-black text-cyan-400 font-mono">{dpiVal}</span>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-3 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-400">BOTÓN DE DISPARO</span>
            <span className="text-lg font-black text-amber-400 font-mono">{buttonSizeVal}%</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
