// Free Fire Clip Extractor — Mobile PWA App JS

document.addEventListener("DOMContentLoaded", () => {
  // Elementos UI
  const videoInput = document.getElementById("videoInput");
  const uploadArea = document.getElementById("uploadArea");
  const uploadText = document.getElementById("uploadText");
  const videoInfo = document.getElementById("videoInfo");
  const videoName = document.getElementById("videoName");
  const videoDuration = document.getElementById("videoDuration");

  const inputMaxClips = document.getElementById("inputMaxClips");
  const inputClipDur = document.getElementById("inputClipDur");
  const valClips = document.getElementById("valClips");
  const valDur = document.getElementById("valDur");

  const btnProcess = document.getElementById("btnProcess");
  const resultCard = document.getElementById("resultCard");
  const progressBox = document.getElementById("progressBox");
  const statusText = document.getElementById("statusText");
  const progressBar = document.getElementById("progressBar");
  const videoResultBox = document.getElementById("videoResultBox");
  const resultVideo = document.getElementById("resultVideo");
  const btnDownload = document.getElementById("btnDownload");

  const sourceVideo = document.getElementById("sourceVideo");
  const procCanvas = document.getElementById("procCanvas");
  const ctx = procCanvas.getContext("2d", { willReadFrequently: true });

  let selectedFile = null;
  let videoDurSec = 0;

  // Actualizar Sliders
  inputMaxClips.addEventListener("input", () => {
    valClips.textContent = `${inputMaxClips.value} clips`;
  });
  inputClipDur.addEventListener("input", () => {
    valDur.textContent = `${parseFloat(inputClipDur.value).toFixed(1)} seg`;
  });

  // Selector de Tarjetas de Eventos
  document.querySelectorAll(".event-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".event-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      const radio = card.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Selector de Formato (Aspect Ratio)
  document.querySelectorAll(".fmt-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".fmt-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const radio = btn.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Cargar Video de la Galería
  videoInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    selectedFile = file;
    uploadText.textContent = `✅ ${file.name}`;
    videoName.textContent = file.name;

    const url = URL.createObjectURL(file);
    sourceVideo.src = url;

    sourceVideo.onloadedmetadata = () => {
      videoDurSec = sourceVideo.duration;
      videoDuration.textContent = `${videoDurSec.toFixed(1)}s`;
      videoInfo.style.display = "flex";
      btnProcess.disabled = false;
    };
  });

  // BOTÓN GENERAR
  btnProcess.addEventListener("click", async () => {
    if (!selectedFile || videoDurSec <= 0) return;

    const eventType = document.querySelector('input[name="eventType"]:checked').value;
    const aspectRatio = document.querySelector('input[name="aspectRatio"]:checked').value;
    const maxClips = parseInt(inputMaxClips.value);
    const clipDur = parseFloat(inputClipDur.value);

    // UI Progress
    btnProcess.disabled = true;
    resultCard.style.display = "block";
    progressBox.style.display = "flex";
    videoResultBox.style.display = "none";
    progressBar.style.width = "5%";
    statusText.textContent = "Analizando cuadros del gameplay con visión de cámara...";

    resultCard.scrollIntoView({ behavior: "smooth" });

    try {
      // 1. Escanear gameplay y detectar clips
      const clips = await scanVideoEvents(eventType, maxClips, clipDur);
      
      progressBar.style.width = "40%";
      statusText.textContent = `Se detectaron ${clips.length} jugadas. Renderizando video final...`;

      // 2. Renderizar y exportar clips unidos
      const compiledBlob = await renderCompiledVideo(clips, aspectRatio);

      progressBar.style.width = "100%";
      statusText.textContent = "¡Recopilación completada con éxito!";

      setTimeout(() => {
        progressBox.style.display = "none";
        videoResultBox.style.display = "block";

        const compiledUrl = URL.createObjectURL(compiledBlob);
        resultVideo.src = compiledUrl;
        btnDownload.href = compiledUrl;
        btnDownload.download = `recopilacion_${eventType}_${aspectRatio.replace(":", "x")}.mp4`;
        btnProcess.disabled = false;
      }, 500);

    } catch (err) {
      console.error(err);
      statusText.textContent = `❌ Error: ${err.message || "No se pudo procesar el video"}`;
      btnProcess.disabled = false;
    }
  });

  // Algoritmo de Escaneo de Cuadros por Evento
  async function scanVideoEvents(eventType, maxClips, clipDur) {
    const sampleStep = 0.5; // analizar cada 0.5s
    const totalSamples = Math.floor(videoDurSec / sampleStep);
    const scoredSamples = [];

    for (let i = 0; i < totalSamples; i++) {
      const time = i * sampleStep;
      sourceVideo.currentTime = time;

      await new Promise(resolve => {
        sourceVideo.onseeked = resolve;
      });

      // Dibujar en Canvas para análisis RGB
      procCanvas.width = 160;
      procCanvas.height = 280;
      ctx.drawImage(sourceVideo, 0, 0, procCanvas.width, procCanvas.height);

      const frameData = ctx.getImageData(0, 0, procCanvas.width, procCanvas.height).data;
      let redCount = 0;
      let goldCount = 0;

      // Escanear píxeles
      for (let p = 0; p < frameData.length; p += 4) {
        const r = frameData[p];
        const g = frameData[p + 1];
        const b = frameData[p + 2];

        // Disparos Rojos (Red damage numbers): R alto, G bajo, B bajo
        if (r > 190 && g < 40 && b < 40) redCount++;
        // BOOYAH banner (Dorado/Amarillo): R alto, G alto, B bajo
        if (r > 200 && g > 170 && b < 50) goldCount++;
      }

      let score = 0;
      if (eventType === "tiros_rojo" || eventType === "highlights") {
        score = redCount;
      } else if (eventType === "booyah") {
        score = goldCount;
      } else {
        score = redCount + Math.random() * 10;
      }

      scoredSamples.push({ time, score });

      const pct = 5 + Math.floor((i / totalSamples) * 35);
      progressBar.style.width = `${pct}%`;
    }

    // Ordenar por score y seleccionar mejores clips
    scoredSamples.sort((a, b) => b.score - a.score);

    const selectedClips = [];
    for (const sample of scoredSamples) {
      if (selectedClips.length >= maxClips) break;

      const t = sample.time;
      const overlaps = selectedClips.some(c => Math.abs(t - c.start) < clipDur);

      if (!overlaps) {
        const start = Math.max(0, t - 1.0);
        const end = Math.min(videoDurSec, start + clipDur);
        selectedClips.push({ start, end });
      }
    }

    // Ordenar cronológicamente
    selectedClips.sort((a, b) => a.start - b.start);
    return selectedClips;
  }

  // Renderizar y concatenar clips en un Blob de Video
  function renderCompiledVideo(clips, aspectRatio) {
    return new Promise((resolve, reject) => {
      let outW = 1080, outH = 1920;
      if (aspectRatio === "16:9") { outW = 1920; outH = 1080; }
      else if (aspectRatio === "1:1") { outW = 1080; outH = 1080; }

      procCanvas.width = outW;
      procCanvas.height = outH;

      const stream = procCanvas.captureStream(30);
      
      let mime = "video/webm;codecs=vp8";
      if (MediaRecorder.isTypeSupported("video/mp4")) {
        mime = "video/mp4";
      } else if (MediaRecorder.isTypeSupported("video/webm;codecs=h264")) {
        mime = "video/webm;codecs=h264";
      }

      const recorder = new MediaRecorder(stream, { mimeType: mime });
      const chunks = [];

      recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: mime });
        resolve(blob);
      };

      recorder.start();

      let currentClipIdx = 0;

      function processClip() {
        if (currentClipIdx >= clips.length) {
          recorder.stop();
          return;
        }

        const clip = clips[currentClipIdx];
        sourceVideo.currentTime = clip.start;

        sourceVideo.onseeked = () => {
          sourceVideo.play();
          const startTime = Date.now();
          const targetDurMs = (clip.end - clip.start) * 1000;

          function drawFrame() {
            const elapsed = Date.now() - startTime;
            if (elapsed >= targetDurMs) {
              sourceVideo.pause();
              currentClipIdx++;
              processClip();
              return;
            }

            // Dibujar frame ajustado al aspect ratio
            ctx.drawImage(sourceVideo, 0, 0, outW, outH);
            requestAnimationFrame(drawFrame);
          }

          drawFrame();
        };
      }

      processClip();
    });
  }
});
