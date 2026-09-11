import React from "react";
import { Composition } from "remotion";
import "./index.css";
import { ViralComposition } from "./ViralComposition";
import type { CaptionChunk } from "./CaptionTrack";

// Definir el esquema de props esperado desde Python
export type ViralProps = {
  videoPath: string;
  startTime: number;
  durationInSeconds: number;
  fps: number;
  cropMeta: {
    orig_width: number;
    orig_height: number;
    crop_w: number;
    crop_h: number;
    fps: number;
  };
  cropPositions: Array<{
    frame_idx: number;
    crop_x: number;
    crop_y: number;
    crop_w: number;
    crop_h: number;
    face_x?: number;
    face_y?: number;
    has_face: boolean;
  }>;
  words: Array<{
    word: string;
    start: number;
    end: number;
    confidence: number;
  }>;
  viralScore: number;
  useZoom: boolean;
  useSubtitles: boolean;
  subtitleStyle: string;
  captionChunks?: CaptionChunk[];
  impactMoments?: Array<{ time: number; word: string; intensity: number }>;
  logoPath?: string;   // ruta relativa en remotion/public/ — e.g. "logo.png"
  layoutStyle?: "header_banner" | "split_screen" | "ranking_list" | "financial_highlight" | "neon_pointer" | "zoom_burst";
  hookTitle?: string;  // Título del gancho para el header banner
  hookHeader?: string; // Encabezado de categoría
  rankingItems?: Array<{
    rank: number;
    title: string;
    subtitle?: string;
    start: number; // segundo relativo inicio
    end: number;   // segundo relativo fin
  }>;
};

// Props default para testear en el Studio sin Python
const defaultProps: ViralProps = {
  videoPath: "file:///C:/Users/SnyX/Documents/Proyectos/Edicion en Capcut/input/Slip N Slide Football Final.mp4",
  startTime: 1225,
  durationInSeconds: 30,
  fps: 30,
  cropMeta: { orig_width: 1920, orig_height: 1080, crop_w: 607, crop_h: 1080, fps: 30 },
  cropPositions: [],
  words: [
    { word: "AT",      start: 0.3,  end: 0.6,  confidence: 0.95 },
    { word: "LEAST",   start: 0.6,  end: 1.0,  confidence: 0.95 },
    { word: "HE",      start: 1.1,  end: 1.3,  confidence: 0.9  },
    { word: "GOT",     start: 1.3,  end: 1.6,  confidence: 0.9  },
    { word: "THE",     start: 1.6,  end: 1.8,  confidence: 0.9  },
    { word: "LAST",    start: 1.8,  end: 2.2,  confidence: 0.9  },
    { word: "ONE",     start: 2.2,  end: 2.7,  confidence: 0.9  },
    { word: "INSANE",  start: 3.0,  end: 3.7,  confidence: 0.98 },
  ],
  viralScore: 0.85,
  useZoom: true,
  useSubtitles: true,
  subtitleStyle: "viral_yellow",
  captionChunks: [
    {
      words: [
        { word: "AT",    start: 0.3, end: 0.6, is_impact: false },
        { word: "LEAST", start: 0.6, end: 1.0, is_impact: false },
        { word: "HE",    start: 1.1, end: 1.3, is_impact: false },
      ],
      start: 0.3, end: 1.3, has_impact: false, primary_idx: 1, text: "AT LEAST HE",
    },
    {
      words: [
        { word: "GOT",  start: 1.3, end: 1.6, is_impact: false },
        { word: "THE",  start: 1.6, end: 1.8, is_impact: false },
        { word: "LAST", start: 1.8, end: 2.2, is_impact: false },
      ],
      start: 1.3, end: 2.2, has_impact: false, primary_idx: 0, text: "GOT THE LAST",
    },
    {
      words: [
        { word: "ONE",    start: 2.2, end: 2.7, is_impact: false },
      ],
      start: 2.2, end: 2.7, has_impact: false, primary_idx: 0, text: "ONE",
    },
    {
      words: [
        { word: "INSANE", start: 3.0, end: 3.7, is_impact: true },
      ],
      start: 3.0, end: 3.7, has_impact: true, primary_idx: 0, text: "INSANE",
    },
  ],
  impactMoments: [
    { time: 3.0, word: "INSANE", intensity: 0.95 },
  ],
  logoPath: "logo.png",
};

import { HUDSensibilidad } from "./HUDSensibilidad";
import { CTALikeSubscribe } from "./CTALikeSubscribe";
import { KillCardOverlay } from "./KillCardOverlay";
import { TopicBadgeOverlay } from "./TopicBadgeOverlay";
import { DiamondAlertOverlay } from "./DiamondAlertOverlay";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ViralComposition"
        component={ViralComposition}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
        calculateMetadata={({ props }) => {
          const fps = props.fps || 30;
          const durationSec = props.durationInSeconds || 30;
          return {
            durationInFrames: Math.round(durationSec * fps),
            fps,
          };
        }}
      />
      <Composition
        id="HUDSensibilidad"
        component={HUDSensibilidad}
        durationInFrames={300}
        fps={60}
        width={1920}
        height={1080}
        defaultProps={{
          playerName: "CODIGO HEADSHOT PRO",
          generalVal: 100,
          redDotVal: 98,
          scope2xVal: 95,
          scope4xVal: 100,
          dpiVal: 580,
          buttonSizeVal: 42,
        }}
      />
      <Composition
        id="CTALikeSubscribe"
        component={CTALikeSubscribe}
        durationInFrames={240}
        fps={60}
        width={1920}
        height={1080}
        defaultProps={{
          channelName: "Código Headshot",
        }}
      />
      <Composition
        id="KillCardOverlay"
        component={KillCardOverlay}
        durationInFrames={156}
        fps={60}
        width={1080}
        height={1920}
        defaultProps={{
          headshots: 3,
          playerTag: "CODIGO HEADSHOT PRO",
        }}
      />
      <Composition
        id="TopicBadgeOverlay"
        component={TopicBadgeOverlay}
        durationInFrames={120}
        fps={60}
        width={1080}
        height={1920}
        defaultProps={{
          title: "TODO ROJO ACTIVADO",
          badge: "TRUCO PRO FREE FIRE",
          accentColor: "#FF2E55",
        }}
      />
      <Composition
        id="DiamondAlertOverlay"
        component={DiamondAlertOverlay}
        durationInFrames={180}
        fps={60}
        width={1080}
        height={1920}
        defaultProps={{
          amount: "+5,000",
          subtitle: "RECARGA DE DIAMANTES FREE FIRE",
        }}
      />
    </>
  );
};

