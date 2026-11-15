/**
 * Suno Studio Master v3.0 Next-Gen Studio Module
 * - Dual Waveform Timeline & 60FPS FFT Spectrum Analyzer
 * - WebAudio API Realtime Virtual Mastering Engine
 * - Zero-breaking switching with v2.5 PRO
 */

class V3StudioEngine {
  constructor() {
    this.audioCtx = null;
    this.sourceNode = null;
    this.audioElement = null;
    this.analyser = null;
    this.biquadFilters = {
      low: null,
      mid: null,
      high: null,
      watermarkLpf: null,
    };
    this.gainNode = null;
    this.isPlaying = false;
    this.isBypassed = false; // A/B bypass (Original vs Mastered)
    this.animFrameId = null;

    // Active track metadata
    this.currentAudioUrl = null;
    this.currentFilename = "미로드 (오디오 파일 필요)";
    this.audioBuffer = null;

    // Presets definitions (3-band: 100Hz / 2.8kHz / 11kHz — same as the server master chain)
    this.presets = {
      kpop: {
        name: "K-POP 펀치 & 보컬 부스트",
        eq_low: 2.5, eq_mid: 1.5, eq_high: 3.2,
        watermark: true, warmth: 0.2, stereo: 1.3
      },
      ballad: {
        name: "발라드 & 어쿠스틱 감성",
        eq_low: 1.0, eq_mid: 0.8, eq_high: 1.2,
        watermark: true, warmth: 0.4, stereo: 1.15
      },
      edm: {
        name: "클럽 EDM & 힙합 베이스 펌핑",
        eq_low: 4.0, eq_mid: 1.2, eq_high: 3.5,
        watermark: true, warmth: 0.1, stereo: 1.45
      },
      lofi: {
        name: "Lo-Fi & 레트로 빈티지",
        eq_low: 3.0, eq_mid: -1.0, eq_high: -3.0,
        watermark: true, warmth: 0.65, stereo: 0.95
      },
      flat: {
        name: "플랫 (기본값 리셋)",
        eq_low: 0, eq_mid: 0, eq_high: 0,
        watermark: true, warmth: 0.1, stereo: 1.1
      }
    };
  }

  init() {
    console.log("[v3 Studio] Engine Initializing...");
    this.audioElement = new Audio();
    this.audioElement.crossOrigin = "anonymous";
    this.audioElement.loop = true;

    this.audioElement.addEventListener("ended", () => {
      this.isPlaying = false;
      this.updatePlayBtnUi();
    });

    this.audioElement.addEventListener("timeupdate", () => {
      this.updateTimelineProgress();
    });

    this.bindEvents();
    this.initVisualizer();
  }

  initAudioContext() {
    if (this.audioCtx) return;
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this.audioCtx = new AudioContextClass();

    // Source from audio element
    this.sourceNode = this.audioCtx.createMediaElementSource(this.audioElement);

    // Filters chain
    // 1. Low Shelf (100 Hz)
    this.biquadFilters.low = this.audioCtx.createBiquadFilter();
    this.biquadFilters.low.type = "lowshelf";
    this.biquadFilters.low.frequency.value = 100;

    // 2. Mid Presence bell (2.8 kHz — matches server mid_presence_db)
    this.biquadFilters.mid = this.audioCtx.createBiquadFilter();
    this.biquadFilters.mid.type = "peaking";
    this.biquadFilters.mid.frequency.value = 2800;
    this.biquadFilters.mid.Q.value = 1.0;

    // 3. Air High Shelf (11 kHz — matches server air_band_boost_db)
    this.biquadFilters.high = this.audioCtx.createBiquadFilter();
    this.biquadFilters.high.type = "highshelf";
    this.biquadFilters.high.frequency.value = 11000;

    // 5. Suno AI Watermark LowPass Filter (18,500 Hz cutoff)
    this.biquadFilters.watermarkLpf = this.audioCtx.createBiquadFilter();
    this.biquadFilters.watermarkLpf.type = "lowpass";
    this.biquadFilters.watermarkLpf.frequency.value = 18500;
    this.biquadFilters.watermarkLpf.Q.value = 0.707;

    // Gain node
    this.gainNode = this.audioCtx.createGain();
    this.gainNode.gain.value = 1.0;

    // FFT Analyser Node (for 60fps spectrum)
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 512;
    this.analyser.smoothingTimeConstant = 0.82;

    // Routing
    this.connectDspChain();
    this.applyCurrentControlsToDsp();
  }

