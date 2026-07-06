const $ = id => document.getElementById(id);
let loadedVideoFps = '25';
const state = (id, active) => {
  const el = $(id);
  el.textContent = active ? 'работает' : 'остановлен';
  el.className = active ? 'ok' : 'bad';
};

async function refresh() {
  try {
    const data = await fetch('/cgi-bin/status.cgi', {cache: 'no-store'}).then(r => r.json());
    $('ip').textContent = data.ip;
    $('uptime').textContent = data.uptime;
    state('rtspState', data.rtsp);
    state('onvifState', data.onvif);
    state('audioState', data.audio);
    state('audioRtspState', data.audioRtsp);
    state('recordState', data.recording);
    state('ftpState', data.ftp);
    if ($('fpsState')) $('fpsState').textContent = `${data.videoFps || loadedVideoFps || '—'} FPS`;
    $('cpuState').textContent = data.cpuPercent === null || data.cpuPercent === undefined
      ? `load ${data.cpuLoad || '—'}`
      : `${data.cpuPercent}% / load ${data.cpuLoad || '—'}`;
    $('memState').textContent = data.memTotalKb
      ? `${data.memUsedPercent}% (${Math.round(data.memUsedKb / 1024)}/${Math.round(data.memTotalKb / 1024)} MB)`
      : '—';
    const rtsp = `rtsp://${data.ip}:8554/mainstream`;
    const audioRtsp = data.audioRtspUrl || rtsp;
    $('rtspUrl').textContent = rtsp;
    $('audioRtspUrl').textContent = audioRtsp;
    $('onvifUrl').textContent = `http://${data.ip}:${data.onvifPort}/onvif/device_service`;
    $('ftpUrl').textContent = `ftp://${data.ip}:${data.ftpPort}/`;
    $('rtsp').dataset.url = rtsp;
  } catch (_) {
    $('ip').textContent = 'камера не отвечает';
  }
}

$('rtsp').addEventListener('click', async event => {
  event.preventDefault();
  await navigator.clipboard.writeText(event.currentTarget.dataset.url);
  event.currentTarget.textContent = 'RTSP скопирован';
});

const updateMessage = $('updateMessage');
$('uploadUpdate').addEventListener('click', async () => {
  const file = $('updateFile').files[0];
  if (!file) {
    updateMessage.textContent = 'Сначала выбери ZIP-файл.';
    return;
  }
  updateMessage.textContent = 'Загружаю...';
  const result = await fetch('/cgi-bin/update.cgi?action=upload', {
    method: 'POST',
    headers: {'Content-Type': 'application/zip'},
    body: file
  }).then(r => r.json());
  updateMessage.textContent = result.ok ? `Загружено ${result.bytes} байт.` : `Ошибка: ${result.error}`;
});

$('installUpdate').addEventListener('click', async () => {
  updateMessage.textContent = 'Запускаю установку...';
  const result = await fetch('/cgi-bin/update.cgi?action=install', {method: 'POST'}).then(r => r.json());
  updateMessage.textContent = result.ok ? 'Установка запущена. Через минуту можно перезагрузить.' : `Ошибка: ${result.error}`;
});

$('rebootCamera').addEventListener('click', async () => {
  updateMessage.textContent = 'Перезагружаю камеру...';
  await fetch('/cgi-bin/update.cgi?action=reboot', {method: 'POST'}).catch(() => {});
});

async function loadSettings() {
  try {
    const data = await fetch('/cgi-bin/settings.cgi', {cache: 'no-store'}).then(r => r.json());
    $('mediaEnabled').checked = data.mediaEnabled;
    $('backchannelEnabled').checked = data.backchannelEnabled;
    $('ftpEnabled').checked = data.ftpEnabled;
    $('ptzEnabled').checked = data.ptzEnabled;
    $('ledIndicator').checked = data.ledIndicator;
    $('fullColor').checked = data.fullColor;
    $('wdrEnabled').checked = data.wdrEnabled;
    $('watermarkEnabled').checked = data.watermarkEnabled;
    $('videoFlip').checked = data.videoFlip;
    $('nightVision').value = data.nightVision;
    $('timezone').value = data.timezone;
    $('audioStartDelay').value = data.audioStartDelay;
    $('backchannelStartDelay').value = data.backchannelStartDelay;
    $('backchannelRestartDelay').value = data.backchannelRestartDelay;
    loadedVideoFps = data.videoFps || '25';
    $('videoFps').value = loadedVideoFps;
    if ($('fpsState')) $('fpsState').textContent = `${loadedVideoFps} FPS`;
    $('settingsMessage').textContent = 'Настройки загружены.';
  } catch (error) {
    $('settingsMessage').textContent = `Не удалось загрузить настройки: ${error.message}`;
  }
}

