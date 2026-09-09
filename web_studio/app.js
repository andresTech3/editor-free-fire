/**
 * CÓDIGO HEADSHOT STUDIO — Frontend Logic (Mobile, Web & Vercel)
 * Handles audio upload, resource selection, live progress polling, and video preview.
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  let selectedAudioFile = null;
  let selectedResourceFiles = [];
  let useDefaultResources = true;
  let currentJobId = null;
  let pollInterval = null;

  // API Base resolution (supports Vercel with remote tunnel or local server)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('api')) {
    localStorage.setItem('FREEFIRE_API_URL', urlParams.get('api'));
  }
  let apiBaseUrl = localStorage.getItem('FREEFIRE_API_URL') || '';

  function buildApiUrl(path) {
    if (!path.startsWith('/')) path = '/' + path;
    if (!apiBaseUrl) return path;
    return apiBaseUrl.replace(/\/+$/, '') + path;
  }

  // DOM Elements
  const serverPill = document.getElementById('serverPill');
  const serverHostLabel = document.getElementById('serverHostLabel');

  // Step 1: Audio
  const audioDropzone = document.getElementById('audioDropzone');
  const audioFileInput = document.getElementById('audioFileInput');
  const audioUploadPrompt = document.getElementById('audioUploadPrompt');
  const audioLoadedInfo = document.getElementById('audioLoadedInfo');
  const loadedAudioName = document.getElementById('loadedAudioName');
  const audioPreview = document.getElementById('audioPreview');
  const btnChangeAudio = document.getElementById('btnChangeAudio');

  // Step 2: Resources
  const btnModeDefault = document.getElementById('btnModeDefault');
  const btnModeCustom = document.getElementById('btnModeCustom');
  const defaultPackBanner = document.getElementById('defaultPackBanner');
  const customResourcesBox = document.getElementById('customResourcesBox');
  const resourcesDropzone = document.getElementById('resourcesDropzone');
  const resourcesFileInput = document.getElementById('resourcesFileInput');
  const resourcesUploadPrompt = document.getElementById('resourcesUploadPrompt');
  const resourcesLoadedInfo = document.getElementById('resourcesLoadedInfo');
  const loadedResourcesCount = document.getElementById('loadedResourcesCount');
  const btnChangeResources = document.getElementById('btnChangeResources');

  // Step 3: Format & Options
  const lblFormatShort = document.getElementById('lblFormatShort');
  const lblFormatLong = document.getElementById('lblFormatLong');
  const speedSelect = document.getElementById('speedSelect');
  const hookSelect = document.getElementById('hookSelect');

  // Action & Progress
  const btnGenerate = document.getElementById('btnGenerate');
  const progressCard = document.getElementById('progressCard');
  const progressStepTitle = document.getElementById('progressStepTitle');
  const progressPercentLabel = document.getElementById('progressPercentLabel');
  const progressBarFill = document.getElementById('progressBarFill');
  const terminalOutput = document.getElementById('terminalOutput');
  const msWhisper = document.getElementById('msWhisper');
  const msInvestigate = document.getElementById('msInvestigate');
  const msMemes = document.getElementById('msMemes');
  const msRender = document.getElementById('msRender');

  // Result
  const resultCard = document.getElementById('resultCard');
  const finalVideoPlayer = document.getElementById('finalVideoPlayer');
  const btnDownloadVideo = document.getElementById('btnDownloadVideo');
  const btnReset = document.getElementById('btnReset');

  // 1. Check Server Connection & Settings Pill
  serverPill.style.cursor = 'pointer';
  serverPill.title = 'Toca para configurar el servidor de renderizado';
  serverPill.addEventListener('click', () => {
    const current = apiBaseUrl || '';
    const newUrl = prompt(
      '⚙️ Servidor de Renderizado (Túnel / PC):\n\n' +
      'Ingresa la URL de tu backend (ej. https://...loca.lt o http://192.168.1.2:8000).\n' +
      'Déjalo vacío para usar el servidor predeterminado:',
      current
    );
    if (newUrl !== null) {
      apiBaseUrl = newUrl.trim();
      if (apiBaseUrl) {
        localStorage.setItem('FREEFIRE_API_URL', apiBaseUrl);
        showToast('✅ Servidor configurado: ' + apiBaseUrl);
      } else {
        localStorage.removeItem('FREEFIRE_API_URL');
        showToast('ℹ️ Usando servidor predeterminado');
      }
      checkServerInfo();
    }
  });

  checkServerInfo();

  async function checkServerInfo() {
    try {
      const res = await fetch(buildApiUrl('/api/info'), {
        headers: {
          'bypass-tunnel-reminder': '1',
          'Bypass-Tunnel-Reminder': 'true'
        }
      });
      if (res.ok) {
        const data = await res.json();
        const isVercelEdge = data.platform && data.platform.includes('Vercel');
        if (isVercelEdge && !apiBaseUrl) {
          // On Vercel edge without a backend rendering tunnel configured
          serverHostLabel.textContent = '⚙️ Conectar Túnel (PC)';
          serverPill.classList.remove('online');
          serverPill.classList.add('needs-config');
          serverPill.title = 'Toca aquí para ingresar la URL de tu túnel o servidor de PC';
        } else {
          const displayHost = apiBaseUrl ? new URL(apiBaseUrl).hostname : (data.host_ip || data.local_ip || 'Online');
          serverHostLabel.textContent = `Online (${displayHost})`;
          serverPill.classList.add('online');
          serverPill.classList.remove('needs-config');
          serverPill.title = `Conectado al servidor de renderizado (${displayHost})`;
        }
      } else {
        serverHostLabel.textContent = apiBaseUrl ? 'Error Servidor' : '⚙️ Conectar Túnel';
        serverPill.classList.remove('online');
      }
    } catch (e) {
      if (window.location.hostname.includes('vercel.app')) {
        serverHostLabel.textContent = '⚙️ Conectar Túnel';
      } else {
        serverHostLabel.textContent = 'Modo Local';
      }
      serverPill.classList.remove('online');
      console.warn('Could not fetch /api/info:', e);
    }
  }

  // 2. Audio Selection & Drag/Drop
  audioDropzone.addEventListener('click', (e) => {
    if (e.target !== btnChangeAudio && !audioPreview.contains(e.target)) {
      audioFileInput.click();
    }
  });

  audioFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedAudio(e.target.files[0]);
    }
  });

  btnChangeAudio.addEventListener('click', (e) => {
    e.stopPropagation();
    audioFileInput.click();
  });

  setupDragAndDrop(audioDropzone, (files) => {
    if (files.length > 0 && files[0].type.startsWith('audio/')) {
      handleSelectedAudio(files[0]);
    } else {
      showToast('Por favor arrastra un archivo de audio (.mp3, .wav, .m4a)');
    }
  });

  function handleSelectedAudio(file) {
    selectedAudioFile = file;
    loadedAudioName.textContent = file.name;
    const objectUrl = URL.createObjectURL(file);
    audioPreview.src = objectUrl;

    audioUploadPrompt.style.display = 'none';
    audioLoadedInfo.style.display = 'block';
  }

  // 3. Resources Mode Toggle
  btnModeDefault.addEventListener('click', () => {
    useDefaultResources = true;
    btnModeDefault.classList.add('active');
    btnModeCustom.classList.remove('active');
    defaultPackBanner.style.display = 'block';
    customResourcesBox.style.display = 'none';
  });

  btnModeCustom.addEventListener('click', () => {
    useDefaultResources = false;
    btnModeCustom.classList.add('active');
    btnModeDefault.classList.remove('active');
    defaultPackBanner.style.display = 'none';
    customResourcesBox.style.display = 'block';
  });

  resourcesDropzone.addEventListener('click', (e) => {
    if (e.target !== btnChangeResources) {
      resourcesFileInput.click();
    }
  });

  resourcesFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleSelectedResources(Array.from(e.target.files));
    }
  });

  btnChangeResources.addEventListener('click', (e) => {
    e.stopPropagation();
    resourcesFileInput.click();
  });

  setupDragAndDrop(resourcesDropzone, (files) => {
    if (files.length > 0) {
      handleSelectedResources(Array.from(files));
    }
  });

  function handleSelectedResources(files) {
    selectedResourceFiles = files;
    loadedResourcesCount.textContent = `${files.length} archivo(s) seleccionado(s)`;
    resourcesUploadPrompt.style.display = 'none';
    resourcesLoadedInfo.style.display = 'block';
  }

  // 4. Format Selection
  lblFormatShort.addEventListener('click', () => {
    lblFormatShort.classList.add('active');
    lblFormatLong.classList.remove('active');
    lblFormatShort.querySelector('input').checked = true;
  });

  lblFormatLong.addEventListener('click', () => {
    lblFormatLong.classList.add('active');
    lblFormatShort.classList.remove('active');
    lblFormatLong.querySelector('input').checked = true;
  });

  // 5. Generate Button Logic
  btnGenerate.addEventListener('click', async () => {
    if (!selectedAudioFile) {
      highlightStep('stepAudioCard');
      showToast('⚠️ Por favor sube un archivo de audio para comenzar');
      return;
    }

    if (!useDefaultResources && selectedResourceFiles.length === 0) {
      highlightStep('stepResourcesCard');
      showToast('⚠️ Selecciona archivos para tu carpeta de recursos o usa el Pack Oficial');
      return;
    }

    // Check Vercel Cloud remote connection
    if (window.location.hostname.includes('vercel.app') && !apiBaseUrl) {
      showToast('⚠️ Para renderizar videos, inicia el servidor en tu PC con Iniciar_Web_Studio_Movil.bat');
      const termLine = document.createElement('p');
      termLine.className = 'term-line';
      termLine.style.color = '#FF0055';
      termLine.textContent = '[AVISO VERCEL] Vercel es una vista previa estática. Para renderizar a 60FPS con FFmpeg y Whisper, abre http://localhost:8000 en tu PC o conecta el túnel en el botón de estado arriba.';
      terminalOutput.appendChild(termLine);
      progressCard.style.display = 'block';
      updateProgress(0, 'Servidor de renderizado no conectado', 'Ejecuta Iniciar_Web_Studio_Movil.bat');
      return;
    }

    // UI State: Starting
    btnGenerate.disabled = true;
    btnGenerate.classList.add('btn-disabled');
    resultCard.style.display = 'none';
    progressCard.style.display = 'block';
    progressCard.scrollIntoView({ behavior: 'smooth' });

    updateProgress(5, 'Subiendo archivos al servidor...', 'Iniciando subida...');
    resetMilestones();

    try {
      // Step A: Upload Files
      const uploadFormData = new FormData();
      uploadFormData.append('audio', selectedAudioFile);

      if (!useDefaultResources && selectedResourceFiles.length > 0) {
        for (const file of selectedResourceFiles) {
          uploadFormData.append('resources', file);
        }
      }

      addLogLine(`[SUBIDA] Subiendo audio: ${selectedAudioFile.name} (${(selectedAudioFile.size / 1024 / 1024).toFixed(1)} MB)...`);
      if (!useDefaultResources) {
        addLogLine(`[SUBIDA] Subiendo ${selectedResourceFiles.length} recursos visuales...`);
      } else {
        addLogLine(`[INFO] Usando Pack Oficial Maestro integrado.`);
      }

      const uploadRes = await fetch(buildApiUrl('/api/upload'), {
        method: 'POST',
        headers: {
          'bypass-tunnel-reminder': '1',
          'Bypass-Tunnel-Reminder': 'true'
        },
        body: uploadFormData
      });

      if (!uploadRes.ok) {
        let errMsg = 'Error en la subida de archivos';
        try {
          const errJson = await uploadRes.json();
          errMsg = errJson.detail || errMsg;
        } catch (_) {
          errMsg = `Error HTTP ${uploadRes.status} (${uploadRes.statusText})`;
        }
        throw new Error(errMsg);
      }

      const uploadData = await uploadRes.json();
      addLogLine(`[OK] Subida completada: ${uploadData.audio_name}`);

      // Step B: Request Generation
      const selectedRatio = document.querySelector('input[name="aspectRatio"]:checked')?.value || '9:16';
      const speedVal = parseFloat(speedSelect.value) || 1.5;
      const hookVal = hookSelect.value || 'auto';

      updateProgress(15, 'Iniciando pipeline de edición...', 'Configurando motor de video');
      setMilestone(msWhisper, 'active');

      const genPayload = {
        session_id: uploadData.session_id,
        audio_path: uploadData.audio_path,
        resources_dir: uploadData.resources_dir || null,
        aspect_ratio: selectedRatio,
        speed: speedVal,
        hook_preference: hookVal
      };

      const genRes = await fetch(buildApiUrl('/api/generate'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'bypass-tunnel-reminder': '1',
          'Bypass-Tunnel-Reminder': 'true'
        },
        body: JSON.stringify(genPayload)
      });

      if (!genRes.ok) {
        let errGenMsg = 'Error al iniciar la generación';
        try {
          const errGen = await genRes.json();
          errGenMsg = errGen.detail || errGenMsg;
        } catch (_) {
          errGenMsg = `Error HTTP ${genRes.status} (${genRes.statusText})`;
        }
        throw new Error(errGenMsg);
      }

      const genData = await genRes.json();
      currentJobId = genData.job_id;
      addLogLine(`[PROCESO] Tarea asignada ID: ${currentJobId} (Formato ${selectedRatio})`);

      // Step C: Start Polling
      startPolling(currentJobId);

    } catch (err) {
      console.error(err);
      addLogLine(`[ERROR] ❌ ${err.message}`);
      updateProgress(0, 'Ocurrió un error en el proceso', 'Error');
      btnGenerate.disabled = false;
      btnGenerate.classList.remove('btn-disabled');
      showToast(`Error: ${err.message}`);
    }
  });

  // 6. Polling Worker
  function startPolling(jobId) {
    if (pollInterval) clearInterval(pollInterval);
    let consecutiveErrors = 0;

    pollInterval = setInterval(async () => {
      try {
        const res = await fetch(buildApiUrl(`/api/status/${jobId}`), {
          headers: {
            'bypass-tunnel-reminder': '1',
            'Bypass-Tunnel-Reminder': 'true'
          }
        });

        if (!res.ok) {
          consecutiveErrors++;
          if (consecutiveErrors >= 6) {
            clearInterval(pollInterval);
            pollInterval = null;
            updateProgress(0, 'Servidor no responde', 'Conexión interrumpida');
            if (res.status === 502) {
              addLogLine(`[ERROR] ❌ Error 502 (Bad Gateway): El servidor de renderizado está apagado o no responde.`);
              addLogLine(`[AYUDA] 💡 Asegúrate de tener 'Iniciar_Web_Studio_Movil.bat' ejecutándose en tu PC (o que tu servicio en Render/HuggingFace haya terminado de iniciar).`);
              showToast('⚠️ Error 502: El servidor de renderizado está apagado.');
            } else {
              addLogLine(`[ERROR] ❌ Pérdida de comunicación con el servidor (HTTP ${res.status}).`);
              showToast(`⚠️ Error HTTP ${res.status}: Conexión perdida.`);
            }
            btnGenerate.disabled = false;
            btnGenerate.classList.remove('btn-disabled');
          }
          return;
        }

        consecutiveErrors = 0;
        const data = await res.json();
        updateProgress(data.progress || 10, data.step || 'Procesando...', `Progreso ${data.progress}%`);

        // Update Terminal Logs
        if (data.logs && Array.isArray(data.logs)) {
          syncLogs(data.logs);
        }

        // Milestone progression based on step & progress
        const prog = data.progress || 0;
        if (prog >= 20) {
          setMilestone(msWhisper, 'completed');
          setMilestone(msInvestigate, 'active');
        }
        if (prog >= 45) {
          setMilestone(msInvestigate, 'completed');
          setMilestone(msMemes, 'active');
        }
        if (prog >= 70) {
          setMilestone(msMemes, 'completed');
          setMilestone(msRender, 'active');
        }

        // Check completion or failure
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          pollInterval = null;
          setMilestone(msRender, 'completed');
          updateProgress(100, '¡Video generado con éxito!', '100% Completado');

          // Show Final Video
          setTimeout(() => {
            showFinalResult(data);
          }, 600);
        } else if (data.status === 'failed' || data.status === 'error') {
          clearInterval(pollInterval);
          pollInterval = null;
          updateProgress(0, 'Error durante la generación', 'Fallido');
          addLogLine(`[ERROR] ❌ ${data.error || 'Fallo durante el renderizado'}`);
          btnGenerate.disabled = false;
          btnGenerate.classList.remove('btn-disabled');
          showToast(`❌ Error: ${data.error || 'Fallo durante el renderizado'}`);
        }

      } catch (e) {
        consecutiveErrors++;
        console.warn('Poll error:', e);
        if (consecutiveErrors >= 12) {
          clearInterval(pollInterval);
          pollInterval = null;
          updateProgress(0, 'Error de conexión', 'Fallido');
          addLogLine(`[ERROR] ❌ No se pudo conectar al servidor: ${e.message}`);
          btnGenerate.disabled = false;
          btnGenerate.classList.remove('btn-disabled');
        }
      }
    }, 1500);
  }

  // 7. Show Final Video Result
  function showFinalResult(jobData) {
    btnGenerate.disabled = false;
    btnGenerate.classList.remove('btn-disabled');

    const videoUrl = buildApiUrl(jobData.video_url || `/api/video/${jobData.job_id}`);
    const downloadUrl = buildApiUrl(jobData.download_url || `/api/download/${jobData.job_id}`);

    finalVideoPlayer.src = videoUrl;
    btnDownloadVideo.href = downloadUrl;

    resultCard.style.display = 'block';
    resultCard.scrollIntoView({ behavior: 'smooth' });

    finalVideoPlayer.play().catch(() => {
      // Autoplay unmuted restriction on mobile
    });
  }

  // 8. Reset Button
  btnReset.addEventListener('click', () => {
    resultCard.style.display = 'none';
    progressCard.style.display = 'none';
    finalVideoPlayer.pause();
    finalVideoPlayer.src = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Helper Functions
  function updateProgress(percent, title, sub) {
    progressBarFill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    if (title) progressStepTitle.textContent = title;
    if (sub) progressPercentLabel.textContent = sub;
  }

  function resetMilestones() {
    [msWhisper, msInvestigate, msMemes, msRender].forEach(ms => {
      ms.className = 'milestone-item';
    });
  }

  function setMilestone(el, state) {
    if (!el) return;
    el.className = `milestone-item ${state}`;
  }

  function addLogLine(text) {
    const line = document.createElement('p');
    line.className = 'term-line';
    line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  let lastLoggedIndex = 0;
  function syncLogs(serverLogs) {
    for (let i = lastLoggedIndex; i < serverLogs.length; i++) {
      const line = document.createElement('p');
      line.className = 'term-line';
      line.textContent = serverLogs[i];
      terminalOutput.appendChild(line);
    }
    lastLoggedIndex = serverLogs.length;
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  function highlightStep(cardId) {
    const el = document.getElementById(cardId);
    if (!el) return;
    el.classList.add('pulse-highlight');
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => {
      el.classList.remove('pulse-highlight');
    }, 2000);
  }

  function setupDragAndDrop(element, onDropFiles) {
    ['dragenter', 'dragover'].forEach(eventName => {
      element.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        element.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      element.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        element.classList.remove('dragover');
      });
    });

    element.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files) {
        onDropFiles(e.dataTransfer.files);
      }
    });
  }

  function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'mobile-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('visible');
    }, 10);
    setTimeout(() => {
      toast.classList.remove('visible');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
});