  connectDspChain() {
    if (!this.sourceNode) return;
    this.sourceNode.disconnect();

    if (this.isBypassed) {
      // Direct Original Sound (Bypass DSP)
      this.sourceNode.connect(this.analyser);
      this.analyser.connect(this.audioCtx.destination);
    } else {
      // Mastered Sound (Through DSP Chain)
      this.sourceNode.connect(this.biquadFilters.low);
      this.biquadFilters.low.connect(this.biquadFilters.mid);
      this.biquadFilters.mid.connect(this.biquadFilters.high);
      this.biquadFilters.high.connect(this.biquadFilters.watermarkLpf);
      this.biquadFilters.watermarkLpf.connect(this.gainNode);
      this.gainNode.connect(this.analyser);
      this.analyser.connect(this.audioCtx.destination);
    }
  }

  bindEvents() {
    // Sliders
    const sliders = [
      { id: "v3-slider-eq-low", filter: "low", valId: "v3-val-eq-low", unit: "dB" },
      { id: "v3-slider-eq-mid", filter: "mid", valId: "v3-val-eq-mid", unit: "dB" },
      { id: "v3-slider-eq-high", filter: "high", valId: "v3-val-eq-high", unit: "dB" },
    ];

    sliders.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) {
        el.addEventListener("input", (e) => {
          const val = parseFloat(e.target.value);
          const valEl = document.getElementById(s.valId);
          if (valEl) valEl.textContent = (val > 0 ? "+" : "") + val.toFixed(1) + s.unit;
          if (this.biquadFilters[s.filter]) {
            this.biquadFilters[s.filter].gain.value = val;
          }
          this.syncToV25();
        });
      }
    });

    // Watermark Cut Toggle
    const wmToggle = document.getElementById("v3-check-watermark");
    if (wmToggle) {
      wmToggle.addEventListener("change", (e) => {
        if (this.biquadFilters.watermarkLpf) {
          this.biquadFilters.watermarkLpf.frequency.value = e.target.checked ? 18500 : 22000;
        }
        this.syncToV25();
      });
    }

    // Speed Slider
    const spdSlider = document.getElementById("v3-slider-speed");
    if (spdSlider) {
      spdSlider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        const valEl = document.getElementById("v3-val-speed");
        if (valEl) valEl.textContent = val.toFixed(2) + "x (" + Math.round(val * 100) + "%)";
        if (this.audioElement) {
          this.audioElement.playbackRate = val;
        }
        this.syncToV25();
      });
    }
  }

  loadAudio(url, title = "오디오 트랙") {
    if (!url) return;
    this.currentAudioUrl = url;
    this.currentFilename = title;

    if (this.audioElement) {
      this.audioElement.src = url;
      this.audioElement.load();
    }

    const titleEl = document.getElementById("v3-track-title");
    if (titleEl) titleEl.textContent = title;

    // Fetch and draw waveform
    this.drawDualWaveforms(url);
  }

  async drawDualWaveforms(url) {
    try {
      const response = await fetch(url);
      const arrayBuffer = await response.arrayBuffer();
      const tempCtx = new (window.AudioContext || window.webkitAudioContext)();
      const decodedData = await tempCtx.decodeAudioData(arrayBuffer);
      this.audioBuffer = decodedData;
      this.renderWaveformCanvas("v3-waveform-orig", decodedData, "#06b6d4");
      this.renderWaveformCanvas("v3-waveform-master", decodedData, "#a855f7");
    } catch (err) {
      console.warn("[v3 Studio] Waveform decode notice:", err);
    }
  }

  renderWaveformCanvas(canvasId, buffer, strokeColor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width = canvas.parentElement.clientWidth || 600;
    const height = canvas.height = 70;

    ctx.clearRect(0, 0, width, height);

    const data = buffer.getChannelData(0);
    const step = Math.ceil(data.length / width);
    const amp = height / 2;

    ctx.fillStyle = strokeColor;
    ctx.beginPath();

    for (let i = 0; i < width; i++) {
      let min = 1.0;
      let max = -1.0;
      for (let j = 0; j < step; j++) {
        const datum = data[(i * step) + j];
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }
      ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
    }
  }

  togglePlay() {
    this.initAudioContext();
    if (this.audioCtx && this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }

    if (!this.audioElement.src) {
      // Check if v2.5 has audio loaded
      if (window.state && window.state.originalAudioUrl) {
        this.loadAudio(window.state.originalAudioUrl, window.state.originalFilename || "Suno Audio");
      } else {
        alert("먼저 오디오 파일을 업로드하거나 [샘플 음원 로드]를 눌러주세요!");
        return;
      }
    }

    if (this.isPlaying) {
      this.audioElement.pause();
      this.isPlaying = false;
    } else {
      this.audioElement.play().then(() => {
        this.isPlaying = true;
      }).catch(e => console.error(e));
    }
    this.updatePlayBtnUi();
  }

  updatePlayBtnUi() {
    const btn = document.getElementById("v3-btn-play");
    if (!btn) return;
    if (this.isPlaying) {
      btn.innerHTML = `<i class="fa-solid fa-pause"></i> <span>일시정지</span>`;
      btn.classList.add("bg-amber-500", "text-slate-950");
      btn.classList.remove("bg-cyan-500");
    } else {
      btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>실시간 청음</span>`;
      btn.classList.add("bg-cyan-500", "text-slate-950");
      btn.classList.remove("bg-amber-500");
    }
  }

  toggleBypass() {
    this.isBypassed = !this.isBypassed;
    this.connectDspChain();

    const btn = document.getElementById("v3-btn-bypass");
    const indicator = document.getElementById("v3-live-indicator");
    if (this.isBypassed) {
      if (btn) {
        btn.innerHTML = `<i class="fa-solid fa-ear-listen text-amber-400"></i> <span>[A] 원본 소리 청음 중</span>`;
        btn.classList.add("border-amber-500/50", "text-amber-300");
      }
      if (indicator) {
        indicator.innerHTML = `<span class="pulse-dot bg-amber-400 shadow-amber-400"></span> <span>ORIGINAL (A)</span>`;
        indicator.classList.remove("bg-emerald-500/15", "text-emerald-400", "border-emerald-500/40");
        indicator.classList.add("bg-amber-500/15", "text-amber-400", "border-amber-500/40");
      }
    } else {
      if (btn) {
        btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-cyan-400"></i> <span>[B] 마스터링 DSP 실시간 적용 중</span>`;
        btn.classList.remove("border-amber-500/50", "text-amber-300");
      }
      if (indicator) {
        indicator.innerHTML = `<span class="pulse-dot"></span> <span>LIVE MASTERED (B)</span>`;
        indicator.classList.remove("bg-amber-500/15", "text-amber-400", "border-amber-500/40");
        indicator.classList.add("bg-emerald-500/15", "text-emerald-400", "border-emerald-500/40");
      }
    }
  }

  applyPreset(presetKey) {
    const p = this.presets[presetKey];
    if (!p) return;

    // Update active chip UI
    document.querySelectorAll(".v3-preset-chip").forEach(el => el.classList.remove("active"));
    const activeChip = document.querySelector(`.v3-preset-chip[data-preset="${presetKey}"]`);
    if (activeChip) activeChip.classList.add("active");

    // Apply values to UI & DSP
    const setSlider = (id, valId, val, unit = "dB") => {
      const el = document.getElementById(id);
      if (el) el.value = val;
      const vEl = document.getElementById(valId);
      if (vEl) vEl.textContent = (val > 0 ? "+" : "") + val.toFixed(1) + unit;
    };

    setSlider("v3-slider-eq-low", "v3-val-eq-low", p.eq_low);
    setSlider("v3-slider-eq-mid", "v3-val-eq-mid", p.eq_mid);
    setSlider("v3-slider-eq-high", "v3-val-eq-high", p.eq_high);

    const wmEl = document.getElementById("v3-check-watermark");
    if (wmEl) wmEl.checked = p.watermark;

    this.applyCurrentControlsToDsp();
    this.syncToV25();
  }

  applyCurrentControlsToDsp() {
    if (!this.biquadFilters.low) return;
    const getVal = (id) => parseFloat(document.getElementById(id)?.value || 0);

    this.biquadFilters.low.gain.value = getVal("v3-slider-eq-low");
    this.biquadFilters.mid.gain.value = getVal("v3-slider-eq-mid");
    this.biquadFilters.high.gain.value = getVal("v3-slider-eq-high");

    const wmChecked = document.getElementById("v3-check-watermark")?.checked ?? true;
    this.biquadFilters.watermarkLpf.frequency.value = wmChecked ? 18500 : 22000;
  }

  initVisualizer() {
    const canvas = document.getElementById("v3-spectrum-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const render = () => {
      this.animFrameId = requestAnimationFrame(render);
      const width = canvas.width = canvas.parentElement.clientWidth || 500;
      const height = canvas.height = 140;

      ctx.clearRect(0, 0, width, height);

      // Background Grid Lines
      ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
      ctx.lineWidth = 1;
      for (let y = 20; y < height; y += 30) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      if (!this.analyser || !this.isPlaying) {
        // Idle gentle waveform wave
        ctx.strokeStyle = "rgba(6, 182, 212, 0.25)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        const t = Date.now() / 600;
        for (let x = 0; x < width; x += 3) {
          const y = height / 2 + Math.sin(x * 0.03 + t) * 8 * Math.cos(x * 0.01);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
        return;
      }

      const bufferLength = this.analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      this.analyser.getByteFrequencyData(dataArray);

      const barWidth = (width / bufferLength) * 2.2;
      let x = 0;

      // Theme-sensitive gradient
      const currentTheme = document.documentElement.getAttribute("data-theme") || "1";
      const grad = ctx.createLinearGradient(0, height, 0, 0);

      if (currentTheme === "2") {
        // Vintage Amber
        grad.addColorStop(0, "rgba(217, 119, 6, 0.2)");
        grad.addColorStop(0.5, "rgba(245, 158, 11, 0.8)");
        grad.addColorStop(1, "rgba(251, 191, 36, 1)");
      } else if (currentTheme === "3") {
        // Glass Emerald
        grad.addColorStop(0, "rgba(5, 150, 105, 0.2)");
        grad.addColorStop(0.5, "rgba(16, 185, 129, 0.8)");
        grad.addColorStop(1, "rgba(52, 211, 153, 1)");
      } else {
        // Neon Cyan / Purple
        grad.addColorStop(0, "rgba(6, 182, 212, 0.2)");
        grad.addColorStop(0.6, "rgba(59, 130, 246, 0.85)");
        grad.addColorStop(1, "rgba(168, 85, 247, 1)");
      }

      ctx.fillStyle = grad;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * (height - 15);
        ctx.fillRect(x, height - barHeight, barWidth - 1, barHeight);
        x += barWidth;
        if (x > width) break;
      }

      // Draw Suno Watermark cut line (around 18.5kHz bin)
      const wmX = width * 0.88;
      ctx.strokeStyle = "rgba(239, 68, 68, 0.6)";
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(wmX, 0);
      ctx.lineTo(wmX, height);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "rgba(239, 68, 68, 0.85)";
      ctx.font = "9px monospace";
      ctx.fillText("18.5kHz CUT", wmX - 60, 12);
    };

    render();
  }

  updateTimelineProgress() {
    if (!this.audioElement || !this.audioElement.duration) return;
    const cur = this.audioElement.currentTime;
    const dur = this.audioElement.duration;
    const percent = (cur / dur) * 100;

    const playhead = document.getElementById("v3-playhead-line");
    if (playhead) playhead.style.left = `${percent}%`;

    const timeLabel = document.getElementById("v3-timeline-time");
    if (timeLabel) {
      const fmt = (s) => {
        const m = Math.floor(s / 60);
        const sec = Math.floor(s % 60);
        return `${m}:${sec.toString().padStart(2, "0")}`;
      };
      timeLabel.textContent = `${fmt(cur)} / ${fmt(dur)}`;
    }
  }

  seekTimeline(e) {
    if (!this.audioElement || !this.audioElement.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    this.audioElement.currentTime = ratio * this.audioElement.duration;
  }

  // Synchronize v3 UI values with the real v2.5 inputs used by the server payload
  syncToV25() {
    const syncInput = (v3Id, v25Id) => {
      const v3 = document.getElementById(v3Id);
      const v25 = document.getElementById(v25Id);
      if (v3 && v25) {
        v25.value = v3.value;
        v25.dispatchEvent(new Event("input"));
      }
    };

    syncInput("v3-slider-eq-low", "eq-bass-slider");
    syncInput("v3-slider-eq-mid", "eq-mid-slider");
    syncInput("v3-slider-eq-high", "eq-air-slider");
    syncInput("v3-slider-speed", "suno-speed-slider");

    const v3Wm = document.getElementById("v3-check-watermark");
    const v25Wm = document.getElementById("toggle-dewatermark");
    if (v3Wm && v25Wm) {
      v25Wm.checked = v3Wm.checked;
      v25Wm.dispatchEvent(new Event("change"));
    }
  }

  // Pull the current v2.5 mastering values into the v3 rack when switching versions
  syncFromV25() {
    const copy = (v3Id, v25Id) => {
      const v3 = document.getElementById(v3Id);
      const v25 = document.getElementById(v25Id);
      if (v3 && v25) {
        v3.value = v25.value;
        const valEl = document.getElementById(v3Id.replace("slider", "val"));
        if (valEl && v3Id !== "v3-slider-speed") {
          const val = parseFloat(v3.value) || 0;
          valEl.textContent = (val > 0 ? "+" : "") + val.toFixed(1) + "dB";
        }
      }
    };

    copy("v3-slider-eq-low", "eq-bass-slider");
    copy("v3-slider-eq-mid", "eq-mid-slider");
    copy("v3-slider-eq-high", "eq-air-slider");
    copy("v3-slider-speed", "suno-speed-slider");

    const v3Wm = document.getElementById("v3-check-watermark");
    const v25Wm = document.getElementById("toggle-dewatermark");
    if (v3Wm && v25Wm) v3Wm.checked = v25Wm.checked;

    const spd = document.getElementById("v3-slider-speed");
    const spdVal = document.getElementById("v3-val-speed");
    if (spd && spdVal) {
      const v = parseFloat(spd.value) || 1.0;
      spdVal.textContent = v.toFixed(2) + "x (" + Math.round(v * 100) + "%)";
      if (this.audioElement) this.audioElement.playbackRate = v;
    }

    this.applyCurrentControlsToDsp();
  }

  // Trigger high quality server mastering render
  executeMasterRender() {
    this.syncToV25();
    // Switch or invoke existing mastering action in app.js
    const v25RenderBtn = document.getElementById("btn-enqueue-full-master");
    if (v25RenderBtn) {
      v25RenderBtn.click();
    } else if (typeof window.enqueueFullMastering === "function") {
      window.enqueueFullMastering();
    } else {
      alert("마스터링 파이프라인을 실행합니다.");
    }
  }
}