$('saveSettings').addEventListener('click', async () => {
  const selectedVideoFps = $('videoFps').value;
  const body = [
    `MEDIA_ENABLE=${$('mediaEnabled').checked ? 'on' : 'off'}`,
    `BACKCHANNEL_ENABLE=${$('backchannelEnabled').checked ? 'on' : 'off'}`,
    `FTP_ENABLE=${$('ftpEnabled').checked ? 'on' : 'off'}`,
    `PTZ_ENABLE=${$('ptzEnabled').checked ? 'on' : 'off'}`,
    `LED_INDICATOR=${$('ledIndicator').checked ? 'on' : 'off'}`,
    `FULL_COLOR=${$('fullColor').checked ? 'on' : 'off'}`,
    `NIGHT_VISION=${$('nightVision').value}`,
    `WDR=${$('wdrEnabled').checked ? 'on' : 'off'}`,
    `WATERMARK=${$('watermarkEnabled').checked ? 'on' : 'off'}`,
    `VIDEO_FLIP=${$('videoFlip').checked ? 'on' : 'off'}`,
    `TIMEZONE=${$('timezone').value}`,
    `AUDIO_START_DELAY=${$('audioStartDelay').value}`,
    `BACKCHANNEL_START_DELAY=${$('backchannelStartDelay').value}`,
    `BACKCHANNEL_RESTART_DELAY=${$('backchannelRestartDelay').value}`,
    `VIDEO_FPS=${selectedVideoFps}`
  ].join('\n');
  $('settingsMessage').textContent = 'Сохраняю…';
  try {
    const result = await fetch('/cgi-bin/settings.cgi', {method: 'POST', headers: {'Content-Type': 'text/plain'}, body}).then(r => r.json());
    if (!result.ok) throw new Error(result.error || 'ошибка сохранения');
    if (selectedVideoFps !== loadedVideoFps) {
      $('settingsMessage').textContent = `Сохранил настройки. Применяю ${selectedVideoFps} FPS, видео на несколько секунд пропадёт…`;
      const fpsResult = await fetch('/cgi-bin/fps.cgi', {
        method: 'POST',
        headers: {'Content-Type': 'text/plain'},
        body: `FPS=${selectedVideoFps}`
      }).then(r => r.json());
      if (!fpsResult.ok) throw new Error(fpsResult.error || 'ошибка применения FPS');
      loadedVideoFps = fpsResult.fps || selectedVideoFps;
      $('settingsMessage').textContent = `Сохранено. FPS ${loadedVideoFps} применён.`;
    } else {
      $('settingsMessage').textContent = result.message;
    }
    await loadSettings();
    await refresh();
  } catch (error) {
    $('settingsMessage').textContent = `Ошибка: ${error.message}`;
  }
});

let talkContext, talkSource, talkProcessor, talkStream;
let talkRemainder = [];
let talkSendChain = Promise.resolve();

function linearToAlaw(sample) {
  let s = Math.round(Math.max(-1, Math.min(1, sample)) * 32767);
  let sign = 0x80;
  if (s < 0) {
    sign = 0x00;
    s = -s;
  }
  s = Math.min(32635, s);
  let compressed;
  if (s >= 256) {
    let exponent = 7;
    for (let mask = 0x4000; exponent > 0 && !(s & mask); mask >>= 1) exponent--;
    const mantissa = (s >> (exponent + 3)) & 0x0f;
    compressed = sign | (exponent << 4) | mantissa;
  } else {
    compressed = sign | (s >> 4);
  }
  return compressed ^ 0x55;
}

