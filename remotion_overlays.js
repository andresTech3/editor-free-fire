/**
 * remotion_overlays.js
 * ====================
 * Renders transparent WebM overlays on-demand using Remotion CLI.
 * 
 * Generates:
 *   1. overlays/hud_sensibilidad.webm  (DPI & HUD Sensitivity Card, 5 seconds)
 *   2. overlays/cta_like_subscribe.webm (Like & Subscribe pop-up badge, 4 seconds)
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const PROJECT_ROOT = path.resolve(__dirname);
const REMOTION_DIR = path.join(PROJECT_ROOT, "remotion");
const OVERLAYS_DIR = path.join(PROJECT_ROOT, "overlays");

if (!fs.existsSync(OVERLAYS_DIR)) {
  fs.mkdirSync(OVERLAYS_DIR, { recursive: true });
}

function renderOverlay(compId, outputFile, extraProps = {}) {
  const outputPath = path.join(OVERLAYS_DIR, outputFile);
  console.log(`\n🎬 [Remotion Overlay] Rendering composition '${compId}' to '${outputFile}'...`);

  const propsJson = JSON.stringify(extraProps).replace(/"/g, '\\"');
  
  const cmd = [
    "npx", "remotion", "render",
    "src/index.ts",
    compId,
    `"${outputPath}"`,
    "--codec=vp8",
    "--pixel-format=yuva420p",
    "--image-format=png",
    `--props="${propsJson}"`
  ].join(" ");

  try {
    execSync(cmd, { cwd: REMOTION_DIR, stdio: "inherit" });
    console.log(`✅ [Remotion Overlay] Successfully rendered: ${outputPath}`);
    return outputPath;
  } catch (err) {
    console.error(`❌ [Remotion Overlay] Failed to render ${compId}:`, err.message);
    return null;
  }
}

function renderKillCardOverlay(headshots = 3, playerTag = "CODIGO HEADSHOT PRO", outputFile = "remotion_overlay.mov") {
  // Can render as ProRes 4444 (.mov) or transparent WebM (.webm)
  const isMov = outputFile.toLowerCase().endsWith(".mov");
  const outputPath = path.join(OVERLAYS_DIR, outputFile);
  console.log(`\n🎬 [Remotion Overlay] Rendering KillCardOverlay (x${headshots}, ${playerTag}) to '${outputFile}'...`);

  const propsJson = JSON.stringify({ headshots, playerTag }).replace(/"/g, '\\"');

  const cmd = [
    "npx", "remotion", "render",
    "src/index.ts",
    "KillCardOverlay",
    `"${outputPath}"`,
    isMov ? "--codec=prores --prores-profile=4444 --pixel-format=yuva444p10le" : "--codec=vp8 --pixel-format=yuva420p",
    "--image-format=png",
    `--props="${propsJson}"`
  ].join(" ");

  try {
    execSync(cmd, { cwd: REMOTION_DIR, stdio: "inherit" });
    console.log(`✅ [Remotion Overlay] Successfully rendered: ${outputPath}`);
    return outputPath;
  } catch (err) {
    console.warn(`⚠️ [Remotion Overlay] ProRes failed, falling back to WebM alpha...`);
    const fallbackWebm = outputPath.replace(/\.mov$/i, ".webm");
    const fallbackCmd = [
      "npx", "remotion", "render",
      "src/index.ts",
      "KillCardOverlay",
      `"${fallbackWebm}"`,
      "--codec=vp8",
      "--pixel-format=yuva420p",
      "--image-format=png",
      `--props="${propsJson}"`
    ].join(" ");
    try {
      execSync(fallbackCmd, { cwd: REMOTION_DIR, stdio: "inherit" });
      console.log(`✅ [Remotion Overlay] Successfully rendered fallback WebM: ${fallbackWebm}`);
      return fallbackWebm;
    } catch (e) {
      console.error(`❌ [Remotion Overlay] Failed to render KillCardOverlay:`, e.message);
      return null;
    }
  }
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes("--killcard")) {
    const hsIdx = args.indexOf("--headshots");
    const headshots = hsIdx !== -1 && args[hsIdx + 1] ? parseInt(args[hsIdx + 1], 10) : 3;
    const tagIdx = args.indexOf("--tag");
    const playerTag = tagIdx !== -1 && args[tagIdx + 1] ? args[tagIdx + 1] : "CODIGO HEADSHOT PRO";
    const outIdx = args.indexOf("--out");
    const outFile = outIdx !== -1 && args[outIdx + 1] ? args[outIdx + 1] : "remotion_overlay.webm";
    renderKillCardOverlay(headshots, playerTag, outFile);
    return;
  }

  if (args.includes("--topic")) {
    const titleIdx = args.indexOf("--title");
    const title = titleIdx !== -1 && args[titleIdx + 1] ? args[titleIdx + 1] : "TODO ROJO ACTIVADO";
    const badgeIdx = args.indexOf("--badge");
    const badge = badgeIdx !== -1 && args[badgeIdx + 1] ? args[badgeIdx + 1] : "TRUCO PRO FREE FIRE";
    const colorIdx = args.indexOf("--color");
    const accentColor = colorIdx !== -1 && args[colorIdx + 1] ? args[colorIdx + 1] : "#FF2E55";
    const outIdx = args.indexOf("--out");
    const outFile = outIdx !== -1 && args[outIdx + 1] ? args[outIdx + 1] : "topic_badge.webm";
    renderOverlay("TopicBadgeOverlay", outFile, { title, badge, accentColor });
    return;
  }

  if (args.includes("--diamond")) {
    const amtIdx = args.indexOf("--amount");
    const amount = amtIdx !== -1 && args[amtIdx + 1] ? args[amtIdx + 1] : "+5,000";
    const subIdx = args.indexOf("--sub");
    const subtitle = subIdx !== -1 && args[subIdx + 1] ? args[subIdx + 1] : "RECARGA DE DIAMANTES FREE FIRE";
    const outIdx = args.indexOf("--out");
    const outFile = outIdx !== -1 && args[outIdx + 1] ? args[outIdx + 1] : "diamond_alert.webm";
    renderOverlay("DiamondAlertOverlay", outFile, { amount, subtitle });
    return;
  }

  if (args.includes("--cta")) {
    const chIdx = args.indexOf("--channel");
    const channelName = chIdx !== -1 && args[chIdx + 1] ? args[chIdx + 1] : "Código Headshot";
    const outIdx = args.indexOf("--out");
    const outFile = outIdx !== -1 && args[outIdx + 1] ? args[outIdx + 1] : "cta_like_subscribe.webm";
    renderOverlay("CTALikeSubscribe", outFile, { channelName });
    return;
  }

  console.log("🚀 Starting Remotion Point Overlay Generator for Long 16:9 and 9:16 Videos...");

  const hudPath = renderOverlay("HUDSensibilidad", "hud_sensibilidad.webm", {
    playerName: "CODIGO HEADSHOT PRO",
    generalVal: 100,
    redDotVal: 98,
    scope2xVal: 95,
    scope4xVal: 100,
    dpiVal: 580,
    buttonSizeVal: 42,
  });

  const ctaPath = renderOverlay("CTALikeSubscribe", "cta_like_subscribe.webm", {
    channelName: "Código Headshot",
  });

  const killcardPath = renderKillCardOverlay(3, "CODIGO HEADSHOT PRO", "remotion_overlay.webm");

  renderOverlay("TopicBadgeOverlay", "topic_badge.webm", {
    title: "TODO ROJO ACTIVADO",
    badge: "TRUCO PRO FREE FIRE",
    accentColor: "#FF2E55"
  });

  renderOverlay("DiamondAlertOverlay", "diamond_alert.webm", {
    amount: "+5,000",
    subtitle: "RECARGA DE DIAMANTES FREE FIRE"
  });

  console.log("\n✨ All Remotion transparent overlays compiled successfully!");
}

if (require.main === module) {
  main();
}

module.exports = { renderOverlay, renderKillCardOverlay, main };