// Global V3 Engine Instance
window.v3Studio = new V3StudioEngine();

// Version Switcher Implementation
function switchStudioVersion(ver, save = true) {
  const rootV25 = document.getElementById("version-v25-root");
  const rootV30 = document.getElementById("version-v30-root");
  const buttons = document.querySelectorAll(".version-switch-btn");

  if (!rootV25 || !rootV30) return;

  if (ver === "v30") {
    rootV25.classList.add("hidden");
    rootV30.classList.remove("hidden");
    document.body.setAttribute("data-studio-version", "v30");

    // Sync current audio from v2.5 if available
    if (window.state && window.state.originalAudioUrl && (!window.v3Studio.currentAudioUrl || window.v3Studio.currentAudioUrl !== window.state.originalAudioUrl)) {
      window.v3Studio.loadAudio(window.state.originalAudioUrl, window.state.originalFilename || "Suno 오디오 트랙");
    }
    // Mirror the current v2.5 mastering controls into the v3 rack
    window.v3Studio.syncFromV25();
  } else {
    rootV25.classList.remove("hidden");
    rootV30.classList.add("hidden");
    document.body.setAttribute("data-studio-version", "v25");
  }

  buttons.forEach(btn => {
    if (btn.getAttribute("data-version") === ver) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  if (save) {
    localStorage.setItem("antigravity_studio_version", ver);
  }
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.v3Studio.init();

  const savedVer = localStorage.getItem("antigravity_studio_version") || "v25";
  switchStudioVersion(savedVer, false);
});
