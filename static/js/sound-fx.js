/**
 * FitTrack Procedural Web Audio Sound Engine
 * Zero external audio files — 100% Web Audio API synthesis.
 */
(function () {
  const STORAGE_KEY = "fittrack_sound_enabled";
  let audioCtx = null;
  let enabled = false;

  try {
    enabled = localStorage.getItem(STORAGE_KEY) === "1";
  } catch (_) {
    enabled = false;
  }

  function ensureContext() {
    if (!audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return null;
      audioCtx = new AudioCtx();
    }
    if (audioCtx.state === "suspended") {
      audioCtx.resume().catch(() => {});
    }
    return audioCtx;
  }

  function syncToggleButtons() {
    document.querySelectorAll("[data-sound-toggle]").forEach((btn) => {
      btn.setAttribute("aria-pressed", enabled ? "true" : "false");
      btn.classList.toggle("is-sound-on", enabled);
      const label = btn.querySelector("[data-sound-label]");
      const icon = btn.querySelector("i");
      if (label) {
        label.textContent = enabled ? "SOUND ON" : "SOUND OFF";
      }
      if (icon) {
        icon.className = enabled
          ? "bi bi-volume-up-fill"
          : "bi bi-volume-mute-fill";
      }
    });
  }

  function setEnabled(nextState) {
    enabled = Boolean(nextState);
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
    } catch (_) {}
    syncToggleButtons();
    if (enabled) {
      ensureContext();
      playTone(520, 0.08, "triangle", 0.08);
      setTimeout(() => playTone(780, 0.11, "triangle", 0.08), 65);
    }
  }

  function playTone(freq, duration = 0.1, type = "sine", volume = 0.08, slideTo = null) {
    if (!enabled) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    if (slideTo) {
      osc.frequency.exponentialRampToValueAtTime(slideTo, now + duration);
    }

    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, volume), now + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + duration + 0.02);
  }

  function playFootstep(speedRatio = 0.5) {
    if (!enabled) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const bufferSize = Math.floor(ctx.sampleRate * 0.045);
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.28));
    }

    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(240 + speedRatio * 260, now);
    filter.Q.setValueAtTime(1.6, now);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.06 + speedRatio * 0.05, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    noise.start(now);
  }

  function playClick() {
    playTone(620, 0.055, "triangle", 0.05, 420);
  }

  function playHoverTick() {
    playTone(880, 0.03, "sine", 0.022, 1020);
  }

  function playStagePass(stageIdx = 1) {
    const base = 440 + stageIdx * 55;
    playTone(base, 0.11, "triangle", 0.08);
    setTimeout(() => playTone(base * 1.25, 0.14, "sine", 0.075), 70);
  }

  function playCountdownBeep(isGo = false) {
    if (isGo) {
      playTone(880, 0.28, "sawtooth", 0.09, 1046);
      setTimeout(() => playTone(1318, 0.25, "triangle", 0.08), 80);
    } else {
      playTone(523.25, 0.14, "square", 0.06);
    }
  }

  function playSlotTick(step = 0) {
    playTone(360 + (step % 8) * 55, 0.045, "triangle", 0.05);
  }

  function playFanfare() {
    if (!enabled) return;
    const notes = [523.25, 659.25, 783.99, 1046.5];
    notes.forEach((n, idx) => {
      setTimeout(() => playTone(n, 0.22, "triangle", 0.09), idx * 85);
    });
  }

  function playCrowdCheer() {
    if (!enabled) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const dur = 0.55;
    const bufferSize = Math.floor(ctx.sampleRate * dur);
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      const env = Math.sin((i / bufferSize) * Math.PI);
      data[i] = (Math.random() * 2 - 1) * env * 0.5;
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(950, now);
    filter.frequency.linearRampToValueAtTime(1450, now + dur * 0.5);
    filter.Q.setValueAtTime(0.9, now);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.05, now);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    noise.start(now);
  }

  window.FitTrackSound = {
    isEnabled: () => enabled,
    toggle: () => setEnabled(!enabled),
    setEnabled,
    playClick,
    playHoverTick,
    playFootstep,
    playStagePass,
    playCountdownBeep,
    playSlotTick,
    playFanfare,
    playCrowdCheer,
  };

  document.addEventListener("DOMContentLoaded", function () {
    syncToggleButtons();
    document.querySelectorAll("[data-sound-toggle]").forEach((btn) => {
      btn.addEventListener("click", function () {
        setEnabled(!enabled);
      });
    });
  });
})();