function linearToMulaw(sample) {
  let s = Math.round(Math.max(-1, Math.min(1, sample)) * 32767);
  const sign = s < 0 ? 0x80 : 0;
  if (s < 0) s = -s;
  s = Math.min(32635, s) + 132;
  let exponent = 7;
  for (let mask = 0x4000; exponent > 0 && !(s & mask); mask >>= 1) exponent--;
  const mantissa = (s >> (exponent + 3)) & 0x0f;
  return (~(sign | (exponent << 4) | mantissa)) & 0xff;
}

function resample(input, sourceRate, targetRate) {
  if (sourceRate === targetRate) return input;
  const ratio = sourceRate / targetRate;
  const length = Math.floor(input.length / ratio);
  const output = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.max(start + 1, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end && j < input.length; j++) sum += input[j];
    output[i] = sum / (end - start);
  }
  return output;
}

function sendTalkChunk(bytes) {
  if (!bytes.length) return talkSendChain;
  const payload = bytes.slice();
  talkSendChain = talkSendChain.then(async () => {
    const response = await fetch('/cgi-bin/talk.cgi', {
      method: 'POST',
      headers: {'Content-Type': 'audio/PCMU'},
      body: payload
    });
    if (!response.ok) throw new Error(`talk HTTP ${response.status}`);
  }).catch(error => {
    $('talkMessage').textContent = `Ошибка передачи: ${error.message}`;
  });
  return talkSendChain;
}

async function startTalk() {
  $('talkMessage').textContent = 'Запрашиваю микрофон...';
  talkStream = await navigator.mediaDevices.getUserMedia({
    audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}
  });
  talkContext = new AudioContext();
  talkRemainder = [];
  talkSendChain = Promise.resolve();
  talkSource = talkContext.createMediaStreamSource(talkStream);
  talkProcessor = talkContext.createScriptProcessor(2048, 1, 1);
  talkRemainder = [];
  talkProcessor.onaudioprocess = event => {
    const input = event.inputBuffer.getChannelData(0);
    const samples = resample(input, talkContext.sampleRate, 8000);
    const encoded = new Uint8Array(samples.length);
    for (let i = 0; i < samples.length; i++) encoded[i] = linearToMulaw(samples[i]);
    talkRemainder.push(...encoded);
    while (talkRemainder.length >= 1600) {
      sendTalkChunk(new Uint8Array(talkRemainder.splice(0, 1600)));
    }
  };
  talkSource.connect(talkProcessor);
  talkProcessor.connect(talkContext.destination);
  $('talkMessage').textContent = 'Говори — звук отправляется в камеру.';
}

async function stopTalk() {
  if (talkRemainder.length) {
    sendTalkChunk(new Uint8Array(talkRemainder.splice(0)));
  }
  await talkSendChain;
  if (talkProcessor) talkProcessor.disconnect();
  if (talkSource) talkSource.disconnect();
  if (talkStream) talkStream.getTracks().forEach(track => track.stop());
  if (talkContext) await talkContext.close();
  talkContext = talkSource = talkProcessor = talkStream = null;
  $('talkMessage').textContent = 'Разговор остановлен.';
}

const talkButton = $('talkButton');
if (talkButton) {
talkButton.addEventListener('pointerdown', async event => {
  event.preventDefault();
  if (!navigator.mediaDevices?.getUserMedia) {
    $('talkMessage').textContent = 'Браузер не даёт доступ к микрофону. Нужен HTTPS или локальный HTTP.';
    return;
  }
  try {
    await startTalk();
    talkButton.textContent = '🔴 Говорю... отпусти чтобы остановить';
  } catch (error) {
    $('talkMessage').textContent = `Ошибка микрофона: ${error.message}`;
  }
});

['pointerup', 'pointercancel', 'pointerleave'].forEach(name => talkButton.addEventListener(name, async () => {
  if (!talkContext) return;
  talkButton.textContent = '🎙️ Удерживать и говорить';
  await stopTalk();
}));
}

refresh();
loadSettings();
setInterval(refresh, 5000);
