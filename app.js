// Free Fire Clip Extractor — Mobile PWA App JS (v3.0 Bulletproof Video Loader)

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

  // ── FIX 1: ACTUALIZACIÓN DE SLIDERS INSTANTÁNEA ──────────────────────────
  function updateSliderValues() {
    if (valClips && inputMaxClips) {
      valClips.textContent = `${inputMaxClips.value} clips`;
    }
    if (valDur && inputClipDur) {
      valDur.textContent = `${parseFloat(inputClipDur.value).toFixed(1)} seg`;
    }
  }

  ["input", "change"].forEach(evtName => {
    if (inputMaxClips) inputMaxClips.addEventListener(evtName, updateSliderValues);
    if (inputClipDur) inputClipDur.addEventListener(evtName, updateSliderValues);
  });
  updateSliderValues();

  // ── FIX 2: SELECCIÓN DE TARJETAS DE EVENTOS ──────────────────────────────
  document.querySelectorAll('input[name="eventType"]').forEach(radio => {
    radio.addEventListener("change", () => {
      document.querySelectorAll(".event-card").forEach(c => c.classList.remove("active"));
      const card = radio.closest(".event-card");
      if (card) card.classList.add("active");
    });
  });

  document.querySelectorAll(".event-card").forEach(card => {
    card.addEventListener("click", (e) => {
      const radio = card.querySelector('input[type="radio"]');
      if (radio && !radio.checked) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change"));
      }
    });
  });

  // ── FIX 3: SELECCIÓN DE FORMATO ──────────────────────────────────────────
  document.querySelectorAll('input[name="aspectRatio"]').forEach(radio => {
    radio.addEventListener("change", () => {
      document.querySelectorAll(".fmt-btn").forEach(b => b.classList.remove("active"));
      const btn = radio.closest(".fmt-btn");
      if (btn) btn.classList.add("active");
    });
  });

  document.querySelectorAll(".fmt-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const radio = btn.querySelector('input[type="radio"]');
      if (radio && !radio.checked) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change"));
      }
    });
  });

  // ── FIX 4: ÁREA DE CARGA Y SELECCIÓN DE VIDEO (BULLETPROOF) ──────────────
  uploadArea.addEventListener("click", (e) => {
    videoInput.click();
  });

  videoInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    selectedFile = file;
    
    // Actualizar UI INMEDIATAMENTE
    uploadText.textContent = `✅ Video Cargado: ${file.name}`;
    uploadArea.style.borderColor = "#00f0ff";
    uploadArea.style.background = "rgba(0, 240, 255, 0.1)";

    videoName.textContent = file.name;
    videoDuration.textContent = "Cargando...";
    videoInfo.style.display = "flex";
    btnProcess.disabled = false;

    const fileUrl = URL.createObjectURL(file);

    // Handlers de Video antes de asignar .src
    function onVideoLoaded() {
      if (sourceVideo.duration && !isNaN(sourceVideo.duration) && sourceVideo.duration > 0) {
        videoDurSec = sourceVideo.duration;
        videoDuration.textContent = `${videoDurSec.toFixed(1)}s`;
      } else {
        videoDurSec = 30.0; // Fallback por defecto si los metadatos se demoran
        videoDuration.textContent = "Listo";
      }
    }

    sourceVideo.onloadedmetadata = onVideoLoaded;
    sourceVideo.onloadeddata = onVideoLoaded;
    sourceVideo.ondurationchange = onVideoLoaded;

    sourceVideo.src = fileUrl;
    sourceVideo.load();
  });

  // ── BOTÓN GENERAR RECOPILACIÓN ──────────────────────────────────────────
  btnProcess.addEventListener("click", async () => {
    if (!selectedFile) {
      alert("Por favor selecciona primero un video de gameplay.");
      return;
    }

    const eventRadio = document.querySelector('input[name="eventType"]:checked');
    const aspectRadio = document.querySelector('input[name="aspectRatio"]:checked');
    
    const eventType = eventRadio ? eventRadio.value : "tiros_rojo";
    const aspectRatio = aspectRadio ? aspectRadio.value : "9:16";
    const maxClips = parseInt(inputMaxClips.value);
    const clipDur = parseFloat(inputClipDur.value);

    if (videoDurSec <= 0) videoDurSec = 30.0;

    btnProcess.disabled = true;
    resultCard.style.display = "block";
    progressBox.style.display = "flex";
    videoResultBox.style.display = "none";
    progressBar.style.width = "5%";
    statusText.textContent = "Analizando cuadros del gameplay...";

    resultCard.scrollIntoView({ behavior: "smooth" });

    try {
      const clips = await scanVideoEvents(eventType, maxClips, clipDur);
      
      progressBar.style.width = "40%";
      statusText.textContent = `Se detectaron ${clips.length} jugadas. Renderizando video...`;

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
      statusText.textContent = `❌ Error: ${err.message || "Ocurrió un problema procesando el video"}`;
      btnProcess.disabled = false;
    }
  });

  // ── ESCANEO DE CUADROS ───────────────────────────────────────────────────
  async function scanVideoEvents(eventType, maxClips, clipDur) {
    const sampleStep = 0.5;
    const dur = (videoDurSec && videoDurSec > 0) ? videoDurSec : 30.0;
    const totalSamples = Math.floor(dur / sampleStep);
    const scoredSamples = [];

    for (let i = 0; i < totalSamples; i++) {
      const time = i * sampleStep;
      sourceVideo.currentTime = time;

      await new Promise(resolve => {
        const timer = setTimeout(resolve, 100);
        sourceVideo.onseeked = () => {
          clearTimeout(timer);
          resolve();
        };
      });

      procCanvas.width = 160;
      procCanvas.height = 280;
      try {
        ctx.drawImage(sourceVideo, 0, 0, procCanvas.width, procCanvas.height);
        const frameData = ctx.getImageData(0, 0, procCanvas.width, procCanvas.height).data;
        let redCount = 0;
        let goldCount = 0;

        for (let p = 0; p < frameData.length; p += 4) {
          const r = frameData[p];
          const g = frameData[p + 1];
          const b = frameData[p + 2];

          if (r > 190 && g < 40 && b < 40) redCount++;
          if (r > 200 && g > 170 && b < 50) goldCount++;
        }

        let score = (eventType === "tiros_rojo" || eventType === "highlights") ? redCount : (eventType === "booyah" ? goldCount : redCount + Math.random() * 10);
        scoredSamples.push({ time, score });
      } catch (e) {
        scoredSamples.push({ time, score: Math.random() * 10 });
      }

      const pct = 5 + Math.floor((i / totalSamples) * 35);
      progressBar.style.width = `${pct}%`;
    }

    scoredSamples.sort((a, b) => b.score - a.score);

    const selectedClips = [];
    for (const sample of scoredSamples) {
      if (selectedClips.length >= maxClips) break;

      const t = sample.time;
      const overlaps = selectedClips.some(c => Math.abs(t - c.start) < clipDur);

      if (!overlaps) {
        const start = Math.max(0, t - 1.0);
        const end = Math.min(dur, start + clipDur);
        selectedClips.push({ start, end });
      }
    }

    selectedClips.sort((a, b) => a.start - b.start);
    return selectedClips;
  }

  // ── RENDER Y CONCATENACIÓN ──────────────────────────────────────────────
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

        const onSeek = () => {
          sourceVideo.play().catch(() => {});
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

            ctx.drawImage(sourceVideo, 0, 0, outW, outH);
            requestAnimationFrame(drawFrame);
          }

          drawFrame();
        };

        sourceVideo.onseeked = onSeek;
        setTimeout(onSeek, 200); // safety fallback seek
      }

      processClip();
    });
  }
});
