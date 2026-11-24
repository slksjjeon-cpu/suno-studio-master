/**
 * Suno AI De-Watermark & Pro Mastering Studio - Client Application
 * Features:
 * - 4-Step Guided Wizard Workflow with Dimmed State Management
 * - Dedicated Section-Only Playback with Loop Support & Visual Playhead
 * - Robust Octave-Locked Tempo Acceleration Diagnostic Dashboard
 * - Ultra-Fast Previews & A/B Comparison Master Player
 */

const state = {
  currentStep: 1, // 1: Upload, 2: Select Section, 3: Mastering Options, 4: Compare & Export
  audio: null,
  audioElement: null,
  isPlayingSection: false,
  sectionTimer: null,
  duration: 0,
  selectedSegment: {
    start: 0.0,
    duration: 15.0
  },
  draftIndex: 0,
  alphabets: ["A", "B", "C", "D", "E", "F"],
  jobs: [],
  cardPlayers: {},
  activeABCardId: null,
  smartRecommendations: null,
  // 3-Way Instant Audio Monitor State (v3.5 Ultimate)
  monitorSource: 'B', // 'A': Original, 'B': Live DSP Preview (중간 사운드), 'C': Rendered Master (완성 마스터)
  webAudioDsp: {
    ctx: null,
    sourceNode: null,
    lowShelf: null,
    midPeak: null,
    airShelf: null,
    compressor: null,
    masterGain: null,
    bypassGain: null,
    isInitialized: false
  },
  lastRenderedMasterUrl: null,
  lastRenderedMasterName: null,
  renderedMasterAudio: null,
  humBackupParams: null
};

const dom = {
  // Navigation & Step Indicators
  stepNav1: document.getElementById("step-nav-1"),
  stepNav2: document.getElementById("step-nav-2"),
  stepNav3: document.getElementById("step-nav-3"),
  stepNav4: document.getElementById("step-nav-4"),
  stepGuideText: document.getElementById("step-guide-text"),

  // Panels
  panelStep1: document.getElementById("panel-step-1"),
  panelStep2: document.getElementById("panel-step-2"),
  panelStep3: document.getElementById("panel-step-3"),
  panelStep4: document.getElementById("panel-step-4"),

  // Step 1: Upload & Diagnostics
  sunoUrlInput: document.getElementById("suno-url-input"),
  btnFetchSuno: document.getElementById("btn-fetch-suno"),
  btnPasteClipboard: document.getElementById("btn-paste-clipboard"),
  sunoLinkDetectBadge: document.getElementById("suno-link-detect-badge"),
  dropzone: document.getElementById("dropzone"),
  audioInput: document.getElementById("audio-input"),
  btnLoadDemo: document.getElementById("btn-load-demo"),
  analysisStatusPill: document.getElementById("analysis-status-pill"),
  analysisProgressBox: document.getElementById("analysis-progress-box"),
  analysisPercentText: document.getElementById("analysis-percent-text"),
  analysisProgressBar: document.getElementById("analysis-progress-bar"),
  analysisStageText: document.getElementById("analysis-stage-text"),
  analysisEtaText: document.getElementById("analysis-eta-text"),
  diagContainer: document.getElementById("diag-container"),
  tempoDriftBadge: document.getElementById("tempo-drift-badge"),
  diagStartBpm: document.getElementById("diag-start-bpm"),
  diagEndBpm: document.getElementById("diag-end-bpm"),
  diagDriftRate: document.getElementById("diag-drift-rate"),
  diagTempoDesc: document.getElementById("diag-tempo-desc"),
  watermarkBadge: document.getElementById("watermark-badge"),
  diagWatermarkConf: document.getElementById("diag-watermark-conf"),
  diagLufs: document.getElementById("diag-lufs"),
  diagDuration: document.getElementById("diag-duration"),

  // Composite Multi-Filter Watermark Matrix
  wmFilterCarrier: document.getElementById("wm-filter-carrier"),
  wmFilterPhase: document.getElementById("wm-filter-phase"),
  wmFilterShelf: document.getElementById("wm-filter-shelf"),
  wmFilterPeriod: document.getElementById("wm-filter-period"),
  wmCompositeSummary: document.getElementById("wm-composite-summary"),
  smartRecCard: document.getElementById("smart-rec-card"),
  smartRecSummary: document.getElementById("smart-rec-summary"),

  // Step 2: Waveform & Section Playback
  waveformContainer: document.getElementById("waveform-container"),
  waveformCanvas: document.getElementById("waveform-canvas"),
  selectionOverlay: document.getElementById("selection-overlay"),
  playheadLine: document.getElementById("playhead-line"),
  btnPlaySection: document.getElementById("btn-play-section"),
  iconPlaySection: document.getElementById("icon-play-section"),
  textPlaySection: document.getElementById("text-play-section"),
  toggleLoopSection: document.getElementById("toggle-loop-section"),
  audioTimeCurrent: document.getElementById("audio-time-current"),
  audioTimeTotal: document.getElementById("audio-time-total"),
  selectionSummary: document.getElementById("selection-summary"),
  startTimeSlider: document.getElementById("start-time-slider"),
  startTimeVal: document.getElementById("start-time-val"),
  durationSlider: document.getElementById("duration-slider"),
  durationVal: document.getElementById("duration-val"),
  btnGotoStep3: document.getElementById("btn-goto-step-3"),

  // Step 3: Mastering Console
  toggleDewatermark: document.getElementById("toggle-dewatermark"),
  toggleTempoStabilize: document.getElementById("toggle-tempo-stabilize"),

  // Suno Audio Speed Controller
  btnSpeedPillMenu: document.getElementById("btn-speed-pill-menu"),
  speedPresetDropdown: document.getElementById("speed-preset-dropdown"),
  btnSunoSpeedReset: document.getElementById("btn-suno-speed-reset"),
  btnSpeedThumbPlay: document.getElementById("btn-speed-thumb-play"),
  iconSpeedThumbPlay: document.getElementById("icon-speed-thumb-play"),
  sunoSpeedTrackName: document.getElementById("suno-speed-track-name"),
  sunoSpeedTime: document.getElementById("suno-speed-time"),
  sunoSpeedValDisplay: document.getElementById("suno-speed-val-display"),
  sunoSpeedSlider: document.getElementById("suno-speed-slider"),
  btnSpeedStepDown: document.getElementById("btn-speed-step-down"),
  btnSpeedStepUp: document.getElementById("btn-speed-step-up"),
  sunoSpeedEndingCalc: document.getElementById("suno-speed-ending-calc"),
  sunoSpeedSeekSlider: document.getElementById("suno-speed-seek-slider"),
  sunoSpeedSeekTimeDisplay: document.getElementById("suno-speed-seek-time-display"),
  btnSyncSectionToSpeed: document.getElementById("btn-sync-section-to-speed"),
  btnExportSpeedMp4: document.getElementById("btn-export-speed-mp4"),
  toggleKeepPitch: document.getElementById("toggle-keep-pitch"),

  sunoPitchSlider: document.getElementById("suno-pitch-slider"),
  sunoPitchValDisplay: document.getElementById("suno-pitch-val-display"),
  btnPitchStepDown: document.getElementById("btn-pitch-step-down"),
  btnPitchStepUp: document.getElementById("btn-pitch-step-up"),
  btnPitchStepSemitoneDown: document.getElementById("btn-pitch-step-semitone-down"),
  btnPitchStepSemitoneUp: document.getElementById("btn-pitch-step-semitone-up"),
  btnPitchReset: document.getElementById("btn-pitch-reset"),
  btnPitchPreviewAudition: document.getElementById("btn-pitch-preview-audition"),

  masteringTargetSelect: document.getElementById("mastering-target-select"),
  toggleAutoLevel: document.getElementById("toggle-auto-level"),
  eqBassSlider: document.getElementById("eq-bass-slider"),
  eqBassVal: document.getElementById("eq-bass-val"),
  eqMidSlider: document.getElementById("eq-mid-slider"),
  eqMidVal: document.getElementById("eq-mid-val"),
  eqAirSlider: document.getElementById("eq-air-slider"),
  eqAirVal: document.getElementById("eq-air-val"),
  stereoSlider: document.getElementById("stereo-slider"),
  stereoVal: document.getElementById("stereo-val"),
  warmthSlider: document.getElementById("warmth-slider"),
  warmthVal: document.getElementById("warmth-val"),
  draftNameInput: document.getElementById("draft-name-input"),
  btnEnqueueFullMaster: document.getElementById("btn-enqueue-full-master"),
  textEnqueueFullMaster: document.getElementById("text-enqueue-full-master"),
  btnEnqueuePreview: document.getElementById("btn-enqueue-preview"),
  badgeCurrentRenderSpeed: document.getElementById("badge-current-render-speed"),
  btnExportSpeedAudio: document.getElementById("btn-export-speed-audio"),

  // Speech bubble recommendation tips
  tipRecTempo: document.getElementById("tip-rec-tempo"),
  tipRecLufs: document.getElementById("tip-rec-lufs"),
  tipRecAutolevel: document.getElementById("tip-rec-autolevel"),
  tipRecBass: document.getElementById("tip-rec-bass"),
  tipRecMid: document.getElementById("tip-rec-mid"),
  tipRecAir: document.getElementById("tip-rec-air"),
  tipRecWidth: document.getElementById("tip-rec-width"),
  tipRecWarmth: document.getElementById("tip-rec-warmth"),

  // Step 4: Comparison & Queue
  queueBadge: document.getElementById("queue-badge"),
  activeJobBox: document.getElementById("active-job-box"),
  activeJobName: document.getElementById("active-job-name"),
  activeJobPercent: document.getElementById("active-job-percent"),
  activeJobBar: document.getElementById("active-job-bar"),
  activeJobMsg: document.getElementById("active-job-msg"),
  draftsCountBadge: document.getElementById("drafts-count-badge"),
  draftsContainer: document.getElementById("drafts-container"),
  draftsEmptyState: document.getElementById("drafts-empty-state")
};

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initAudioElement();
  setupEventListeners();
  setWorkflowStep(1); // Start strictly at Step 1 (Dimmed others)
  startQueuePolling();
  initStudioVersionInfo();
});

// =========================================================================
// STUDIO VERSION & LAST UPDATE DISPLAY SYSTEM
// =========================================================================
async function initStudioVersionInfo() {
  const DEFAULT_VERSION = "v3.6.0";
  const DEFAULT_UPDATED = "2026.11.23 00:15";

  const applyVersionData = (data) => {
    const ver = data.version || DEFAULT_VERSION;
    const updatedAt = data.updated_at || DEFAULT_UPDATED;
    const dateStr = data.updated_date || updatedAt.split(" ")[0] || "2026.11.23";
    const timeStr = data.updated_time || (updatedAt.split(" ")[1] || "00:15");

    // 1. Classic Header Tags
    document.querySelectorAll(".studio-version-tag").forEach(el => {
      el.textContent = ver;
    });
    document.querySelectorAll(".studio-updated-tag").forEach(el => {
      el.innerHTML = `<i class="fa-regular fa-clock text-cyan-400 text-[10px]"></i> <span class="font-semibold text-slate-300">최종 업데이트: ${updatedAt}</span>`;
      el.title = `최종 업데이트 일시: ${updatedAt} (${data.timezone || 'KST'})`;
    });

    // 2. Modern Workspace Shell Tags
    const brandVer = document.getElementById("ws-brand-ver");
    if (brandVer) brandVer.textContent = ver;

    const wsVerNum = document.getElementById("ws-ver-num");
    if (wsVerNum) wsVerNum.textContent = ver;

    const wsVerDate = document.getElementById("ws-ver-date");
    if (wsVerDate) wsVerDate.textContent = `· ${updatedAt}`;

    const wsSidebarVer = document.getElementById("ws-sidebar-ver");
    if (wsSidebarVer) wsSidebarVer.textContent = ver;

    const wsSidebarUpdated = document.getElementById("ws-sidebar-updated");
    if (wsSidebarUpdated) {
      wsSidebarUpdated.innerHTML = `<i class="fa-regular fa-clock" style="color:#06b6d4; font-size:9.5px;"></i> <span>업데이트: ${updatedAt}</span>`;
    }

    const wsFooterVer = document.getElementById("ws-footer-ver");
    if (wsFooterVer) wsFooterVer.textContent = ver;

    const wsFooterUpdated = document.getElementById("ws-footer-updated");
    if (wsFooterUpdated) {
      wsFooterUpdated.textContent = `최종 업데이트: ${updatedAt} (${data.timezone || 'KST'}) / 로컬 작업 공간`;
    }

    // 3. Document Title
    if (document.title && !document.title.includes(ver)) {
      document.title = `Suno Studio Master ${ver} (업데이트: ${updatedAt}) - ITU-R BS.1770-4 & AI MV Studio`;
    }
  };

  try {
    const res = await fetch("/api/version", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      applyVersionData(data);
    } else {
      applyVersionData({ version: DEFAULT_VERSION, updated_at: DEFAULT_UPDATED });
    }
  } catch (e) {
    applyVersionData({ version: DEFAULT_VERSION, updated_at: DEFAULT_UPDATED });
  }
}

// =========================================================================
// UI THEME SWITCHER (1: Cyber Neon, 2: Amber Gold, 3: Emerald Matrix)
// =========================================================================
function switchUiTheme(themeId) {
  const validThemes = ["1", "2", "3"];
  let theme = validThemes.includes(String(themeId)) ? String(themeId) : "1";
  
  // Strict ban on brown Theme 2 in Modern Workspace
  if (theme === "2" || document.body?.classList.contains("workspace-modern")) {
    theme = "1";
  }
  
  document.documentElement.setAttribute("data-theme", theme);
  document.body.setAttribute("data-theme", theme);
  try {
    localStorage.setItem("antigravity_studio_ui_theme", theme);
  } catch (e) {}

  document.querySelectorAll(".theme-switch-btn").forEach(btn => {
    if (btn.dataset.theme === theme) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}
window.switchUiTheme = switchUiTheme;

function initTheme() {
  try {
    localStorage.setItem("antigravity_studio_ui_theme", "1");
  } catch (e) {}
  switchUiTheme("1");
}

// Manage 4-Step Guided Wizard State & Dimming
function setWorkflowStep(step) {
  state.currentStep = step;

  // Update Nav Indicators
  [dom.stepNav1, dom.stepNav2, dom.stepNav3, dom.stepNav4].forEach((nav, idx) => {
    const num = idx + 1;
    if (num < step) {
      nav.className = "step-indicator-item completed";
    } else if (num === step) {
      nav.className = "step-indicator-item active";
    } else {
      nav.className = "step-indicator-item";
    }
  });

  // Guide message
  const guideMessages = {
    1: "👉 1단계: Suno 음원을 업로드하거나 상단의 [테스트 음원 불러오기]를 눌러주세요.",
    2: "👉 2단계: 파형에서 원하는 미리듣기 구간(10~15초)을 선택하고 [선택 구간만 재생]으로 들어보세요.",
    3: "👉 3단계: 디워터마킹 및 템포 평탄화, 마스터링 음압을 설정하고 [미리듣기 렌더링]을 실행하세요.",
    4: "👉 4단계: 원본과 마스터링 결과를 비교 청음하고, 마음에 들면 완곡 전체 마스터링을 진행하세요!"
  };
  dom.stepGuideText.textContent = guideMessages[step] || "";

  // Apply Dimmed & Active CSS classes to panels
  if (step === 1) {
    dom.panelStep1.className = "daw-card step-active";
    dom.panelStep2.className = "daw-card step-dimmed";
    dom.panelStep3.className = "daw-card step-dimmed";
    dom.panelStep4.className = "daw-card flex-1 step-dimmed flex flex-col min-h-[820px]";
  } else if (step === 2) {
    dom.panelStep1.className = "daw-card step-completed-dimmed";
    dom.panelStep2.className = "daw-card step-active";
    dom.panelStep3.className = "daw-card step-dimmed";
    dom.panelStep4.className = "daw-card flex-1 step-dimmed flex flex-col min-h-[820px]";
  } else if (step === 3) {
    dom.panelStep1.className = "daw-card step-completed-dimmed";
    dom.panelStep2.className = "daw-card step-completed-dimmed";
    dom.panelStep3.className = "daw-card step-active";
    dom.panelStep4.className = "daw-card flex-1 step-dimmed flex flex-col min-h-[820px]";
    updateSpeedBadge();
  } else if (step >= 4) {
    // Focus Mode: Dim Steps 1, 2, 3 so Step 4 stands out with zero visual distraction
    dom.panelStep1.className = "daw-card step-completed-dimmed";
    dom.panelStep2.className = "daw-card step-completed-dimmed";
    dom.panelStep3.className = "daw-card step-completed-dimmed";
    dom.panelStep4.className = "daw-card flex-1 step-active flex flex-col min-h-[820px] ring-2 ring-emerald-500/30 shadow-2xl shadow-emerald-950/40";
  }
}

function initAudioElement() {
  state.audioElement = new Audio();
  state.audioElement.crossOrigin = "anonymous";
  
  // Real-time tracking of audio playback & Suno speed card sync
  state.audioElement.addEventListener("timeupdate", () => {
    if (!state.duration) return;

    const cur = state.audioElement.currentTime;

    // Live update Suno Speed card time display (00:00 / 04:10)
    if (dom.sunoSpeedTime) {
      const curStr = formatTime(cur);
      const totStr = state.audio?.duration_str || formatTime(state.duration);
      dom.sunoSpeedTime.textContent = `${curStr} / ${totStr}`;
    }

    // Sync preview seek slider position
    if (dom.sunoSpeedSeekSlider && !dom.sunoSpeedSeekSlider.matches(":active")) {
      const pct = (cur / state.duration) * 100;
      dom.sunoSpeedSeekSlider.value = pct.toFixed(1);
      if (dom.sunoSpeedSeekTimeDisplay) {
        dom.sunoSpeedSeekTimeDisplay.textContent = `${formatTime(cur)} / ${state.audio?.duration_str || formatTime(state.duration)}`;
      }
    }

    // Update playhead on waveform
    updatePlayheadPosition(cur);

    // Section Boundary Enforcement if in section playback mode
    if (state.isPlayingSection) {
      const start = state.selectedSegment.start;
      const end = start + state.selectedSegment.duration;

      if (cur >= end) {
        if (dom.toggleLoopSection.checked) {
          // Loop back to start of section
          state.audioElement.currentTime = start;
        } else {
          // Stop playback
          stopSectionPlayback();
        }
      }
    }
  });

  state.audioElement.addEventListener("ended", () => {
    stopSectionPlayback();
    if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-play text-white text-xs";
  });

  state.audioElement.addEventListener("pause", () => {
    if (!state.audioElement.seeking) {
      state.isPlayingSection = false;
      updatePlaySectionButtonUI(false);
      if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-play text-white text-xs";
    }
  });

  state.audioElement.addEventListener("play", () => {
    if (state.webAudioDsp.ctx && state.webAudioDsp.ctx.state === "suspended") {
      state.webAudioDsp.ctx.resume();
    }
    if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-pause text-white text-xs";
  });
}

// =========================================================================
// 3-WAY INSTANT AUDIO AUDITION MONITOR & WEB AUDIO LIVE DSP (v3.5 Ultimate)
// =========================================================================
function initLiveDspChain() {
  if (state.webAudioDsp.isInitialized) return;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    state.webAudioDsp.ctx = ctx;

    const sourceNode = ctx.createMediaElementSource(state.audioElement);
    state.webAudioDsp.sourceNode = sourceNode;

    // Filters for Live Intermediate DSP Preview (중간 사운드 실시간 필터 체인)
    const lowShelf = ctx.createBiquadFilter();
    lowShelf.type = "lowshelf";
    lowShelf.frequency.value = 100;
    lowShelf.gain.value = 1.0;

    const midPeak = ctx.createBiquadFilter();
    midPeak.type = "peaking";
    midPeak.frequency.value = 2800;
    midPeak.Q.value = 1.0;
    midPeak.gain.value = 0.5;

    const airShelf = ctx.createBiquadFilter();
    airShelf.type = "highshelf";
    airShelf.frequency.value = 12000;
    airShelf.gain.value = 1.5;

    const compressor = ctx.createDynamicsCompressor();
    compressor.threshold.value = -18;
    compressor.knee.value = 12;
    compressor.ratio.value = 3.0;
    compressor.attack.value = 0.005;
    compressor.release.value = 0.15;

    // Path B: Live DSP Processed Gain
    const masterGain = ctx.createGain();
    masterGain.gain.value = 1.0; // Default: B (Live DSP) is active

    // Path A: Pure Clean Bypass Gain
    const bypassGain = ctx.createGain();
    bypassGain.gain.value = 0.0;

    // Connect DSP Chain (source -> lowShelf -> midPeak -> airShelf -> compressor -> masterGain -> destination)
    sourceNode.connect(lowShelf);
    lowShelf.connect(midPeak);
    midPeak.connect(airShelf);
    airShelf.connect(compressor);
    compressor.connect(masterGain);
    masterGain.connect(ctx.destination);

    // Connect Pure Bypass Chain (source -> bypassGain -> destination)
    sourceNode.connect(bypassGain);
    bypassGain.connect(ctx.destination);

    state.webAudioDsp.lowShelf = lowShelf;
    state.webAudioDsp.midPeak = midPeak;
    state.webAudioDsp.airShelf = airShelf;
    state.webAudioDsp.compressor = compressor;
    state.webAudioDsp.masterGain = masterGain;
    state.webAudioDsp.bypassGain = bypassGain;
    state.webAudioDsp.isInitialized = true;

    updateLiveDspParameters();
  } catch (err) {
    console.warn("Web Audio API DSP initialization failed or bypassed:", err);
  }
}

function updateLiveDspParameters() {
  if (!state.webAudioDsp.isInitialized || !state.webAudioDsp.ctx) return;
  const dsp = state.webAudioDsp;
  const now = dsp.ctx.currentTime;

  const bassDb = dom.eqBassSlider ? (parseFloat(dom.eqBassSlider.value) || 1.0) : 1.0;
  const midDb = dom.eqMidSlider ? (parseFloat(dom.eqMidSlider.value) || 0.5) : 0.5;
  const airDb = dom.eqAirSlider ? (parseFloat(dom.eqAirSlider.value) || 1.5) : 1.5;

  if (dsp.lowShelf) dsp.lowShelf.gain.setValueAtTime(bassDb, now);
  if (dsp.midPeak) dsp.midPeak.gain.setValueAtTime(midDb, now);
  if (dsp.airShelf) dsp.airShelf.gain.setValueAtTime(airDb, now);

  if (state.monitorSource === 'A') {
    dsp.bypassGain.gain.setValueAtTime(1.0, now);
    dsp.masterGain.gain.setValueAtTime(0.0, now);
  } else if (state.monitorSource === 'B') {
    dsp.bypassGain.gain.setValueAtTime(0.0, now);
    dsp.masterGain.gain.setValueAtTime(1.0, now);
  }
}

window.switchMonitorSource = function(source) {
  if (!state.audio) {
    alert("먼저 Suno 또는 오디오 음원을 불러와주세요!");
    return;
  }

  // Ensure Web Audio context is started on user gesture
  if (state.webAudioDsp.ctx && state.webAudioDsp.ctx.state === "suspended") {
    state.webAudioDsp.ctx.resume();
  } else if (!state.webAudioDsp.isInitialized) {
    initLiveDspChain();
  }

  state.monitorSource = source;

  const btnA = document.getElementById("btn-monitor-a");
  const btnB = document.getElementById("btn-monitor-b");
  const btnC = document.getElementById("btn-monitor-c");
  const activeLabel = document.getElementById("monitor-active-label");

  // Reset button styles
  [btnA, btnB, btnC].forEach(b => {
    if (b) {
      b.className = "monitor-btn px-2 py-2 rounded-md text-xs font-bold transition flex flex-col items-center gap-0.5 cursor-pointer bg-white/5 text-slate-300 hover:text-white";
    }
  });

  if (source === 'A') {
    // 1. 순수 원본 무손실 (A)
    if (btnA) btnA.className = "monitor-btn active px-2 py-2 rounded-md text-xs font-bold transition flex flex-col items-center gap-0.5 cursor-pointer bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/30 font-black";
    if (activeLabel) activeLabel.textContent = "1. 순수 원본 사운드 (Pure Clean) 청음 중";
    if (state.renderedMasterAudio) {
      state.renderedMasterAudio.pause();
    }
    updateLiveDspParameters();
  } else if (source === 'B') {
    // 2. 실시간 중간 사운드 Live DSP (B)
    if (btnB) btnB.className = "monitor-btn active px-2 py-2 rounded-md text-xs font-bold transition flex flex-col items-center gap-0.5 cursor-pointer bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-950 shadow-md shadow-cyan-500/30 font-black";
    if (activeLabel) activeLabel.textContent = "2. 실시간 중간 사운드 (Live DSP) 청음 중";
    if (state.renderedMasterAudio) {
      state.renderedMasterAudio.pause();
    }
    updateLiveDspParameters();
  } else if (source === 'C') {
    // 3. 완성 마스터 (C)
    if (!state.lastRenderedMasterUrl) {
    alert("아직 렌더링된 완성 마스터가 없습니다.\n[완성 · 내보내기] 화면 또는 완곡 마스터링 버튼으로 먼저 마스터를 만들어 주세요.");
      switchMonitorSource('B');
      return;
    }
    if (btnC) btnC.className = "monitor-btn active px-2 py-2 rounded-md text-xs font-bold transition flex flex-col items-center gap-0.5 cursor-pointer bg-gradient-to-r from-amber-500 to-yellow-400 text-slate-950 shadow-md shadow-amber-500/30 font-black";
    if (activeLabel) activeLabel.textContent = `3. 완성 마스터 청음 중 (${state.lastRenderedMasterName || "완곡 마스터"})`;

    const curTime = state.audioElement ? state.audioElement.currentTime : 0;
    const wasPlaying = state.audioElement && !state.audioElement.paused;
    state.audioElement.pause();

    if (!state.renderedMasterAudio) {
      state.renderedMasterAudio = new Audio();
      state.renderedMasterAudio.crossOrigin = "anonymous";
    }
    state.renderedMasterAudio.src = state.lastRenderedMasterUrl;
    state.renderedMasterAudio.currentTime = Math.min(curTime, state.renderedMasterAudio.duration || curTime);
    if (wasPlaying) {
      state.renderedMasterAudio.play().catch(e => console.log("Rendered master play error:", e));
    }
  }
};

function setupEventListeners() {
  // Suno URL Input listeners
  let sunoInputTimer = null;
  if (dom.sunoUrlInput) {
    dom.sunoUrlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSunoUrlImport();
      }
    });

    dom.sunoUrlInput.addEventListener("paste", (e) => {
      const pasted = (e.clipboardData || window.clipboardData)?.getData("text")?.trim();
      if (pasted) {
        e.preventDefault();
        clearTimeout(sunoInputTimer);
        dom.sunoUrlInput.value = pasted;
        handleSunoUrlImport(pasted);
      } else {
        setTimeout(() => {
          const val = dom.sunoUrlInput.value.trim();
          if (val) handleSunoUrlImport(val);
        }, 30);
      }
    });

    const singleThumbEl = document.getElementById("suno-single-input-thumb");
    const updateSinglePreview = (url) => {
      if (!singleThumbEl) return;
      const { thumb, sunoId } = extractSongThumb(url);
      if (thumb) {
        singleThumbEl.src = thumb;
        singleThumbEl.dataset.triedPng = '';
        singleThumbEl.onerror = function() {
          if (sunoId && !this.dataset.triedPng) {
            this.dataset.triedPng = '1';
            this.src = `https://cdn1.suno.ai/image_${sunoId}.png`;
          } else {
            this.classList.add("hidden");
          }
        };
        singleThumbEl.classList.remove("hidden");
      } else {
        singleThumbEl.classList.add("hidden");
      }
    };

    // Also trigger on input event (handles mouse right-click paste, autofill, drag, etc.)
    dom.sunoUrlInput.addEventListener("input", () => {
      const val = dom.sunoUrlInput.value.trim();
      updateSinglePreview(val);
      if (/suno\.(com|ai)|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(youtube\.com|youtu\.be)/i.test(val)) {
        clearTimeout(sunoInputTimer);
        sunoInputTimer = setTimeout(() => {
          handleSunoUrlImport(val);
        }, 200);
      }
    });
  }

  // Global paste handler: If user pastes Suno or YouTube link anywhere on the page
  window.addEventListener("paste", (e) => {
    if (document.activeElement === dom.sunoUrlInput) return;
    const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
    if (activeTag === "input" || activeTag === "textarea") return;

    const pastedText = (e.clipboardData || window.clipboardData)?.getData("text") || "";
    if (/suno\.(com|ai)|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(youtube\.com|youtu\.be)/i.test(pastedText)) {
      e.preventDefault();
      if (dom.sunoUrlInput) dom.sunoUrlInput.value = pastedText.trim();
      handleSunoUrlImport(pastedText.trim());
    }
  });

  // File Upload
  dom.dropzone.addEventListener("click", () => dom.audioInput.click());
  dom.audioInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) uploadAudio(e.target.files[0]);
  });
  dom.dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dom.dropzone.classList.add("border-cyan-500");
  });
  dom.dropzone.addEventListener("dragleave", () => {
    dom.dropzone.classList.remove("border-cyan-500");
  });
  dom.dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dom.dropzone.classList.remove("border-cyan-500");
    const textData = e.dataTransfer.getData("text");
    if (textData && /suno\.com|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(youtube\.com|youtu\.be)/i.test(textData)) {
      if (dom.sunoUrlInput) dom.sunoUrlInput.value = textData.trim();
      handleSunoUrlImport(textData.trim());
      return;
    }
    if (e.dataTransfer.files.length > 0) uploadAudio(e.dataTransfer.files[0]);
  });

  // Load Demo Track
  dom.btnLoadDemo.addEventListener("click", loadDemoTrack);

  // Section-Only Playback
  dom.btnPlaySection.addEventListener("click", toggleSectionPlayback);

  // Range Sliders
  dom.startTimeSlider.addEventListener("input", (e) => {
    state.selectedSegment.start = parseFloat(e.target.value);
    dom.startTimeVal.textContent = `${state.selectedSegment.start.toFixed(1)}초`;
    updateSelectionOverlay();
    if (state.isPlayingSection) {
      state.audioElement.currentTime = state.selectedSegment.start;
    }
  });

  dom.durationSlider.addEventListener("input", (e) => {
    state.selectedSegment.duration = parseFloat(e.target.value);
    dom.durationVal.textContent = `${state.selectedSegment.duration.toFixed(1)}초`;
    updateSelectionOverlay();
  });

  // Duration Presets (10s, 15s, full)
  document.querySelectorAll(".slice-preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".slice-preset-btn").forEach(b => {
        b.className = "slice-preset-btn px-2 py-1 rounded text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300";
      });
      btn.className = "slice-preset-btn px-2 py-1 rounded text-[11px] bg-cyan-600/40 text-cyan-200 border border-cyan-500/40";

      const d = btn.dataset.dur;
      if (d === "full") {
        state.selectedSegment.start = 0.0;
        state.selectedSegment.duration = state.duration;
      } else {
        state.selectedSegment.duration = parseFloat(d);
      }
      dom.startTimeSlider.value = state.selectedSegment.start;
      dom.startTimeVal.textContent = `${state.selectedSegment.start.toFixed(1)}초`;
      dom.durationSlider.value = state.selectedSegment.duration;
      dom.durationVal.textContent = `${state.selectedSegment.duration.toFixed(1)}초`;
      updateSelectionOverlay();
    });
  });

  // Navigate to Step 3
  dom.btnGotoStep3.addEventListener("click", () => {
    stopSectionPlayback();
    setWorkflowStep(3);
  });

  // Step 3 Knobs
  dom.eqBassSlider.addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    dom.eqBassVal.textContent = `${v > 0 ? "+" : ""}${v.toFixed(1)} dB`;
    updateLiveDspParameters();
  });
  dom.eqMidSlider.addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    dom.eqMidVal.textContent = `${v > 0 ? "+" : ""}${v.toFixed(1)} dB`;
    updateLiveDspParameters();
  });
  dom.eqAirSlider.addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    dom.eqAirVal.textContent = `+${v.toFixed(1)} dB`;
    updateLiveDspParameters();
  });
  dom.stereoSlider.addEventListener("input", (e) => {
    dom.stereoVal.textContent = `${Math.round(e.target.value * 100)}%`;
  });
  dom.warmthSlider.addEventListener("input", (e) => {
    dom.warmthVal.textContent = `${Math.round(e.target.value * 100)}%`;
  });

  // Suno Speed Controller Event Listeners
  if (dom.sunoSpeedSlider) {
    dom.sunoSpeedSlider.addEventListener("input", (e) => {
      setAudioSpeed(parseFloat(e.target.value) || 1.0);
    });
  }

  if (dom.btnSpeedStepDown) {
    dom.btnSpeedStepDown.addEventListener("click", () => stepSpeed(-0.01));
  }

  if (dom.btnSpeedStepUp) {
    dom.btnSpeedStepUp.addEventListener("click", () => stepSpeed(+0.01));
  }

  document.querySelectorAll(".btn-fine-speed-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      const spd = parseFloat(btn.dataset.spd) || 1.0;
      setAudioSpeed(spd);
    });
  });

  // Fine Pitch Slider & Steppers (0.05 semitones / 5 cents)
  if (dom.sunoPitchSlider) {
    dom.sunoPitchSlider.addEventListener("input", (e) => {
      setAudioPitch(parseFloat(e.target.value) || 0.0);
      triggerSunoPitchLiveUpdate(false);
    });
    dom.sunoPitchSlider.addEventListener("change", (e) => {
      setAudioPitch(parseFloat(e.target.value) || 0.0);
      triggerSunoPitchLiveUpdate(true);
    });
  }

  if (dom.btnPitchStepDown) {
    dom.btnPitchStepDown.addEventListener("click", () => {
      stepPitch(-0.05);
      triggerSunoPitchLiveUpdate(true);
    });
  }

  if (dom.btnPitchStepUp) {
    dom.btnPitchStepUp.addEventListener("click", () => {
      stepPitch(+0.05);
      triggerSunoPitchLiveUpdate(true);
    });
  }

  if (dom.btnPitchStepSemitoneDown) {
    dom.btnPitchStepSemitoneDown.addEventListener("click", () => {
      stepPitch(-1.0);
      triggerSunoPitchLiveUpdate(true);
    });
  }

  if (dom.btnPitchStepSemitoneUp) {
    dom.btnPitchStepSemitoneUp.addEventListener("click", () => {
      stepPitch(+1.0);
      triggerSunoPitchLiveUpdate(true);
    });
  }

  if (dom.btnPitchReset) {
    dom.btnPitchReset.addEventListener("click", () => {
      resetAudioPitch();
      triggerSunoPitchLiveUpdate(true);
    });
  }

  if (dom.btnPitchPreviewAudition) {
    dom.btnPitchPreviewAudition.addEventListener("click", () => playPitchPreviewAudition({ toggleStop: true }));
  }

  document.querySelectorAll(".btn-fine-pitch-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      const pitch = parseFloat(btn.dataset.pitch) || 0.0;
      setAudioPitch(pitch);
      triggerSunoPitchLiveUpdate(true);
    });
  });

  // Unified Audition Seek & Section Navigation
  function setAuditionPosition(targetTime, shouldReplay = false) {
    if (!state.duration || state.duration <= 0) return;
    const clampedTime = Math.max(0, Math.min(targetTime, Math.max(0, state.duration - 0.2)));
    state.auditionSeekSec = clampedTime;
    if (state.selectedSegment) {
      state.selectedSegment.start = clampedTime;
    }
    if (state.audioElement) {
      state.audioElement.currentTime = clampedTime;
    }
    if (dom.startTimeSlider) {
      dom.startTimeSlider.value = clampedTime;
    }
    if (dom.startTimeVal) {
      dom.startTimeVal.textContent = `${clampedTime.toFixed(1)}초`;
    }
    const pct = (clampedTime / state.duration) * 100;
    if (dom.sunoSpeedSeekSlider) {
      dom.sunoSpeedSeekSlider.value = pct.toFixed(1);
    }
    if (dom.sunoSpeedSeekTimeDisplay) {
      dom.sunoSpeedSeekTimeDisplay.textContent = `${formatTime(clampedTime)} (${Math.round(pct)}%)`;
    }
    updatePlayheadPosition(clampedTime);
    updateSelectionOverlay();

    // If pitch audition preview is currently active or explicit replay requested:
    if (sunoPitchAuditioning || (pitchPreviewAudio && !pitchPreviewAudio.paused) || shouldReplay) {
      clearTimeout(sunoPitchLiveTimer);
      sunoPitchLiveTimer = setTimeout(() => {
        playPitchPreviewAudition({
          preserveTime: false,
          autoPlay: true,
          isLiveUpdate: true
        });
      }, 40);
    }
  }
  window.setAuditionPosition = setAuditionPosition;

  // Speed Preview Section & Seek Slider
  if (dom.sunoSpeedSeekSlider) {
    dom.sunoSpeedSeekSlider.addEventListener("input", (e) => {
      if (!state.duration) return;
      const pct = parseFloat(e.target.value) || 0;
      const targetTime = (pct / 100) * state.duration;
      setAuditionPosition(targetTime, false);
    });
    dom.sunoSpeedSeekSlider.addEventListener("change", (e) => {
      if (!state.duration) return;
      const pct = parseFloat(e.target.value) || 0;
      const targetTime = (pct / 100) * state.duration;
      setAuditionPosition(targetTime, true);
    });
  }

  document.querySelectorAll(".btn-seek-quick").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!state.duration) return;
      const ratio = parseFloat(btn.dataset.pos) || 0;
      const targetTime = ratio * state.duration;
      setAuditionPosition(targetTime, true);
    });
  });

  if (dom.btnSyncSectionToSpeed) {
    dom.btnSyncSectionToSpeed.addEventListener("click", () => {
      if (!state.duration) return;
      const targetTime = state.selectedSegment?.start || 0;
      setAuditionPosition(targetTime, true);
    });
  }

  if (dom.toggleKeepPitch) {
    dom.toggleKeepPitch.addEventListener("change", (e) => {
      if (state.audioElement) {
        state.audioElement.preservesPitch = e.target.checked;
      }
      updateSpeedBadge();
    });
  }

  if (dom.btnSunoSpeedReset) {
    dom.btnSunoSpeedReset.addEventListener("click", () => {
      setAudioSpeed(1.0);
    });
  }

  if (dom.btnSpeedThumbPlay) {
    dom.btnSpeedThumbPlay.addEventListener("click", toggleSunoSpeedPlay);
  }

  if (dom.btnSpeedPillMenu) {
    dom.btnSpeedPillMenu.addEventListener("click", (e) => {
      e.stopPropagation();
      if (dom.speedPresetDropdown) {
        dom.speedPresetDropdown.classList.toggle("hidden");
      }
    });
  }

  document.querySelectorAll(".speed-preset-item").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const spd = parseFloat(btn.dataset.speed) || 1.0;
      setAudioSpeed(spd);
      if (dom.speedPresetDropdown) dom.speedPresetDropdown.classList.add("hidden");
    });
  });

  document.addEventListener("click", () => {
    if (dom.speedPresetDropdown && !dom.speedPresetDropdown.classList.contains("hidden")) {
      dom.speedPresetDropdown.classList.add("hidden");
    }
  });

  // Enqueue Full Song Mastering & Preview Actions
  if (dom.btnEnqueueFullMaster) dom.btnEnqueueFullMaster.addEventListener("click", enqueueFullSongMastering);
  if (dom.btnEnqueuePreview) dom.btnEnqueuePreview.addEventListener("click", enqueuePreviewMastering);

  // Live Title Sync from draftNameInput to workspace header & studio
  if (dom.draftNameInput) {
    dom.draftNameInput.addEventListener("input", (e) => {
      dom.draftNameInput.dataset.userEdited = "true";
      const val = e.target.value.trim();
      if (val) {
        const cleanTitle = extractCleanSongTitle(val, val);
        if (state.audio) state.audio.title = cleanTitle;
        const bannerTitle = document.getElementById("loaded-track-title");
        if (bannerTitle) bannerTitle.textContent = cleanTitle;
        const wsTrackName = document.getElementById("ws-track-name");
        if (wsTrackName) wsTrackName.textContent = cleanTitle;
        if (dom.sunoSpeedTrackName) dom.sunoSpeedTrackName.textContent = cleanTitle;
      }
    });
  }

  // Click Waveform Seek
  dom.waveformContainer.addEventListener("click", (e) => {
    if (!state.duration) return;
    const rect = dom.waveformContainer.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = clickX / rect.width;
    const newStart = ratio * state.duration;
    setAuditionPosition(newStart, false);

    if (state.isPlayingSection && state.audioElement) {
      state.audioElement.currentTime = state.selectedSegment.start;
    }
  });

  updateSpeedBadge();
}

// Audition Audio Elements & Highest Priority Coordination
let pitchPreviewAudio = null;
let sunoPitchLiveTimer = null;
let sunoPitchSequence = 0;
let sunoPitchAuditioning = false;

// ENFORCE TOP PRIORITY PLAYBACK: Pauses all competing audio players immediately
function enforceAuditionTopPriority(targetPlayer) {
  // 1. Pause main DAW audio if target is different
  if (state.audioElement && targetPlayer !== state.audioElement && !state.audioElement.paused) {
    state.audioElement.pause();
    state.isPlaying = false;
    if (dom.btnPlayPause) dom.btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
    if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-play text-white text-xs";
  }
  // 2. Pause pitch preview player if target is different
  if (pitchPreviewAudio && targetPlayer !== pitchPreviewAudio && !pitchPreviewAudio.paused) {
    pitchPreviewAudio.pause();
    sunoPitchAuditioning = false;
    if (dom.btnPitchPreviewAudition) {
      dom.btnPitchPreviewAudition.innerHTML = `<i class="fa-solid fa-headphones text-[10px]"></i> <span>피치 미리듣기</span>`;
    }
  }
  // 3. Pause hum engine if active
  if (window.humAudio && !window.humAudio.paused) {
    try { window.humAudio.pause(); } catch(e) {}
  }
  // 4. Pause rendered master preview if active
  if (state.renderedMasterAudio && !state.renderedMasterAudio.paused) {
    try { state.renderedMasterAudio.pause(); } catch(e) {}
  }
}

// Unified Audition Real-time / Processing Status & Guidance Notification Bar
function updateAuditionNotice(status, title, desc) {
  const notice = document.getElementById("audition-live-status-notice");
  const dot = document.getElementById("audition-live-indicator-dot");
  const titleEl = document.getElementById("audition-live-status-title");
  const descEl = document.getElementById("audition-live-status-desc");
  if (!notice || !titleEl) return;

  if (status === "processing" || status === "updating") {
    notice.className = "mt-2.5 p-2 rounded-lg bg-[#191308] border border-amber-500/40 flex items-center justify-between gap-2 text-[10.5px] font-mono transition-all";
    if (dot) dot.className = "fa-solid fa-spinner fa-spin text-amber-400 text-xs shrink-0";
    titleEl.className = "font-bold text-amber-300 shrink-0";
    titleEl.textContent = title || "반영 중 (연산 중...)";
    if (descEl) {
      descEl.textContent = desc || "정밀 피치 알고리즘(Rubberband) 연산 중입니다. 완료 즉시 최우선 재생됩니다.";
      descEl.className = "text-amber-200/80 text-[10px] truncate";
    }
  } else if (status === "live") {
    notice.className = "mt-2.5 p-2 rounded-lg bg-[#081512] border border-emerald-500/40 flex items-center justify-between gap-2 text-[10.5px] font-mono transition-all";
    if (dot) dot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0";
    titleEl.className = "font-bold text-emerald-300 shrink-0";
    titleEl.textContent = title || "LIVE 실시간 적용 중";
    if (descEl) {
      descEl.textContent = desc || "재생 중 배속 및 피치가 지연 없이 즉각 다이렉트 반영 중입니다.";
      descEl.className = "text-emerald-200/80 text-[10px] truncate";
    }
  } else {
    notice.className = "mt-2.5 p-2 rounded-lg bg-[#0a101d] border border-cyan-500/20 flex items-center justify-between gap-2 text-[10.5px] font-mono transition-all";
    if (dot) dot.className = "w-2 h-2 rounded-full bg-cyan-400 shrink-0";
    titleEl.className = "font-bold text-cyan-300 shrink-0";
    titleEl.textContent = title || "미리듣기 대기 중";
    if (descEl) {
      descEl.textContent = desc || "재생 시 0ms 실시간 배속 및 정밀 피치가 최우선으로 청음됩니다.";
      descEl.className = "text-slate-400 text-[10px] truncate";
    }
  }
}

// Speed Live Badge Controller
function setSunoSpeedLiveBadge(mode, customText) {
  const badge = document.getElementById("suno-speed-live-badge");
  if (!badge) return;
  if (mode === "updating" || mode === "processing") {
    badge.className = "text-[9.5px] px-2 py-0.5 rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-300 font-mono font-bold flex items-center gap-1.5 transition-all";
    badge.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[8px] text-amber-400"></i><span>${customText || "반영 중..."}</span>`;
  } else if (mode === "live") {
    badge.className = "text-[9.5px] px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-mono font-bold flex items-center gap-1.5 shadow-sm transition-all";
    badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span><span>${customText || "LIVE 실시간 적용 중"}</span>`;
  } else {
    badge.className = "text-[9.5px] px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400 font-mono font-bold flex items-center gap-1.5 transition-all";
    badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span><span>${customText || "실시간 대기"}</span>`;
  }
}

// Pitch Live Badge Controller
function setSunoPitchLiveBadge(mode, customText) {
  const badge = document.getElementById("suno-pitch-live-badge");
  if (!badge) return;
  if (mode === "updating" || mode === "processing") {
    badge.className = "text-[9.5px] px-2 py-0.5 rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-300 font-mono font-bold flex items-center gap-1.5 transition-all";
    badge.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[8px] text-amber-400"></i><span>${customText || "반영 중 (연산 중...)"}</span>`;
  } else if (mode === "live" || mode === "updated") {
    badge.className = "text-[9.5px] px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-mono font-bold flex items-center gap-1.5 shadow-sm transition-all";
    badge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span><span>${customText || "LIVE 실시간 적용 중"}</span>`;
  } else {
    badge.className = "text-[9.5px] px-2 py-0.5 rounded-full bg-purple-950/80 border border-purple-500/40 text-purple-300 font-mono font-bold flex items-center gap-1.5 transition-all";
    badge.innerHTML = `<i class="fa-solid fa-bolt text-[8px] text-purple-400"></i><span>${customText || "LIVE 실시간 적용 중"}</span>`;
  }
}

// Suno Speed Card Audition Playback Logic (Highest Priority)
function toggleSunoSpeedPlay() {
  if (!state.audio || !state.audioElement.src) {
    alert("먼저 Suno 음원을 불러와주세요!");
    return;
  }

  const spd = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  const pitch = (state.pitchShift !== undefined) ? state.pitchShift : (dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0);

  // If fine pitch shift is non-zero, route to unified pitch & speed audition with Top Priority:
  if (Math.abs(pitch) > 0.005) {
    playPitchPreviewAudition({ toggleStop: true });
    return;
  }

  if (state.audioElement.paused) {
    // ENFORCE TOP PRIORITY
    enforceAuditionTopPriority(state.audioElement);

    state.isPlayingSection = false; // Audition full track at speed
    state.audioElement.playbackRate = spd;
    state.audioElement.preservesPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;

    if (state.auditionSeekSec !== undefined && Math.abs(state.audioElement.currentTime - state.auditionSeekSec) > 0.3) {
      state.audioElement.currentTime = state.auditionSeekSec;
    } else if (state.audioElement.currentTime >= state.duration - 0.2) {
      state.audioElement.currentTime = 0;
    }

    state.audioElement.play().then(() => {
      if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-pause text-white text-xs";
      dom.playheadLine.classList.remove("hidden");
      setSunoSpeedLiveBadge("live", "LIVE 실시간 적용 중");
      setSunoPitchLiveBadge("live", "LIVE 실시간 적용 중");
      updateAuditionNotice("live", "LIVE 실시간 적용 중", `${spd.toFixed(2)}x 배속이 0ms 지연으로 최우선 실시간 재생 중입니다.`);
    }).catch(e => console.log("Speed audition play error:", e));
  } else {
    state.audioElement.pause();
    if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-play text-white text-xs";
    updateAuditionNotice("idle", "미리듣기 일시정지", "재생 버튼을 누르면 최우선으로 즉시 청음됩니다.");
  }
}

// 0.01x Precision Stepper & Speed Setter
function stepSpeed(delta) {
  if (!dom.sunoSpeedSlider) return;
  let cur = parseFloat(dom.sunoSpeedSlider.value) || 1.0;
  cur = Math.round((cur + delta) * 100) / 100;
  cur = Math.max(0.50, Math.min(2.00, cur));
  setAudioSpeed(cur);
}

function setAudioSpeed(speed) {
  const val = Math.max(0.50, Math.min(2.00, speed));
  if (dom.sunoSpeedSlider) dom.sunoSpeedSlider.value = val.toFixed(2);
  if (dom.sunoSpeedValDisplay) dom.sunoSpeedValDisplay.textContent = `${val.toFixed(2)}x`;

  // Real-time 0ms latency update on both active player elements:
  if (state.audioElement) {
    state.audioElement.playbackRate = val;
    state.audioElement.preservesPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;
  }
  if (pitchPreviewAudio) {
    pitchPreviewAudio.playbackRate = val;
    pitchPreviewAudio.preservesPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;
  }

  const isPlaying = (state.audioElement && !state.audioElement.paused) || (pitchPreviewAudio && !pitchPreviewAudio.paused);
  setSunoSpeedLiveBadge("live", "LIVE 실시간 적용 중");
  if (isPlaying) {
    updateAuditionNotice("live", "LIVE 실시간 적용 중", `${val.toFixed(2)}x 정밀 배속이 실시간(0ms 지연)으로 즉각 반영되었습니다.`);
  }

  updateEndingTimeCalculation();
  updateDraftNameInput();
  updateSpeedBadge();
}

// 0.05 Semitone / 5 Cents Precision Pitch Setter & Steppers
function stepPitch(delta) {
  let cur = (state.pitchShift !== undefined) ? state.pitchShift : (dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0);
  cur = Math.round((cur + delta) * 100) / 100;
  cur = Math.max(-12.0, Math.min(12.0, cur));
  setAudioPitch(cur);
}

function resetAudioPitch() {
  setAudioPitch(0.0);
}

function setAudioPitch(pitch) {
  const val = Math.max(-12.0, Math.min(12.0, pitch));
  state.pitchShift = val;
  if (dom.sunoPitchSlider) dom.sunoPitchSlider.value = val.toFixed(2);
  if (dom.sunoPitchValDisplay) {
    if (Math.abs(val) < 0.005) {
      dom.sunoPitchValDisplay.textContent = "0 (원음)";
    } else {
      const cents = Math.round(val * 100);
      const sign = val > 0 ? "+" : "";
      dom.sunoPitchValDisplay.textContent = `${sign}${val.toFixed(2)}키 (${sign}${cents}¢)`;
    }
  }
  const pitchPills = document.querySelectorAll(".btn-fine-pitch-pill");
  pitchPills.forEach(btn => {
    const pVal = parseFloat(btn.dataset.pitch) || 0.0;
    if (Math.abs(pVal - val) < 0.05) {
      btn.className = "btn-fine-pitch-pill px-1.5 py-0.5 rounded bg-purple-600 text-white font-bold text-[10px] font-mono transition shadow-sm";
    } else {
      btn.className = "btn-fine-pitch-pill px-1.5 py-0.5 rounded bg-white/5 hover:bg-purple-500/20 text-slate-300 hover:text-purple-300 text-[10px] font-mono transition";
    }
  });
  updateDraftNameInput();
  updateSpeedBadge();
}

async function playPitchPreviewAudition(options = {}) {
  const {
    preserveTime = false,
    autoPlay = true,
    isLiveUpdate = false,
    toggleStop = false
  } = options;

  if (!state.audio && !state.audioElement?.src) {
    if (!isLiveUpdate) alert("먼저 Suno 음원을 업로드해주세요!");
    return;
  }

  const btn = dom.btnPitchPreviewAudition;

  if (toggleStop && pitchPreviewAudio && !pitchPreviewAudio.paused) {
    pitchPreviewAudio.pause();
    sunoPitchAuditioning = false;
    if (btn) btn.innerHTML = `<i class="fa-solid fa-headphones text-[10px]"></i> <span>피치 미리듣기</span>`;
    updateAuditionNotice("idle", "미리듣기 일시정지", "피치 미리듣기가 정지되었습니다.");
    return;
  }

  const spd = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  const pitch = (state.pitchShift !== undefined) ? state.pitchShift : (dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0);

  // If pitch is 0, play directly through real-time audio player
  if (Math.abs(pitch) < 0.005) {
    toggleSunoSpeedPlay();
    return;
  }

  // Exact section start position requested by user (unified position)
  let startSec = 0.0;
  if (state.auditionSeekSec !== undefined) {
    startSec = state.auditionSeekSec;
  } else if (state.selectedSegment?.start !== undefined && state.selectedSegment.start > 0) {
    startSec = state.selectedSegment.start;
  } else if (state.audioElement && !state.audioElement.paused && state.audioElement.currentTime) {
    startSec = state.audioElement.currentTime;
  }

  if (state.duration && state.duration > 0) {
    startSec = Math.max(0.0, Math.min(startSec, Math.max(0, state.duration - 0.5)));
  }

  state.pitchAuditionStartSec = startSec;

  const sequence = ++sunoPitchSequence;

  // Show "반영 중 (연산 중...)" status indicator while computing pitch
  setSunoPitchLiveBadge("updating", "반영 중 (연산 중...)");
  updateAuditionNotice("processing", "반영 중 (연산 중...)", `정밀 피치(${pitch > 0 ? "+" : ""}${pitch.toFixed(2)}키) 알고리즘 연산 중입니다. 완료 즉시 최우선 재생됩니다.`);

  if (!isLiveUpdate && btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> <span>반영 중...</span>`;
  }

  try {
    const audioUrl = state.audio?.audio_url || state.originalAudioUrl || state.audioElement?.src;
    const res = await fetch("/api/preview-pitch-speed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: audioUrl,
        speed: spd,
        pitch_shift: pitch,
        start_sec: startSec,
        duration_sec: 15.0
      })
    });
    const data = await res.json();
    if (sequence !== sunoPitchSequence) return;
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "미리듣기 렌더링 실패");
    }

    if (!pitchPreviewAudio) {
      pitchPreviewAudio = new Audio();
      pitchPreviewAudio.addEventListener("ended", () => {
        sunoPitchAuditioning = false;
        if (btn) btn.innerHTML = `<i class="fa-solid fa-headphones text-[10px]"></i> <span>피치 미리듣기</span>`;
        updateAuditionNotice("idle", "미리듣기 완료", "15초 구간 청음 완료. 다시 누르면 최우선 재생됩니다.");
      });
      pitchPreviewAudio.addEventListener("pause", () => {
        if (pitchPreviewAudio.currentTime >= (pitchPreviewAudio.duration || 15) - 0.2) {
          sunoPitchAuditioning = false;
        }
      });
    }

    // TOP PRIORITY: Pause all other competing audios
    enforceAuditionTopPriority(pitchPreviewAudio);

    const onReady = () => {
      if (autoPlay) {
        pitchPreviewAudio.playbackRate = spd;
        pitchPreviewAudio.play().then(() => {
          sunoPitchAuditioning = true;
          if (btn) {
            btn.disabled = false;
            const sign = pitch > 0 ? "+" : "";
            const pitchTxt = `${sign}${pitch.toFixed(1)}키`;
            btn.innerHTML = `<i class="fa-solid fa-pause text-[10px] text-amber-300"></i> <span>피치 정지 (${pitchTxt})</span>`;
          }
          // Switched to LIVE:
          setSunoPitchLiveBadge("live", "LIVE 실시간 적용 중");
          setSunoSpeedLiveBadge("live", "LIVE 실시간 적용 중");
          updateAuditionNotice("live", "LIVE 실시간 적용 중", `정밀 음정(${pitch > 0 ? "+" : ""}${pitch.toFixed(2)}키) & 배속(${spd.toFixed(2)}x) 최우선 실시간 재생 중`);
        }).catch(err => console.warn("Pitch play warning:", err));
      }
    };

    pitchPreviewAudio.addEventListener("loadedmetadata", onReady, { once: true });
    pitchPreviewAudio.src = data.preview_url;

    if (btn) {
      btn.disabled = false;
      const sign = pitch > 0 ? "+" : "";
      const pitchTxt = `${sign}${pitch.toFixed(1)}키`;
      btn.innerHTML = `<i class="fa-solid fa-pause text-[10px] text-amber-300"></i> <span>피치 정지 (${pitchTxt})</span>`;
    }

  } catch (err) {
    if (sequence !== sunoPitchSequence) return;
    console.error("Pitch audition error:", err);
    setSunoPitchLiveBadge("idle");
    updateAuditionNotice("idle", "미리듣기 실패", `오류: ${err.message || err}`);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-headphones text-[10px]"></i> <span>피치 미리듣기</span>`;
    }
    if (!isLiveUpdate) alert("피치 미리듣기 오류: " + err.message);
  }
}

function triggerSunoPitchLiveUpdate(immediate = false) {
  if (!state.audio && !state.audioElement?.src) return;

  const isAnyPlaying = sunoPitchAuditioning || (pitchPreviewAudio && !pitchPreviewAudio.paused) || (state.audioElement && !state.audioElement.paused) || state.isPlayingSection;

  setSunoPitchLiveBadge("updating", "반영 중 (연산 중...)");
  updateAuditionNotice("processing", "반영 중 (연산 중...)", "정밀 음정 연산 대기 중...");
  clearTimeout(sunoPitchLiveTimer);

  const delay = immediate ? 15 : 120;
  sunoPitchLiveTimer = setTimeout(async () => {
    if (isAnyPlaying || immediate) {
      await playPitchPreviewAudition({
        preserveTime: false,
        autoPlay: true,
        isLiveUpdate: true
      });
    }
  }, delay);
}

// Real-time Ending Time Calculation (e.g., 03:42 (-18초))
function updateEndingTimeCalculation() {
  if (!dom.sunoSpeedEndingCalc) return;
  const dur = state.duration || 0;
  if (dur <= 0) {
    dom.sunoSpeedEndingCalc.textContent = "⏱️ 앤딩: 00:00";
    return;
  }
  const spd = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  const newSec = dur / spd;
  const diffSec = Math.round(newSec - dur);
  const diffStr = diffSec > 0 ? `(+${diffSec}초)` : diffSec < 0 ? `(${diffSec}초)` : "(변화 없음)";
  const newTimeStr = formatTime(newSec);
  dom.sunoSpeedEndingCalc.textContent = `⏱️ 앤딩: ${newTimeStr} ${diffStr}`;
}

// Real-time Visual Speed & Pitch Reflection Badge in Step 3
function updateSpeedBadge() {
  const badge = document.getElementById("badge-current-render-speed");
  const label = document.getElementById("text-enqueue-full-master");

  const spd = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  const pitch = dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0;
  const keepPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;

  const hasSpeedChange = Math.abs(spd - 1.0) >= 0.005;
  const hasPitchChange = Math.abs(pitch) >= 0.005;

  if (!hasSpeedChange && !hasPitchChange) {
    if (badge) {
      badge.textContent = "1.00x • 원음 키 (원곡 그대로)";
      badge.className = "font-bold text-slate-300 bg-white/5 border border-white/10 px-2 py-0.5 rounded";
    }
    if (label) {
      label.textContent = "🚀 완곡 전체 마스터링 렌더링 (원곡 속도 • 원음 키)";
    }
  } else {
    const parts = [];
    const labelParts = [];

    if (hasSpeedChange) {
      const diffPct = Math.round((spd - 1.0) * 100);
      const sign = diffPct > 0 ? "+" : "";
      const pitchStr = keepPitch ? "피치 유지" : "LP 가감속";
      parts.push(`⚡ ${spd.toFixed(2)}x (${sign}${diffPct}% • ${pitchStr})`);
      labelParts.push(`${spd.toFixed(2)}x 배속`);
    }

    if (hasPitchChange) {
      const sign = pitch > 0 ? "+" : "";
      const cents = Math.round(pitch * 100);
      parts.push(`🎵 ${sign}${pitch.toFixed(2)}키 (${sign}${cents}¢)`);
      labelParts.push(`${sign}${pitch.toFixed(2)}키`);
    }

    if (badge) {
      badge.textContent = `${parts.join(" • ")} 완곡 음원에 직접 반영`;
      badge.className = "font-bold text-purple-300 bg-purple-500/20 border border-purple-500/40 px-2 py-0.5 rounded";
    }
    if (label) {
      label.textContent = `🚀 완곡 전체 마스터링 렌더링 (${labelParts.join(" • ")} 직접 반영)`;
    }
  }
}

// 720P (1280x720, 16:9) Cover Canvas Generator
async function generate720pCoverCanvas(title, speed, imageUrl) {
  const canvas = document.createElement("canvas");
  canvas.width = 1280;
  canvas.height = 720;
  const ctx = canvas.getContext("2d");

  let img = null;
  if (imageUrl) {
    img = await new Promise((resolve) => {
      const i = new Image();
      i.crossOrigin = "anonymous";
      i.onload = () => resolve(i);
      i.onerror = () => resolve(null);
      i.src = imageUrl;
    });
  }

  if (img) {
    // 1. Ambient blurred & darkened background fill
    ctx.save();
    ctx.filter = "blur(32px) brightness(0.38)";
    ctx.drawImage(img, -40, -40, 1360, 800);
    ctx.restore();

    // Dark gradient overlay
    const overlayGrad = ctx.createLinearGradient(0, 0, 0, 720);
    overlayGrad.addColorStop(0, "rgba(7, 10, 18, 0.45)");
    overlayGrad.addColorStop(1, "rgba(7, 10, 18, 0.88)");
    ctx.fillStyle = overlayGrad;
    ctx.fillRect(0, 0, 1280, 720);

    // 2. Centered crisp album art (440x440) with rounded corners and drop shadow
    const size = 440;
    const x = (1280 - size) / 2;
    const y = 80;
    const radius = 24;

    ctx.save();
    ctx.shadowColor = "rgba(0, 0, 0, 0.7)";
    ctx.shadowBlur = 36;
    ctx.shadowOffsetY = 16;

    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + size, y, x + size, y + size, radius);
    ctx.arcTo(x + size, y + size, x, y + size, radius);
    ctx.arcTo(x, y + size, x, y, radius);
    ctx.arcTo(x, y, x + size, y, radius);
    ctx.closePath();
    ctx.clip();

    ctx.drawImage(img, x, y, size, size);
    ctx.restore();

    // Subtle crisp border
    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + size, y, x + size, y + size, radius);
    ctx.arcTo(x + size, y + size, x, y + size, radius);
    ctx.arcTo(x, y + size, x, y, radius);
    ctx.arcTo(x, y, x + size, y, radius);
    ctx.closePath();
    ctx.stroke();

  } else {
    // Elegant Dark Studio Gradient Background
    const bgGrad = ctx.createLinearGradient(0, 0, 1280, 720);
    bgGrad.addColorStop(0, "#0b0f19");
    bgGrad.addColorStop(0.5, "#0f172a");
    bgGrad.addColorStop(1, "#050811");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 1280, 720);

    // Vinyl emblem in center
    const cx = 640;
    const cy = 290;
    const r = 180;

    ctx.save();
    ctx.shadowColor = "rgba(0, 210, 255, 0.25)";
    ctx.shadowBlur = 40;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = "#111420";
    ctx.fill();
    ctx.restore();

    // Vinyl grooves
    for (let gr = 60; gr < r; gr += 18) {
      ctx.beginPath();
      ctx.arc(cx, cy, gr, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Vinyl center label
    const centerGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, 55);
    centerGrad.addColorStop(0, "#06b6d4");
    centerGrad.addColorStop(1, "#0284c7");
    ctx.beginPath();
    ctx.arc(cx, cy, 55, 0, Math.PI * 2);
    ctx.fillStyle = centerGrad;
    ctx.fill();

    // Center hole
    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fillStyle = "#050811";
    ctx.fill();
  }

  // Track Title text (Crisp, bold, centered)
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 32px 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  const displayTitle = (title || "Suno Master Track").length > 40
    ? (title || "Suno Master Track").substring(0, 38) + "..."
    : (title || "Suno Master Track");

  ctx.shadowColor = "rgba(0, 0, 0, 0.85)";
  ctx.shadowBlur = 12;
  ctx.shadowOffsetY = 2;
  ctx.fillText(displayTitle, 640, 580);

  // Speed & Pitch Badge & Studio Branding
  ctx.shadowBlur = 0;
  ctx.shadowOffsetY = 0;
  const spdText = `${parseFloat(speed || 1.0).toFixed(2)}x Speed`;
  const pitchVal = (state.pitchShift !== undefined) ? state.pitchShift : (dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0);
  const pitchText = Math.abs(pitchVal) > 0.005 ? `  •  Key ${pitchVal > 0 ? '+' : ''}${pitchVal.toFixed(2)}st` : "";
  ctx.font = "bold 15px 'JetBrains Mono', Consolas, monospace";
  ctx.fillStyle = "#22d3ee";
  ctx.fillText(`⚡ ${spdText}${pitchText}  •  720P HD Audio Video  •  SUNO STUDIO`, 640, 630);

  return canvas.toDataURL("image/png");
}

// Export Current Track Audio (WAV or MP3) with Speed & Pitch Baked In
async function exportCurrentTrackAudio(format = "wav") {
  if (!state.audio || !state.audioElement.src) {
    alert("먼저 음원을 불러와주세요!");
    return;
  }

  const speed = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  const pitch = (state.pitchShift !== undefined) ? state.pitchShift : (dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0);
  const keepPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;
  const inputVal = dom.draftNameInput ? dom.draftNameInput.value.trim() : "";
  const title = inputVal ? extractCleanSongTitle(inputVal, state.audio.title) : (state.audio.title || "Suno_Master");
  const audioUrl = state.audio.audio_url;

  const btn = dom.btnExportSpeedAudio;
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-white"></i> <span>${format.toUpperCase()} 렌더링 중...</span>`;
  }

  try {
    const res = await fetch("/api/export-audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: audioUrl,
        speed: speed,
        pitch_shift: pitch,
        title: title,
        format: format,
        keep_pitch: keepPitch
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "마스터 오디오 렌더링 실패");
    }

    const dlLink = document.createElement("a");
    dlLink.href = data.audio_url.includes("?") ? `${data.audio_url}&dl=${Date.now()}` : `${data.audio_url}?dl=${Date.now()}`;
    dlLink.download = data.filename;
    document.body.appendChild(dlLink);
    dlLink.click();
    document.body.removeChild(dlLink);

    if (btn) {
      btn.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-300"></i> <span>저장 완료!</span>`;
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }, 2500);
    }
  } catch (err) {
    console.error("Audio Export error:", err);
    alert("마스터 음원 저장 오류:\n" + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}
window.exportCurrentTrackAudio = exportCurrentTrackAudio;

// Export Current Track as 720P MP4
async function exportCurrentTrackMp4() {
  if (!state.audio || !state.audioElement.src) {
    alert("먼저 음원을 불러와주세요!");
    return;
  }

  const speed = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  const pitch = (state.pitchShift !== undefined) ? state.pitchShift : (dom.sunoPitchSlider ? (parseFloat(dom.sunoPitchSlider.value) || 0.0) : 0.0);
  const inputVal = dom.draftNameInput ? dom.draftNameInput.value.trim() : "";
  const title = inputVal ? extractCleanSongTitle(inputVal, state.audio.title) : (state.audio.title || "Suno_Master");
  const imageUrl = state.audio.image_url || null;
  const audioUrl = state.audio.audio_url;
  const uploadYoutube = document.getElementById('export-opt-youtube')?.checked ?? false;

  const btn = dom.btnExportSpeedMp4;
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-white"></i> <span>MP4 렌더링 중...</span>`;
  }

  try {
    const imageBase64 = await generate720pCoverCanvas(title, speed, imageUrl);

    const res = await fetch("/api/export-mp4", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: audioUrl,
        speed: speed,
        pitch_shift: pitch,
        title: title,
        image_base64: imageBase64,
        image_url: imageUrl,
        upload_youtube: uploadYoutube
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "MP4 렌더링 실패");
    }

    const dlLink = document.createElement("a");
    dlLink.href = data.mp4_url.includes("?") ? `${data.mp4_url}&dl=${Date.now()}` : `${data.mp4_url}?dl=${Date.now()}`;
    dlLink.download = data.filename;
    document.body.appendChild(dlLink);
    dlLink.click();
    document.body.removeChild(dlLink);

    if (data.youtube_url) {
      alert(`🎉 MP4 저장 및 유튜브 채널 업로드 완료!\n\n동영상 링크: ${data.youtube_url}`);
    }

    if (btn) {
      btn.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-300"></i> <span>저장 완료!</span>`;
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }, 2500);
    }
  } catch (err) {
    console.error("MP4 Export error:", err);
    alert("MP4 비디오 내보내기 오류:\n" + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

// Export Mastered Draft as 720P MP4
async function exportDraftMp4(jobId) {
  const job = state.jobs.find(j => j.id === jobId);
  if (!job || !job.result_url) {
    alert("작업 결과를 찾을 수 없습니다.");
    return;
  }

  const speed = (job.mastering_options && job.mastering_options.speed_ratio) ? parseFloat(job.mastering_options.speed_ratio) : 1.0;
  const rawTitle = state.audio?.title || "Suno Track";
  const jobName = job.name || "Master";
  const title = jobName.includes(rawTitle) ? jobName : `${rawTitle} [${jobName}]`;
  const imageUrl = (state.audio && state.audio.image_url) ? state.audio.image_url : null;
  const audioUrl = job.result_url;

  const btn = document.querySelector(`.btn-draft-export-mp4[onclick*="${jobId}"]`);
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-purple-400"></i> MP4 제작 중...`;
  }

  try {
    const imageBase64 = await generate720pCoverCanvas(title, speed, imageUrl);

    const res = await fetch("/api/export-mp4", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: audioUrl,
        speed: 1.0, // Mastered audio already has speed applied
        pitch_shift: 0.0,
        title: title,
        image_base64: imageBase64,
        image_url: imageUrl
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "MP4 렌더링 실패");
    }

    const dlLink = document.createElement("a");
    dlLink.href = data.mp4_url.includes("?") ? `${data.mp4_url}&dl=${Date.now()}` : `${data.mp4_url}?dl=${Date.now()}`;
    dlLink.download = data.filename;
    document.body.appendChild(dlLink);
    dlLink.click();
    document.body.removeChild(dlLink);

    if (btn) {
      btn.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> 저장 완료!`;
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }, 2500);
    }
  } catch (err) {
    console.error("Draft MP4 export error:", err);
    alert("마스터링 MP4 비디오 저장 실패:\n" + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

// Export Mastered Draft as WAV or MP3
async function exportDraftAudio(jobId, format = "wav") {
  const job = state.jobs.find(j => j.id === jobId);
  if (!job || !job.result_url) {
    alert("작업 결과를 찾을 수 없습니다.");
    return;
  }

  const speed = (job.mastering_options && job.mastering_options.speed_ratio) ? parseFloat(job.mastering_options.speed_ratio) : 1.0;
  const speedTag = Math.abs(speed - 1.0) > 0.005 ? `_${speed.toFixed(2)}x` : "";
  const title = (state.audio && state.audio.title) ? `${state.audio.title}_${job.name}` : job.name;
  const cleanTitle = title.replace(/[<>:"/\\|?*\x00-\x1f]/g, "").trim();

  // If WAV: direct download from result_url
  if (format.toLowerCase() === "wav") {
    const a = document.createElement("a");
    a.href = job.result_url;
    a.download = job.filename || `${cleanTitle}${speedTag}_Master.wav`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    return;
  }

  // If MP3: convert using /api/export-audio with format="mp3"
  const btn = document.querySelector(`.btn-draft-export-mp3[data-job-id="${jobId}"]`);
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<div class="flex items-center gap-1.5"><i class="fa-solid fa-spinner fa-spin text-amber-400 text-sm"></i><span>MP3 생성 중</span></div><span class="text-[9.5px] text-amber-400/80 font-mono">인코딩 진행</span>`;
  }

  try {
    const res = await fetch("/api/export-audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: job.result_url,
        speed: 1.0, // Speed is already rendered into the master track
        keep_pitch: true,
        title: cleanTitle,
        format: "mp3"
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "MP3 음원 변환 실패");
    }

    const a = document.createElement("a");
    a.href = data.audio_url;
    a.download = data.filename || `${cleanTitle}${speedTag}_Master.mp3`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    if (btn) {
      btn.innerHTML = `<div class="flex items-center gap-1.5"><i class="fa-solid fa-circle-check text-emerald-400 text-sm"></i><span>저장 완료!</span></div><span class="text-[9.5px] text-emerald-400/80 font-mono">다운로드 완료</span>`;
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }, 2500);
    }
  } catch (err) {
    console.error("Draft MP3 export error:", err);
    alert("MP3 음원 저장 실패:\n" + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}
window.exportDraftAudio = exportDraftAudio;

// Section-Only Playback Logic
function toggleSectionPlayback() {
  if (!state.audioElement.src) return;

  if (state.isPlayingSection) {
    stopSectionPlayback();
  } else {
    startSectionPlayback();
  }
}

function startSectionPlayback() {
  state.isPlayingSection = true;
  state.audioElement.currentTime = state.selectedSegment.start;
  const spd = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
  state.audioElement.playbackRate = spd;
  state.audioElement.preservesPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;
  state.audioElement.play();
  updatePlaySectionButtonUI(true);
  dom.playheadLine.classList.remove("hidden");
}

function stopSectionPlayback() {
  state.isPlayingSection = false;
  state.audioElement.pause();
  state.audioElement.currentTime = state.selectedSegment.start;
  updatePlaySectionButtonUI(false);
  dom.playheadLine.classList.add("hidden");
}

function updatePlaySectionButtonUI(isPlaying) {
  if (isPlaying) {
    dom.btnPlaySection.className = "px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-md shadow-rose-600/30";
    dom.iconPlaySection.className = "fa-solid fa-stop";
    dom.textPlaySection.textContent = "구간 재생 정지";
  } else {
    dom.btnPlaySection.className = "px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-md shadow-cyan-600/30";
    dom.iconPlaySection.className = "fa-solid fa-play";
    dom.textPlaySection.textContent = "선택 구간만 재생";
  }
}

function updatePlayheadPosition(currentTime) {
  if (!state.duration || state.duration <= 0) return;
  const ratio = Math.min(1.0, Math.max(0.0, currentTime / state.duration));
  dom.playheadLine.style.left = `${ratio * 100}%`;
  
  const m = Math.floor(currentTime / 60);
  const s = Math.floor(currentTime % 60);
  dom.audioTimeCurrent.textContent = `재생 중: ${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

// Polling analysis task with smart 429 Rate Limit backoff & retry
async function pollAnalysisTask(taskId) {
  isAnalysisActive = true;
  dom.analysisProgressBox.classList.remove("hidden");
  dom.analysisPercentText.textContent = "0%";
  dom.analysisProgressBar.style.width = "0%";
  dom.analysisStageText.textContent = "분석 초기화 중...";
  dom.analysisEtaText.textContent = "예상 남은 시간: 계산 중...";

  return new Promise((resolve, reject) => {
    let failRetries = 0;
    const maxRetries = 30; // Up to 60 seconds tolerance for cloud Rate Limit
    let timerId = null;

    const cleanup = () => {
      if (timerId) clearTimeout(timerId);
      isAnalysisActive = false;
    };

    const doPoll = async () => {
      try {
        const res = await fetch(`/api/analysis-status/${taskId}`);

        // Handle 429 Too Many Requests specifically
        if (res.status === 429) {
          failRetries++;
          console.warn(`Analysis status hit 429 (Rate limit). Backing off 3s... (${failRetries}/${maxRetries})`);
          dom.analysisStageText.textContent = `클라우드 서버 대기열 순서 대기 중... (${failRetries})`;
          if (failRetries > maxRetries) {
            cleanup();
            dom.analysisProgressBox.classList.add("hidden");
            reject(new Error("분석 대기 시간 초과 (429 Rate Limit)"));
            return;
          }
          timerId = setTimeout(doPoll, 3000);
          return;
        }

        if (!res.ok) {
          failRetries++;
          if (failRetries <= maxRetries) {
            console.warn(`Analysis status retry ${failRetries}/${maxRetries} (${res.status})`);
            dom.analysisStageText.textContent = `클라우드 서버 연결 확인 중... (${failRetries}/${maxRetries})`;
            timerId = setTimeout(doPoll, 2000);
            return;
          }
          cleanup();
          dom.analysisProgressBox.classList.add("hidden");
          throw new Error("분석 상태 확인 실패 (서버 응답 오류: " + res.status + ")");
        }

        failRetries = 0;
        const data = await res.json();

        const pct = Math.min(100, Math.max(0, data.progress || 0));
        dom.analysisPercentText.textContent = `${pct}%`;
        dom.analysisProgressBar.style.width = `${pct}%`;
        dom.analysisStageText.textContent = data.stage || "진행 중...";
        if (data.remaining_sec !== undefined) {
          dom.analysisEtaText.textContent = pct >= 100 ? "완료!" : `남은 시간: 약 ${data.remaining_sec.toFixed(1)}초`;
        }

        if (data.status === "completed") {
          cleanup();
          setTimeout(() => dom.analysisProgressBox.classList.add("hidden"), 600);
          resolve(data.data);
          return;
        } else if (data.status === "failed") {
          cleanup();
          dom.analysisProgressBox.classList.add("hidden");
          reject(new Error(data.error || "분석 실패"));
          return;
        }

        // Schedule next check smoothly
        timerId = setTimeout(doPoll, 1500);
      } catch (e) {
        failRetries++;
        if (failRetries <= maxRetries) {
          console.warn(`Analysis status network error retry ${failRetries}/${maxRetries}`);
          timerId = setTimeout(doPoll, 2500);
          return;
        }
        cleanup();
        dom.analysisProgressBox.classList.add("hidden");
        reject(e);
      }
    };

    timerId = setTimeout(doPoll, 400);
  });
}

// Suno URL Direct Import & Decrypt
let isImportingAudio = false;
async function handleSunoUrlImport(urlOverride, forceAutoMaster = null) {
  if (isImportingAudio) return;
  const inputEl = dom.sunoUrlInput;
  let rawUrl = (urlOverride || (inputEl ? inputEl.value : "")).trim();
  if (!rawUrl) {
    if (inputEl) {
      inputEl.focus();
      inputEl.classList.add("border-rose-500");
      setTimeout(() => inputEl.classList.remove("border-rose-500"), 1500);
    }
    return;
  }

  // Extract clean Suno or YouTube URL if surrounding text or duplicate exists
  const sunoMatch = rawUrl.match(/(https?:\/\/(?:[a-z0-9-]+\.)*suno\.(?:com|ai)(?::\d+)?(?:[/?#][^\s"'<>]*)?)/i);
  const sunoIdMatch = rawUrl.match(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i);
  const ytMatch = rawUrl.match(/(https?:\/\/[^\s"'<>]+(youtube\.com|youtu\.be)[^\s"'<>]*)/i);
  if (sunoMatch) {
    rawUrl = sunoMatch[0];
  } else if (ytMatch) {
    rawUrl = ytMatch[0];
  } else if (sunoIdMatch) {
    rawUrl = `https://suno.com/song/${sunoIdMatch[0]}`;
  }

  if (inputEl) inputEl.value = rawUrl;

  const isSuno = /suno\.(com|ai)|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i.test(rawUrl);
  const isYoutube = /(youtube\.com|youtu\.be)/i.test(rawUrl);
  if (!isSuno && !isYoutube) {
    alert("올바른 Suno 또는 YouTube 링크 형식이 아닙니다.\n예:\n- https://suno.com/song/...\n- https://www.youtube.com/watch?v=...");
    return;
  }

  isImportingAudio = true;
  const autoMasterToggle = document.getElementById("suno-auto-master-toggle");
  const willAutoMaster = forceAutoMaster !== null ? forceAutoMaster : (autoMasterToggle ? autoMasterToggle.checked : true);

  if (dom.btnFetchSuno) {
    dom.btnFetchSuno.disabled = true;
    dom.btnFetchSuno.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-slate-950"></i> <span>다운로드 중...</span>`;
  }
  if (dom.sunoLinkDetectBadge) {
    dom.sunoLinkDetectBadge.classList.remove("hidden");
    dom.sunoLinkDetectBadge.textContent = "링크 감지됨 · 다운로드 및 분석 중...";
  }
  dom.analysisStatusPill.textContent = isYoutube ? "YouTube 다운로드 및 음원 추출 중..." : "Suno 다운로드 & 복호화 중...";
  dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono animate-pulse";

  try {
    const res = await fetch("/api/suno-async", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: rawUrl })
    });
    const result = await res.json();
    if (!res.ok || !result.success) {
      throw new Error(result.detail || result.error || "음원 스트림 요청 실패");
    }

    // Poll the background task (Downloads -> Decrypts -> Analyzes)
    const analyzedData = await pollAnalysisTask(result.task_id);
    applyAudioAnalysis(analyzedData);

    dom.analysisStatusPill.textContent = "분석 완료 (100%)";
    dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono";

    if (dom.sunoLinkDetectBadge) {
      dom.sunoLinkDetectBadge.classList.remove("hidden");
      setTimeout(() => dom.sunoLinkDetectBadge?.classList.add("hidden"), 3000);
    }

    if (willAutoMaster) {
      dom.analysisStatusPill.textContent = "분석 완료 -> 즉시 마스터링 생성 중...";
      dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono animate-pulse";
      setTimeout(async () => {
        try {
          await enqueueFullSongMastering();
          dom.analysisStatusPill.textContent = "마스터링 대기열 등록 완료 (Step 4 확인)";
          dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono";
        } catch (mErr) {
          console.error("Auto master error:", mErr);
          setWorkflowStep(2);
        }
      }, 350);
    } else {
      setWorkflowStep(2);
    }

  } catch (err) {
    console.error("Audio import error:", err);
    alert("음원 불러오기 실패:\n" + err.message);
    dom.analysisStatusPill.textContent = "불러오기 실패";
    dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-mono";
  } finally {
    isImportingAudio = false;
    if (dom.btnFetchSuno) {
      dom.btnFetchSuno.disabled = false;
      dom.btnFetchSuno.innerHTML = `<i class="fa-solid fa-arrow-down"></i> <span>음원 불러오기</span>`;
    }
  }
}

async function pasteSunoFromClipboard() {
  try {
    let text = "";
    if (navigator.clipboard && navigator.clipboard.readText) {
      text = await navigator.clipboard.readText();
    }
    if (text && text.trim()) {
      if (dom.sunoUrlInput) dom.sunoUrlInput.value = text.trim();
      handleSunoUrlImport(text.trim());
      return;
    }
  } catch (err) {
    console.warn("Clipboard access denied or unavailable:", err);
  }
  // Fallback: prompt dialog if clipboard permission is denied
  if (dom.sunoUrlInput) {
    dom.sunoUrlInput.focus();
    dom.sunoUrlInput.select();
    const promptVal = prompt("Suno 곡 링크(URL)를 입력해주세요:\n(예: https://suno.com/song/...)");
    if (promptVal && promptVal.trim()) {
      dom.sunoUrlInput.value = promptVal.trim();
      handleSunoUrlImport(promptVal.trim());
    }
  }
}

window.handleSunoUrlImport = handleSunoUrlImport;
window.pasteSunoFromClipboard = pasteSunoFromClipboard;

// ==========================================
// SEPARATE YOUTUBE RAW MP4 INSTANT DOWNLOADER
// ==========================================
window.pasteToYtRawInput = async function() {
  const inputEl = document.getElementById("yt-raw-url-input");
  if (!inputEl) return;
  try {
    if (navigator.clipboard && navigator.clipboard.readText) {
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        inputEl.value = text.trim();
        return;
      }
    }
  } catch (_) {}
  inputEl.focus();
  inputEl.select();
  const promptVal = prompt("유튜브 영상 링크를 입력해주세요:\n(예: https://www.youtube.com/watch?v=...)");
  if (promptVal && promptVal.trim()) {
    inputEl.value = promptVal.trim();
  }
};

window.downloadRawMp4Dedicated = async function() {
  const inputEl = document.getElementById("yt-raw-url-input");
  let rawUrl = (inputEl ? inputEl.value : "").trim();

  // If input is empty, try clipboard
  if (!rawUrl && navigator.clipboard && navigator.clipboard.readText) {
    try {
      const clipText = await navigator.clipboard.readText();
      if (clipText && /(youtube\.com|youtu\.be|suno\.(com|ai)|[0-9a-f]{8}-[0-9a-f]{4})/i.test(clipText)) {
        rawUrl = clipText.trim();
        if (inputEl) inputEl.value = rawUrl;
      }
    } catch (_) {}
  }

  if (!rawUrl) {
    if (inputEl) {
      inputEl.focus();
      inputEl.classList.add("border-red-500");
      setTimeout(() => inputEl.classList.remove("border-red-500"), 1500);
    }
    alert("다운로드할 YouTube 링크를 입력해주세요.\n(예: https://www.youtube.com/watch?v=...)");
    return;
  }

  // Extract clean URL
  const ytMatch = rawUrl.match(/(https?:\/\/[^\s"'<>]+(youtube\.com|youtu\.be)[^\s"'<>]*)/i);
  const sunoMatch = rawUrl.match(/(https?:\/\/(?:[a-z0-9-]+\.)*suno\.(?:com|ai)(?::\d+)?(?:[/?#][^\s"'<>]*)?)/i);
  const sunoIdMatch = rawUrl.match(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i);
  if (ytMatch) rawUrl = ytMatch[0];
  else if (sunoMatch) rawUrl = sunoMatch[0];
  else if (sunoIdMatch) rawUrl = `https://suno.com/song/${sunoIdMatch[0]}`;

  if (inputEl) inputEl.value = rawUrl;

  const btn = document.getElementById("btn-download-yt-raw") || document.getElementById("btn-download-raw-mp4");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-white"></i> <span>MP4 다운로드 중...</span>`;
  }

  const progressBox = document.getElementById("yt-raw-progress-box");
  const stageText = document.getElementById("yt-raw-stage-text");
  const percentText = document.getElementById("yt-raw-percent-text");
  const progressBar = document.getElementById("yt-raw-progress-bar");
  const banner = document.getElementById("yt-raw-status-banner");
  const statusMsg = document.getElementById("yt-raw-status-msg");
  const directLink = document.getElementById("yt-raw-direct-link");

  if (progressBox) progressBox.classList.remove("hidden");
  if (banner) banner.classList.add("hidden");
  if (stageText) stageText.textContent = "YouTube 영상 정보 분석 중...";
  if (percentText) percentText.textContent = "5%";
  if (progressBar) progressBar.style.width = "5%";

  try {
    const res = await fetch("/api/download/raw-mp4-async", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: rawUrl })
    });
    const result = await res.json();
    if (!res.ok || !result.success) {
      throw new Error(result.detail || result.error || "MP4 다운로드 요청 실패");
    }

    const taskId = result.task_id;
    const taskData = await new Promise((resolve, reject) => {
      const timer = setInterval(async () => {
        try {
          const sRes = await fetch(`/api/analysis-status/${taskId}`);
          if (!sRes.ok) throw new Error("진행 상태 조회 실패");
          const sData = await sRes.json();
          const p = Math.min(100, Math.max(0, sData.progress || 0));
          if (percentText) percentText.textContent = `${p}%`;
          if (progressBar) progressBar.style.width = `${p}%`;
          if (stageText) stageText.textContent = sData.stage || "다운로드 진행 중...";

          if (sData.status === "completed") {
            clearInterval(timer);
            resolve(sData.data);
          } else if (sData.status === "failed") {
            clearInterval(timer);
            reject(new Error(sData.error || "다운로드 실패"));
          }
        } catch (pollErr) {
          clearInterval(timer);
          reject(pollErr);
        }
      }, 700);
    });

    if (taskData && taskData.download_url) {
      const rawTitle = (taskData.title || "").trim();
      let saveName = rawTitle ? `${rawTitle}.mp4` : (taskData.filename || "video.mp4");
      saveName = saveName.replace(/[<>:"/\\|?*\x00-\x1f]/g, "").trim();
      if (!saveName.toLowerCase().endsWith(".mp4")) saveName += ".mp4";

      // Trigger instant browser download with exact content title
      const a = document.createElement("a");
      a.href = taskData.download_url;
      a.download = saveName;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => a.remove(), 1000);

      if (progressBox) progressBox.classList.add("hidden");
      if (banner) {
        banner.classList.remove("hidden");
        if (statusMsg) statusMsg.textContent = `✅ 다운로드 완료: ${saveName} (${taskData.filesize_mb}MB)`;
        if (directLink) {
          directLink.href = taskData.download_url;
          directLink.download = saveName;
        }
      }
    }
  } catch (err) {
    console.error("YouTube raw MP4 download error:", err);
    alert("유튜브 원본 MP4 다운로드 실패:\n" + err.message);
    if (progressBox) progressBox.classList.add("hidden");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
};
window.downloadRawMp4FromInput = window.downloadRawMp4Dedicated;

// Upload audio
async function uploadAudio(file) {
  dom.analysisStatusPill.textContent = "Suno 음원 분석 중...";
  dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono animate-pulse";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload-async", { method: "POST", body: formData });
    const result = await res.json();
    if (result.success && result.task_id) {
      const analyzedData = await pollAnalysisTask(result.task_id);
      applyAudioAnalysis(analyzedData);
      dom.analysisStatusPill.textContent = "분석 완료 (100%)";
      dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono";
      // Transition to Step 2
      setWorkflowStep(2);
    }
  } catch (err) {
    console.error("Upload error:", err);
    alert("오디오 분석 오류: " + err.message);
    dom.analysisStatusPill.textContent = "분석 오류";
    dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-mono";
  }
}

// Load Demo Track
async function loadDemoTrack() {
  dom.btnLoadDemo.disabled = true;
  dom.btnLoadDemo.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-amber-400"></i> 분석 중...`;
  dom.analysisStatusPill.textContent = "데모 분석 진행 중...";
  dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono animate-pulse";

  try {
    const res = await fetch("/api/load-sample-async", { method: "POST" });
    const result = await res.json();
    if (result.success && result.task_id) {
      const analyzedData = await pollAnalysisTask(result.task_id);
      applyAudioAnalysis(analyzedData);
      dom.analysisStatusPill.textContent = "분석 완료 (100%)";
      dom.analysisStatusPill.className = "text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono";
      // Transition to Step 2
      setWorkflowStep(2);
    }
  } catch (err) {
    console.error("Demo load error:", err);
    alert("데모 트랙 로드 오류: " + err.message);
  } finally {
    dom.btnLoadDemo.disabled = false;
    dom.btnLoadDemo.innerHTML = `<i class="fa-solid fa-bolt text-amber-400"></i> <span>Suno 테스트 음원 불러오기</span>`;
  }
}

// Apply audio analysis
function applyAudioAnalysis(data) {
  state.audio = data;
  state.currentTrackData = data;
  state.duration = data.duration;
  state.audioElement.src = data.audio_url;
  state.originalAudioUrl = data.audio_url;
  state.originalFilename = data.filename || "Suno 오디오 트랙";

  // Seamless Bridge with v3.0 Studio
  if (window.v3Studio && typeof window.v3Studio.loadAudio === "function") {
    window.v3Studio.loadAudio(data.audio_url, state.originalFilename);
  }

  // Auto-update Hum Studio active track card & auto-sync
  if (typeof updateHumActiveStudioCard === "function") {
    updateHumActiveStudioCard();
  }

  // Diagnostics
  dom.diagContainer.classList.remove("hidden");
  
  // Robust Tempo Drift
  const tInfo = data.tempo_analysis || {};
  dom.diagStartBpm.textContent = `${tInfo.start_bpm || 100.0} BPM`;
  dom.diagEndBpm.textContent = `${tInfo.end_bpm || 104.0} BPM`;
  dom.diagDriftRate.textContent = `${tInfo.drift_percent > 0 ? "+" : ""}${tInfo.drift_percent || 0.0}%`;
  
  if (tInfo.is_accelerating) {
    dom.tempoDriftBadge.textContent = "미세 가속 감지됨";
    dom.tempoDriftBadge.className = "badge-tag bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold";
    dom.diagTempoDesc.textContent = `시작 ${tInfo.start_bpm} BPM에서 곡 후반부로 갈수록 서서히 ${tInfo.end_bpm} BPM으로 빨라지고 있습니다. 3단계에서 시작 BPM에 완벽히 평탄화할 수 있습니다.`;
  } else {
    dom.tempoDriftBadge.textContent = "일정 템포 유지됨";
    dom.tempoDriftBadge.className = "badge-tag bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
    dom.diagTempoDesc.textContent = `옥타브 락킹 분석 결과, 곡 전체 템포가 안정적으로 유지되고 있습니다.`;
  }

  // Multi-Filter Composite Watermark Analysis
  const wInfo = data.watermark_analysis || {};
  if (dom.diagWatermarkConf) dom.diagWatermarkConf.textContent = `신뢰도 ${wInfo.confidence || 0}%`;

  const filters = wInfo.filters || {};
  const fCarrier = filters.carrier_spikes || {};
  const fPhase = filters.phase_anomaly || {};
  const fShelf = filters.energy_shelf || {};
  const fPeriod = filters.periodicity || {};

  const carrierDetected = fCarrier.detected ?? wInfo.carrier_spike_detected ?? false;
  const carrierPromDb = fCarrier.prominence_db ?? wInfo.carrier_prominence_db ?? 0;
  const carrierFreqs = fCarrier.frequencies || (wInfo.carrier_freq_hz ? [wInfo.carrier_freq_hz] : []);
  const carrierFreqStr = carrierFreqs.length > 0 ? `${(carrierFreqs[0] / 1000).toFixed(1)}kHz` : "초고역";

  if (dom.wmFilterCarrier) {
    if (carrierDetected) {
      dom.wmFilterCarrier.innerHTML = `<span class="text-rose-400 font-bold">+${carrierPromDb}dB (${carrierFreqStr} 피크 감지)</span>`;
    } else {
      dom.wmFilterCarrier.innerHTML = `<span class="text-emerald-400 font-semibold">정상 (파일럿 피크 없음)</span>`;
    }
  }

  const phaseDetected = fPhase.detected ?? wInfo.phase_disparity_detected ?? false;
  const phaseDeg = fPhase.disparity_deg ?? wInfo.phase_disparity_deg ?? 0;
  if (dom.wmFilterPhase) {
    if (phaseDetected) {
      dom.wmFilterPhase.innerHTML = `<span class="text-rose-400 font-bold">${phaseDeg}° (비자연적 위상 변조)</span>`;
    } else {
      dom.wmFilterPhase.innerHTML = `<span class="text-emerald-400 font-semibold">${phaseDeg > 0 ? phaseDeg + '° ' : ''}정상 (위상 일관성 유지)</span>`;
    }
  }

  const shelfDetected = fShelf.detected ?? wInfo.shelf_excess_detected ?? false;
  const shelfExcess = fShelf.excess_db ?? wInfo.shelf_excess_ratio ?? 0;
  if (dom.wmFilterShelf) {
    if (shelfDetected) {
      dom.wmFilterShelf.innerHTML = `<span class="text-amber-400 font-bold">+${shelfExcess}dB (초고역 쉘프 초과)</span>`;
    } else {
      dom.wmFilterShelf.innerHTML = `<span class="text-emerald-400 font-semibold">정상 (자연 감쇄 프로파일)</span>`;
    }
  }

  const periodDetected = fPeriod.detected ?? wInfo.sync_pulses_detected ?? false;
  const periodMs = fPeriod.pulse_interval_ms ?? wInfo.frame_period_ms ?? 0;
  if (dom.wmFilterPeriod) {
    if (periodDetected) {
      dom.wmFilterPeriod.innerHTML = `<span class="text-rose-400 font-bold">주기 ${periodMs}ms (동기 펄스 감지)</span>`;
    } else {
      dom.wmFilterPeriod.innerHTML = `<span class="text-emerald-400 font-semibold">미검출 (비동기 패턴)</span>`;
    }
  }

  if (dom.wmCompositeSummary) {
    dom.wmCompositeSummary.textContent = wInfo.summary || wInfo.description || (wInfo.detected ? "4단계 복합 필터에 의해 AI 비가청 워터마크가 감지되었습니다." : "복합 필터 검사 완료: 인공 워터마크 패턴이 감지되지 않았습니다.");
  }

  if (wInfo.detected) {
    dom.watermarkBadge.textContent = "복합 지문 탐지";
    dom.watermarkBadge.className = "badge-tag bg-rose-500/20 text-rose-300 border border-rose-500/30 font-semibold";
  } else {
    dom.watermarkBadge.textContent = "워터마크 미탐지";
    dom.watermarkBadge.className = "badge-tag bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
  }

  // Loudness & Meta
  dom.diagLufs.textContent = `${data.input_lufs || -16.0} LUFS`;
  dom.diagDuration.textContent = data.duration_str;
  dom.audioTimeTotal.textContent = data.duration_str;

  // Sliders range initialization
  dom.startTimeSlider.max = Math.max(0, data.duration - 5);
  dom.startTimeSlider.value = 0;
  dom.durationSlider.max = data.duration;
  dom.durationSlider.value = Math.min(15.0, data.duration);
  state.selectedSegment.start = 0.0;
  state.selectedSegment.duration = Math.min(15.0, data.duration);
  dom.startTimeVal.textContent = "0.0초";
  dom.durationVal.textContent = `${state.selectedSegment.duration.toFixed(1)}초`;

  // Smart Recommendations: Store and auto-populate
  state.smartRecommendations = data.smart_recommendations || null;
  if (state.smartRecommendations && dom.smartRecSummary) {
    dom.smartRecSummary.textContent = state.smartRecommendations.reason_summary || state.smartRecommendations.summary || "음향 밸런스를 측정하여 최적의 마스터링 파라미터를 추천값으로 자동 반영했습니다.";
    applySmartRecommendations(false);
  }

  // Update track title and filename banner
  const trackTitle = data.title || (data.filename ? data.filename.replace(/\.[^/.]+$/, "").replace(/^\d+_/, "") : "SunoTrack");
  const trackFilename = data.filename || `${trackTitle}.mp3`;

  const bannerTitle = document.getElementById("loaded-track-title");
  const bannerFilename = document.getElementById("loaded-track-filename");
  if (bannerTitle) bannerTitle.textContent = trackTitle;
  if (bannerFilename) bannerFilename.textContent = trackFilename;

  // Update Suno Speed Card info & default rate
  if (dom.sunoSpeedTrackName) dom.sunoSpeedTrackName.textContent = trackTitle;
  if (dom.sunoSpeedTime) dom.sunoSpeedTime.textContent = `00:00 / ${data.duration_str || "00:00"}`;
  if (dom.iconSpeedThumbPlay) dom.iconSpeedThumbPlay.className = "fa-solid fa-play text-white text-xs";
  
  if (dom.btnSpeedThumbPlay) {
    if (data.image_url) {
      dom.btnSpeedThumbPlay.style.backgroundImage = `url("${data.image_url}")`;
      dom.btnSpeedThumbPlay.style.backgroundSize = "cover";
      dom.btnSpeedThumbPlay.style.backgroundPosition = "center";
    } else {
      dom.btnSpeedThumbPlay.style.backgroundImage = "";
    }
  }

  if (state.audioElement && dom.sunoSpeedSlider) {
    const curSpd = parseFloat(dom.sunoSpeedSlider.value) || 1.0;
    state.audioElement.playbackRate = curSpd;
    state.audioElement.preservesPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;
  }

  updateEndingTimeCalculation();
  if (dom.sunoSpeedSeekSlider) dom.sunoSpeedSeekSlider.value = "0";
  if (dom.sunoSpeedSeekTimeDisplay) dom.sunoSpeedSeekTimeDisplay.textContent = `00:00 / ${data.duration_str || "00:00"}`;
  drawWaveform(data.waveform_peaks || []);
  updateSelectionOverlay();
  if (dom.draftNameInput) {
    dom.draftNameInput.dataset.userEdited = "false";
  }
  updateDraftNameInput(true);
  updateSpeedBadge();
  populateSunoV6Prompt(data);
}

function applySmartRecommendations(showNotice = false) {
  const rec = state.smartRecommendations;
  if (!rec) return;

  if (dom.masteringTargetSelect && rec.target_lufs !== undefined) {
    const tFloat = parseFloat(rec.target_lufs);
    const matchedOpt = Array.from(dom.masteringTargetSelect.options).find(o => Math.abs(parseFloat(o.value) - tFloat) < 0.1);
    dom.masteringTargetSelect.value = matchedOpt ? matchedOpt.value : "-14.0";
  }
  if (dom.toggleAutoLevel) {
    dom.toggleAutoLevel.checked = Boolean(rec.auto_leveling ?? rec.auto_level ?? true);
  }
  if (dom.toggleDewatermark) {
    dom.toggleDewatermark.checked = Boolean(rec.dewatermark_enabled ?? rec.dewatermark ?? true);
  }
  if (dom.toggleTempoStabilize) {
    dom.toggleTempoStabilize.checked = Boolean(rec.tempo_stabilize_enabled ?? rec.tempo_stabilize ?? true);
  }
  if (dom.eqBassSlider && rec.bass_boost_db !== undefined) {
    dom.eqBassSlider.value = rec.bass_boost_db;
    dom.eqBassVal.textContent = `${rec.bass_boost_db > 0 ? "+" : ""}${Number(rec.bass_boost_db).toFixed(1)} dB`;
  }
  if (dom.eqMidSlider && rec.mid_presence_db !== undefined) {
    dom.eqMidSlider.value = rec.mid_presence_db;
    dom.eqMidVal.textContent = `${rec.mid_presence_db > 0 ? "+" : ""}${Number(rec.mid_presence_db).toFixed(1)} dB`;
  }
  if (dom.eqAirSlider && rec.air_band_boost_db !== undefined) {
    dom.eqAirSlider.value = rec.air_band_boost_db;
    dom.eqAirVal.textContent = `+${Number(rec.air_band_boost_db).toFixed(1)} dB`;
  }
  if (dom.stereoSlider && rec.stereo_width !== undefined) {
    dom.stereoSlider.value = rec.stereo_width;
    dom.stereoVal.textContent = `${Math.round(rec.stereo_width * 100)}%`;
  }
  if (dom.warmthSlider && rec.tape_warmth !== undefined) {
    dom.warmthSlider.value = rec.tape_warmth;
    dom.warmthVal.textContent = `${Math.round(rec.tape_warmth * 100)}%`;
  }

  // Update speech bubble recommendation text
  const reasons = rec.details || rec.reasons || {};
  const isDewater = rec.dewatermark_enabled ?? rec.dewatermark ?? true;
  const isTempo = rec.tempo_stabilize_enabled ?? rec.tempo_stabilize ?? true;

  if (dom.tipRecBass) dom.tipRecBass.textContent = `AI 추천: ${reasons.bass_reason || reasons.bass || (rec.bass_boost_db > 0 ? `저역 보강 +${rec.bass_boost_db}dB` : '중립 유지')}`;
  if (dom.tipRecMid) dom.tipRecMid.textContent = `AI 추천: ${reasons.mid_reason || reasons.mid || (rec.mid_presence_db > 0 ? `보컬 명료도 +${rec.mid_presence_db}dB` : '원음 보존')}`;
  if (dom.tipRecAir) dom.tipRecAir.textContent = `AI 추천: ${reasons.air_reason || reasons.air || `초고역 공기감 복원 +${rec.air_band_boost_db}dB`}`;
  if (dom.tipRecWidth) dom.tipRecWidth.textContent = `AI 추천: ${reasons.width_reason || reasons.width || `스테레오 무대감 ${Math.round(rec.stereo_width * 100)}%`}`;
  if (dom.tipRecWarmth) dom.tipRecWarmth.textContent = `AI 추천: ${reasons.warmth_reason || reasons.warmth || `배음 온기 ${Math.round(rec.tape_warmth * 100)}%`}`;
  if (dom.tipRecTempo) dom.tipRecTempo.textContent = `AI 추천: ${reasons.tempo_reason || reasons.tempo || (isTempo ? "템포 가속 감지로 평탄화 활성화" : "템포 안정적")}`;
  if (dom.tipRecLufs) dom.tipRecLufs.textContent = `AI 추천: ${reasons.lufs_reason || reasons.lufs || `타깃 ${rec.target_lufs} LUFS`}`;
  if (dom.tipRecAutolevel) dom.tipRecAutolevel.textContent = `AI 추천: ${reasons.autolevel_reason || reasons.autolevel || "볼륨 편차 자동 정돈 활성화"}`;

  updateDraftNameInput();
  updateLiveDspParameters();

  if (showNotice && dom.smartRecCard) {
    dom.smartRecCard.classList.add("ring-2", "ring-purple-400");
    setTimeout(() => dom.smartRecCard.classList.remove("ring-2", "ring-purple-400"), 1200);
  }
}

function resetToDefaults() {
  if (dom.masteringTargetSelect) dom.masteringTargetSelect.value = "-14.0";
  if (dom.toggleAutoLevel) dom.toggleAutoLevel.checked = true;
  if (dom.toggleDewatermark) dom.toggleDewatermark.checked = true;
  if (dom.toggleTempoStabilize) dom.toggleTempoStabilize.checked = true;
  if (dom.eqBassSlider) {
    dom.eqBassSlider.value = 1.0;
    dom.eqBassVal.textContent = "+1.0 dB";
  }
  if (dom.eqMidSlider) {
    dom.eqMidSlider.value = 0.5;
    dom.eqMidVal.textContent = "+0.5 dB";
  }
  if (dom.eqAirSlider) {
    dom.eqAirSlider.value = 1.5;
    dom.eqAirVal.textContent = "+1.5 dB";
  }
  if (dom.stereoSlider) {
    dom.stereoSlider.value = 1.15;
    dom.stereoVal.textContent = "115%";
  }
  if (dom.warmthSlider) {
    dom.warmthSlider.value = 0.08;
    dom.warmthVal.textContent = "8%";
  }
  if (dom.sunoSpeedSlider) {
    dom.sunoSpeedSlider.value = "1.00";
    if (dom.sunoSpeedValDisplay) dom.sunoSpeedValDisplay.textContent = "1.00x";
  }
  if (dom.sunoPitchSlider) {
    dom.sunoPitchSlider.value = "0";
    if (dom.sunoPitchValDisplay) dom.sunoPitchValDisplay.textContent = "0 (원음)";
  }
  if (dom.toggleKeepPitch) {
    dom.toggleKeepPitch.checked = true;
  }
  if (state.audioElement) {
    state.audioElement.playbackRate = 1.0;
    state.audioElement.preservesPitch = true;
  }
  updateDraftNameInput();
  updateLiveDspParameters();
}

function formatTime(sec) {
  if (isNaN(sec) || sec < 0) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

window.applySmartRecommendations = applySmartRecommendations;
window.resetToDefaults = resetToDefaults;

// Clean helper to extract pure song title without draft tags
function extractCleanSongTitle(inputVal, fallbackTitle = "SunoTrack") {
  if (!inputVal || !inputVal.trim()) return fallbackTitle;
  let s = inputVal.trim();
  s = s.replace(/^\[(?:완곡\s*마스터|마스터)[^\]]*\]\s*/i, "");
  s = s.replace(/\s*-\s*마스터\s+[A-Z].*$/i, "");
  s = s.replace(/\s*\(-?\d+(?:\.\d+)?\s*LUFS.*?\)$/i, "");
  s = s.replace(/\s*\[(?:\d+(?:\.\d+)?x|\+?-?\d+(?:\.\d+)?st)[^\]]*\]/gi, "");
  s = s.trim();
  return s || inputVal.trim() || fallbackTitle;
}

function updateDraftNameInput(force = false) {
  if (!dom.draftNameInput) return;
  // If user already manually edited the title, do not overwrite unless forced
  if (!force && dom.draftNameInput.dataset.userEdited === "true") {
    return;
  }
  const trackTitle = state.audio?.title || (state.audio?.filename ? state.audio.filename.replace(/\.[^/.]+$/, "").replace(/^\d+_/, "") : "");
  if (trackTitle) {
    dom.draftNameInput.value = trackTitle;
  }
}

function drawWaveform(peaks) {
  const canvas = dom.waveformCanvas;
  const ctx = canvas.getContext("2d");
  const rect = dom.waveformContainer.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);
  if (!peaks || peaks.length === 0) return;

  const barCount = peaks.length;
  const barWidth = Math.max(1.8, w / barCount);
  const midY = h / 2;

  const grad = ctx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, "#00f2fe");
  grad.addColorStop(0.35, "#38bdf8");
  grad.addColorStop(0.7, "#818cf8");
  grad.addColorStop(1, "#c084fc");
  ctx.fillStyle = grad;

  for (let i = 0; i < barCount; i++) {
    const x = i * (w / barCount);
    const val = peaks[i];
    const barH = Math.max(2, val * (h * 0.88));
    const y = midY - barH / 2;
    // Draw rounded bar with 2027 aesthetic
    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth - 0.4, barH, 2);
      ctx.fill();
    } else {
      ctx.fillRect(x, y, barWidth - 0.4, barH);
    }
  }
}

function updateSelectionOverlay() {
  if (!state.duration || state.duration <= 0) return;
  const startRatio = state.selectedSegment.start / state.duration;
  const durRatio = state.selectedSegment.duration / state.duration;

  const leftPercent = Math.min(100, Math.max(0, startRatio * 100));
  const widthPercent = Math.min(100 - leftPercent, durRatio * 100);

  dom.selectionOverlay.style.left = `${leftPercent}%`;
  dom.selectionOverlay.style.width = `${widthPercent}%`;

  const endSec = (state.selectedSegment.start + state.selectedSegment.duration).toFixed(1);
  dom.selectionSummary.textContent = `구간: ${state.selectedSegment.start.toFixed(1)}s ~ ${endSec}s (${state.selectedSegment.duration.toFixed(1)}초)`;
}

// Enqueue Full Song Mastering Job (Whole track rendered with current speed directly baked in)
async function enqueueFullSongMastering() {
  const sourcePath = state.audio?.file_path || state.audio?.audio_url || state.currentTrackData?.file_path || state.originalAudioUrl;
  if (!state.audio || !sourcePath) {
    alert("마스터링할 음원이 준비되지 않았습니다.\n먼저 Step 1(01 음원 불러오기)에서 음원 링크를 입력하거나 오디오 파일을 업로드해주세요.");
    return;
  }

  stopSectionPlayback();

  const safeNum = (el, fallback) => {
    if (!el) return fallback;
    const v = parseFloat(el.value);
    return isNaN(v) ? fallback : v;
  };

  const inputVal = dom.draftNameInput ? dom.draftNameInput.value.trim() : "";
  const originalTitle = state.audio?.title || (state.audio?.filename ? state.audio.filename.replace(/\.[^/.]+$/, "").replace(/^\d+_/, "") : "SunoTrack");
  const trackTitle = extractCleanSongTitle(inputVal, originalTitle);

  // Sync state.audio.title to the user's edited title
  if (state.audio) {
    state.audio.title = trackTitle;
  }

  const speedRatio = safeNum(dom.sunoSpeedSlider, 1.0);
  const pitchShift = (state.pitchShift !== undefined) ? state.pitchShift : safeNum(dom.sunoPitchSlider, 0.0);
  const keepPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true;
  const targetLufs = safeNum(dom.masteringTargetSelect, -14.0);

  const speedTag = Math.abs(speedRatio - 1.0) > 0.005 ? ` [${speedRatio.toFixed(2)}x ${keepPitch ? 'Pitch' : 'Vinyl'}]` : "";
  const pitchTag = Math.abs(pitchShift) > 0.005 ? ` [Key ${pitchShift > 0 ? '+' : ''}${pitchShift.toFixed(2)}st]` : "";
  const draftName = `[완곡 마스터] ${trackTitle}${speedTag}${pitchTag} (${targetLufs} LUFS)`;

  const masteringOptions = {
    track_title: trackTitle,
    dewatermark_enabled: dom.toggleDewatermark ? dom.toggleDewatermark.checked : true,
    tempo_stabilize_enabled: dom.toggleTempoStabilize ? dom.toggleTempoStabilize.checked : true,
    tempo_info: state.audio.tempo_analysis,
    pitch_shift: pitchShift,
    speed_ratio: speedRatio,
    keep_pitch: keepPitch,
    target_lufs: targetLufs,
    auto_leveling: dom.toggleAutoLevel ? dom.toggleAutoLevel.checked : true,
    bass_boost_db: safeNum(dom.eqBassSlider, 1.0),
    mid_presence_db: safeNum(dom.eqMidSlider, 0.5),
    air_band_boost_db: safeNum(dom.eqAirSlider, 1.5),
    stereo_width: safeNum(dom.stereoSlider, 1.15),
    tape_warmth: safeNum(dom.warmthSlider, 0.08),
    limiter_ceiling_db: -1.0
  };

  const payload = {
    name: draftName,
    track_title: trackTitle,
    job_type: "full",
    source_audio_path: sourcePath || state.audio.file_path,
    start_sec: 0.0,
    duration_sec: state.duration || 0.0,
    mastering_options: masteringOptions
  };

  const btn = dom.btnEnqueueFullMaster;
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-slate-950"></i> <span>완곡 대기열 등록 중...</span>`;
  }

  try {
    const res = await fetch("/api/queue/enqueue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.success) {
      setWorkflowStep(4);
      pollQueue();
    } else {
      alert("완곡 마스터링 대기열 등록 실패: " + result.detail);
    }
  } catch (err) {
    console.error("Enqueue full mastering error:", err);
    alert("완곡 마스터링 요청 오류: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-base"></i> <span id="text-enqueue-full-master"></span>`;
      updateSpeedBadge();
    }
  }
}
window.enqueueFullSongMastering = enqueueFullSongMastering;

// Enqueue Mastering Preview Job
async function enqueuePreviewMastering() {
  if (!state.audio) {
    alert("먼저 분석할 Suno 음원을 업로드해주세요!");
    return;
  }

  stopSectionPlayback();

  const safeNum = (el, fallback) => {
    if (!el) return fallback;
    const v = parseFloat(el.value);
    return isNaN(v) ? fallback : v;
  };

  const inputVal = dom.draftNameInput ? dom.draftNameInput.value.trim() : "";
  const originalTitle = state.audio?.title || (state.audio?.filename ? state.audio.filename.replace(/\.[^/.]+$/, "").replace(/^\d+_/, "") : "SunoTrack");
  const trackTitle = extractCleanSongTitle(inputVal, originalTitle);

  // Sync state.audio.title to the user's edited title
  if (state.audio) {
    state.audio.title = trackTitle;
  }

  const letter = state.alphabets[state.draftIndex % state.alphabets.length];
  const targetLufs = safeNum(dom.masteringTargetSelect, -14.0);
  const draftName = `${trackTitle} - 마스터 ${letter} (${targetLufs} LUFS)`;
  const pitchShift = (state.pitchShift !== undefined) ? state.pitchShift : safeNum(dom.sunoPitchSlider, 0.0);

  const masteringOptions = {
    track_title: trackTitle,
    dewatermark_enabled: dom.toggleDewatermark ? dom.toggleDewatermark.checked : true,
    tempo_stabilize_enabled: dom.toggleTempoStabilize ? dom.toggleTempoStabilize.checked : true,
    tempo_info: state.audio.tempo_analysis,
    pitch_shift: pitchShift,
    speed_ratio: safeNum(dom.sunoSpeedSlider, 1.0),
    keep_pitch: dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : true,
    target_lufs: safeNum(dom.masteringTargetSelect, -14.0),
    auto_leveling: dom.toggleAutoLevel ? dom.toggleAutoLevel.checked : true,
    bass_boost_db: safeNum(dom.eqBassSlider, 1.0),
    mid_presence_db: safeNum(dom.eqMidSlider, 0.5),
    air_band_boost_db: safeNum(dom.eqAirSlider, 1.5),
    stereo_width: safeNum(dom.stereoSlider, 1.15),
    tape_warmth: safeNum(dom.warmthSlider, 0.08),
    limiter_ceiling_db: -1.0
  };

  const sourcePath = state.audio?.file_path || state.audio?.audio_url || state.currentTrackData?.file_path || state.originalAudioUrl;
  if (!state.audio || !sourcePath) {
    alert("미리듣기할 음원이 준비되지 않았습니다.\n먼저 음원을 업로드하거나 분석을 완료해주세요.");
    return;
  }

  const payload = {
    name: draftName,
    track_title: trackTitle,
    job_type: "preview",
    source_audio_path: sourcePath || state.audio.file_path,
    start_sec: state.selectedSegment.start,
    duration_sec: state.selectedSegment.duration,
    mastering_options: masteringOptions
  };

  try {
    dom.btnEnqueuePreview.disabled = true;
    dom.btnEnqueuePreview.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 대기열 등록 중...`;

    const res = await fetch("/api/queue/enqueue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.success) {
      state.draftIndex++;
      updateDraftNameInput();
      // Transition to Step 4 (Comparison Room)
      setWorkflowStep(4);
      pollQueue();
    } else {
      alert("대기열 등록 실패: " + result.detail);
    }
  } catch (err) {
    console.error("Enqueue error:", err);
  } finally {
    dom.btnEnqueuePreview.disabled = false;
    dom.btnEnqueuePreview.innerHTML = `<i class="fa-solid fa-bolt text-cyan-400"></i> <span>⚡ 15초 구간 고속 미리듣기 렌더링 (배속 반영)</span>`;
  }
}

let queuePollTimer = null;
let isAnalysisActive = false;

function startQueuePolling() {
  pollQueue();
  scheduleNextQueuePoll();
}

function scheduleNextQueuePoll() {
  if (queuePollTimer) clearTimeout(queuePollTimer);
  // While audio import/analysis is active, back off queue polling to avoid 429 Rate Limits
  if (isAnalysisActive) {
    queuePollTimer = setTimeout(scheduleNextQueuePoll, 6000);
    return;
  }
  const hasActiveJob = state.jobs && state.jobs.some(j => j.status === "processing" || j.status === "pending" || j.status === "queued");
  const delay = hasActiveJob ? 2500 : 8000;
  queuePollTimer = setTimeout(async () => {
    try {
      await pollQueue();
    } catch(e) {
      // ignore transient queue errors
    } finally {
      scheduleNextQueuePoll();
    }
  }, delay);
}

async function pollQueue() {
  try {
    const res = await fetch("/api/queue/jobs");
    const data = await res.json();
    const jobs = data.jobs || [];
    state.jobs = jobs;

    dom.queueBadge.textContent = `대기열: ${data.queue_length}개`;

    const activeJob = jobs.find(j => j.status === "processing" || j.status === "pending" || j.status === "queued");
    if (activeJob) {
      dom.activeJobBox.classList.remove("hidden");
      dom.activeJobName.textContent = activeJob.name;
      dom.activeJobPercent.textContent = `${activeJob.progress || 10}%`;
      dom.activeJobBar.style.width = `${activeJob.progress || 15}%`;
      dom.activeJobBar.className = "bg-cyan-400 h-1.5 rounded-full transition-all duration-300";
      dom.activeJobMsg.textContent = activeJob.progress_msg || "마스터링 작업 진행 중...";
    } else {
      const failedJob = jobs.find(j => j.status === "failed");
      const completedJobs = jobs.filter(j => j.status === "completed");
      if (failedJob && completedJobs.length === 0) {
        dom.activeJobBox.classList.remove("hidden");
        dom.activeJobName.textContent = `❌ ${failedJob.name} 렌더링 오류`;
        dom.activeJobPercent.textContent = "에러";
        dom.activeJobBar.style.width = "100%";
        dom.activeJobBar.className = "bg-rose-500 h-1.5 rounded-full";
        dom.activeJobMsg.textContent = failedJob.error_msg || "마스터링 처리 중 오류가 발생했습니다.";
      } else {
        dom.activeJobBox.classList.add("hidden");
      }
    }

    renderCompletedDrafts(jobs.filter(j => j.status === "completed"));

  } catch (err) {
    console.error("pollQueue error:", err);
  }
}

function renderCompletedDrafts(completedJobs) {
  dom.draftsCountBadge.textContent = `${completedJobs.length}개 시안`;

  if (completedJobs.length === 0) {
    dom.draftsEmptyState.classList.remove("hidden");
    return;
  }
  dom.draftsEmptyState.classList.add("hidden");

  // Sync latest master with 3-Way Instant Audio Monitor (C)
  const latestJob = completedJobs[completedJobs.length - 1];
  if (latestJob && latestJob.master_audio_url) {
    state.lastRenderedMasterUrl = latestJob.master_audio_url;
    state.lastRenderedMasterName = latestJob.name;
    const cStatus = document.getElementById("monitor-c-status");
    if (cStatus) {
      cStatus.textContent = "청음 준비 완료";
      cStatus.className = "text-[8.5px] font-mono text-emerald-400 font-bold";
    }
  }

  // Keep existing cards and prepend new ones without destroying audio tags!
  completedJobs.forEach(job => {
    const cardId = `master-card-${job.id}`;
    let card = document.getElementById(cardId);
    if (card) return;

    const meta = job.metadata || {};
    card = document.createElement("div");
    card.id = cardId;
    card.className = "draft-card-pro flex flex-col gap-3";

    const isFullRender = job.type === "full";
    const typeBadge = isFullRender 
      ? `<span class="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-bold font-mono">완곡 전체 마스터</span>` 
      : `<span class="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold font-mono">미리듣기 (${meta.duration || 15}s)</span>`;

    const watermarkStatus = meta.watermark_removed
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">지문 삭제</span>`
      : ``;

    const tempoStatus = meta.tempo_stabilized
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">템포 평탄화</span>`
      : ``;

    const speedRatio = job.mastering_options?.speed_ratio ? parseFloat(job.mastering_options.speed_ratio) : (meta.speed_ratio ? parseFloat(meta.speed_ratio) : 1.0);
    const keepPitch = job.mastering_options?.keep_pitch ?? meta.keep_pitch ?? true;
    const speedStatus = (Math.abs(speedRatio - 1.0) > 0.005)
      ? `<span class="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold font-mono">⚡ ${speedRatio.toFixed(2)}x ${keepPitch ? 'Pitch유지' : 'Vinyl'}</span>`
      : `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-850 text-slate-400 border border-white/5 font-mono">1.00x</span>`;

    const origAudioUrl = state.audio?.audio_url || (job.source_audio_path ? (job.source_audio_path.includes("samples") ? "/samples/" + job.source_audio_path.split(/[\\/]/).pop() : "/uploads/" + job.source_audio_path.split(/[\\/]/).pop()) : "");
    const gainDiff = ((meta.output_lufs || -14.0) - (meta.input_lufs || -16.0)).toFixed(1);

    card.innerHTML = `
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-1 border-b border-white/5">
        <div class="flex items-center gap-2">
          <span class="text-cyan-400 text-sm"><i class="fa-solid fa-compact-disc"></i></span>
          <div>
            <h4 class="text-xs font-bold text-white">${job.name}</h4>
            <p class="text-[10px] text-slate-400 font-mono">목표: ${meta.target_lufs} LUFS • 렌더: ${meta.render_time_sec || 0}s</p>
          </div>
        </div>
        <div class="flex items-center gap-1">
          ${typeBadge}
          ${speedStatus}
          ${watermarkStatus}
          ${tempoStatus}
        </div>
      </div>

      <!-- Filename Indicator -->
      <div class="flex items-center gap-1.5 text-[10px] text-slate-400 bg-[#0e111a] px-2 py-1 rounded border border-white/5 font-mono truncate">
        <i class="fa-solid fa-file-waveform text-cyan-400 shrink-0"></i>
        <span class="truncate" title="${job.filename || job.name + '.wav'}">${job.filename || job.name + '.wav'}</span>
      </div>

      <!-- Visual Difference Spectrum Canvas -->
      <div class="daw-inset p-2.5 flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-[10px]">
          <span class="font-bold text-slate-200 flex items-center gap-1.5">
            <i class="fa-solid fa-chart-area text-cyan-400"></i> 주파수 스펙트럼 커브 육안 비교 (Before vs After)
          </span>
          <div class="flex items-center gap-2 font-mono text-[9px]">
            <span class="flex items-center gap-1 text-sky-400"><span class="inline-block w-2.5 h-0.5 bg-sky-400 border-dashed"></span> 원본</span>
            <span class="flex items-center gap-1 text-emerald-400"><span class="inline-block w-2.5 h-0.5 bg-emerald-400"></span> 마스터</span>
            <span class="text-rose-400 font-semibold">✂️ 18.5k LPF</span>
          </div>
        </div>
        <div class="relative w-full h-24 bg-[#07090e] rounded overflow-hidden border border-white/5">
          <canvas id="spectrum-canvas-${job.id}" class="w-full h-full"></canvas>
        </div>
      </div>

      <!-- Visual Metrics Before vs After Dashboard -->
      <div class="grid grid-cols-3 gap-1.5 text-[10px] bg-[#0e111a] p-2 rounded border border-white/5 font-mono">
        <div class="flex flex-col gap-0.5 border-r border-white/5 pr-1.5">
          <span class="text-slate-400 text-[9px]">통합 음압 (LUFS)</span>
          <div class="flex items-center justify-between">
            <span class="text-slate-400">${meta.input_lufs}</span>
            <span class="text-slate-600">➔</span>
            <span class="text-cyan-300 font-bold">${meta.output_lufs}</span>
          </div>
          <span class="text-[8.5px] text-cyan-400 font-mono">${gainDiff > 0 ? '+' : ''}${gainDiff} LUFS 이득</span>
        </div>

        <div class="flex flex-col gap-0.5 border-r border-white/5 pr-1.5">
          <span class="text-slate-400 text-[9px]">True Peak (리미터)</span>
          <div class="flex items-center justify-between">
            <span class="text-slate-400">${meta.metrics_before?.peak_db ?? -2.4}</span>
            <span class="text-slate-600">➔</span>
            <span class="text-emerald-400 font-bold">${meta.metrics_after?.peak_db ?? -1.0} dB</span>
          </div>
          <span class="text-[8.5px] text-emerald-400 font-mono truncate">클리핑 방지 리미팅</span>
        </div>

        <div class="flex flex-col gap-0.5">
          <span class="text-slate-400 text-[9px]">스테레오 M/S 폭</span>
          <div class="flex items-center justify-between">
            <span class="text-slate-400">100%</span>
            <span class="text-slate-600">➔</span>
            <span class="text-purple-300 font-bold">${meta.metrics_after?.stereo_width_pct ?? 115}%</span>
          </div>
          <span class="text-[8.5px] text-purple-300 font-mono truncate">입체감 무대 확장</span>
        </div>
      </div>

      <!-- Synchronized 0-Latency A/B Comparison Player -->
      <div class="bg-[#090b10] p-2.5 rounded-lg border border-white/10 flex flex-col gap-2">
        <audio id="audio-orig-${job.id}" src="${origAudioUrl}" preload="auto"></audio>
        <audio id="audio-mast-${job.id}" src="${job.result_url}" preload="auto"></audio>

        <!-- A/B Instant Switch Buttons -->
        <div class="flex items-center gap-2">
          <button type="button" id="btn-ab-a-${job.id}" class="ab-switch-btn flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500">
            <i class="fa-solid fa-headphones text-[10px]"></i>
            <span>[A] 원본 (Before)</span>
          </button>

          <button type="button" id="btn-ab-b-${job.id}" class="ab-switch-btn ab-btn-active-b flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer">
            <i class="fa-solid fa-wand-magic-sparkles text-[10px]"></i>
            <span>[B] 마스터 (After)</span>
          </button>
        </div>

        <!-- Transport Controls -->
        <div class="flex items-center gap-2.5 pt-1">
          <button type="button" id="btn-ab-play-${job.id}" class="w-8 h-8 rounded-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold flex items-center justify-center transition shrink-0 cursor-pointer shadow-md shadow-cyan-500/20">
            <i class="fa-solid fa-play text-xs" id="icon-ab-play-${job.id}"></i>
          </button>

          <div class="flex-1 flex flex-col gap-1">
            <div class="relative w-full h-2 bg-[#181d2c] rounded-full overflow-hidden cursor-pointer" id="progress-ab-container-${job.id}">
              <div id="progress-ab-bar-${job.id}" class="bg-gradient-to-r from-cyan-400 to-emerald-400 h-2 rounded-full w-0 transition-all duration-75"></div>
            </div>
            <div class="flex items-center justify-between text-[9px] text-slate-400 font-mono">
              <span id="time-ab-current-${job.id}" class="text-cyan-400 font-semibold">00:00</span>
              <span class="text-slate-500">단축키: [A] 원곡 / [B] 마스터 / [Space] 재생</span>
              <span id="time-ab-total-${job.id}">${formatTime(meta.duration || 15)}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Final Export & Full Mastering Action Section -->
      <div class="flex flex-col gap-2 pt-2 border-t border-white/10">
        <div class="flex items-center justify-between text-[11px] font-semibold text-slate-400">
          <span class="flex items-center gap-1.5 text-cyan-400">
            <i class="fa-solid fa-cloud-arrow-down"></i>
            <span>최종 완성 파일 저장 & 내보내기:</span>
          </span>
          ${!isFullRender ? `
            <button class="btn-full-render px-3.5 py-1.5 rounded-xl bg-[#3182f6] hover:bg-[#1b64da] text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition active:scale-[0.98] cursor-pointer" data-job-id="${job.id}">
              <i class="fa-solid fa-wand-magic-sparkles text-xs"></i>
              <span>완곡 전체 마스터링</span>
            </button>
          ` : `
            <span class="text-xs text-emerald-400 font-bold flex items-center gap-1 font-mono bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
              <i class="fa-solid fa-circle-check"></i> 완곡 마스터링 완료
            </span>
          `}
        </div>

        <!-- 4-Button Prominent Export Grid: WAV, MP3, MP4, AI MV (Toss Style) -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <!-- 1. WAV Download Button -->
          <button type="button" onclick="exportDraftAudio('${job.id}', 'wav')" class="py-2.5 px-2.5 rounded-xl bg-[#1b2333] hover:bg-[#253248] text-slate-200 hover:text-white border border-slate-700/60 text-xs font-semibold flex flex-col items-center justify-center gap-0.5 transition shadow-sm active:scale-[0.98] cursor-pointer group" title="무손실 마스터링 WAV 음원 다운로드">
            <div class="flex items-center gap-1.5">
              <i class="fa-solid fa-file-audio text-[#3182f6] text-sm"></i>
              <span>WAV 저장</span>
            </div>
            <span class="text-[9.5px] text-slate-400 font-mono">${Math.abs(speedRatio - 1.0) > 0.005 ? `${speedRatio.toFixed(2)}x 무손실` : '무손실 16/24b'}</span>
          </button>

          <!-- 2. MP3 Download Button -->
          <button type="button" data-job-id="${job.id}" onclick="exportDraftAudio('${job.id}', 'mp3')" class="btn-draft-export-mp3 py-2.5 px-2.5 rounded-xl bg-[#1b2333] hover:bg-[#253248] text-slate-200 hover:text-white border border-slate-700/60 text-xs font-semibold flex flex-col items-center justify-center gap-0.5 transition shadow-sm active:scale-[0.98] cursor-pointer group" title="320kbps 고음질 MP3 음원 다운로드">
            <div class="flex items-center gap-1.5">
              <i class="fa-solid fa-music text-[#3182f6] text-sm"></i>
              <span>MP3 저장</span>
            </div>
            <span class="text-[9.5px] text-slate-400 font-mono">320k 고음질</span>
          </button>

          <!-- 3. Single Cover MP4 Button -->
          <button type="button" onclick="exportDraftMp4('${job.id}')" class="btn-draft-export-mp4 py-2.5 px-2.5 rounded-xl bg-[#1b2333] hover:bg-[#253248] text-slate-200 hover:text-white border border-slate-700/60 text-xs font-semibold flex flex-col items-center justify-center gap-0.5 transition shadow-sm active:scale-[0.98] cursor-pointer group" title="720P 단일 커버 MP4 비디오 영상 저장">
            <div class="flex items-center gap-1.5">
              <i class="fa-solid fa-video text-[#3182f6] text-sm"></i>
              <span>단일 MP4</span>
            </div>
            <span class="text-[9.5px] text-slate-400 font-mono">720P 커버 비디오</span>
          </button>

          <!-- 4. AI Music Video Button -->
          <button type="button" onclick="openMvStudioModal('${job.result_url}', '${(job.name || "Master_Draft").replace(/'/g, "\\'")}', ${speedRatio})" class="py-2.5 px-2.5 rounded-xl bg-[#3182f6]/10 hover:bg-[#3182f6]/20 text-[#3182f6] hover:text-white border border-[#3182f6]/30 text-xs font-semibold flex flex-col items-center justify-center gap-0.5 transition shadow-sm active:scale-[0.98] cursor-pointer group" title="가사 싱크 AI 씬 이미지 & 슬라이드쇼 디졸브 애니메이션 MP4 제작">
            <div class="flex items-center gap-1.5">
              <i class="fa-solid fa-clapperboard text-[#3182f6] text-sm"></i>
              <span>🎬 AI MV</span>
            </div>
            <span class="text-[9.5px] text-slate-400 font-mono">노래방 싱크 MV</span>
          </button>
        </div>
      </div>
    `;

    // Wire up A/B Player state
    const player = {
      active: "B",
      isPlaying: false,
      startSec: meta.start_sec || 0.0,
      duration: meta.duration || 15.0
    };
    state.cardPlayers[job.id] = player;
    state.activeABCardId = job.id;

    // Prepend card
    dom.draftsContainer.prepend(card);

    // Draw spectrum comparison
    const beforeCurve = meta.metrics_before?.frequency_curve;
    const afterCurve = meta.metrics_after?.frequency_curve;
    setTimeout(() => {
      drawComparisonSpectrum(`spectrum-canvas-${job.id}`, beforeCurve, afterCurve);
    }, 60);

    // Event Listeners for Player
    const btnA = card.querySelector(`#btn-ab-a-${job.id}`);
    const btnB = card.querySelector(`#btn-ab-b-${job.id}`);
    const btnPlay = card.querySelector(`#btn-ab-play-${job.id}`);
    const progressContainer = card.querySelector(`#progress-ab-container-${job.id}`);
    const progressBar = card.querySelector(`#progress-ab-bar-${job.id}`);
    const timeCurrent = card.querySelector(`#time-ab-current-${job.id}`);
    const audioOrig = card.querySelector(`#audio-orig-${job.id}`);
    const audioMast = card.querySelector(`#audio-mast-${job.id}`);

    if (btnA) btnA.addEventListener("click", () => switchABTrack(job.id, "A"));
    if (btnB) btnB.addEventListener("click", () => switchABTrack(job.id, "B"));
    if (btnPlay) btnPlay.addEventListener("click", () => toggleABPlay(job.id));

    // Scrubber click
    if (progressContainer) {
      progressContainer.addEventListener("click", (e) => {
        const rect = progressContainer.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const seekRel = ratio * player.duration;
        audioMast.currentTime = seekRel;
        audioOrig.currentTime = (player.startSec || 0) + seekRel;
        progressBar.style.width = `${ratio * 100}%`;
        timeCurrent.textContent = formatTime(seekRel);
      });
    }

    // Timeupdate handler for both audios
    const onTimeUpdate = () => {
      const activeAudio = player.active === "B" ? audioMast : audioOrig;
      const relTime = player.active === "B" 
        ? audioMast.currentTime 
        : Math.max(0, audioOrig.currentTime - (player.startSec || 0));

      const pct = Math.min(100, (relTime / player.duration) * 100);
      progressBar.style.width = `${pct}%`;
      timeCurrent.textContent = formatTime(relTime);

      // Boundary loop enforcement
      if (relTime >= player.duration) {
        if (player.active === "B") {
          audioMast.currentTime = 0;
        } else {
          audioOrig.currentTime = player.startSec || 0;
        }
      }
    };

    audioOrig.addEventListener("timeupdate", onTimeUpdate);
    audioMast.addEventListener("timeupdate", onTimeUpdate);

    audioOrig.addEventListener("ended", () => {
      if (player.active === "A") {
        audioOrig.currentTime = player.startSec || 0;
        audioOrig.play().catch(() => {});
      }
    });

    audioMast.addEventListener("ended", () => {
      if (player.active === "B") {
        audioMast.currentTime = 0;
        audioMast.play().catch(() => {});
      }
    });

    const fullRenderBtn = card.querySelector(".btn-full-render");
    if (fullRenderBtn) {
      fullRenderBtn.addEventListener("click", () => triggerFullSongMastering(job));
    }
  });
}

function switchABTrack(jobId, targetTrack) {
  const p = state.cardPlayers[jobId];
  if (!p) return;
  state.activeABCardId = jobId;

  const audioOrig = document.getElementById(`audio-orig-${jobId}`);
  const audioMast = document.getElementById(`audio-mast-${jobId}`);
  const btnA = document.getElementById(`btn-ab-a-${jobId}`);
  const btnB = document.getElementById(`btn-ab-b-${jobId}`);
  if (!audioOrig || !audioMast || !btnA || !btnB) return;

  if (p.active === targetTrack) return;

  const wasPlaying = p.isPlaying;

  if (targetTrack === "A") {
    // Switch to Original (A)
    const curTime = audioMast.currentTime;
    audioMast.pause();
    audioOrig.currentTime = (p.startSec || 0) + curTime;
    if (wasPlaying) {
      audioOrig.play().catch(() => {});
    }
    btnA.className = "ab-switch-btn ab-btn-active-a flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer";
    btnB.className = "ab-switch-btn flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500";
    p.active = "A";
  } else {
    // Switch to Master (B)
    const curTime = Math.max(0, audioOrig.currentTime - (p.startSec || 0));
    audioOrig.pause();
    audioMast.currentTime = curTime;
    if (wasPlaying) {
      audioMast.play().catch(() => {});
    }
    btnB.className = "ab-switch-btn ab-btn-active-b flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer";
    btnA.className = "ab-switch-btn flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-500";
    p.active = "B";
  }
}

function toggleABPlay(jobId) {
  const p = state.cardPlayers[jobId];
  if (!p) return;
  state.activeABCardId = jobId;

  const audioOrig = document.getElementById(`audio-orig-${jobId}`);
  const audioMast = document.getElementById(`audio-mast-${jobId}`);
  const icon = document.getElementById(`icon-ab-play-${jobId}`);
  if (!audioOrig || !audioMast || !icon) return;

  // Stop any other card players
  Object.keys(state.cardPlayers).forEach(id => {
    if (id !== jobId && state.cardPlayers[id].isPlaying) {
      const oOrig = document.getElementById(`audio-orig-${id}`);
      const oMast = document.getElementById(`audio-mast-${id}`);
      const oIcon = document.getElementById(`icon-ab-play-${id}`);
      if (oOrig) oOrig.pause();
      if (oMast) oMast.pause();
      if (oIcon) oIcon.className = "fa-solid fa-play text-xs";
      state.cardPlayers[id].isPlaying = false;
    }
  });

  const activeAudio = p.active === "B" ? audioMast : audioOrig;

  if (p.isPlaying) {
    activeAudio.pause();
    p.isPlaying = false;
    icon.className = "fa-solid fa-play text-xs";
  } else {
    if (p.active === "A") {
      if (audioOrig.currentTime < (p.startSec || 0) || audioOrig.currentTime >= (p.startSec || 0) + p.duration) {
        audioOrig.currentTime = p.startSec || 0;
      }
    } else {
      if (audioMast.currentTime >= p.duration) {
        audioMast.currentTime = 0;
      }
    }
    activeAudio.play().then(() => {
      p.isPlaying = true;
      icon.className = "fa-solid fa-pause text-xs";
    }).catch(err => console.log("Play error:", err));
  }
}

function drawComparisonSpectrum(canvasId, beforeCurve, afterCurve) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    setTimeout(() => drawComparisonSpectrum(canvasId, beforeCurve, afterCurve), 100);
    return;
  }

  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);

  // Background
  ctx.fillStyle = "#07090e";
  ctx.fillRect(0, 0, w, h);

  // Faint horizontal dB grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  ctx.lineWidth = 1;
  [0.25, 0.5, 0.75].forEach(ratio => {
    ctx.beginPath();
    ctx.moveTo(0, h * ratio);
    ctx.lineTo(w, h * ratio);
    ctx.stroke();
  });

  const numBands = 32;
  const bCurve = (beforeCurve && beforeCurve.length === numBands) ? beforeCurve : generateFallbackCurve("before");
  const aCurve = (afterCurve && afterCurve.length === numBands) ? afterCurve : generateFallbackCurve("after");

  // Vertical frequency marks: 100Hz (~band 4), 1kHz (~band 16), 10kHz (~band 26), 18.5kHz (~band 29)
  const freqMarks = [
    { band: 4, label: "100Hz (Bass)" },
    { band: 16, label: "1kHz" },
    { band: 26, label: "10kHz (Air)" },
    { band: 29, label: "18.5k (LPF)" }
  ];

  ctx.font = "8.5px monospace";
  ctx.fillStyle = "rgba(148, 163, 184, 0.5)";
  freqMarks.forEach(mark => {
    const x = (mark.band / (numBands - 1)) * w;
    ctx.strokeStyle = mark.band === 29 ? "rgba(244, 63, 94, 0.25)" : "rgba(255, 255, 255, 0.06)";
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
    ctx.fillText(mark.label, Math.min(w - 55, x + 2), h - 4);
  });

  // Calculate points
  const pointsB = [];
  const pointsA = [];
  const paddingY = 8;
  const usableH = h - paddingY * 2;

  for (let i = 0; i < numBands; i++) {
    const x = (i / (numBands - 1)) * w;
    const yB = paddingY + (1.0 - Math.min(1.0, Math.max(0.0, bCurve[i]))) * usableH;
    const yA = paddingY + (1.0 - Math.min(1.0, Math.max(0.0, aCurve[i]))) * usableH;
    pointsB.push({ x, y: yB });
    pointsA.push({ x, y: yA });
  }

  // Shaded difference region
  // 1. Audible boost area (bands 0 to 28)
  ctx.beginPath();
  ctx.moveTo(pointsB[0].x, pointsB[0].y);
  for (let i = 1; i <= 28; i++) {
    ctx.lineTo(pointsB[i].x, pointsB[i].y);
  }
  for (let i = 28; i >= 0; i--) {
    ctx.lineTo(pointsA[i].x, pointsA[i].y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
  ctx.fill();

  // 2. Dewatermark cut area (> 18.5kHz, bands 29 to 31)
  ctx.beginPath();
  ctx.moveTo(pointsB[28].x, pointsB[28].y);
  for (let i = 29; i < numBands; i++) {
    ctx.lineTo(pointsB[i].x, pointsB[i].y);
  }
  for (let i = numBands - 1; i >= 28; i--) {
    ctx.lineTo(pointsA[i].x, pointsA[i].y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(244, 63, 94, 0.25)";
  ctx.fill();

  // Draw Before Curve (Cyan dashed)
  ctx.save();
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 1.6;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(pointsB[0].x, pointsB[0].y);
  for (let i = 1; i < numBands; i++) {
    ctx.lineTo(pointsB[i].x, pointsB[i].y);
  }
  ctx.stroke();
  ctx.restore();

  // Draw After Curve (Emerald solid with glow)
  ctx.save();
  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 2.2;
  ctx.shadowColor = "rgba(16, 185, 129, 0.5)";
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.moveTo(pointsA[0].x, pointsA[0].y);
  for (let i = 1; i < numBands; i++) {
    ctx.lineTo(pointsA[i].x, pointsA[i].y);
  }
  ctx.stroke();
  ctx.restore();
}

function generateFallbackCurve(type) {
  const curve = [];
  for (let i = 0; i < 32; i++) {
    const norm = 0.85 - (i / 31) * 0.45;
    if (type === "after") {
      let boost = 0;
      if (i >= 2 && i <= 8) boost = 0.12;
      if (i >= 14 && i <= 20) boost = 0.08;
      if (i >= 22 && i <= 27) boost = 0.15;
      if (i >= 29) boost = -0.45;
      curve.push(Math.max(0.05, Math.min(0.95, norm + boost)));
    } else {
      let spike = (i === 29) ? 0.20 : 0;
      curve.push(Math.max(0.05, Math.min(0.95, norm + spike)));
    }
  }
  return curve;
}

// Global hotkeys for 3-Way Monitor & A/B switching
window.addEventListener("keydown", (e) => {
  const tag = (document.activeElement?.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea") return;

  const isHumStudio = !document.getElementById("view-hum-studio")?.classList.contains("hidden");

  if (isHumStudio) {
    if (e.key === "a" || e.key === "A" || e.key === "ㅁ") {
      e.preventDefault();
      switchHumAB("A");
    } else if (e.key === "b" || e.key === "B" || e.key === "ㅠ") {
      e.preventDefault();
      switchHumAB("B");
    }
    return;
  }

  // If a specific Step 4 card is active
  if (state.activeABCardId) {
    if (e.key === "a" || e.key === "A" || e.key === "ㅁ") {
      e.preventDefault();
      switchABTrack(state.activeABCardId, "A");
      return;
    } else if (e.key === "b" || e.key === "B" || e.key === "ㅠ") {
      e.preventDefault();
      switchABTrack(state.activeABCardId, "B");
      return;
    } else if (e.code === "Space") {
      e.preventDefault();
      toggleABPlay(state.activeABCardId);
      return;
    }
  }

  // 3-Way Instant Audio Monitor Shortcuts (A, B, C)
  if (e.key === "a" || e.key === "A" || e.key === "ㅁ") {
    e.preventDefault();
    switchMonitorSource("A");
  } else if (e.key === "b" || e.key === "B" || e.key === "ㅠ") {
    e.preventDefault();
    switchMonitorSource("B");
  } else if (e.key === "c" || e.key === "C" || e.key === "ㅊ") {
    e.preventDefault();
    switchMonitorSource("C");
  } else if (e.code === "Space") {
    e.preventDefault();
    toggleSectionPlayback();
  }
});

window.switchABTrack = switchABTrack;
window.toggleABPlay = toggleABPlay;

async function triggerFullSongMastering(draftJob) {
  const curSpeed = dom.sunoSpeedSlider ? parseFloat(dom.sunoSpeedSlider.value) || 1.0 : 1.0;
  const draftSpeed = draftJob.mastering_options?.speed_ratio ? parseFloat(draftJob.mastering_options.speed_ratio) : 1.0;

  let effectiveSpeed = draftSpeed;
  if (Math.abs(curSpeed - draftSpeed) > 0.005) {
    const useCur = confirm(`현재 슬라이더 배속(${curSpeed.toFixed(2)}x)과 시안 배속(${draftSpeed.toFixed(2)}x)이 다릅니다.\n\n[확인]을 누르면 현재 슬라이더 배속(${curSpeed.toFixed(2)}x)을 적용하여 완곡을 렌더링하고,\n[취소]를 누르면 시안의 원래 배속(${draftSpeed.toFixed(2)}x)으로 렌더링합니다.`);
    effectiveSpeed = useCur ? curSpeed : draftSpeed;
  }

  const keepPitch = dom.toggleKeepPitch ? dom.toggleKeepPitch.checked : (draftJob.mastering_options?.keep_pitch ?? true);
  const speedNotice = Math.abs(effectiveSpeed - 1.0) > 0.005 ? ` (배속: ${effectiveSpeed.toFixed(2)}x ${keepPitch ? '피치유지' : 'Vinyl'})` : "";

  if (!confirm(`'${draftJob.name}' 설정을 사용하여 전체 곡(완곡)${speedNotice} 마스터링을 렌더링하시겠습니까?`)) {
    return;
  }

  const updatedOptions = Object.assign({}, draftJob.mastering_options || {});
  updatedOptions.speed_ratio = effectiveSpeed;
  updatedOptions.keep_pitch = keepPitch;

  const payload = {
    name: `[완곡 마스터] ${draftJob.name}${speedNotice}`,
    job_type: "full",
    source_audio_path: draftJob.source_audio_path,
    start_sec: 0.0,
    duration_sec: state.duration || 0.0,
    mastering_options: updatedOptions
  };

  try {
    const res = await fetch("/api/queue/enqueue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      alert(`'${payload.name}' 작업이 대기열에 등록되었습니다! 완곡 마스터링이 즉시 진행됩니다.`);
      pollQueue();
    }
  } catch (err) {
    alert("완곡 마스터링 요청 오류: " + err);
  }
}

// =========================================================================
// SMART EXPORT HUB (WAV / MP3 / MP4 내보내기 통합 드롭다운 핸들러)
// =========================================================================
window.toggleExportHubMenu = function(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById("export-hub-dropdown");
  if (menu) menu.classList.toggle("hidden");
};

window.closeExportHubMenu = function() {
  const menu = document.getElementById("export-hub-dropdown");
  if (menu) menu.classList.add("hidden");
};

document.addEventListener("click", () => {
  const menu = document.getElementById("export-hub-dropdown");
  if (menu && !menu.classList.contains("hidden")) {
    menu.classList.add("hidden");
  }
});

// =========================================================================
// HUM STUDIO v3.5 PRO SOURCE 3-WAY TAB & INSTANT A/B MONITOR
// =========================================================================
window.switchHumSourceTab = function(tabId) {
  const tabs = ['active-track', 'youtube', 'upload'];
  tabs.forEach(t => {
    const btnId = `tab-btn-hum-${t === 'active-track' ? 'active' : t === 'youtube' ? 'yt' : 'upload'}`;
    const btn = document.getElementById(btnId);
    const content = document.getElementById(`hum-tab-${t}`);
    if (t === tabId) {
      if (btn) {
        btn.className = "hum-source-tab active px-3 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm";
      }
      if (content) content.classList.remove("hidden");
    } else {
      if (btn) {
        btn.className = "hum-source-tab px-3 py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer bg-white/5 text-slate-400 hover:text-white";
      }
      if (content) content.classList.add("hidden");
    }
  });
};

window.updateHumActiveStudioCard = async function() {
  const songNameEl = document.getElementById('hum-studio-song-name');
  if (!songNameEl) return;
  let track = state.audio || state.currentTrackData;
  if (!track || (!track.title && !track.filename)) {
    try {
      const resp = await fetch('/api/studio/active-track').then(r => r.json());
      if (resp && resp.track && (resp.track.title || resp.track.filename)) {
        track = resp.track;
        if (!state.audio) state.audio = track;
      }
    } catch (_) {}
  }
  if (track && (track.title || track.filename)) {
    songNameEl.textContent = track.title || track.filename;
  } else {
    songNameEl.textContent = '마스터링 스튜디오에 아직 곡이 없습니다 (Step 1에서 입력)';
  }
};

window.loadHumFromActiveStudioTrack = async function(silent = false) {
  let track = state.audio || state.currentTrackData;
  if (!track || (!track.filename && !track.title && !track.file_path)) {
    try {
      const resp = await fetch('/api/studio/active-track').then(r => r.json());
      if (resp && resp.track && (resp.track.file_path || resp.track.filename)) {
        track = resp.track;
        state.audio = track;
      }
    } catch (_) {}
  }

  if (!track || (!track.filename && !track.title && !track.file_path && !track.audio_url)) {
    if (!silent) alert("마스터링 스튜디오에 등록된 곡이 없습니다. 먼저 Step 1에서 유튜브 링크를 넣거나 음원을 업로드해주세요!");
    return;
  }

  const filename = track.filename || (track.audio_url ? track.audio_url.split('/').pop() : "track.mp3");
  const title = track.title || filename;
  const filePath = track.file_path || "";

  const statusEl = document.getElementById('hum-status');
  if (statusEl) statusEl.textContent = `마스터링 곡 [${title}] 연결 및 분석 중…`;

  try {
    const res = await fetch('/api/hum/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: filePath,
        name: filename,
        title: title
      })
    });
    const r = await res.json();
    if (!r.ok) {
      if (!silent) alert(r.error || '음원 로드 실패');
      return;
    }
    await updateHumActiveStudioCard();
    await fetchHumFiles();
    await pollHumStatus();
    if (!silent) {
      const msg = r.ready ? '즉시 사용 가능합니다.' : '음원 분석 및 피치 트래킹이 자동 시작되었습니다!';
      console.log(`[HumStudio] Active studio track [${title}] loaded successfully: ${msg}`);
    }
  } catch (err) {
    if (!silent) alert('마스터링 곡 불러오기 오류: ' + err);
  }
};

// =========================================================================
// HUM STUDIO REAL-TIME LIVE CONTROLLER & PARAM UTILITIES
// =========================================================================

function getHumParams() {
  const getVal = (id, def) => {
    const el = document.getElementById(id);
    return el ? parseFloat(el.value) || def : def;
  };
  return {
    hum: getVal('hum-slider-hum', 0.0),
    bed: getVal('hum-slider-bed', 0.0),
    leak: getVal('hum-slider-leak', 1.0),
    bed_lp: getVal('hum-slider-bed-lp', 800),
    leak_lp: getVal('hum-slider-leak-lp', 20000),
    pitch: getVal('hum-slider-pitch', 0.0),
    speed: getVal('hum-slider-speed', 1.0),
    vocal_cut: getVal('hum-slider-vocal-cut', 0.0),
    wobble: getVal('hum-slider-wobble', 0.0),
    reverb: getVal('hum-slider-reverb', 0.0),
    saturation: getVal('hum-slider-saturation', 0.0),
    formant: getVal('hum-slider-formant', 0.0)
  };
}

let humLiveUpdateTimer = null;
let humIsAuditioning = false;
let humIsSwappingSource = false;

function setHumLiveIndicator(mode, customText) {
  const ind = document.getElementById('hum-live-indicator');
  if (!ind) return;
  if (mode === 'updating') {
    ind.className = 'text-[10px] px-2 py-0.5 rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-300 font-mono font-bold flex items-center gap-1.5 shadow-sm transition-all duration-200';
    ind.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[9px] text-amber-400"></i><span>${customText || '실시간 믹스 갱신 중...'}</span>`;
  } else if (mode === 'updated') {
    ind.className = 'text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-mono font-bold flex items-center gap-1.5 shadow-sm transition-all duration-200';
    ind.innerHTML = `<i class="fa-solid fa-circle-check text-[9px] text-emerald-400"></i><span>${customText || '실시간 반영 완료'}</span>`;
    setTimeout(() => {
      const cur = document.getElementById('hum-live-indicator');
      if (cur && cur.textContent.includes('실시간 반영 완료')) {
        setHumLiveIndicator('idle');
      }
    }, 1500);
  } else {
    ind.className = 'text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-mono font-bold flex items-center gap-1.5 shadow-sm transition-all duration-200';
    ind.innerHTML = `<i class="fa-solid fa-bolt text-[9px] text-emerald-400 animate-pulse"></i><span>${customText || '실시간 자동 반영'}</span>`;
  }
}

function triggerHumLiveUpdate(immediate = false, forceAudition = false) {
  const player = document.getElementById('hum-player');
  if (!player) return;

  if (forceAudition) {
    humIsAuditioning = true;
  }

  // If not forceAudition, only auto-request preview if user was actively playing or preview is already active
  if (!forceAudition && !humIsAuditioning && !humIsSwappingSource && player.paused) {
    return;
  }

  clearTimeout(humLiveUpdateTimer);
  setHumLiveIndicator('updating');

  const delay = immediate ? 30 : 180;
  humLiveUpdateTimer = setTimeout(async () => {
    const isPlaying = forceAudition || humIsAuditioning || humIsSwappingSource || (!player.paused);
    await window.previewHum({
      preserveTime: true,
      autoPlay: isPlaying,
      isLiveUpdate: true
    });
  }, delay);
}

window.switchHumAB = function(source) {
  const btnA = document.getElementById("btn-hum-ab-a");
  const btnB = document.getElementById("btn-hum-ab-b");
  if (source === 'A') {
    // A: 순수 원곡 100% (허밍 0%, 반주 0%, 원곡 100%)
    if (!state.humBackupParams) {
      state.humBackupParams = getHumParams();
    }
    const cleanSettings = { hum: 0.0, bed: 0.0, leak: 1.0, bed_lp: 800, leak_lp: 20000, pitch: 0.0, speed: 1.0 };
    for (const [k, val] of Object.entries(cleanSettings)) {
      const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
      if (el) el.value = val;
    }
    paintHumSliders();
    triggerHumLiveUpdate(true);
    if (btnA) btnA.className = "px-2.5 py-0.5 rounded text-[10px] font-bold transition flex items-center gap-1 cursor-pointer bg-teal-500 text-slate-950 shadow-sm";
    if (btnB) btnB.className = "px-2.5 py-0.5 rounded text-[10px] font-bold transition flex items-center gap-1 cursor-pointer bg-white/10 text-slate-300 hover:text-white";
  } else {
    // B: 허밍 믹스 사운드 (원래 설정 복원)
    if (state.humBackupParams) {
      for (const [k, val] of Object.entries(state.humBackupParams)) {
        const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
        if (el) el.value = val;
      }
      paintHumSliders();
      triggerHumLiveUpdate(true);
    }
    if (btnB) btnB.className = "px-2.5 py-0.5 rounded text-[10px] font-bold transition flex items-center gap-1 cursor-pointer bg-teal-500 text-slate-950 shadow-sm";
    if (btnA) btnA.className = "px-2.5 py-0.5 rounded text-[10px] font-bold transition flex items-center gap-1 cursor-pointer bg-white/10 text-slate-300 hover:text-white";
  }
};

// =========================================================================
// STUDIO MODE SWITCHER & HUM STUDIO CLIENT IMPLEMENTATION
// =========================================================================

window.switchStudioMode = function(mode) {
  if (mode === 'hum') pauseOtherStudioAudio(document.getElementById('hum-player'));
  else document.getElementById('hum-player')?.pause();
  const sunoNav = document.getElementById("suno-step-nav-bar");
  const sunoView = document.getElementById("view-suno-studio");
  const humView = document.getElementById("view-hum-studio");
  const tabSuno = document.getElementById("tab-btn-suno");
  const tabHum = document.getElementById("tab-btn-hum");

  if (mode === "suno") {
    if (sunoNav) sunoNav.style.display = "";
    if (sunoView) {
      sunoView.style.display = "";
      sunoView.classList.remove("hidden");
    }
    if (humView) {
      humView.style.display = "none";
      humView.classList.add("hidden");
    }
    if (tabSuno) {
      tabSuno.classList.add("active");
      tabSuno.classList.remove("hum-active");
    }
    if (tabHum) {
      tabHum.classList.remove("active", "hum-active");
    }
  } else {
    if (sunoNav) sunoNav.style.display = "none";
    if (sunoView) {
      sunoView.style.display = "none";
      sunoView.classList.add("hidden");
    }
    if (humView) {
      humView.style.display = "flex";
      humView.classList.remove("hidden");
    }
    if (tabHum) {
      tabHum.classList.add("hum-active");
    }
    if (tabSuno) {
      tabSuno.classList.remove("active", "hum-active");
    }

    // Initialize Hum Studio on first open
    initHumStudio();
    if (typeof updateHumActiveStudioCard === 'function') updateHumActiveStudioCard();
    fetchHumFiles();
    pollHumStatus();

    // Auto-Sync: Automatically connect the mastering track if Hum Studio doesn't have it active
    fetch('/api/hum/status').then(r => r.json()).then(r => {
      const curName = (r && r.file) ? (r.file.name || r.file.title || '') : '';
      const track = state.audio || state.currentTrackData;
      const studioName = track ? (track.filename || track.title || '') : '';
      if (!curName || (studioName && !curName.includes(studioName) && !studioName.includes(curName))) {
        loadHumFromActiveStudioTrack(true);
      }
    }).catch(() => {});
  }
};

let humInitialized = false;
let humPrevJob = 'idle';
let humLastYt = '';
let humYtTimer = null;
let HUM_PRESETS = {};

function initHumStudio() {
  if (humInitialized) return;
  humInitialized = true;

  // Bind slider input events
  const keys = [
    'hum', 'bed', 'leak', 'bed_lp', 'leak_lp', 'pitch', 'speed',
    'vocal_cut', 'wobble', 'reverb', 'saturation', 'formant'
  ];
  for (const k of keys) {
    const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
    if (el) {
      el.addEventListener('input', () => {
        paintHumSliders();
        if (k === 'speed') {
          const player = document.getElementById('hum-player');
          if (player) player.playbackRate = parseFloat(el.value) || 1.0;
        }
        triggerHumLiveUpdate(false, false);
      });
      el.addEventListener('change', () => {
        paintHumSliders();
        triggerHumLiveUpdate(true, k === 'pitch' || k === 'vocal_cut' || k === 'wobble' || k === 'formant');
      });
    }
  }

  const humPlayer = document.getElementById('hum-player');
  if (humPlayer && !humPlayer._humTracked) {
    humPlayer._humTracked = true;
    humPlayer.addEventListener('play', () => { humIsAuditioning = true; });
    humPlayer.addEventListener('pause', () => {
      if (!humIsSwappingSource) humIsAuditioning = false;
    });
    humPlayer.addEventListener('ended', () => { humIsAuditioning = false; });
  }

  // Bind YouTube input events
  const ytInput = document.getElementById('hum-yt');
  if (ytInput) {
    ytInput.addEventListener('input', () => {
      const url = ytInput.value.trim();
      const isYt = /^https?:\/\/(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\//.test(url);
      const isSuno = /^https?:\/\/(www\.)?(suno\.com|suno\.ai|audiopipe\.suno\.ai)\//.test(url);
      const ok = isYt || isSuno;
      const ytBtn = document.getElementById('hum-ytbtn');
      if (ytBtn) ytBtn.disabled = !ok;
      clearTimeout(humYtTimer);
      if (ok && url !== humLastYt) {
        humYtTimer = setTimeout(() => downloadHumYoutube(), 800);
      }
    });

    ytInput.addEventListener('paste', () => {
      setTimeout(() => {
        const url = ytInput.value.trim();
        const isYt = /^https?:\/\/(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\//.test(url);
        const isSuno = /^https?:\/\/(www\.)?(suno\.com|suno\.ai|audiopipe\.suno\.ai)\//.test(url);
        if (isYt || isSuno) {
          downloadHumYoutube();
        }
      }, 100);
    });
  }

  // Bind Title input auto-normalization (converts Unicode mathematical bold/italic to standard regular font)
  const humTitleEl = document.getElementById('hum-title-input');
  if (humTitleEl && !humTitleEl._normBound) {
    humTitleEl._normBound = true;
    const cleanFn = () => {
      const cur = humTitleEl.value;
      const norm = cur.normalize('NFKC');
      if (norm !== cur) {
        const start = humTitleEl.selectionStart;
        const end = humTitleEl.selectionEnd;
        humTitleEl.value = norm;
        try { humTitleEl.setSelectionRange(start, end); } catch (e) {}
      }
    };
    humTitleEl.addEventListener('input', cleanFn);
    humTitleEl.addEventListener('paste', () => setTimeout(cleanFn, 20));
  }

  // Setup Drag & Drop Zone
  const dz = document.getElementById('hum-drop');
  if (dz) {
    ['dragenter', 'dragover'].forEach(e => {
      dz.addEventListener(e, ev => {
        ev.preventDefault();
        dz.classList.add('border-teal-300', 'bg-teal-950/40');
      });
    });
    ['dragleave', 'drop'].forEach(e => {
      dz.addEventListener(e, ev => {
        ev.preventDefault();
        dz.classList.remove('border-teal-300', 'bg-teal-950/40');
      });
    });
    dz.addEventListener('drop', async ev => {
      const fs = [...ev.dataTransfer.files].filter(f => f.type.startsWith('audio') || /\.(mp3|wav|m4a|flac|ogg)$/i.test(f.name));
      if (!fs.length) return alert('오디오 파일을 드롭해주세요.');
      for (const f of fs) {
        await uploadHumDirect(f);
      }
    });
    dz.addEventListener('click', () => {
      const upEl = document.getElementById('hum-up');
      if (upEl) upEl.click();
    });
    const upEl = document.getElementById('hum-up');
    if (upEl) {
      upEl.addEventListener('change', () => {
        if (upEl.files.length) uploadHumFile();
      });
    }
  }

  paintHumSliders();
  fetchHumFiles();
  fetchHumPresets();
  pollHumStatus();
}

function paintHumSliders() {
  const p = getHumParams();
  for (const k of ['hum', 'bed', 'leak', 'bed_lp', 'leak_lp', 'pitch', 'speed',
                   'vocal_cut', 'wobble', 'reverb', 'saturation', 'formant']) {
    const valEl = document.getElementById(`${k}_v`);
    if (!valEl) continue;
    let v = p[k];
    if (k === 'vocal_cut') {
      if (v <= 0.001) valEl.textContent = '0% (원음)';
      else if (v >= 0.98) valEl.textContent = '100% (보컬 0)';
      else valEl.textContent = `${Math.round(v * 100)}% (보컬 컷)`;
    } else if (k === 'hum') {
      if (v <= 0.001) valEl.textContent = '0% (허밍 끔)';
      else valEl.textContent = Math.round(v * 100) + '%';
    } else if (k === 'bed') {
      if (v <= 0.001) valEl.textContent = '0% (반주 끔)';
      else valEl.textContent = Math.round(v * 100) + '%';
    } else if (k === 'reverb') {
      if (v <= 0.001) valEl.textContent = '0% (울림 끔)';
      else valEl.textContent = Math.round(v * 100) + '%';
    } else if (k === 'speed' || k === 'leak' || k === 'wobble' || k === 'saturation') {
      valEl.textContent = Math.round(v * 100) + '%';
    } else if (k === 'formant') {
      if (Math.abs(v) < 0.1) {
        valEl.textContent = '0 (내추럴)';
      } else {
        const sign = v > 0 ? '+' : '';
        valEl.textContent = `${sign}${v.toFixed(1)} (${v > 0 ? '밝은톤' : '딥톤'})`;
      }
    } else if (k === 'pitch') {
      if (Math.abs(v) < 0.005) {
        valEl.textContent = '0 (원음)';
      } else {
        const cents = Math.round(v * 100);
        const sign = v > 0 ? '+' : '';
        valEl.textContent = `${sign}${v.toFixed(2)} (${sign}${cents}¢)`;
      }
      const pitchPills = document.querySelectorAll('.btn-hum-pitch-pill');
      pitchPills.forEach(btn => {
        const txt = btn.textContent.trim();
        const pVal = txt === '원음' ? 0 : parseFloat(txt.replace('키', '').replace('+', ''));
        if (Math.abs(pVal - v) < 0.05) {
          btn.className = 'btn-hum-pitch-pill px-1.5 py-0.5 rounded bg-purple-600 text-white font-bold text-[10px] font-mono transition shadow-sm';
        } else {
          btn.className = 'btn-hum-pitch-pill px-1.5 py-0.5 rounded bg-white/5 hover:bg-purple-500/20 text-slate-300 hover:text-purple-300 text-[10px] font-mono transition';
        }
      });
    } else if (k === 'leak_lp') {
      valEl.textContent = v >= 19000 ? '원음 바이패스' : Math.round(v) + 'Hz';
    } else if (k === 'bed_lp') {
      valEl.textContent = Math.round(v) + 'Hz';
    } else {
      valEl.textContent = v;
    }
  }
}

window.setHumSliderVal = function(id, val) {
  const el = document.getElementById(id);
  if (el) {
    el.value = val;
    paintHumSliders();
    triggerHumLiveUpdate(true, true);
  }
};

window.stepHumPitch = function(delta) {
  const el = document.getElementById('hum-slider-pitch');
  if (!el) return;
  let cur = parseFloat(el.value) || 0.0;
  cur = Math.round((cur + delta) * 100) / 100;
  cur = Math.max(-12.0, Math.min(12.0, cur));
  el.value = cur.toFixed(2);
  paintHumSliders();
  triggerHumLiveUpdate(true, true);
};

window.setHumPitchPreset = function(pitch) {
  const el = document.getElementById('hum-slider-pitch');
  if (!el) return;
  el.value = Number(pitch).toFixed(2);
  paintHumSliders();
  triggerHumLiveUpdate(true, true);
};

window.setHumQuickMode = function(mode) {
  const settings = {
    clean: { hum: 0.0, bed: 0.0, leak: 1.0, bed_lp: 800, leak_lp: 20000, pitch: 0.0, speed: 1.0, vocal_cut: 0.0, wobble: 0.0, reverb: 0.0, saturation: 0.0, formant: 0.0 },
    balanced: { hum: 0.80, bed: 0.0, leak: 0.85, bed_lp: 800, leak_lp: 20000, pitch: 0.0, speed: 1.0, vocal_cut: 0.0, wobble: 0.0, reverb: 0.0, saturation: 0.0, formant: 0.0 },
    ethereal: { hum: 0.60, bed: 0.15, leak: 0.50, bed_lp: 800, leak_lp: 8000, pitch: 0.0, speed: 1.0, vocal_cut: 0.50, wobble: 0.12, reverb: 0.10, saturation: 0.10, formant: 0.0 }
  };
  const target = settings[mode] || settings.clean;
  for (const [k, val] of Object.entries(target)) {
    const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
    if (el) el.value = val;
  }
  paintHumSliders();
  triggerHumLiveUpdate(true);
  if (window.showToast) {
    if (mode === 'clean') showToast('💿 원곡 100% 무손실 모드: 허밍 0%, 반주 0%, 원곡 100%', 'success');
    else if (mode === 'balanced') showToast('🎵 원곡 + 허밍 믹스: 원곡 85% + 허밍 80% (반주 0%)', 'info');
    else if (mode === 'ethereal') showToast('✨ 몽환 허밍 모드가 적용되었습니다.', 'info');
  }
};

window.setAntiFilterPreset = function(preset) {
  const presets = {
    safe: {
      vocal_cut: 0.80,
      wobble: 0.12,
      reverb: 0.0,
      saturation: 0.15,
      formant: 1.0,
      hum: 0.0,
      bed: 0.0,
      leak: 1.0
    },
    vocal_cloak: {
      vocal_cut: 1.0,
      wobble: 0.10,
      reverb: 0.0,
      saturation: 0.15,
      formant: 0.0,
      hum: 0.80,
      bed: 0.0,
      leak: 0.70
    },
    wobble_tape: {
      vocal_cut: 0.60,
      wobble: 0.35,
      reverb: 0.0,
      saturation: 0.25,
      formant: -0.6,
      hum: 0.0,
      bed: 0.0,
      leak: 1.0,
      speed: 0.98
    },
    formant_warp: {
      vocal_cut: 0.60,
      wobble: 0.10,
      reverb: 0.0,
      saturation: 0.15,
      formant: 2.5,
      pitch: 1.0,
      hum: 0.0,
      bed: 0.0,
      leak: 1.0
    },
    reset: {
      vocal_cut: 0.0,
      wobble: 0.0,
      reverb: 0.0,
      saturation: 0.0,
      formant: 0.0,
      hum: 0.0,
      bed: 0.0,
      leak: 1.0,
      pitch: 0.0,
      speed: 1.0
    }
  };

  const target = presets[preset] || presets.safe;
  for (const [k, val] of Object.entries(target)) {
    const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
    if (el) el.value = val;
  }
  paintHumSliders();
  triggerHumLiveUpdate(true, true);

  if (window.showToast) {
    if (preset === 'safe') showToast('🛡️ Suno 안전 모드: 보컬 80% 컷 + 배음 워블 & 포먼트 (허밍/반주/울림 0%)', 'success');
    else if (preset === 'vocal_cloak') showToast('🎤 보컬 컷 & 허밍: 원곡 리드보컬 100% 제거(보컬 0) + 보코더 80%', 'info');
    else if (preset === 'wobble_tape') showToast('📻 빈티지 테이프 워블: 4.8Hz 피치 플러터로 지문 교란 (허밍 0%)', 'info');
    else if (preset === 'formant_warp') showToast('🎭 포먼트 음색 변조: 보컬 톤 컬러 + 키 변조 (허밍 0%)', 'info');
    else if (preset === 'reset') showToast('모든 안티-필터링 변조 효과 및 허밍/울림이 초기화되었습니다.', 'info');
  }
};

window.saveHumTitleManual = async function() {
  const input = document.getElementById('hum-title-input');
  if (!input) return;
  const val = (input.value || '').normalize('NFKC').trim();
  input.value = val;
  if (!val) {
    if (window.showToast) showToast('제목을 입력해주세요.', 'warning');
    return;
  }
  try {
    const res = await fetch('/api/hum/set-title', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: val })
    });
    const r = await res.json();
    if (r.ok) {
      state.humCustomTitle = (r.title || val).normalize('NFKC');
      const badge = document.getElementById('hum-title-saved-badge');
      if (badge) {
        badge.classList.remove('hidden');
        setTimeout(() => badge.classList.add('hidden'), 2500);
      }
      const songNameEl = document.getElementById('hum-studio-song-name');
      if (songNameEl) songNameEl.textContent = state.humCustomTitle;
      const statusEl = document.getElementById('hum-status');
      if (statusEl && statusEl.textContent.includes('|')) {
        const parts = statusEl.textContent.split('|');
        statusEl.textContent = `${state.humCustomTitle} | ${parts.slice(1).join('|').trim()}`;
      }
      if (window.showToast) showToast(`곡 제목이 '${state.humCustomTitle}'(으)로 변경되었습니다.`, 'success');
    }
  } catch (err) {
    console.error('Save hum title error:', err);
  }
};

window.resetHumTitleOriginal = async function() {
  const input = document.getElementById('hum-title-input');
  if (!input) return;
  try {
    const r = await fetch('/api/hum/status').then(res => res.json());
    const orig = (r.file ? (r.file.name || r.file.title || '') : '') || state.humOriginalTitle || '';
    if (orig) {
      input.value = orig.normalize('NFKC');
      await window.saveHumTitleManual();
    }
  } catch (err) {
    console.error('Reset hum title error:', err);
  }
};

function humEtaTxt(s) {
  if (s == null) return '';
  s = Math.round(s);
  return s < 60 ? ` (남은 약 ${s}초)` : ` (남은 약 ${Math.floor(s / 60)}분 ${s % 60}초)`;
}

async function syncHumFile(r) {
  if (!r.file) return;
  const v = r.file.path;
  const sel = document.getElementById('hum-files');
  if (sel) {
    if (![...sel.options].some(o => o.value === v)) {
      await fetchHumFiles();
    }
    for (let opt of sel.options) {
      if (opt.value === v) {
        sel.value = opt.value;
        break;
      }
    }
  }
}

let humStatusTimer = null;
let humStatusPending = false;
let humPreviewFile = null;
let humPreviewSequence = 0;
let humPreviewObjectUrl = null;
async function pollHumStatus() {
  clearTimeout(humStatusTimer);
  if (humStatusPending) return;
  humStatusPending = true;
  try {
    const r = await fetch('/api/hum/status').then(res => res.json());
    const currentFile = r.file?.path || null;
    if (humPreviewFile && humPreviewFile !== currentFile) {
      humPreviewSequence++;
      const player = document.getElementById('hum-player');
      if (player) { player.pause(); player.removeAttribute('src'); player.load(); }
      if (humPreviewObjectUrl) URL.revokeObjectURL(humPreviewObjectUrl);
      humPreviewObjectUrl = null;
      humPreviewFile = null;
    }
    await syncHumFile(r);

    let fileName = (r.file ? (r.file.custom_title || r.file.title || r.file.name || '') : '').normalize('NFKC');
    state.humOriginalTitle = (r.file ? (r.file.name || r.file.title || '') : '').normalize('NFKC');
    const titleInput = document.getElementById('hum-title-input');
    if (titleInput && fileName) {
      if (document.activeElement !== titleInput && (!titleInput.value || !state.humCustomTitle)) {
        titleInput.value = fileName;
      }
    }
    let msg = (fileName ? `${fileName} | ` : '') + (r.message || '') + humEtaTxt(r.eta);
    const statusEl = document.getElementById('hum-status');
    if (statusEl) statusEl.textContent = msg || '준비 완료';

    const readyBadge = document.getElementById('hum-ready-badge');
    const ytBtn = document.getElementById('hum-ytbtn');
    if (readyBadge) {
      if (r.ready) {
        readyBadge.textContent = '준비 완료 (재생 가능)';
        readyBadge.className = 'px-3 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
        if (ytBtn) ytBtn.disabled = false;
      } else if (r.job === 'error') {
        readyBadge.textContent = '오류 발생';
        readyBadge.className = 'px-3 py-1 rounded-full text-xs font-mono font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40';
        humLastYt = '';
        if (ytBtn) ytBtn.disabled = false;
      } else {
        readyBadge.textContent = r.job === 'working' ? '분석 처리 중...' : '분석 필요';
        readyBadge.className = 'px-3 py-1 rounded-full text-xs font-mono font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40';
      }
    }

    const bar = document.getElementById('hum-bar');
    const fill = document.getElementById('hum-fill');
    const pctText = document.getElementById('hum-pct-text');

    if (r.job === 'working') {
      if (bar) bar.classList.remove('hidden');
      if (fill) {
        if (r.pct == null) {
          fill.style.width = '100%';
          fill.textContent = '…';
        } else {
          fill.style.width = r.pct + '%';
          fill.textContent = Math.round(r.pct) + '%';
        }
      }
      if (pctText) pctText.textContent = r.pct ? Math.round(r.pct) + '%' : '작업 중...';
    } else {
      if (bar) bar.classList.add('hidden');
      if (pctText) pctText.textContent = '';
    }

    const pvBtn = document.getElementById('hum-pv');
    if (pvBtn) pvBtn.disabled = !r.ready;

    humPrevJob = r.job;
    humStatusTimer = setTimeout(pollHumStatus, r.job === 'working' ? 1000 : 3000);
  } catch (err) {
    console.error('Hum status error:', err);
    humStatusTimer = setTimeout(pollHumStatus, 4000);
  } finally {
    humStatusPending = false;
  }
}

async function fetchHumFiles() {
  try {
    const r = await fetch('/api/hum/files').then(res => res.json());
    const sel = document.getElementById('hum-files');
    if (sel && r.files) {
      sel.replaceChildren(...r.files.map(f => new Option(`${f.name} · ${f.dir} (${f.mb}MB)`, f.path)));
      if (r.current?.path) sel.value = r.current.path;
    }
  } catch (err) {
    console.error('Fetch hum files error:', err);
  }
}

window.resetHumJob = async function() {
  try {
    const res = await fetch('/api/hum/reset', { method: 'POST' });
    const r = await res.json();
    const statusEl = document.getElementById('hum-status');
    if (statusEl) statusEl.textContent = '상태 초기화 완료';
    await pollHumStatus();
  } catch (err) {
    console.error('Reset error:', err);
  }
};

window.selectHumFile = async function() {
  const sel = document.getElementById('hum-files');
  if (!sel || !sel.value) return;
  const path = sel.value;
  const name = sel.selectedOptions[0]?.textContent || '';
  try {
    const res = await fetch('/api/hum/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    const r = await res.json();
    if (!r.ok) {
      alert(r.error || '음원 선택 실패');
      return;
    }
    const statusEl = document.getElementById('hum-status');
    if (statusEl) {
      statusEl.textContent = r.ready
        ? `${name} (캐시 적중, 즉시 믹싱 가능)`
        : `${name} 선택됨 (분석 중)`;
    }
    await pollHumStatus();
  } catch (err) {
    console.error('Select file error:', err);
  }
};

window.uploadHumFile = async function() {
  const input = document.getElementById('hum-up');
  const f = input?.files[0];
  if (!f) return alert('오디오 파일을 선택해주세요.');
  await uploadHumDirect(f);
  if (input) input.value = '';
};

async function uploadHumDirect(file) {
  const fd = new FormData();
  fd.append('f', file);
  const statusEl = document.getElementById('hum-status');
  if (statusEl) statusEl.textContent = '업로드 중… ' + file.name;

  try {
    const res = await fetch('/api/hum/upload', { method: 'POST', body: fd });
    const r = await res.json();
    if (!r.ok) return alert(r.error || '업로드 실패');
    await fetchHumFiles();
    if (statusEl) {
      statusEl.textContent = r.ready ? '캐시 적중, 바로 재생 가능' : '업로드 완료! 분석 버튼을 눌러주세요.';
    }
    await pollHumStatus();
  } catch (err) {
    alert('업로드 오류: ' + err);
  }
}

window.downloadHumYoutube = async function() {
  const ytInput = document.getElementById('hum-yt');
  const url = ytInput ? ytInput.value.trim() : '';
  if (!url) return;
  const isYt = /^https?:\/\/(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\//.test(url);
  const isSuno = /^https?:\/\/(www\.)?(suno\.com|suno\.ai|audiopipe\.suno\.ai)\//.test(url);
  if (!isYt && !isSuno) {
    return alert('올바른 유튜브 또는 Suno 링크가 아닙니다.');
  }
  if (url === humLastYt && humPrevJob === 'working') return;

  const ytBtn = document.getElementById('hum-ytbtn');
  if (ytBtn) ytBtn.disabled = true;
  humLastYt = url;

  const statusEl = document.getElementById('hum-status');
  if (statusEl) statusEl.textContent = '음원 다운로드 요청 중…';

  try {
    const res = await fetch('/api/hum/youtube', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      humLastYt = '';
      if (ytBtn) ytBtn.disabled = false;
      const errData = await res.json().catch(() => ({}));
      return alert(errData.error || `서버 요청 오류 (${res.status})`);
    }
    const r = await res.json();
    if (!r.ok) {
      humLastYt = '';
      if (ytBtn) ytBtn.disabled = false;
      return alert(r.error || '음원 다운로드 실패');
    }
    if (statusEl) statusEl.textContent = '음원 다운로드 시작 → 오디오 추출 및 분석이 자동 진행됩니다.';
    pollHumStatus();
  } catch (err) {
    humLastYt = '';
    if (ytBtn) ytBtn.disabled = false;
    alert('유튜브 다운로드 요청 오류: ' + err + '\n\n서버 연결을 확인하세요. (브라우저 주소가 실행 중인 포트(예: http://127.0.0.1:8001)와 일치하는지 확인)');
  }
};

window.analyzeHumFile = async function() {
  try {
    const res = await fetch('/api/hum/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: true })
    });
    const r = await res.json();
    if (!r.ok) {
      alert(r.error || '분석 요청 실패');
      return;
    }
    const statusEl = document.getElementById('hum-status');
    if (statusEl) statusEl.textContent = '허밍 분리 및 F0 피치 트래킹 분석 시작…';
    await pollHumStatus();
  } catch (err) {
    alert('분석 요청 오류: ' + err);
  }
};

window.previewHum = async function(options = {}) {
  const {
    preserveTime = false,
    autoPlay = null,
    isLiveUpdate = false
  } = options;

  const player = document.getElementById('hum-player');
  const startInput = Number(document.getElementById('hum-start')?.value);
  const startSec = Number.isFinite(startInput) ? Math.max(0, startInput) : 30;

  const savedCurrentTime = (player && preserveTime) ? (player.currentTime || 0) : 0;
  const wasPlaying = (player && !player.paused);
  const shouldPlay = autoPlay !== null ? autoPlay : (wasPlaying || !isLiveUpdate);

  const sequence = ++humPreviewSequence;
  const payload = {
    ...getHumParams(),
    start: startSec,
    length: 15
  };
  const statusEl = document.getElementById('hum-status');
  if (!isLiveUpdate && statusEl) {
    statusEl.textContent = '미리듣기(15초) 오디오 렌더링 중…';
  }

  try {
    const res = await fetch('/api/hum/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      let errMsg = '미리듣기 렌더링에 실패했습니다.';
      try {
        const errJson = await res.json();
        errMsg = errJson.error || errJson.message || errMsg;
      } catch (e) {
        errMsg = `서버 오류 (HTTP ${res.status})`;
      }
      if (statusEl) statusEl.textContent = errMsg;
      if (!isLiveUpdate) alert(errMsg);
      setHumLiveIndicator('idle');
      return;
    }
    const blob = await res.blob();
    if (sequence !== humPreviewSequence) return;
    if (player) {
      if (shouldPlay) {
        humIsAuditioning = true;
        pauseOtherStudioAudio(player);
      }
      const oldUrl = humPreviewObjectUrl;
      const newUrl = URL.createObjectURL(blob);
      humPreviewObjectUrl = newUrl;

      const currentSpeed = getHumParams().speed || 1.0;

      const onReady = () => {
        humIsSwappingSource = false;
        try {
          player.playbackRate = currentSpeed;
          if (preserveTime && savedCurrentTime > 0) {
            player.currentTime = Math.min(savedCurrentTime, Math.max(0, (player.duration || 15) - 0.1));
          }
        } catch (e) {
          console.warn('Seek error in hum preview:', e);
        }
        if (shouldPlay) {
          player.play().then(() => {
            humIsAuditioning = true;
          }).catch(err => {
            if (statusEl) statusEl.textContent = '미리듣기가 준비되었습니다. 아래 재생 버튼을 눌러주세요.';
          });
        }
      };

      humIsSwappingSource = true;
      player.addEventListener('loadedmetadata', onReady, { once: true });
      player.src = newUrl;
      player.load();

      if (oldUrl) {
        setTimeout(() => URL.revokeObjectURL(oldUrl), 1000);
      }
    }
    setHumLiveIndicator('updated');
    if (statusEl) {
      statusEl.textContent = shouldPlay ? '15초 미리듣기 재생 중 (실시간 조절 반영)' : '15초 미리듣기 믹스 업데이트 완료';
    }
  } catch (err) {
    humIsSwappingSource = false;
    console.error('previewHum error:', err);
    setHumLiveIndicator('idle');
    if (!isLiveUpdate) {
      alert('미리듣기 생성 오류: ' + err);
    }
  }
};

function pauseOtherStudioAudio(except) {
  if (state.audioElement && state.audioElement !== except) {
    if (state.isPlayingSection) stopSectionPlayback(); else state.audioElement.pause();
  }
  if (state.renderedMasterAudio !== except) state.renderedMasterAudio?.pause();
  if (pitchPreviewAudio !== except) pitchPreviewAudio?.pause();
  if (window.v3Studio?.audioElement && window.v3Studio.audioElement !== except) {
    window.v3Studio.audioElement.pause();
    window.v3Studio.isPlaying = false;
    window.v3Studio.updatePlayBtnUi();
  }
  document.querySelectorAll('audio, video').forEach(el => { if (el !== except) el.pause(); });
}
document.addEventListener('play', event => {
  if (event.target.id === 'hum-player') pauseOtherStudioAudio(event.target);
  else if (event.target instanceof HTMLMediaElement) document.getElementById('hum-player')?.pause();
}, true);

let humActivePreset = '';

function findMatchingPreset(p) {
  if (humActivePreset && HUM_PRESETS[humActivePreset]) {
    const pr = HUM_PRESETS[humActivePreset];
    let match = true;
    for (const k of ['hum', 'bed', 'leak', 'bed_lp', 'leak_lp', 'pitch', 'speed']) {
      if (pr[k] !== undefined && Math.abs(pr[k] - p[k]) > 0.001) {
        match = false;
        break;
      }
    }
    if (match) return humActivePreset;
  }
  for (const [name, pr] of Object.entries(HUM_PRESETS)) {
    let match = true;
    for (const k of ['hum', 'bed', 'leak', 'bed_lp', 'leak_lp', 'pitch', 'speed']) {
      if (pr[k] !== undefined && Math.abs(pr[k] - p[k]) > 0.001) {
        match = false;
        break;
      }
    }
    if (match) return name;
  }
  return '';
}

let humIsRendering = false;

window.renderHum = async function(format) {
  if (humIsRendering) {
    if (window.showToast) showToast('이미 렌더링 작업이 진행 중입니다.', 'info');
    return;
  }
  humIsRendering = true;

  const isMp3 = format === 'mp3';
  const activeBtn = document.getElementById(isMp3 ? 'btn-hum-render-mp3' : 'btn-hum-render-wav');
  const otherBtn = document.getElementById(isMp3 ? 'btn-hum-render-wav' : 'btn-hum-render-mp3');
  const activeBtnFill = document.getElementById(isMp3 ? 'btn-hum-render-mp3-fill' : 'btn-hum-render-wav-fill');
  const activeBtnText = document.getElementById(isMp3 ? 'btn-hum-render-mp3-text' : 'btn-hum-render-wav-text');
  const activeBtnIcon = document.getElementById(isMp3 ? 'btn-hum-render-mp3-icon' : 'btn-hum-render-wav-icon');
  const activeBtnPct = document.getElementById(isMp3 ? 'btn-hum-render-mp3-pct' : 'btn-hum-render-wav-pct');

  const progressCard = document.getElementById('hum-render-progress-card');
  const stageEl = document.getElementById('hum-render-stage');
  const stageTextEl = document.getElementById('hum-render-stage-text');
  const pctEl = document.getElementById('hum-render-pct');
  const barEl = document.getElementById('hum-render-bar');
  const msgEl = document.getElementById('hum-render-msg');
  const timerEl = document.getElementById('hum-render-timer');
  const statusEl = document.getElementById('hum-status');

  const origBtnText = activeBtnText ? activeBtnText.textContent : '';
  const origBtnIconHtml = activeBtnIcon ? activeBtnIcon.innerHTML : '';

  // Disable buttons while rendering
  if (activeBtn) activeBtn.disabled = true;
  if (otherBtn) otherBtn.disabled = true;

  // Reveal progress gauge card
  if (progressCard) progressCard.classList.remove('hidden');

  // Format-specific theme styling for progress bar & gauge
  if (barEl) {
    if (isMp3) {
      barEl.className = 'h-full rounded-full transition-all duration-200 bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400 shadow-sm shadow-emerald-500/50';
    } else {
      barEl.className = 'h-full rounded-full transition-all duration-200 bg-gradient-to-r from-indigo-500 via-purple-500 to-violet-400 shadow-sm shadow-indigo-500/50';
    }
  }

  if (activeBtnPct) {
    activeBtnPct.classList.remove('hidden');
    activeBtnPct.textContent = '0%';
  }
  if (activeBtnIcon) {
    activeBtnIcon.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
  }
  if (activeBtnText) {
    activeBtnText.textContent = `전체 ${format.toUpperCase()} 렌더링 중...`;
  }

  // Update progress gauge UI helper
  const updateProgress = (pct, stageText, msgText) => {
    pct = Math.min(100, Math.max(0, Math.round(pct)));
    if (pctEl) pctEl.textContent = `${pct}%`;
    if (barEl) barEl.style.width = `${pct}%`;
    if (activeBtnFill) activeBtnFill.style.width = `${pct}%`;
    if (activeBtnPct) activeBtnPct.textContent = `${pct}%`;
    if (stageText && stageTextEl) stageTextEl.textContent = stageText;
    if (msgText && msgEl) {
      msgEl.innerHTML = `<i class="fa-solid fa-gear fa-spin text-[9px] ${isMp3 ? 'text-emerald-400' : 'text-violet-400'}"></i> <span>${msgText}</span>`;
    }
  };

  const t0 = Date.now();
  updateProgress(5, `[${format.toUpperCase()}] 전체 음원 합성 시작...`, '1단계: 허밍 및 원곡 스템 고품질 분리 합성 연산 중...');

  // Smooth progress ticker
  let currentPct = 5;
  const progressInterval = setInterval(() => {
    const elapsedSec = ((Date.now() - t0) / 1000).toFixed(1);
    if (timerEl) timerEl.textContent = `${elapsedSec}초 경과`;

    if (currentPct < 40) {
      currentPct += 4.5;
      updateProgress(currentPct, `[${format.toUpperCase()}] 허밍 & 원곡 스템 믹싱 중...`, '1단계: 허밍 및 원곡 스템 고품질 분리 합성 연산 중...');
    } else if (currentPct < 72) {
      currentPct += 3.2;
      updateProgress(currentPct, `[${format.toUpperCase()}] 필터 & 볼륨 밸런싱 중...`, '2단계: 4-Band 로우패스 필터링 및 볼륨 레벨링 적용 중...');
    } else if (currentPct < 92) {
      currentPct += 1.8;
      updateProgress(currentPct, `[${format.toUpperCase()}] 고음질 오디오 인코딩 중...`, isMp3 ? '3단계: MP3 320kbps 고음질 인코딩 및 태그 패키징 중...' : '3단계: WAV 24bit 무손실 오디오 마스터링 인코딩 중...');
    }
  }, 120);

  const p = getHumParams();
  const matchedPreset = findMatchingPreset(p);
  const customTitleInput = document.getElementById('hum-title-input');
  const customTitle = customTitleInput ? customTitleInput.value.normalize('NFKC').trim() : (state.humCustomTitle ? state.humCustomTitle.normalize('NFKC') : '');
  const payload = {
    ...p,
    format: format,
    preset_name: matchedPreset,
    custom_title: customTitle
  };

  if (statusEl) statusEl.textContent = `전체 곡 ${format.toUpperCase()} 렌더링 중…`;

  try {
    const res = await fetch('/api/hum/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      clearInterval(progressInterval);
      let errMsg = '음원 렌더링에 실패했습니다.';
      try {
        const errJson = await res.json();
        errMsg = errJson.error || errJson.message || errMsg;
      } catch (e) {
        errMsg = `서버 오류 (HTTP ${res.status})`;
      }
      if (statusEl) statusEl.textContent = errMsg;
      if (stageEl) {
        stageEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-rose-400"></i> <span class="text-rose-300">렌더링 오류 발생</span>`;
      }
      if (msgEl) msgEl.textContent = errMsg;
      if (barEl) barEl.className = 'h-full rounded-full bg-rose-500';
      if (activeBtnText) activeBtnText.textContent = origBtnText;
      if (activeBtnIcon) activeBtnIcon.innerHTML = origBtnIconHtml;
      if (activeBtnPct) activeBtnPct.classList.add('hidden');
      alert(errMsg);
      return;
    }

    const blob = await res.blob();
    clearInterval(progressInterval);

    // Hit 100% complete
    const totalElapsed = ((Date.now() - t0) / 1000).toFixed(1);
    if (timerEl) timerEl.textContent = `${totalElapsed}초 소요`;
    updateProgress(100, `[${format.toUpperCase()}] 렌더링 완료!`, '다운로드가 시작되었습니다.');

    if (barEl) {
      barEl.className = 'h-full rounded-full bg-emerald-400 shadow-md shadow-emerald-400/50';
    }
    if (stageEl) {
      stageEl.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> <span class="text-emerald-300 font-bold">[${format.toUpperCase()}] 렌더링 완료!</span>`;
    }

    const cd = res.headers.get('content-disposition') || '';
    let fn = `hum_final.${format}`;
    let m = cd.match(/filename\*=UTF-8''([^;]+)/i) || cd.match(/filename="([^"]+)"/i);
    if (m) {
      try { fn = decodeURIComponent(m[1]); } catch(e) { fn = m[1]; }
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fn;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);

    if (msgEl) {
      msgEl.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> <span class="text-slate-200 font-semibold">'${fn}' 저장 완료</span>`;
    }
    if (statusEl) {
      statusEl.textContent = `저장 완료 → 다운로드 폴더에서 '${fn}' 확인 가능 (${totalElapsed}s)`;
    }

    if (activeBtnText) activeBtnText.textContent = '✔ 다운로드 완료!';
    if (activeBtnIcon) activeBtnIcon.innerHTML = '<i class="fa-solid fa-check text-emerald-300"></i>';

    if (window.showToast) {
      showToast(`🎉 ${format.toUpperCase()} 파일 '${fn}' 다운로드가 완료되었습니다!`, 'success');
    }

    // Reset button state smoothly after 3.5 seconds
    setTimeout(() => {
      if (activeBtnText) activeBtnText.textContent = origBtnText;
      if (activeBtnIcon) activeBtnIcon.innerHTML = origBtnIconHtml;
      if (activeBtnPct) activeBtnPct.classList.add('hidden');
      if (activeBtnFill) activeBtnFill.style.width = '0%';
      if (activeBtn) activeBtn.disabled = false;
      if (otherBtn) otherBtn.disabled = false;
    }, 3500);

  } catch (err) {
    clearInterval(progressInterval);
    console.error('renderHum error:', err);
    if (stageEl) {
      stageEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-rose-400"></i> <span class="text-rose-300">오류 발생</span>`;
    }
    if (msgEl) msgEl.textContent = String(err);
    if (activeBtnText) activeBtnText.textContent = origBtnText;
    if (activeBtnIcon) activeBtnIcon.innerHTML = origBtnIconHtml;
    if (activeBtnPct) activeBtnPct.classList.add('hidden');
    alert('전체 렌더 오류: ' + err);
  } finally {
    humIsRendering = false;
    if (activeBtn && !activeBtn.disabled) activeBtn.disabled = false;
    if (otherBtn && !otherBtn.disabled) otherBtn.disabled = false;
  }
};

const SUNO_RECOMMENDATIONS = {
  rec_suno_natural: {
    id: "rec_suno_natural",
    name: "🛡️ Suno 우회: 자연스러운 보컬 허밍 (Natural Blend)",
    badge: "가장 추천 • 감성 유지",
    tag: "보컬85%컷 + 12%워블 + 0.5키",
    desc: "원곡 멜로디의 감성을 온전히 살리면서 미드 대역 보컬 지문을 85% 감쇄하고 +0.5키/1.02배속 및 12% 워블을 가미하여 Suno 오디오 핑거프린트 매칭을 자연스럽게 무력화합니다.",
    params: {
      hum: 0.65, bed: 0.0, leak: 0.55,
      bed_lp: 800, leak_lp: 20000,
      pitch: 0.5, speed: 1.02,
      vocal_cut: 0.85, wobble: 0.12, reverb: 0.08, saturation: 0.15, formant: 0.8
    }
  },
  rec_suno_vocoder: {
    id: "rec_suno_vocoder",
    name: "🎤 Suno 우회: 클로킹 멜로디 보코더 (Melodic Cloak)",
    badge: "100% 필터 무력화",
    tag: "보컬100%차단 + F0리드",
    desc: "사람의 실제 목소리(Vocal Print)를 100% 완전히 차단(Mute)하고, 원곡 F0 멜로디 윤곽선을 합성 보코더 허밍으로 대체하여 AI 음성 식별 및 저작권 필터를 원천 우회합니다.",
    params: {
      hum: 0.85, bed: 0.10, leak: 0.40,
      bed_lp: 900, leak_lp: 12000,
      pitch: -1.0, speed: 0.98,
      vocal_cut: 1.0, wobble: 0.18, reverb: 0.12, saturation: 0.20, formant: -1.0
    }
  },
  rec_suno_lofi: {
    id: "rec_suno_lofi",
    name: "📻 Suno 우회: 로파이 어쿠스틱 스미어 (Lo-Fi Acoustic)",
    badge: "빈티지 리믹스 효과",
    tag: "테이프세츄레이션 + 스미어",
    desc: "아날로그 테이프 세츄레이션(30%)과 공간감 리버브 스미어링, 4.8Hz 주기 워블로 주파수 스펙트로그램을 산란시켜 Suno 해시 인식을 회피합니다.",
    params: {
      hum: 0.50, bed: 0.30, leak: 0.45,
      bed_lp: 750, leak_lp: 6500,
      pitch: 1.0, speed: 1.04,
      vocal_cut: 0.75, wobble: 0.35, reverb: 0.18, saturation: 0.30, formant: 1.5
    }
  }
};

window.applySunoRecommendation = function(recId) {
  const rec = SUNO_RECOMMENDATIONS[recId];
  if (!rec) return;
  const p = rec.params;

  for (const k of ['hum', 'bed', 'leak', 'bed_lp', 'leak_lp', 'pitch', 'speed',
                   'vocal_cut', 'wobble', 'reverb', 'saturation', 'formant']) {
    if (p[k] !== undefined) {
      const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
      if (el) el.value = p[k];
    }
  }
  paintHumSliders();
  const player = document.getElementById('hum-player');
  if (player && p.speed !== undefined) {
    player.playbackRate = p.speed;
  }
  setHumLiveIndicator('updated', `${rec.name.slice(0, 20)}... 적용!`);
  triggerHumLiveUpdate(true);
};

window.selectAllRecommendationsForBatch = function() {
  document.querySelectorAll('.hum-batch-checkbox').forEach(cb => { cb.checked = true; });
  updateHumBatchCount();
};

window.toggleSelectAllPresets = function() {
  const cbs = document.querySelectorAll('.hum-preset-row-checkbox');
  const allChecked = Array.from(cbs).every(cb => cb.checked);
  cbs.forEach(cb => { cb.checked = !allChecked; });
  const btnText = document.getElementById('text-select-all-presets');
  if (btnText) btnText.textContent = allChecked ? '전체 선택' : '전체 해제';
  updateHumBatchCount();
};

function updateHumBatchButtonText() {
  const recCount = document.querySelectorAll('.hum-batch-checkbox:checked').length;
  const presetCount = document.querySelectorAll('.hum-preset-row-checkbox:checked').length;
  const total = recCount + presetCount;
  const badge = document.getElementById('hum-batch-count-badge');
  if (badge) badge.textContent = `${total}개 선택됨`;

  const useZip = document.getElementById('hum-batch-zip-opt')?.checked;
  const renderBtnText = document.getElementById('text-hum-batch-render');
  const renderIcon = document.getElementById('icon-hum-batch-render');

  if (renderIcon) {
    renderIcon.className = useZip ? 'fa-solid fa-file-zipper' : 'fa-solid fa-cloud-arrow-down';
  }

  if (renderBtnText) {
    if (useZip) {
      renderBtnText.textContent = total > 0
        ? `선택한 프리셋 (${total}개) ZIP 압축 파일로 다운로드`
        : '선택한 프리셋 ZIP 압축 다운로드';
    } else {
      renderBtnText.textContent = total > 0
        ? `선택한 프리셋 (${total}개) 개별 MP3 순차 저장`
        : '선택한 프리셋 일괄 MP3 개별 저장';
    }
  }
}
window.updateHumBatchButtonText = updateHumBatchButtonText;

function updateHumBatchCount() {
  updateHumBatchButtonText();
}

function renderHumPresetCheckboxes() {
  const container = document.getElementById('hum-presets-checkbox-list');
  if (!container) return;

  const keys = Object.keys(HUM_PRESETS);
  if (keys.length === 0) {
    container.innerHTML = `<span class="text-xs text-slate-500 py-2 text-center">저장된 프리셋이 없습니다.</span>`;
    updateHumBatchCount();
    return;
  }

  container.innerHTML = keys.map((name, idx) => {
    const p = HUM_PRESETS[name] || {};
    const tags = [];
    if (p.vocal_cut) tags.push(`보컬컷 ${Math.round(p.vocal_cut * 100)}%`);
    if (p.hum) tags.push(`허밍 ${Math.round(p.hum * 100)}%`);
    if (p.pitch) tags.push(`피치 ${p.pitch > 0 ? '+' : ''}${p.pitch}st`);
    if (p.speed && Math.abs(p.speed - 1.0) > 0.005) tags.push(`배속 ${p.speed.toFixed(2)}x`);
    if (p.wobble) tags.push(`워블 ${Math.round(p.wobble * 100)}%`);
    if (p.saturation) tags.push(`세츄 ${Math.round(p.saturation * 100)}%`);
    const tagHtml = tags.slice(0, 3).map(t => `<span class="text-[9px] px-1.5 py-0.5 rounded bg-white/5 font-mono text-slate-400">${t}</span>`).join(' ');

    return `
      <div class="flex items-center justify-between gap-2 p-1.5 px-2.5 rounded-lg bg-[#0e1422] border border-white/5 hover:border-blue-500/30 transition group">
        <label class="flex items-center gap-2 flex-1 cursor-pointer select-none truncate">
          <input type="checkbox" class="hum-preset-row-checkbox rounded accent-blue-500 w-3.5 h-3.5 shrink-0" data-preset-name="${name.replace(/"/g, '&quot;')}" onchange="updateHumBatchCount()">
          <span class="text-xs text-slate-200 font-semibold truncate group-hover:text-blue-300 transition">${name}</span>
          <div class="hidden sm:flex items-center gap-1 shrink-0">${tagHtml}</div>
        </label>
        <div class="flex items-center gap-1 shrink-0">
          <button type="button" onclick="applyHumPreset('${name.replace(/'/g, "\\'")}')" class="px-2 py-1 rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 text-[11px] font-bold transition cursor-pointer" title="이 프리셋 즉시 적용">
            적용
          </button>
          <button type="button" onclick="promptRenamePreset('${name.replace(/'/g, "\\'")}')" class="px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-[11px] font-bold transition cursor-pointer" title="이름 변경">
            <i class="fa-solid fa-pen text-[9.5px] text-amber-400"></i>
          </button>
          <button type="button" onclick="deleteHumPresetNamed('${name.replace(/'/g, "\\'")}')" class="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/25 text-rose-300 text-[11px] font-bold transition cursor-pointer" title="삭제">
            <i class="fa-solid fa-trash text-[9.5px]"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');

  updateHumBatchCount();
}

window.onHumPresetSelectChange = function() {
  const sel = document.getElementById('hum-presets');
  if (sel && sel.value) {
    applyHumPreset(sel.value);
  }
};

async function fetchHumPresets() {
  try {
    const res = await fetch('/api/hum/presets');
    const r = await res.json();
    HUM_PRESETS = r.presets || {};

    const sel = document.getElementById('hum-presets');
    if (sel) {
      const prevVal = sel.value;
      sel.innerHTML = Object.keys(HUM_PRESETS).map(k => `<option value="${k}">${k}</option>`).join('');
      if (prevVal && HUM_PRESETS[prevVal]) sel.value = prevVal;
    }

    renderHumPresetCheckboxes();

    const speedsDiv = document.getElementById('hum-speeds');
    if (speedsDiv && r.speeds) {
      speedsDiv.innerHTML = r.speeds.map(p => 
        `<button type="button" class="preset-pill" onclick="setHumSpeed(${p})">${p}%</button>`
      ).join(' ');
    }
  } catch (err) {
    console.error('Fetch hum presets error:', err);
  }
}

window.setHumSpeed = function(p) {
  const spInput = document.getElementById('hum-slider-speed');
  if (spInput) {
    const spVal = p / 100;
    spInput.value = spVal;
    paintHumSliders();
    const player = document.getElementById('hum-player');
    if (player) {
      player.playbackRate = spVal;
    }
    triggerHumLiveUpdate(true);
  }
};

window.applyHumPreset = function(presetName) {
  const sel = document.getElementById('hum-presets');
  const targetName = presetName || (sel ? sel.value : null);
  if (!targetName) return;
  const p = HUM_PRESETS[targetName];
  if (!p) return;
  humActivePreset = targetName;
  if (sel) sel.value = targetName;

  for (const k of ['hum', 'bed', 'leak', 'bed_lp', 'leak_lp', 'pitch', 'speed',
                   'vocal_cut', 'wobble', 'reverb', 'saturation', 'formant']) {
    if (p[k] !== undefined) {
      const el = document.getElementById(`hum-slider-${k.replace('_', '-')}`);
      if (el) el.value = p[k];
    }
  }
  paintHumSliders();
  const player = document.getElementById('hum-player');
  if (player && p.speed !== undefined) {
    player.playbackRate = p.speed;
  }
  setHumLiveIndicator('updated', `'${targetName.slice(0, 16)}' 적용!`);
  triggerHumLiveUpdate(true);
};

window.saveHumPreset = async function() {
  const nameInput = document.getElementById('hum-pname');
  const name = nameInput ? nameInput.value.trim() : '';
  if (!name) return alert('새 프리셋 이름을 입력해주세요.');

  try {
    const res = await fetch('/api/hum/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, values: getHumParams() })
    });
    const r = await res.json();
    if (r.ok) {
      nameInput.value = '';
      await fetchHumPresets();
      const sel = document.getElementById('hum-presets');
      if (sel) sel.value = name;
      alert(`프리셋 '${name}' 저장 완료!`);
    } else {
      alert(r.error || '저장 실패');
    }
  } catch (err) {
    alert('프리셋 저장 오류: ' + err);
  }
};

window.promptRenamePreset = async function(presetName) {
  const sel = document.getElementById('hum-presets');
  const oldName = presetName || (sel ? sel.value : null);
  if (!oldName) return alert('이름을 변경할 프리셋을 선택하세요.');

  const newName = prompt(`'${oldName}' 프리셋의 새 이름을 입력하세요:`, oldName);
  if (!newName || newName.trim() === '' || newName.trim() === oldName) return;

  try {
    const res = await fetch('/api/hum/presets/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_name: oldName, new_name: newName.trim() })
    });
    const r = await res.json();
    if (r.ok) {
      await fetchHumPresets();
      const sel2 = document.getElementById('hum-presets');
      if (sel2) sel2.value = newName.trim();
      alert(`프리셋 이름이 '${newName.trim()}'(으)로 변경되었습니다!`);
    } else {
      alert(r.error || '이름 변경 실패');
    }
  } catch (err) {
    alert('프리셋 이름 변경 오류: ' + err);
  }
};

window.deleteHumPresetNamed = async function(name) {
  if (!name) return;
  if (!confirm(`프리셋 '${name}'을(를) 삭제하시겠습니까?`)) return;

  try {
    const res = await fetch('/api/hum/presets', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const r = await res.json();
    if (r.ok) {
      await fetchHumPresets();
      alert(`프리셋 '${name}' 삭제 완료!`);
    } else {
      alert(r.error || '삭제 실패');
    }
  } catch (err) {
    alert('프리셋 삭제 오류: ' + err);
  }
};

window.deleteHumPreset = async function() {
  const sel = document.getElementById('hum-presets');
  if (!sel || !sel.value) return alert('삭제할 프리셋을 선택하세요.');
  await window.deleteHumPresetNamed(sel.value);
};

window.renderHumBatch = async function() {
  const items = [];

  // 1. Gather checked recommendations
  document.querySelectorAll('.hum-batch-checkbox:checked').forEach(cb => {
    const recId = cb.dataset.recId;
    const rec = SUNO_RECOMMENDATIONS[recId];
    if (rec) {
      items.push({
        name: rec.name,
        params: rec.params
      });
    }
  });

  // 2. Gather checked presets
  document.querySelectorAll('.hum-preset-row-checkbox:checked').forEach(cb => {
    const pName = cb.dataset.presetName;
    const p = HUM_PRESETS[pName];
    if (p) {
      items.push({
        name: pName,
        params: p
      });
    }
  });

  if (items.length === 0) {
    return alert('일괄 렌더링할 프리셋 또는 AI 추천 세팅을 하나 이상 선택해주세요.\n(체크박스를 선택하세요)');
  }

  const titleInput = document.getElementById('hum-title-input');
  const title = (titleInput ? titleInput.value.trim() : '') || state.humOriginalTitle || 'Suno_HumMix';

  const btn = document.getElementById('btn-hum-batch-render');
  const origBtnHtml = btn ? btn.innerHTML : '';
  const progressBox = document.getElementById('hum-batch-progress-box');
  const stageText = document.getElementById('hum-batch-stage-text');
  const percentText = document.getElementById('hum-batch-percent-text');
  const progressBar = document.getElementById('hum-batch-progress-bar');
  const useZip = document.getElementById('hum-batch-zip-opt')?.checked;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>일괄 렌더링 중 (${items.length}곡)...</span>`;
  }
  if (progressBox) progressBox.classList.remove('hidden');
  if (percentText) percentText.textContent = '0%';
  if (progressBar) progressBar.style.width = '0%';

  // =========================================================================
  // OPTION A: ZIP 압축 파일로 한 번에 다운로드 (체크 시 비동기 태스크 + 실시간 폴링)
  // =========================================================================
  if (useZip) {
    if (stageText) stageText.textContent = `총 ${items.length}개 프리셋 일괄 MP3 변환 및 ZIP 압축 작업 시작...`;
    try {
      const res = await fetch('/api/hum/render-batch-async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, items })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'ZIP 일괄 렌더링 요청 실패');

      const taskId = data.task_id;
      const zipData = await new Promise((resolve, reject) => {
        const timer = setInterval(async () => {
          try {
            const sRes = await fetch(`/api/analysis-status/${taskId}`);
            if (!sRes.ok) throw new Error("진행 상태 조회 실패");
            const sData = await sRes.json();
            const p = Math.min(100, Math.max(0, sData.progress || 0));
            if (percentText) percentText.textContent = `${p}%`;
            if (progressBar) progressBar.style.width = `${p}%`;
            if (stageText) stageText.textContent = sData.stage || "ZIP 생성 중...";

            if (sData.status === "completed") {
              clearInterval(timer);
              resolve(sData.data);
            } else if (sData.status === "failed") {
              clearInterval(timer);
              reject(new Error(sData.error || sData.stage || "ZIP 생성 실패"));
            }
          } catch (pollErr) {
            clearInterval(timer);
            reject(pollErr);
          }
        }, 700);
      });

      if (percentText) percentText.textContent = '100%';
      if (progressBar) progressBar.style.width = '100%';
      if (stageText) stageText.textContent = `ZIP 압축 파일 다운로드 시작...`;

      const a = document.createElement("a");
      a.href = zipData.download_url;
      a.download = zipData.filename || `${title}_Batch.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      setTimeout(() => {
        if (progressBox) progressBox.classList.add('hidden');
      }, 2500);

      alert(`🎉 총 ${items.length}개 프리셋 ZIP 압축 다운로드가 완료되었습니다!\n파일명: ${zipData.filename}`);
    } catch (err) {
      console.error('Batch ZIP error:', err);
      alert('ZIP 일괄 렌더링 오류:\n' + err.message);
      if (progressBox) progressBox.classList.add('hidden');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = origBtnHtml;
      }
    }
    return;
  }

  // =========================================================================
  // OPTION B (기본값): 개별 파일 순차 렌더링 & 즉시 다운로드 (타임아웃 0%)
  // =========================================================================
  let successCount = 0;
  const total = items.length;

  try {
    for (let i = 0; i < total; i++) {
      const item = items[i];
      const idxStr = String(i + 1).padStart(2, '0');
      const cleanName = item.name.replace(/^[^\w\s가-힣一-龥ぁ-ゔァ-ヴー]+/, '').trim();
      const currentPct = Math.round((i / total) * 100);

      if (percentText) percentText.textContent = `${currentPct}%`;
      if (progressBar) progressBar.style.width = `${currentPct}%`;
      if (stageText) stageText.textContent = `[${i + 1}/${total}곡] '${cleanName}' 320k MP3 렌더링 중...`;

      try {
        const res = await fetch('/api/hum/render', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            format: 'mp3',
            params: item.params,
            preset_name: item.name,
            title: title,
            prefix: idxStr
          })
        });

        if (!res.ok) {
          let errTxt = '렌더링 실패';
          try { const j = await res.json(); errTxt = j.error || errTxt; } catch (_) {}
          console.warn(`[HumBatch] Track ${i+1} failed:`, errTxt);
          continue;
        }

        let dlName = `${idxStr}_${title}_${cleanName}.mp3`;
        const headerName = res.headers.get('X-Rendered-Filename');
        if (headerName) {
          try { dlName = decodeURIComponent(headerName); } catch (_) {}
        }

        const blob = await res.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = dlName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 4000);

        successCount++;
        if (stageText) stageText.textContent = `[${i + 1}/${total}곡 완료] '${dlName}' 다운로드됨!`;
        // Delay between downloads so browser doesn't block multi-file popups
        await new Promise(r => setTimeout(r, 450));
      } catch (trackErr) {
        console.error(`[HumBatch] Track ${i+1} error:`, trackErr);
      }
    }

    if (percentText) percentText.textContent = '100%';
    if (progressBar) progressBar.style.width = '100%';
    if (stageText) stageText.textContent = `🎉 총 ${successCount}/${total}곡 개별 MP3 다운로드 완료!`;

    setTimeout(() => {
      if (progressBox) progressBox.classList.add('hidden');
    }, 2500);

    alert(`🎉 총 ${successCount}개 곡이 개별 고음질 MP3(320kbps)로 다운로드 폴더에 모두 저장되었습니다!\n(로컬 outputs 폴더에도 영구 보관되었습니다)`);
  } catch (err) {
    console.error('Batch individual error:', err);
    alert('일괄 MP3 렌더링 오류:\n' + err.message);
    if (progressBox) progressBox.classList.add('hidden');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnHtml;
    }
  }
};

window.stepSpeed = stepSpeed;
window.setAudioSpeed = setAudioSpeed;
window.exportCurrentTrackMp4 = exportCurrentTrackMp4;
window.exportDraftMp4 = exportDraftMp4;

// =========================================================================
// AI MUSIC VIDEO (MV) & ANIMATED SLIDESHOW STUDIO (Ken-Burns & Dissolve)
// =========================================================================

let mvState = {
  activeAudioUrl: null,
  activeTitle: "Music Video",
  activeSpeed: 1.0,
  activeCoverUrl: null,
  selectedStyle: "cinematic_anime",
  storyboard: null,
  taskId: null,
  pollTimer: null
};

window.closeMvStudioModal = function() {
  const modal = document.getElementById("modal-mv-studio");
  if (modal) modal.classList.add("hidden");
  const video = document.getElementById("mv-result-video");
  if (video) video.pause();
  if (mvState.pollTimer) {
    clearInterval(mvState.pollTimer);
    mvState.pollTimer = null;
  }
  if (visState.animFrameId) {
    cancelAnimationFrame(visState.animFrameId);
    visState.animFrameId = null;
  }
};

window.openMvStudioModal = function(customAudioUrl = null, customTitle = null, customSpeed = null, customCoverUrl = null) {
  let audioUrl = customAudioUrl;
  let title = customTitle;
  let speed = customSpeed;
  let coverUrl = customCoverUrl;

  // Resolve best audio source (Mastered track first, then original Suno audio)
  if (!audioUrl) {
    if (state.lastRenderedMasterUrl) {
      audioUrl = state.lastRenderedMasterUrl;
      title = state.lastRenderedMasterName ? state.lastRenderedMasterName.replace(/^\[.*?\]\s*/, "") : (state.audio?.title || "Mastered_Track");
      speed = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
      coverUrl = state.audio?.image_url || null;
    } else if (state.audio && (state.audio.audio_url || state.audio.file_path)) {
      audioUrl = state.audio.audio_url || state.originalAudioUrl;
      title = state.audio.title || state.originalFilename || "Suno_Track";
      speed = dom.sunoSpeedSlider ? (parseFloat(dom.sunoSpeedSlider.value) || 1.0) : 1.0;
      coverUrl = state.audio.image_url || null;
    } else if (state.originalAudioUrl) {
      audioUrl = state.originalAudioUrl;
      title = state.originalFilename ? state.originalFilename.replace(/\.[^/.]+$/, "") : "Suno_Track";
      speed = 1.0;
    } else {
      alert("먼저 Suno 오디오 음원을 불러오거나 마스터링을 진행해주세요!");
      return;
    }
  }

  if (!coverUrl && state.audio && state.audio.image_url) {
    coverUrl = state.audio.image_url;
  }

  mvState.activeAudioUrl = audioUrl;
  mvState.activeTitle = title || "Music Video";
  mvState.activeSpeed = typeof speed === "number" ? speed : 1.0;
  mvState.activeCoverUrl = coverUrl;
  mvState.selectedStyle = mvState.selectedStyle || "cinematic_anime";
  mvState.taskId = `mv_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  mvState.storyboard = null;

  // Sync with Hero Visualizer State
  visState.heroImageUrl = coverUrl || null;
  visState.heroImageObj = new Image();
  visState.heroImageObj.crossOrigin = "anonymous";
  visState.heroImageObj.src = coverUrl || "/outputs/verify_real_photo.png";

  const visTitleInput = document.getElementById("vis-title-input");
  if (visTitleInput) {
    visTitleInput.value = mvState.activeTitle;
  }

  const photoLabel = document.getElementById("vis-photo-filename-label");
  if (photoLabel) {
    photoLabel.textContent = coverUrl ? "앨범 커버 사진 적용됨" : "선택된 사진: 35mm 실사 프리셋";
  }

  const modal = document.getElementById("modal-mv-studio");
  if (!modal) return;

  const titleInput = document.getElementById("mv-title-input");
  if (titleInput) {
    titleInput.value = mvState.activeTitle;
  }

  const badge = document.getElementById("mv-track-info-badge");
  if (badge) {
    const spdStr = Math.abs(mvState.activeSpeed - 1.0) > 0.005 ? ` • ${mvState.activeSpeed.toFixed(2)}x 배속` : "";
    badge.textContent = `현재 음원: ${mvState.activeTitle}${spdStr}`;
  }

  const conceptInput = document.getElementById("mv-concept-input");
  if (conceptInput && !conceptInput.value.trim()) {
    conceptInput.value = `${mvState.activeTitle}에 어울리는 감성적인 영상 스토리`;
  }

  const stillsSection = document.getElementById("mv-stills-section");
  if (stillsSection) stillsSection.classList.add("hidden");

  const progBox = document.getElementById("mv-progress-box");
  const resBox = document.getElementById("mv-result-box");
  if (progBox) progBox.classList.add("hidden");
  if (resBox) resBox.classList.add("hidden");

  // Default to Visualizer mode as recommended
  switchMvTabMode("visualizer");

  modal.classList.remove("hidden");
};

// ============================================================================
// VISUALIZER MV STATE & REAL-TIME INTERACTIVE CANVAS ENGINE
// ============================================================================
const visState = {
  activeTab: "visualizer",
  heroImageUrl: null,
  heroImageObj: null,
  styleKey: "real_photo",
  titleTemplate: "modern_official", // modern_official, vinyl_label, minimal_clean, cyber_hud
  visualizerEffect: "spectrum_bars", // spectrum_bars, waveform_line, spectrum_mirror, spectrum_dots, subtle_pulse
  cameraMotion: "slow_zoom",
  isPreviewPlaying: true,
  animFrameId: null,
  animTime: 0
};

// Real-Time Canvas Preview Loop (60FPS Interactive Live Renderer)
function initVisLivePreviewCanvas() {
  const canvas = document.getElementById("vis-live-preview-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // Load default placeholder if hero image not set
  if (!visState.heroImageObj) {
    visState.heroImageObj = new Image();
    visState.heroImageObj.crossOrigin = "anonymous";
    visState.heroImageObj.src = visState.heroImageUrl || "/outputs/verify_real_photo.png";
  }

  function renderLoop() {
    visState.animFrameId = requestAnimationFrame(renderLoop);
    if (!visState.isPreviewPlaying) return;

    visState.animTime += 0.04;
    const t = visState.animTime;
    const w = canvas.width = 1280;
    const h = canvas.height = 720;

    ctx.clearRect(0, 0, w, h);

    // 1. Draw Background Photo (With subtle breathing motion if pulse effect)
    if (visState.heroImageObj && visState.heroImageObj.complete && visState.heroImageObj.naturalWidth > 0) {
      if (visState.visualizerEffect === "subtle_pulse") {
        const zoom = 1.0 + Math.sin(t * 0.8) * 0.035;
        const zw = w * zoom;
        const zh = h * zoom;
        ctx.drawImage(visState.heroImageObj, (w - zw) / 2, (h - zh) / 2, zw, zh);
      } else {
        ctx.drawImage(visState.heroImageObj, 0, 0, w, h);
      }
    } else {
      // Default dark stage background if loading
      const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
      bgGrad.addColorStop(0, "#080c16");
      bgGrad.addColorStop(1, "#141c2e");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);
    }

    // 2. Draw Vignette Gradient for text & visualizer legibility
    const vigTop = ctx.createLinearGradient(0, 0, 0, 160);
    vigTop.addColorStop(0, "rgba(0, 0, 0, 0.75)");
    vigTop.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = vigTop;
    ctx.fillRect(0, 0, w, 160);

    const vigBottom = ctx.createLinearGradient(0, 520, 0, h);
    vigBottom.addColorStop(0, "rgba(0, 0, 0, 0)");
    vigBottom.addColorStop(1, "rgba(0, 0, 0, 0.85)");
    ctx.fillStyle = vigBottom;
    ctx.fillRect(0, 520, w, 200);

    // 3. Draw Selected Audio Visualizer Effect
    renderLiveVisualizerEffect(ctx, w, h, t);

    // 4. Draw Selected Title Template Overlay
    renderLiveTitleTemplate(ctx, w, h);
  }

  if (visState.animFrameId) cancelAnimationFrame(visState.animFrameId);
  renderLoop();
}

function renderLiveVisualizerEffect(ctx, w, h, t) {
  const eff = visState.visualizerEffect;

  // EFFECT 1: Classic Neon Bars (Bottom)
  if (eff === "spectrum_bars") {
    const bars = 42;
    const startX = 60;
    const barW = (w - 120) / bars - 4;
    const baseH = 510;

    for (let i = 0; i < bars; i++) {
      const freq = (i / bars) * 8.0;
      const wave = Math.sin(t * 3.5 + freq) * 0.45 + Math.cos(t * 2.2 + i * 0.4) * 0.35 + 0.5;
      const barH = Math.max(12, wave * 175);
      const x = startX + i * (barW + 4);
      const y = h - 20 - barH;

      const grad = ctx.createLinearGradient(0, y, 0, h - 20);
      grad.addColorStop(0, "#a855f7"); // Purple top
      grad.addColorStop(0.5, "#3b82f6"); // Blue mid
      grad.addColorStop(1, "#06b6d4"); // Cyan base

      ctx.fillStyle = grad;
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 10;
      ctx.fillRect(x, y, barW, barH);
      ctx.shadowBlur = 0;
    }
  }

  // EFFECT 2: Cyber Waveform Line
  else if (eff === "waveform_line") {
    ctx.save();
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3.5;
    ctx.shadowColor = "#38bdf8";
    ctx.shadowBlur = 16;
    ctx.beginPath();

    const cy = 600;
    for (let x = 0; x <= w; x += 6) {
      const normX = x / w;
      const amp = Math.sin(normX * 18 + t * 4.5) * 35 * Math.sin(normX * Math.PI) +
                  Math.cos(normX * 36 - t * 3.0) * 18 * Math.sin(normX * Math.PI);
      const y = cy + amp;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  // EFFECT 3: Center Mirrored Spectrum
  else if (eff === "spectrum_mirror") {
    const bars = 48;
    const cy = 360;
    const startX = 80;
    const barW = (w - 160) / bars - 4;

    for (let i = 0; i < bars; i++) {
      const wave = Math.sin(t * 3.2 + i * 0.35) * 0.5 + Math.cos(t * 1.8 + i * 0.2) * 0.3 + 0.4;
      const barH = Math.max(8, wave * 110);
      const x = startX + i * (barW + 4);

      const grad = ctx.createLinearGradient(0, cy - barH, 0, cy + barH);
      grad.addColorStop(0, "#ec4899");
      grad.addColorStop(0.5, "#a855f7");
      grad.addColorStop(1, "#38bdf8");

      ctx.fillStyle = grad;
      ctx.shadowColor = "#ec4899";
      ctx.shadowBlur = 8;
      // Draw top and bottom mirrored
      ctx.fillRect(x, cy - barH, barW, barH * 2);
      ctx.shadowBlur = 0;
    }
  }

  // EFFECT 4: Dot Particles Pulse
  else if (eff === "spectrum_dots") {
    const dots = 36;
    const startX = 70;
    const spacing = (w - 140) / dots;

    for (let i = 0; i < dots; i++) {
      const wave = Math.sin(t * 4.0 + i * 0.4) * 0.5 + Math.cos(t * 2.5 + i * 0.25) * 0.35 + 0.5;
      const dotY = h - 40 - (wave * 180);
      const dotX = startX + i * spacing;
      const dotR = 4.5 + wave * 4.0;

      ctx.beginPath();
      ctx.arc(dotX, dotY, dotR, 0, Math.PI * 2);
      ctx.fillStyle = i % 2 === 0 ? "#06b6d4" : "#34d399";
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }
}

function renderLiveTitleTemplate(ctx, w, h) {
  const tpl = visState.titleTemplate;
  const title = (document.getElementById("vis-title-input")?.value || mvState.activeTitle || "Suno Studio Master").trim();
  const artist = (document.getElementById("vis-artist-input")?.value || "Antigravity Studio Mastered").trim();

  // TEMPLATE 1: Modern Official (Top Left)
  if (tpl === "modern_official") {
    // Badge
    ctx.fillStyle = "rgba(10, 16, 28, 0.85)";
    ctx.strokeStyle = "rgba(6, 182, 212, 0.8)";
    ctx.lineWidth = 1;
    roundRect(ctx, 50, 42, 240, 26, 13, true, true);

    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 13px sans-serif";
    ctx.fillText("🎵 OFFICIAL AUDIO • 720P MASTER", 64, 59);

    // Title
    ctx.fillStyle = "#ffffff";
    ctx.shadowColor = "rgba(0, 0, 0, 0.9)";
    ctx.shadowBlur = 8;
    ctx.shadowOffsetY = 2;
    ctx.font = "bold 34px 'Pretendard', sans-serif";
    ctx.fillText(title, 50, 108);

    // Artist
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "600 18px sans-serif";
    ctx.fillText(artist, 52, 138);
    ctx.shadowBlur = 0;
  }

  // TEMPLATE 2: Retro Vinyl Label (Top Center)
  else if (tpl === "vinyl_label") {
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(245, 200, 100, 0.9)";
    ctx.font = "bold 12px monospace";
    ctx.fillText("— STEREO • 33 1/3 RPM • HIGH FIDELITY RECORDING —", 640, 42);

    ctx.fillStyle = "#fff8e7";
    ctx.shadowColor = "rgba(0, 0, 0, 0.95)";
    ctx.shadowBlur = 10;
    ctx.font = "bold 36px 'Times New Roman', serif";
    ctx.fillText(title.toUpperCase(), 640, 84);

    ctx.fillStyle = "#d1d5db";
    ctx.font = "bold 16px monospace";
    ctx.fillText(`PERFORMED BY: ${artist.toUpperCase()}`, 640, 116);
    ctx.textAlign = "start";
    ctx.shadowBlur = 0;
  }

  // TEMPLATE 3: Minimal Clean (Bottom Center)
  else if (tpl === "minimal_clean") {
    ctx.textAlign = "center";
    const boxW = Math.min(800, Math.max(460, title.length * 20 + 80));
    const bx = 640 - boxW / 2;
    const by = 485;

    ctx.fillStyle = "rgba(10, 14, 24, 0.85)";
    ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
    ctx.lineWidth = 1;
    roundRect(ctx, bx, by, boxW, 76, 14, true, true);

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 26px sans-serif";
    ctx.fillText(title, 640, by + 34);

    ctx.fillStyle = "#94a3b8";
    ctx.font = "15px sans-serif";
    ctx.fillText(artist, 640, by + 60);
    ctx.textAlign = "start";
  }

  // TEMPLATE 4: Cyber HUD (Top Right)
  else if (tpl === "cyber_hud") {
    const rx = 1230;
    const ry = 42;
    const hw = 400;
    const hh = 86;

    ctx.fillStyle = "rgba(6, 12, 24, 0.88)";
    ctx.strokeStyle = "#ec4899";
    ctx.lineWidth = 2;
    ctx.fillRect(rx - hw, ry, hw, hh);
    ctx.strokeRect(rx - hw, ry, hw, hh);

    // Cyan Corner Accent Brackets
    ctx.strokeStyle = "#06b6d4";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(rx - hw - 4, ry); ctx.lineTo(rx - hw + 16, ry);
    ctx.moveTo(rx - 16, ry + hh); ctx.lineTo(rx + 4, ry + hh);
    ctx.stroke();

    ctx.fillStyle = "#06b6d4";
    ctx.font = "bold 11px monospace";
    ctx.fillText("SYS//AUDIO_STREAM.720P", rx - hw + 14, ry + 20);

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 24px sans-serif";
    ctx.fillText(title, rx - hw + 14, ry + 48);

    ctx.fillStyle = "#f472b6";
    ctx.font = "600 14px monospace";
    ctx.fillText(`OPERATOR: ${artist}`, rx - hw + 14, ry + 72);
  }
}

// Utility to draw rounded rectangle on canvas
function roundRect(ctx, x, y, width, height, radius, fill, stroke) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
  if (fill) ctx.fill();
  if (stroke) ctx.stroke();
}

window.toggleVisPreviewPlayback = function() {
  visState.isPreviewPlaying = !visState.isPreviewPlaying;
  const icon = document.getElementById("icon-vis-canvas-play");
  const text = document.getElementById("text-vis-canvas-play");
  if (icon && text) {
    if (visState.isPreviewPlaying) {
      icon.className = "fa-solid fa-pause";
      text.textContent = "모션 일시정지";
    } else {
      icon.className = "fa-solid fa-play";
      text.textContent = "스펙트럼 모션 재생";
    }
  }
};

window.switchMvTabMode = function(tab) {
  visState.activeTab = tab;
  const tabVis = document.getElementById("tab-mv-visualizer");
  const tabSlide = document.getElementById("tab-mv-slideshow");
  const viewVis = document.getElementById("mv-view-visualizer");
  const viewSlide = document.getElementById("mv-view-slideshow");
  const mainRenderBtn = document.getElementById("btn-start-mv-render");

  if (tab === "visualizer") {
    if (tabVis) tabVis.className = "px-4 py-2 border-b-2 border-cyan-400 text-cyan-300 font-bold text-xs flex items-center gap-2 transition cursor-pointer";
    if (tabSlide) tabSlide.className = "px-4 py-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 font-bold text-xs flex items-center gap-2 transition cursor-pointer";
    if (viewVis) viewVis.classList.remove("hidden");
    if (viewSlide) viewSlide.classList.add("hidden");
    if (mainRenderBtn) {
      mainRenderBtn.onclick = window.startHeroVisualizerRender;
      mainRenderBtn.innerHTML = `<i class="fa-solid fa-play"></i> <span>🚀 업로드 사진 & 선택 스타일로 MP4 즉시 렌더링</span>`;
    }
    // Initialize canvas preview
    setTimeout(initVisLivePreviewCanvas, 50);
  } else {
    if (tabVis) tabVis.className = "px-4 py-2 border-b-2 border-transparent text-slate-400 hover:text-slate-200 font-bold text-xs flex items-center gap-2 transition cursor-pointer";
    if (tabSlide) tabSlide.className = "px-4 py-2 border-b-2 border-pink-500 text-pink-300 font-bold text-xs flex items-center gap-2 transition cursor-pointer";
    if (viewVis) viewVis.classList.add("hidden");
    if (viewSlide) viewSlide.classList.remove("hidden");
    if (mainRenderBtn) {
      mainRenderBtn.onclick = window.autoGenerateMv;
      mainRenderBtn.innerHTML = `<i class="fa-solid fa-play"></i> <span>🚀 AI 노래방 슬라이드쇼 MP4 렌더링 시작</span>`;
    }
  }
};

window.selectTitleTemplate = function(templateKey) {
  visState.titleTemplate = templateKey;
  document.querySelectorAll(".vis-template-card").forEach(card => {
    if (card.dataset.template === templateKey) {
      card.className = "vis-template-card active p-2.5 rounded-lg border text-left transition flex flex-col gap-0.5 cursor-pointer bg-cyan-950/50 border-cyan-500/60 text-white shadow-sm";
    } else {
      card.className = "vis-template-card p-2.5 rounded-lg border text-left transition flex flex-col gap-0.5 cursor-pointer bg-slate-900/60 border-white/5 text-slate-300 hover:border-slate-700";
    }
  });
};

window.selectVisEffect = function(effectKey) {
  visState.visualizerEffect = effectKey;
  document.querySelectorAll(".vis-effect-card").forEach(card => {
    if (card.dataset.effect === effectKey) {
      card.className = "vis-effect-card active p-2.5 rounded-lg border text-left transition flex flex-col gap-0.5 cursor-pointer bg-cyan-950/50 border-cyan-500/60 text-white shadow-sm";
    } else {
      card.className = "vis-effect-card p-2.5 rounded-lg border text-left transition flex flex-col gap-0.5 cursor-pointer bg-slate-900/60 border-white/5 text-slate-300 hover:border-slate-700";
    }
  });
};

window.updateVisTitlePreview = function() {
  // Real-time canvas render loop picks up title/artist input automatically
};

window.selectHeroVisualizerStyle = function(styleKey) {
  visState.styleKey = styleKey;
  const select = document.getElementById("vis-quick-style-select");
  if (select) select.value = styleKey;
  window.generateHeroAiImage();
};

window.generateHeroAiImage = async function() {
  const btn = document.getElementById("btn-vis-generate-ai");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>생성 중...</span>`;
  }

  const title = (document.getElementById("vis-title-input")?.value || mvState.activeTitle || "Track").trim();
  const styleKey = visState.styleKey || "real_photo";

  try {
    const res = await fetch("/api/mv/generate-still", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: `vis_${Date.now()}`,
        still_index: 0,
        prompt: `Master album hero still, best cinematic art, 8k wallpaper`,
        style_key: styleKey,
        fallback_title: title,
        fallback_subtitle: "Visualizer Hero"
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || "이미지 생성 실패");

    visState.heroImageUrl = data.image_url;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      visState.heroImageObj = img;
    };
    img.src = data.image_url;

    const label = document.getElementById("vis-photo-filename-label");
    if (label) label.textContent = `화풍 썸네일: ${styleKey}`;
  } catch (e) {
    console.error("Hero AI image error:", e);
    alert("이미지 생성 실패:\n" + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
};

window.handleHeroImageUpload = function(event) {
  const file = event.target.files[0];
  if (!file) return;

  const label = document.getElementById("vis-photo-filename-label");
  if (label) label.textContent = `업로드된 사진: ${file.name}`;

  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target.result;
    visState.heroImageUrl = dataUrl;

    const img = new Image();
    img.onload = () => {
      visState.heroImageObj = img;
    };
    img.src = dataUrl;
  };
  reader.readAsDataURL(file);
};

// Bind Drag & Drop on Visualizer Dropzone Box
document.addEventListener("DOMContentLoaded", () => {
  const dropBox = document.getElementById("vis-dropzone-box");
  if (dropBox) {
    ["dragenter", "dragover"].forEach(ev => {
      dropBox.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropBox.classList.add("border-cyan-400", "scale-[1.01]");
      });
    });

    ["dragleave", "drop"].forEach(ev => {
      dropBox.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropBox.classList.remove("border-cyan-400", "scale-[1.01]");
      });
    });

    dropBox.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0 && files[0].type.startsWith("image/")) {
        window.handleHeroImageUpload({ target: { files: files } });
      }
    });
  }
});

window.startHeroVisualizerRender = async function() {
  if (!mvState.activeAudioUrl) {
    alert("먼저 오디오 음원을 불러오거나 마스터링을 진행해주세요!");
    return;
  }

  const btn = document.getElementById("btn-quick-visualizer-render");
  const mainBtn = document.getElementById("btn-start-mv-render");
  if (btn) btn.disabled = true;
  if (mainBtn) mainBtn.disabled = true;

  const progBox = document.getElementById("mv-progress-box");
  const resBox = document.getElementById("mv-result-box");
  if (progBox) {
    progBox.classList.remove("hidden");
    progBox.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  if (resBox) resBox.classList.add("hidden");

  const title = (document.getElementById("vis-title-input")?.value || mvState.activeTitle || "Music Video").trim();
  const artist = (document.getElementById("vis-artist-input")?.value || "Antigravity Studio Mastered").trim();
  const styleSelect = document.getElementById("vis-style-select");
  const styleKey = visState.styleKey || (styleSelect ? styleSelect.value : "real_photo");

  try {
    const res = await fetch("/api/mv/render-visualizer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: mvState.activeAudioUrl,
        title: title,
        artist: artist,
        hero_image_url: visState.heroImageUrl || mvState.activeCoverUrl || null,
        style_key: styleKey,
        title_template: visState.titleTemplate || "modern_official",
        visualizer_effect: visState.visualizerEffect || "spectrum_bars",
        camera_motion: "slow_zoom",
        speed: mvState.activeSpeed || 1.0,
        start_sec: 0.0,
        duration_sec: null
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || data.error || "렌더링 작업 등록 실패");

    pollMvRenderProgress(data.task_id);

  } catch (err) {
    alert("비주얼라이저 MP4 렌더링 실패:\n" + err.message);
    if (btn) btn.disabled = false;
    if (mainBtn) mainBtn.disabled = false;
  }
};

window.closeMvStudioModal = function() {
  const modal = document.getElementById("modal-mv-studio");
  if (modal) modal.classList.add("hidden");
  const video = document.getElementById("mv-result-video");
  if (video) video.pause();
  if (mvState.pollTimer) {
    clearInterval(mvState.pollTimer);
    mvState.pollTimer = null;
  }
};

window.selectMvStyle = function(styleKey) {
  mvState.selectedStyle = styleKey;
  document.querySelectorAll(".mv-style-card").forEach(card => {
    if (card.dataset.style === styleKey) {
      card.className = "mv-style-card active p-2.5 rounded-lg border text-left transition flex flex-col gap-0.5 cursor-pointer bg-cyan-950/40 border-cyan-500/50 text-white";
    } else {
      card.className = "mv-style-card p-2.5 rounded-lg border text-left transition flex flex-col gap-0.5 cursor-pointer bg-slate-900/60 border-white/5 text-slate-300 hover:border-slate-700";
    }
  });
};

window.planMvStoryboard = async function() {
  if (!mvState.activeAudioUrl) {
    alert("오디오 음원 정보를 찾을 수 없습니다.");
    return false;
  }

  const btn = document.getElementById("btn-plan-mv");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-white"></i> <span>가사 분석 & 갤러리 기획 중...</span>`;
  }

  const titleInput = document.getElementById("mv-title-input");
  const artistInput = document.getElementById("mv-artist-input");
  const conceptEl = document.getElementById("mv-concept-input");
  const lyricsEl = document.getElementById("mv-lyrics-input");

  const title = (titleInput && titleInput.value.trim()) || mvState.activeTitle;
  const artist = (artistInput && artistInput.value.trim()) || "Antigravity Studio";
  const customConcept = conceptEl ? conceptEl.value.trim() : "";
  const userLyrics = lyricsEl ? lyricsEl.value.trim() : "";

  try {
    const res = await fetch("/api/mv/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_url: mvState.activeAudioUrl,
        title: title,
        artist: artist,
        style_key: mvState.selectedStyle,
        custom_concept: customConcept,
        user_lyrics: userLyrics,
        still_count: 4,
        target_cuts: 8,
        cover_url: mvState.activeCoverUrl
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "스토리보드 계획 생성 실패");
    }

    mvState.storyboard = data.storyboard;
    renderMvStills(mvState.storyboard.key_stills);

    const stillsSection = document.getElementById("mv-stills-section");
    if (stillsSection) stillsSection.classList.remove("hidden");

    const cutsBadge = document.getElementById("mv-cuts-info-badge");
    if (cutsBadge) {
      cutsBadge.textContent = `총 ${mvState.storyboard.scenes.length}개 컷 순환 (${mvState.storyboard.duration.toFixed(1)}초)`;
    }

    // Automatically trigger generating all stills for seamless UX
    await generateAllStillImages();
    return true;

  } catch (err) {
    console.error("MV Plan error:", err);
    alert("스틸이미지 기획 오류:\n" + err.message);
    return false;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml || `<i class="fa-solid fa-wand-magic-sparkles"></i> <span>스틸 갤러리 다시 기획하기</span>`;
    }
  }
};

function renderMvStills(keyStills) {
  const container = document.getElementById("mv-stills-container");
  if (!container) return;
  container.innerHTML = "";

  keyStills.forEach((still, idx) => {
    const isHero = still.is_hero || idx === 0;
    const card = document.createElement("div");
    card.id = `mv-still-card-${idx}`;
    card.className = `p-3 rounded-xl border flex flex-col gap-2 transition ${
      isHero
        ? "bg-[#101426] border-amber-500/50 shadow-lg shadow-amber-950/20"
        : "bg-[#0b0f1a] border-white/10 hover:border-slate-700"
    }`;

    const badgeHtml = isHero
      ? `<span class="bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-black text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm"><i class="fa-solid fa-crown text-[9px]"></i> 화면 대표 이미지 (Hero)</span>`
      : `<span class="bg-cyan-500/20 text-cyan-300 font-bold text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1 border border-cyan-500/30"><i class="fa-solid fa-image text-[9px]"></i> 추가 씬 #${idx} (${still.role})</span>`;

    const imgDisplay = still.image_url
      ? `<img src="${still.image_url}" id="mv-still-img-${idx}" class="w-full h-full object-cover rounded-lg">`
      : `<div id="mv-still-img-${idx}" class="w-full h-full flex flex-col items-center justify-center bg-slate-900/90 rounded-lg text-slate-500 gap-1 text-[11px]"><i class="fa-solid fa-spinner fa-spin text-cyan-400 text-lg"></i><span class="text-slate-400 font-mono text-[10px]">이미지 대기 중</span></div>`;

    card.innerHTML = `
      <div class="flex items-center justify-between">
        ${badgeHtml}
        <span class="text-[10px] text-slate-400 font-mono font-medium">${isHero ? "인트로/시그니처" : "모션 교차 순환"}</span>
      </div>

      <div class="relative w-full aspect-video rounded-lg overflow-hidden border border-white/10 bg-black shadow-inner">
        ${imgDisplay}
      </div>

      <div class="flex flex-col gap-1 text-left">
        <div class="flex items-center justify-between text-[11px]">
          <span class="font-bold text-white truncate">${still.name}</span>
        </div>
        <p class="text-[10px] text-slate-400 line-clamp-1">${still.desc}</p>
        <textarea id="mv-still-prompt-${idx}" rows="2" class="w-full bg-[#07090e] border border-slate-800 rounded px-2 py-1 text-[10px] text-slate-300 placeholder-slate-600 outline-none focus:border-cyan-500 font-mono resize-none" onchange="updateStillPrompt(${idx}, this.value)">${still.prompt || ''}</textarea>
      </div>

      <div class="flex items-center justify-end pt-1 border-t border-white/5">
        <button type="button" onclick="regenerateStillImage(${idx})" id="btn-regen-still-${idx}" class="w-full py-1.5 rounded-lg bg-white/5 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-300 text-[11px] font-bold flex items-center justify-center gap-1.5 transition cursor-pointer border border-white/5">
          <i class="fa-solid fa-arrows-rotate text-[10px]"></i>
          <span>새로고침 / 재생성</span>
        </button>
      </div>
    `;

    container.appendChild(card);
  });
}

window.updateStillPrompt = function(idx, prompt) {
  if (mvState.storyboard && mvState.storyboard.key_stills && mvState.storyboard.key_stills[idx]) {
    mvState.storyboard.key_stills[idx].prompt = prompt;
  }
};

window.regenerateStillImage = async function(idx) {
  if (!mvState.storyboard || !mvState.storyboard.key_stills || !mvState.storyboard.key_stills[idx]) return;
  const still = mvState.storyboard.key_stills[idx];
  const btn = document.getElementById(`btn-regen-still-${idx}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-cyan-400"></i> 생성 중...`;
  }

  const promptInput = document.getElementById(`mv-still-prompt-${idx}`);
  const promptVal = (promptInput && promptInput.value.trim()) || still.prompt;

  const imgBox = document.getElementById(`mv-still-img-${idx}`);
  if (imgBox) {
    const parent = imgBox.parentElement;
    parent.innerHTML = `<div id="mv-still-img-${idx}" class="w-full h-full flex flex-col items-center justify-center bg-slate-900/90 rounded-lg text-slate-400 gap-1.5 text-[11px]"><i class="fa-solid fa-spinner fa-spin text-cyan-400 text-xl"></i><span class="font-mono text-[10px]">AI 이미지 렌더링 중...</span></div>`;
  }

  const projId = mvState.taskId || "preview";

  try {
    const res = await fetch("/api/mv/generate-still", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projId,
        still_index: idx,
        prompt: promptVal,
        style_key: mvState.selectedStyle,
        fallback_title: still.name,
        fallback_subtitle: still.desc
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "스틸 이미지 생성 실패");
    }

    still.image_url = data.image_url;
    still.filename = data.filename;

    const updatedBox = document.getElementById(`mv-still-img-${idx}`);
    if (updatedBox) {
      const parent = updatedBox.parentElement;
      parent.innerHTML = `<img src="${data.image_url}" id="mv-still-img-${idx}" class="w-full h-full object-cover rounded-lg animate-in fade-in duration-300">`;
    }

  } catch (err) {
    console.error("Still gen error:", err);
    alert("이미지 생성 오류: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-arrows-rotate text-[10px]"></i> <span>새로고침 / 재생성</span>`;
    }
  }
};

window.generateAllStillImages = async function() {
  if (!mvState.storyboard || !mvState.storyboard.key_stills) return;
  const btn = document.getElementById("btn-gen-all-stills");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-white"></i> <span>스틸 이미지 일괄 생성 중...</span>`;
  }

  for (let i = 0; i < mvState.storyboard.key_stills.length; i++) {
    await window.regenerateStillImage(i);
  }

  if (btn) {
    btn.disabled = false;
    btn.innerHTML = origHtml;
  }
};

window.startMvRender = async function() {
  if (!mvState.activeAudioUrl) {
    alert("오디오 음원 정보를 찾을 수 없습니다.");
    return false;
  }

  // Seamless UX: If storyboard is not prepared yet, automatically prepare it first!
  if (!mvState.storyboard || !mvState.storyboard.scenes || mvState.storyboard.scenes.length === 0) {
    const planned = await window.planMvStoryboard();
    if (!planned || !mvState.storyboard) {
      return false;
    }
  }

  const btn = document.getElementById("btn-start-mv-render");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>MP4 렌더링 작업 시작 중...</span>`;
  }

  const titleInput = document.getElementById("mv-title-input");
  const artistInput = document.getElementById("mv-artist-input");
  if (titleInput && titleInput.value.trim()) {
    mvState.storyboard.title = titleInput.value.trim();
  }
  if (artistInput && artistInput.value.trim()) {
    mvState.storyboard.artist = artistInput.value.trim();
  }

  const dissolveSelect = document.getElementById("mv-dissolve-select");
  const karaokeToggle = document.getElementById("mv-toggle-karaoke");
  const introToggle = document.getElementById("mv-toggle-intro");
  const outroToggle = document.getElementById("mv-toggle-outro");

  const dissolveSec = dissolveSelect ? parseFloat(dissolveSelect.value) || 1.0 : 1.0;
  const enableKaraoke = karaokeToggle ? karaokeToggle.checked : true;
  const enableIntro = introToggle ? introToggle.checked : true;
  const enableOutro = outroToggle ? outroToggle.checked : true;

  const progBox = document.getElementById("mv-progress-box");
  const resBox = document.getElementById("mv-result-box");
  if (progBox) {
    progBox.classList.remove("hidden");
    progBox.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  if (resBox) resBox.classList.add("hidden");

  try {
    const res = await fetch("/api/mv/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: mvState.taskId || null,
        storyboard: mvState.storyboard,
        audio_url: mvState.activeAudioUrl,
        dissolve_sec: dissolveSec,
        enable_subtitles: enableKaraoke,
        enable_intro: enableIntro,
        enable_outro: enableOutro,
        speed: mvState.activeSpeed,
        start_sec: 0.0,
        duration_sec: null
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "렌더링 작업 등록 실패");
    }

    const taskId = data.task_id;
    mvState.taskId = taskId;

    pollMvRenderProgress(taskId);
    return true;

  } catch (err) {
    alert("MP4 렌더링 시작 실패:\n" + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>🚀 AI 노래방 뮤직비디오 MP4 렌더링 시작</span>`;
    }
    return false;
  }
};

window.autoGenerateMv = async function() {
  if (!mvState.activeAudioUrl) {
    alert("먼저 오디오 음원을 불러오거나 마스터링을 진행해주세요!");
    return;
  }

  const quickBtn = document.getElementById("btn-quick-auto-mv");
  const origHtml = quickBtn ? quickBtn.innerHTML : "";
  if (quickBtn) {
    quickBtn.disabled = true;
    quickBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>원스톱 MV 제작 진행 중...</span>`;
  }

  try {
    // 1. If storyboard not planned, plan it
    if (!mvState.storyboard || !mvState.storyboard.scenes || mvState.storyboard.scenes.length === 0) {
      const ok = await window.planMvStoryboard();
      if (!ok) return;
    }
    // 2. Start rendering
    await window.startMvRender();
  } catch (e) {
    console.error("Auto MV error:", e);
  } finally {
    if (quickBtn) {
      quickBtn.disabled = false;
      quickBtn.innerHTML = origHtml;
    }
  }
};

function pollMvRenderProgress(taskId) {
  if (mvState.pollTimer) clearInterval(mvState.pollTimer);

  const stageEl = document.getElementById("mv-progress-stage");
  const pctEl = document.getElementById("mv-progress-percent");
  const barEl = document.getElementById("mv-progress-bar");
  const btn = document.getElementById("btn-start-mv-render");

  mvState.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/mv/status/${taskId}`);
      const data = await res.json();

      if (pctEl) pctEl.textContent = `${data.progress || 0}%`;
      if (barEl) barEl.style.width = `${data.progress || 0}%`;
      if (stageEl) {
        stageEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-cyan-400"></i> <span>${data.stage || "렌더링 진행 중..."}</span>`;
      }

      if (data.status === "completed") {
        clearInterval(mvState.pollTimer);
        mvState.pollTimer = null;

        if (stageEl) {
          stageEl.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> <span>${data.stage}</span>`;
        }

        const resBox = document.getElementById("mv-result-box");
        const video = document.getElementById("mv-result-video");
        const dlBtn = document.getElementById("mv-download-btn");
        const fname = document.getElementById("mv-result-filename");
        const meta = document.getElementById("mv-result-file-meta");

        if (resBox) {
          resBox.classList.remove("hidden");
          resBox.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        if (video) {
          video.src = data.mp4_url;
          video.load();
          video.play().catch(e => console.log("Video autoplay prevented:", e));
        }
        if (dlBtn) {
          dlBtn.href = data.mp4_url;
          dlBtn.download = data.filename || "music_video.mp4";
        }
        if (fname) fname.textContent = data.filename || "music_video.mp4";
        if (meta) meta.textContent = `720P HD • ${data.size_mb || 0} MB • Ken-Burns & Dissolve`;

        const quickVisBtn = document.getElementById("btn-quick-visualizer-render");
        if (quickVisBtn) quickVisBtn.disabled = false;

        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> <span>다시 렌더링</span>`;
        }
      } else if (data.status === "failed") {
        clearInterval(mvState.pollTimer);
        mvState.pollTimer = null;
        alert("렌더링 실패:\n" + (data.error || data.stage));
        const quickVisBtn = document.getElementById("btn-quick-visualizer-render");
        if (quickVisBtn) quickVisBtn.disabled = false;
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>다시 시도</span>`;
        }
      }

    } catch (err) {
      console.error("MV status poll error:", err);
    }
  }, 1200);
}

window.openMvStudioModal = openMvStudioModal;
window.closeMvStudioModal = closeMvStudioModal;
window.selectMvStyle = selectMvStyle;
window.planMvStoryboard = planMvStoryboard;
window.renderMvStills = renderMvStills;
window.updateStillPrompt = updateStillPrompt;
window.regenerateStillImage = regenerateStillImage;
window.generateAllStillImages = generateAllStillImages;
window.startMvRender = startMvRender;
window.autoGenerateMv = autoGenerateMv;

// ============================================================================
// YOUTUBE CONTENT ID COPYRIGHT PRE-CHECK SYSTEM
// ============================================================================

let copyrightInspectableFiles = [];

window.switchCopyrightTab = function(tabName) {
  const tabs = ['link', 'upload', 'recent'];
  for (const t of tabs) {
    const content = document.getElementById(`tab-content-cp-${t}`);
    const btn = document.getElementById(`tab-btn-cp-${t}`);
    if (t === tabName) {
      if (content) content.classList.remove('hidden');
      if (btn) {
        btn.className = 'flex-1 py-2 px-3 rounded-lg font-bold transition flex items-center justify-center gap-2 text-white bg-red-600/30 border border-red-500/40 cursor-pointer shadow-sm';
      }
    } else {
      if (content) content.classList.add('hidden');
      if (btn) {
        btn.className = 'flex-1 py-2 px-3 rounded-lg font-semibold text-slate-400 hover:text-white transition flex items-center justify-center gap-2 cursor-pointer';
      }
    }
  }
  if (tabName === 'recent') {
    loadCopyrightFiles();
  }
};

window.runCopyrightUrlCheck = async function() {
  const input = document.getElementById('copyright-url-input');
  const url = input ? input.value.trim() : '';
  if (!url) {
    alert('Suno 링크, YouTube 링크, 또는 MP3 오디오 URL을 입력해주세요.');
    if (input) input.focus();
    return;
  }

  const loading = document.getElementById('copyright-loading');
  const resultCard = document.getElementById('copyright-result-card');
  const btn = document.getElementById('btn-run-copyright-url');
  const loadingMsg = document.getElementById('copyright-loading-msg');

  if (loading) loading.classList.remove('hidden');
  if (resultCard) resultCard.classList.add('hidden');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>음원 추출 및 지문 대조 중...</span>`;
  }
  if (loadingMsg) {
    loadingMsg.textContent = 'Suno / YouTube 링크에서 음원을 추출하고 비공식 음향 인식·카탈로그 검색을 진행하는 중입니다... (약 5~15초 소요, 검사 엔진에 따라 시간이 더 걸릴 수 있습니다)';
  }

  try {
    const res = await fetch('/api/copyright/url-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || data.detail || '링크 음원 저작권 검사 중 오류가 발생했습니다.');
    }
    renderCopyrightResult(data);
    loadCopyrightFiles();
  } catch (err) {
    alert('링크 저작권 진단 실패:\n' + err.message);
  } finally {
    if (loading) loading.classList.add('hidden');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>음원 추출 & 저작권 진단</span>`;
    }
  }
};

window.openCopyrightModal = async function(preselectTarget = null, autoRunActive = false) {
  const modal = document.getElementById('youtube-copyright-modal');
  if (window.showCopyrightPage) {
    window.showCopyrightPage();
  } else if (modal) {
    modal.classList.remove('hidden');
  }

  // Check if track is active in the studio
  const activeBanner = document.getElementById('copyright-active-track-banner');
  const activeTitle = document.getElementById('copyright-active-track-title');
  const activeSub = document.getElementById('copyright-active-track-sub');

  const curData = state.currentTrackData || state.audio;
  const audioUrl = state.lastRenderedMasterUrl || state.originalAudioUrl || curData?.audio_url || (state.audioElement && state.audioElement.src);
  const filePath = curData?.file_path;
  const hasActive = Boolean(filePath || audioUrl);

  const isMastered = Boolean(state.lastRenderedMasterUrl);
  const songTitle = state.lastRenderedMasterName 
    ? state.lastRenderedMasterName.replace(/^\[.*?\]\s*/, "") 
    : ((curData && curData.title) || state.originalFilename || (isMastered ? '완곡 마스터링 음원' : '현재 작업 트랙'));
  const fName = (curData && curData.filename) || state.originalFilename || '';
  const dur = (curData && curData.duration_str) || '';

  if (activeBanner) {
    if (hasActive) {
      activeBanner.classList.remove('hidden');
      if (activeTitle) activeTitle.textContent = songTitle;
      const masterTag = isMastered ? " • [완곡 마스터링 음원]" : " • [스튜디오 활성 원본]";
      if (activeSub) activeSub.textContent = `${fName} ${dur ? '• ' + dur : ''}${masterTag}`;
    } else {
      activeBanner.classList.add('hidden');
    }
  }

  // If user opened with autoRunActive or has active track and no explicit other target:
  if (hasActive && autoRunActive && !preselectTarget) {
    // Automatically perform copyright check on the active studio track!
    await checkActiveStudioTrackCopyright();
  } else if (preselectTarget) {
    switchCopyrightTab('recent');
    await loadCopyrightFiles(preselectTarget);
  } else {
    switchCopyrightTab('link');
    loadCopyrightFiles();
  }
};

window.checkActiveStudioTrackCopyright = async function() {
  const curData = state.currentTrackData || state.audio;
  const filePath = curData?.file_path;
  const audioUrl = state.lastRenderedMasterUrl || state.originalAudioUrl || curData?.audio_url || (state.audioElement && state.audioElement.src);

  if (!filePath && !audioUrl) {
    alert('현재 스튜디오에 로드된 곡이 없습니다. 먼저 음원을 불러와주세요.');
    return;
  }

  const isMastered = Boolean(state.lastRenderedMasterUrl);
  const songTitle = state.lastRenderedMasterName 
    ? state.lastRenderedMasterName.replace(/^\[.*?\]\s*/, "") 
    : ((curData && curData.title) || state.originalFilename || (isMastered ? '완곡 마스터링 음원' : '현재 스튜디오 음원'));

  const loading = document.getElementById('copyright-loading');
  const resultCard = document.getElementById('copyright-result-card');
  const loadingMsg = document.getElementById('copyright-loading-msg');

  if (loading) {
    loading.classList.remove('hidden');
    loading.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  if (resultCard) resultCard.classList.add('hidden');
  if (loadingMsg) {
    const trackLabel = isMastered ? '완곡 마스터 음원' : '스튜디오 선택 트랙';
    loadingMsg.innerHTML = `<span class="text-cyan-400 font-bold">참고용 저작권 진단 중:</span> [${trackLabel}: ${songTitle}]의 음향 인식(Shazam) + 가사 인식 + 작곡/출판 카탈로그 검색을 진행합니다. 공식 Content ID 판정이 아닙니다...`;
  }

  try {
    const payload = {
      file_path: filePath || null,
      audio_url: audioUrl || null,
      title: songTitle || null
    };
    const res = await fetch('/api/copyright/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || data.detail || '저작권 검사 중 오류가 발생했습니다.');
    }
    // Inject song title if missing in response
    if (!data.target_file) data.target_file = songTitle;
    renderCopyrightResult(data);
    if (resultCard) {
      resultCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } catch (err) {
    alert('현재 작업곡 저작권 진단 실패:\n' + err.message);
  } finally {
    if (loading) loading.classList.add('hidden');
  }
};

window.closeCopyrightModal = function() {
  if (window.leaveCopyrightPage) {
    window.leaveCopyrightPage();
    return;
  }
  const modal = document.getElementById('youtube-copyright-modal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }
};

window.loadCopyrightFiles = async function(selectTarget = null) {
  const sel = document.getElementById('copyright-file-select');
  const countEl = document.getElementById('copyright-file-count');
  if (!sel) return;

  sel.innerHTML = '<option value="">음원 및 영상 목록 불러오는 중...</option>';
  try {
    const res = await fetch('/api/copyright/files');
    const data = await res.json();
    copyrightInspectableFiles = data.files || [];

    if (countEl) {
      countEl.textContent = `최근 작업 파일 ${copyrightInspectableFiles.length}개 감지됨`;
    }

    if (copyrightInspectableFiles.length === 0) {
      sel.innerHTML = '<option value="">검사 가능한 최근 파일이 없습니다. 직접 업로드해주세요.</option>';
      return;
    }

    // Group files by category
    const groups = {};
    for (const f of copyrightInspectableFiles) {
      const cat = f.category || '기타 음원';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(f);
    }

    let html = '';
    let foundPreselect = false;

    for (const [cat, files] of Object.entries(groups)) {
      html += `<optgroup label="── ${cat} ──">`;
      for (const f of files) {
        const isMatch = selectTarget && (f.filename.includes(selectTarget) || f.path === selectTarget);
        if (isMatch) foundPreselect = true;
        html += `<option value="${encodeURIComponent(f.path)}" ${isMatch ? 'selected' : ''}>${f.filename} (${f.size_mb} MB)</option>`;
      }
      html += `</optgroup>`;
    }

    sel.innerHTML = html;

    // If preselectTarget is specified and found, trigger check automatically
    if (selectTarget && foundPreselect) {
      setTimeout(() => runCopyrightCheck(), 200);
    }
  } catch (err) {
    console.error('Error loading copyright files:', err);
    sel.innerHTML = '<option value="">파일 목록을 불러오지 못했습니다.</option>';
  }
};

window.runCopyrightCheck = async function() {
  const sel = document.getElementById('copyright-file-select');
  if (!sel || !sel.value) {
    alert('검사할 음원 또는 영상 파일을 선택해주세요.');
    return;
  }

  const filePath = decodeURIComponent(sel.value);
  const loading = document.getElementById('copyright-loading');
  const resultCard = document.getElementById('copyright-result-card');
  const btn = document.getElementById('btn-run-copyright-check');
  const loadingMsg = document.getElementById('copyright-loading-msg');

  if (loading) loading.classList.remove('hidden');
  if (resultCard) resultCard.classList.add('hidden');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>진단 분석 중...</span>`;
  }
  if (loadingMsg) {
    loadingMsg.textContent = '비공식 음향 인식(Shazam) 및 카탈로그 검색 대조 중...';
  }

  try {
    const res = await fetch('/api/copyright/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath })
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || data.detail || '저작권 검사 중 오류가 발생했습니다.');
    }
    renderCopyrightResult(data);
  } catch (err) {
    alert('저작권 검사 실패:\n' + err.message);
  } finally {
    if (loading) loading.classList.add('hidden');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>저작권 진단 시작</span>`;
    }
  }
};

window.uploadAndCheckCopyright = async function(file) {
  if (!file) return;

  const loading = document.getElementById('copyright-loading');
  const resultCard = document.getElementById('copyright-result-card');
  const btn = document.getElementById('btn-run-copyright-check');
  const loadingMsg = document.getElementById('copyright-loading-msg');

  if (loading) loading.classList.remove('hidden');
  if (resultCard) resultCard.classList.add('hidden');
  if (btn) btn.disabled = true;
  if (loadingMsg) {
    loadingMsg.textContent = `파일 업로드 및 참고용 음향 인식·카탈로그 검색 중... (${file.name})`;
  }

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res = await fetch('/api/copyright/upload-check', {
      method: 'POST',
      body: fd
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.error || data.detail || '파일 업로드 검사 중 오류가 발생했습니다.');
    }
    renderCopyrightResult(data);
    // Reload file list in background
    loadCopyrightFiles();
  } catch (err) {
    alert('업로드 및 저작권 검사 실패:\n' + err.message);
  } finally {
    if (loading) loading.classList.add('hidden');
    if (btn) btn.disabled = false;
  }
};

window.checkCurrentMasterCopyright = function() {
  openCopyrightModal(null, true);
};

window.checkCurrentMvCopyright = function() {
  const mvFilenameEl = document.getElementById('mv-result-filename');
  const mvFilename = mvFilenameEl ? mvFilenameEl.textContent.trim() : null;
  openCopyrightModal(mvFilename);
};

function renderCopyrightResult(data) {
  const resultCard = document.getElementById('copyright-result-card');
  if (!resultCard) return;

  // Elements
  const verdictBox = document.getElementById('copyright-verdict-box');
  const statusIcon = document.getElementById('copyright-status-icon');
  const riskBadge = document.getElementById('copyright-risk-badge');
  const targetFilename = document.getElementById('copyright-target-filename');
  const verdictTitle = document.getElementById('copyright-verdict-title');
  const verdictDesc = document.getElementById('copyright-verdict-desc');
  const scoreNum = document.getElementById('copyright-score-num');
  const scoreLabel = document.getElementById('copyright-score-label');

  const matchedBox = document.getElementById('copyright-matched-box');
  const matchCover = document.getElementById('copyright-match-cover');
  const matchTitle = document.getElementById('copyright-match-title');
  const matchArtist = document.getElementById('copyright-match-artist');
  const matchAlbum = document.getElementById('copyright-match-album');
  const matchLabel = document.getElementById('copyright-match-label');
  const matchLink = document.getElementById('copyright-match-link');

  const monetizationTxt = document.getElementById('copyright-monetization-txt');
  const specLufs = document.getElementById('copyright-spec-lufs');
  const specPeak = document.getElementById('copyright-spec-peak');
  const specDur = document.getElementById('copyright-spec-dur');
  const recList = document.getElementById('copyright-recommendations');

  // Fill Header Data
  if (targetFilename) targetFilename.textContent = data.filename || '';
  const coverage = Number(data.coverage_pct ?? data.safety_score ?? 0);
  if (scoreNum) scoreNum.textContent = Math.round(coverage);
  if (verdictDesc) verdictDesc.textContent = data.verdict || '';

  // Theme according to risk / verification state
  const isCritical = (data.risk_level === 'CRITICAL');
  const isHigh = (data.risk_level === 'HIGH');
  const isMatched = isCritical || isHigh || data.matched === true;
  const isCover = (data.match_category === 'COVER_COMPOSITION');
  const isNoMatch = (data.risk_level === 'NO_MATCH');
  const isUnverified = (data.risk_level === 'UNVERIFIED');

  if (verdictBox) {
    if (isCritical || isHigh) {
      verdictBox.className = 'p-4 rounded-xl border border-orange-500/60 bg-orange-950/40 flex flex-col md:flex-row items-center justify-between gap-4 transition shadow-lg shadow-orange-950/40';
    } else if (isUnverified) {
      verdictBox.className = 'p-4 rounded-xl border border-amber-500/50 bg-amber-950/30 flex flex-col md:flex-row items-center justify-between gap-4 transition shadow-lg shadow-amber-950/30';
    } else {
      verdictBox.className = 'p-4 rounded-xl border border-slate-500/40 bg-slate-900/50 flex flex-col md:flex-row items-center justify-between gap-4 transition shadow-lg shadow-slate-950/40';
    }
  }

  if (statusIcon) {
    if (isCritical || isHigh) {
      statusIcon.className = 'w-12 h-12 rounded-xl bg-red-500/20 text-red-400 border border-red-500/50 flex items-center justify-center text-2xl font-bold animate-pulse';
      statusIcon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
    } else if (isCover) {
      statusIcon.className = 'w-12 h-12 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/50 flex items-center justify-center text-2xl font-bold animate-pulse';
      statusIcon.innerHTML = '<i class="fa-solid fa-microphone-lines"></i>';
    } else if (isUnverified) {
      statusIcon.className = 'w-12 h-12 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center justify-center text-2xl font-bold';
      statusIcon.innerHTML = '<i class="fa-solid fa-circle-question"></i>';
    } else {
      statusIcon.className = 'w-12 h-12 rounded-xl bg-slate-500/20 text-slate-300 border border-slate-500/40 flex items-center justify-center text-2xl font-bold';
      statusIcon.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i>';
    }
  }

  if (riskBadge) {
    if (isCritical) {
      riskBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-red-500/20 text-red-300 border border-red-500/50';
      riskBadge.textContent = '🚨 음원 지문 일치 (CRITICAL)';
    } else if (isHigh) {
      riskBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-orange-500/20 text-orange-300 border border-orange-500/50';
      riskBadge.textContent = '⚠️ 유사 음원 감지 (HIGH)';
    } else if (isUnverified) {
      riskBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-amber-500/20 text-amber-300 border border-amber-500/50';
      riskBadge.textContent = '⚠️ 검사 미완료 (UNVERIFIED)';
    } else {
      riskBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-slate-500/20 text-slate-300 border border-slate-500/40';
      riskBadge.textContent = '검사 범위 내 미감지 (NO MATCH)';
    }
  }

  if (verdictTitle) {
    if (isCritical) {
      verdictTitle.textContent = '음원 지문이 기존 상용 음원과 일치합니다';
    } else if (isCover) {
      verdictTitle.textContent = '커버곡/편곡 가능성 — 작곡·작사 저작권 확인 필요';
    } else if (isHigh) {
      verdictTitle.textContent = '유사 음원이 감지되었습니다';
    } else if (isUnverified) {
      verdictTitle.textContent = '검사 엔진이 실행되지 않아 판단할 수 없습니다';
    } else {
      verdictTitle.textContent = '검사 범위 내 일치 항목이 발견되지 않았습니다';
    }
  }

  if (scoreLabel) {
    if (isCritical || isHigh) {
      scoreLabel.textContent = '일치/유사 후보 발견';
      scoreLabel.className = 'text-[10px] font-bold font-mono text-red-400';
    } else if (isUnverified) {
      scoreLabel.textContent = '일부 엔진 미실행 — 안전 아님';
      scoreLabel.className = 'text-[10px] font-bold font-mono text-amber-400';
    } else {
      scoreLabel.textContent = '검사 커버리지 (안전 보장 아님)';
      scoreLabel.className = 'text-[10px] font-bold font-mono text-slate-400';
    }
  }

  // Matched Track Box
  if (data.matched && data.track_info) {
    if (matchedBox) matchedBox.classList.remove('hidden');
    if (matchTitle) matchTitle.textContent = data.track_info.title || '알 수 없음';
    if (matchArtist) matchArtist.textContent = data.track_info.artist || '알 수 없음';
    if (matchAlbum) matchAlbum.textContent = data.track_info.album || 'Single';
    if (matchLabel) matchLabel.textContent = data.track_info.label || '정보 없음';
    if (matchCover) {
      matchCover.src = data.track_info.cover_art || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=200&q=80';
    }
    if (matchLink) {
      if (data.track_info.external_url) {
        matchLink.href = data.track_info.external_url;
        matchLink.classList.remove('hidden');
      } else {
        matchLink.classList.add('hidden');
      }
    }
  } else {
    if (matchedBox) matchedBox.classList.add('hidden');
  }

  // Detected Lyric Snippet Box
  const lyricsBox = document.getElementById('copyright-detected-lyrics-box');
  const lyricsTxt = document.getElementById('copyright-detected-lyrics-txt');
  if (lyricsBox && lyricsTxt) {
    if (data.detected_lyrics) {
      lyricsBox.classList.remove('hidden');
      lyricsTxt.textContent = `"${data.detected_lyrics}"`;
    } else {
      lyricsBox.classList.add('hidden');
    }
  }

  // Monetization Outlook (reference only, never a guarantee)
  if (monetizationTxt) {
    monetizationTxt.textContent = data.monetization || '';
    monetizationTxt.className = isMatched ? 'text-xs text-orange-300 leading-relaxed font-semibold' : (isUnverified ? 'text-xs text-amber-300 leading-relaxed font-semibold' : 'text-xs text-slate-300 leading-relaxed');
  }

  // Audio Specs
  const ac = data.acoustic || {};
  if (specLufs) specLufs.textContent = `${ac.est_lufs || -14.0} LUFS`;
  if (specPeak) specPeak.textContent = `${ac.peak_db || 0.0} dBFS`;
  if (specDur) {
    const s = Math.round(ac.duration || 0);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    specDur.textContent = `${m.toString().padStart(2, '0')}:${rem.toString().padStart(2, '0')}`;
  }

  // Per-engine check results
  const checksList = document.getElementById('copyright-checks');
  if (checksList) {
    checksList.innerHTML = '';
    const checks = data.checks || [];
    if (!checks.length) {
      const li = document.createElement('li');
      li.className = 'text-slate-400';
      li.textContent = '검사 항목 정보가 없습니다.';
      checksList.appendChild(li);
    }
    for (const c of checks) {
      const li = document.createElement('li');
      li.className = 'flex items-start gap-2 leading-relaxed';
      const ok = c.status === 'ok' || c.status === 'matched' || c.status === 'no_match';
      const icon = c.status === 'matched' ? 'fa-triangle-exclamation text-red-400'
        : (c.status === 'no_match' ? 'fa-magnifying-glass text-slate-400'
        : (ok ? 'fa-check text-emerald-400' : 'fa-circle-question text-amber-400'));
      const name = c.label || c.name || c.engine || '검사';
      const statusText = {
        matched: '일치 항목 발견',
        no_match: '일치 항목 없음',
        unavailable: '엔진 미실행',
        timeout: '시간 초과',
        error: '오류',
        ok: '완료',
      }[c.status] || c.status || '';
      const detail = c.detail || c.message || statusText;
      li.innerHTML = `<i class="fa-solid ${icon} mt-0.5 w-3.5"></i><span><b>${name}</b>${detail ? ' — ' + detail : ''}</span>`;
      checksList.appendChild(li);
    }
  }

  const disclaimerEl = document.getElementById('copyright-disclaimer');
  if (disclaimerEl) {
    disclaimerEl.textContent = data.disclaimer || '이 진단은 비공식 참고 자료이며 공식 YouTube Content ID 판정이 아닙니다.';
  }

  // Recommendations
  if (recList) {
    recList.innerHTML = '';
    const recs = data.recommendations || [];
    for (const r of recs) {
      const li = document.createElement('li');
      li.className = 'flex items-start gap-2 leading-relaxed';
      li.innerHTML = `<span class="text-amber-400 mt-0.5">•</span> <span>${r}</span>`;
      recList.appendChild(li);
    }
  }

  resultCard.classList.remove('hidden');
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ============================================================================
// SUNO V6 REVERSE PROMPT ENGINEERING UI CONTROLLER
// ============================================================================

state.currentSunoV6Prompt = null;

function populateSunoV6Prompt(data) {
  const pCard = document.getElementById('suno-v6-prompt-card');
  const pData = data.suno_v6_prompt;
  if (!pData) {
    if (pCard) pCard.classList.add('hidden');
    return;
  }

  state.currentSunoV6Prompt = pData;
  if (pCard) pCard.classList.remove('hidden');

  const stylesBox = document.getElementById('suno-v6-styles-box');
  const stylesCounter = document.getElementById('suno-v6-styles-counter');
  const excludeBox = document.getElementById('suno-v6-exclude-box');

  const paramWeirdness = document.getElementById('suno-v6-param-weirdness');
  const paramInfluence = document.getElementById('suno-v6-param-influence');
  const paramBpm = document.getElementById('suno-v6-param-bpm');
  const paramKey = document.getElementById('suno-v6-param-key');

  const repVocal = document.getElementById('suno-v6-rep-vocal');
  const repInst = document.getElementById('suno-v6-rep-inst');
  const repStruct = document.getElementById('suno-v6-rep-struct');

  // Styles
  if (stylesBox) stylesBox.textContent = pData.styles_prompt || '';
  if (stylesCounter) {
    const chars = pData.styles_char_count || (pData.styles_prompt || '').length;
    stylesCounter.textContent = `${chars} / 1,000자`;
    stylesCounter.className = chars <= 1000 
      ? 'text-[10px] font-mono text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30'
      : 'text-[10px] font-mono text-rose-400 font-bold bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-500/30';
  }

  // Exclude
  if (excludeBox) excludeBox.textContent = pData.exclude_prompt || '-';

  // Precision Structured Lyrics Architecture
  const lyricsBox = document.getElementById('suno-v6-lyrics-box');
  if (lyricsBox) {
    lyricsBox.textContent = pData.lyrics_architecture || pData.raw_lyrics || '분석된 가사 데이터가 없습니다.';
  }

  // Advanced Params
  const adv = pData.advanced_params || {};
  if (paramWeirdness) paramWeirdness.textContent = adv.weirdness_creativity || '0.25';
  if (paramInfluence) paramInfluence.textContent = adv.style_influence_adherence || '90%';
  if (paramBpm) paramBpm.textContent = `${adv.tempo_bpm || Math.round(data.tempo_analysis?.start_bpm || 120)} BPM`;
  if (paramKey) paramKey.textContent = adv.musical_key || data.musical_key || 'C Major';

  // In-depth Commentary
  const rep = pData.technical_report || {};
  const vRep = rep.vocal_breakdown || {};
  const aRep = rep.arrangement_breakdown || {};

  if (repVocal) {
    repVocal.textContent = `${vRep.vocal_classification || '리드 보컬'} • ${vRep.performance_technique || ''} | ${vRep.vocal_layering || ''} | ${vRep.rap_and_rhythm || ''}`;
  }
  if (repInst) {
    repInst.textContent = `${aRep.instrument_texture || ''} | 저역대: ${aRep.bass_and_kick || ''}`;
  }
  if (repStruct) {
    repStruct.textContent = `${rep.structural_dynamics || ''} | 템포/하모니: ${aRep.rhythm_and_tempo || ''} (${aRep.harmony_and_key || ''})`;
  }
}

window.toggleSunoDeepCommentary = function() {
  const body = document.getElementById('suno-deep-commentary-body');
  const icon = document.getElementById('suno-deep-commentary-icon');
  if (!body) return;
  const isHidden = body.classList.contains('hidden');
  if (isHidden) {
    body.classList.remove('hidden');
    if (icon) icon.className = 'fa-solid fa-chevron-up text-xs text-slate-400 transition-transform';
  } else {
    body.classList.add('hidden');
    if (icon) icon.className = 'fa-solid fa-chevron-down text-xs text-slate-400 transition-transform';
  }
};

window.copySunoSection = function(type) {
  if (!state.currentSunoV6Prompt) {
    alert('아직 분석된 Suno v6 프롬프트가 없습니다.');
    return;
  }
  let txt = '';
  let label = '';
  if (type === 'styles') {
    txt = state.currentSunoV6Prompt.styles_prompt;
    label = 'Suno Styles 프롬프트 (1,000자 미만)';
  } else if (type === 'exclude') {
    txt = state.currentSunoV6Prompt.exclude_prompt;
    label = 'Exclude Styles (제외할 스타일)';
  } else if (type === 'lyrics') {
    txt = state.currentSunoV6Prompt.lyrics_architecture || state.currentSunoV6Prompt.raw_lyrics;
    label = 'Suno v6 정밀 가사 & 연출 프롬프트';
  }

  if (navigator.clipboard && txt) {
    navigator.clipboard.writeText(txt).then(() => {
      if (window.showToast) {
        showToast(`📋 ${label}가 클립보드에 복사되었습니다!`, 'success');
      } else {
        alert(`${label}가 클립보드에 복사되었습니다!`);
      }
    });
  }
};

window.copyAllSunoPromptSuite = function() {
  const p = state.currentSunoV6Prompt;
  if (!p) {
    alert('아직 분석된 Suno v6 프롬프트가 없습니다.');
    return;
  }

  const adv = p.advanced_params || {};
  const blueprint = (p.structure_blueprint || []).join('\n');
  const lyricsArchitecture = p.lyrics_architecture || p.raw_lyrics || '';

  const fullText = `[Suno v6 Reverse Prompt Suite - Complete Edition]
══════════════════════════════════════════════════════════════
▶ 1. STYLES (스타일스 프롬프트 - ${p.styles_char_count}자 / 1,000자 미만):
${p.styles_prompt}

▶ 2. EXCLUDE STYLES (제외할 스타일 / 네거티브 프롬프트):
${p.exclude_prompt}

▶ 3. SUNO v6 ADVANCED SETTINGS (고급 옵션 추천값):
- Engine Version: ${adv.engine_version || 'Suno v6'}
- Weirdness (창의성/변주): ${adv.weirdness_creativity || '0.25'}
- Style Influence (스타일 반영도): ${adv.style_influence_adherence || '90%'}
- BPM (템포): ${adv.tempo_bpm} BPM
- Musical Key (조성): ${adv.musical_key}
- Vocal Mix Priority: ${adv.vocal_mix_priority}
- Stereo Panorama: ${adv.stereo_dimension}

▶ 4. PRECISION STRUCTURED LYRICS (정밀 가사 구조 & 연출 프롬프트):
${lyricsArchitecture}
══════════════════════════════════════════════════════════════`;

  if (navigator.clipboard) {
    navigator.clipboard.writeText(fullText).then(() => {
      if (window.showToast) {
        showToast('🔥 Suno v6 가사 포함 전체 프롬프트 설계도가 클립보드에 복사되었습니다!', 'success');
      } else {
        alert('🔥 Suno v6 가사 포함 전체 프롬프트 설계도가 클립보드에 복사되었습니다!');
      }
    });
  }
};

// Drag & Drop Setup for Copyright Dropzone
document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('copyright-dropzone');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.add('border-red-400', 'bg-[#181d2c]');
      });
    });
    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-red-400', 'bg-[#181d2c]');
      });
    });
    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        uploadAndCheckCopyright(e.dataTransfer.files[0]);
      }
    });
  }
});

// =========================================================================
// HIGH-SPEED MULTI-URL BATCH SYSTEM (FAST MP4 & MP3 BATCH EXPORT)
// =========================================================================

let currentBatchId = null;
let batchPollTimer = null;
const batchAutoDownloadedUrls = new Set();

function triggerAutoDownload(url, filename) {
  if (!url) return;
  try {
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    if (filename) a.setAttribute('download', filename);
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      try { document.body.removeChild(a); } catch (_) {}
    }, 1500);
  } catch (e) {
    console.warn('Auto download error:', e);
  }
}

function extractSongThumb(url, explicitImg = '') {
  if (explicitImg) return { thumb: explicitImg, sunoId: null };
  if (!url) return { thumb: null, sunoId: null };
  const sm = url.match(/(?:suno\.(?:com|ai)\/song\/|\b)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b/i);
  if (sm) {
    const sunoId = sm[1];
    return {
      thumb: `https://cdn2.suno.ai/image_${sunoId}.jpeg`,
      sunoId: sunoId
    };
  }
  const ym = url.match(/(?:youtu\.be\/|v=|\/embed\/|\/v\/)([a-zA-Z0-9_-]{11})/);
  if (ym) {
    return {
      thumb: `https://img.youtube.com/vi/${ym[1]}/mqdefault.jpg`,
      sunoId: null
    };
  }
  return { thumb: null, sunoId: null };
}

function updateRowThumbnail(row, val) {
  if (!row) return;
  const input = row.querySelector('.batch-url-input');
  const currentVal = val !== undefined ? val : (input ? input.value.trim() : '');
  const { thumb, sunoId } = extractSongThumb(currentVal, row.dataset.imageUrl);

  let thumbEl = row.querySelector('.batch-row-thumb');
  if (thumb) {
    if (!thumbEl) {
      thumbEl = document.createElement('img');
      thumbEl.className = 'batch-row-thumb w-8 h-8 rounded-md object-cover shrink-0 border border-white/20 shadow-xs transition-transform duration-200 hover:scale-105';
      thumbEl.setAttribute('referrerpolicy', 'no-referrer');
      const numSpan = row.querySelector('.batch-row-num');
      if (numSpan && numSpan.nextSibling) {
        row.insertBefore(thumbEl, numSpan.nextSibling);
      } else {
        row.prepend(thumbEl);
      }
    }
    thumbEl.alt = 'Thumbnail';
    thumbEl.onerror = function() {
      if (sunoId && !this.dataset.triedPng) {
        this.dataset.triedPng = '1';
        this.src = `https://cdn1.suno.ai/image_${sunoId}.png`;
      } else if (sunoId && !this.dataset.triedLarge) {
        this.dataset.triedLarge = '1';
        this.src = `https://cdn2.suno.ai/image_large_${sunoId}.jpeg`;
      } else {
        this.remove();
      }
    };
    if (thumbEl.src !== thumb) {
      thumbEl.dataset.triedPng = '';
      thumbEl.dataset.triedLarge = '';
      thumbEl.src = thumb;
    }
    thumbEl.style.display = '';
  } else if (thumbEl) {
    thumbEl.remove();
  }
}

function createBatchRowElement(list, val = '', title = '', imageUrl = '') {
  const idx = list.children.length + 1;
  const row = document.createElement('div');
  row.className = 'batch-url-row flex items-center gap-2 bg-[#090c14] border border-slate-800 rounded-lg p-1.5 transition focus-within:border-amber-400/80 hover:border-slate-700';
  if (title) row.dataset.title = title;
  if (imageUrl) row.dataset.imageUrl = imageUrl;

  const { thumb, sunoId } = extractSongThumb(val, imageUrl);
  const thumbEl = thumb ? `<img src="${thumb}" referrerpolicy="no-referrer" alt="Thumb" class="batch-row-thumb w-8 h-8 rounded-md object-cover shrink-0 border border-white/20 shadow-xs transition-transform duration-200 hover:scale-105" onerror="if(!this.dataset.triedPng && '${sunoId || ''}'){ this.dataset.triedPng='1'; this.src='https://cdn1.suno.ai/image_${sunoId}.png'; } else if(!this.dataset.triedLarge && '${sunoId || ''}'){ this.dataset.triedLarge='1'; this.src='https://cdn2.suno.ai/image_large_${sunoId}.jpeg'; } else { this.remove(); }">` : '';
  const titleBadge = title ? `<span class="batch-song-title text-[10px] text-cyan-300 font-bold truncate max-w-[130px] px-1.5 py-0.5 rounded bg-cyan-950/70 border border-cyan-800/60 shrink-0 select-none" title="${title.replace(/"/g, '&quot;')}">${title.replace(/</g, '&lt;')}</span>` : '';
  row.innerHTML = `
    <span class="batch-row-num text-[10px] font-mono font-bold text-amber-400/90 w-5 text-center shrink-0 select-none">${idx}</span>
    ${thumbEl}
    ${titleBadge}
    <input type="text" 
      placeholder="YouTube, Suno 곡 링크 (https://...)" 
      value="${val ? val.replace(/"/g, '&quot;') : ''}"
      class="batch-url-input flex-1 bg-transparent border-0 outline-none text-xs text-white placeholder-slate-500 font-mono"
      oninput="handleBatchUrlInput(this)"
    >
    <button type="button" onclick="pasteToBatchRow(this)" title="클립보드 붙여넣기" class="text-slate-400 hover:text-amber-300 text-xs px-1.5 py-1 transition cursor-pointer shrink-0">
      <i class="fa-regular fa-paste"></i>
    </button>
    <button type="button" onclick="removeBatchUrlRow(this)" title="이 줄 삭제" class="text-slate-500 hover:text-rose-400 text-xs px-1.5 py-1 transition cursor-pointer shrink-0">
      <i class="fa-solid fa-xmark"></i>
    </button>
  `;
  list.appendChild(row);
  return row;
}

window.handleBatchUrlInput = function(inp) {
  const val = inp.value.trim();
  const row = inp.closest('.batch-url-row');
  if (row) {
    updateRowThumbnail(row, val);
  }
  if (/suno\.(com|ai)\/playlist\/[0-9a-f-]+/i.test(val)) {
    loadSunoPlaylistIntoBatch(val, row);
    return;
  }
  updateBatchBadgeCount();
};

window.focusPlaylistInput = function() {
  toggleBatchMode(true);
  const box = document.getElementById('batch-playlist-inline-box');
  const inp = document.getElementById('batch-playlist-input');
  if (box) {
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    box.classList.remove('ring-2', 'ring-cyan-400', 'shadow-cyan-500/40');
    void box.offsetWidth;
    box.classList.add('ring-2', 'ring-cyan-400', 'shadow-cyan-500/40');
    setTimeout(() => {
      box.classList.remove('ring-2', 'ring-cyan-400', 'shadow-cyan-500/40');
    }, 2000);
  }
  if (inp) {
    inp.focus();
    inp.select();
  }
};

window.pasteToPlaylistInput = async function() {
  const inp = document.getElementById('batch-playlist-input');
  if (!inp) return;
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      inp.value = text.trim();
      if (/suno\.(com|ai)\/playlist\/[0-9a-f-]+/i.test(text.trim())) {
        importPlaylistFromInput();
      }
    }
  } catch (e) {
    inp.focus();
  }
};

function playlistResolveError(message) {
  const text = String(message || '플레이리스트에서 곡을 찾을 수 없습니다.');
  if (/삭제된 플레이리스트|플레이리스트를 찾을 수 없습니다|404 Not Found/i.test(text)) {
    return 'Suno가 앱의 요청에 404를 반환해 목록을 가져오지 못했습니다. 로그인한 Suno에서는 목록이 보일 수 있으므로 삭제 여부는 확인할 수 없습니다. 공개 범위를 확인하거나 개별 곡 링크를 추가해 주세요.';
  }
  return text;
}

// Read a user-selected saved page locally. Never submit the HTML or cookies.
window.importSunoPlaylistHtml = async function(input) {
  const file = input?.files?.[0];
  if (!file) return;
  const status = document.getElementById('playlist-inline-status');
  try {
    if (file.size > 20 * 1024 * 1024) throw new Error('HTML 파일은 20MB 이하여야 합니다.');
    const html = await file.text();
    // DOMParser may fetch resources in some browsers. Extract only song paths
    // from text instead, without executing scripts or loading page resources.
    const text = html.replace(/\\\//g, '/').replace(/&amp;/g, '&');
    const matches = text.matchAll(/(?:https?:\/\/(?:www\.)?suno\.(?:com|ai))?\/song\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?![0-9a-f-])/gi);
    const ids = [...new Set(Array.from(matches, m => m[1].toLowerCase()))].reverse();
    if (!ids.length) throw new Error('저장된 페이지에서 곡 링크를 찾지 못했습니다. Suno에서 곡 목록을 아래까지 스크롤한 뒤 HTML만 저장해 다시 선택해 주세요.');
    const list = document.getElementById('batch-urls-list');
    if (!list) throw new Error('곡 목록을 찾을 수 없습니다.');
    const rows = [...list.querySelectorAll('.batch-url-row')];
    const existing = new Set(rows.map(row => row.querySelector('.batch-url-input')?.value.trim().toLowerCase()));
    if (rows.every(row => !row.querySelector('.batch-url-input')?.value.trim())) list.replaceChildren();
    let added = 0;
    for (const id of ids) {
      const url = `https://suno.com/song/${id}`;
      if (!existing.has(url)) { createBatchRowElement(list, url); existing.add(url); added++; }
    }
    renumberBatchRows();
    updateBatchBadgeCount();
    if (status) {
      status.textContent = `저장된 페이지에서 ${ids.length}곡을 찾았고 ${added}곡을 추가했습니다. Suno의 전체 곡 수와 비교해 주세요.`;
      status.className = 'text-[10.5px] font-mono text-emerald-400 font-medium whitespace-pre-line leading-relaxed';
      status.classList.remove('hidden');
    }
  } catch (err) {
    if (status) {
      status.textContent = `페이지 가져오기 실패: ${err.message || err}`;
      status.className = 'text-[10.5px] font-mono text-rose-400 font-medium whitespace-pre-line leading-relaxed';
      status.classList.remove('hidden');
    }
  } finally { input.value = ''; }
};

window.importPlaylistFromInput = async function() {
  const inp = document.getElementById('batch-playlist-input');
  if (!inp) return;
  const rawText = inp.value.trim();
  if (!rawText) {
    inp.focus();
    return;
  }

  const btn = document.getElementById('btn-import-playlist-run');
  const statusEl = document.getElementById('playlist-inline-status');
  const origHtml = btn ? btn.innerHTML : '';

  // 1. Check if user pasted multiple individual song links or raw text with UUIDs
  const isPlaylistUrl = /suno\.(?:com|ai)\/playlist\/[0-9a-f-]+/i.test(rawText);
  const songIdMatches = Array.from(rawText.matchAll(/(?:suno\.(?:com|ai)\/song\/)?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/gi));

  if (!isPlaylistUrl && songIdMatches.length > 0) {
    const list = document.getElementById('batch-urls-list');
    const uniqueIds = Array.from(new Set(songIdMatches.map(m => m[1].toLowerCase())));
    const currentRows = list.querySelectorAll('.batch-url-row');
    const allEmpty = Array.from(currentRows).every(r => !(r.querySelector('.batch-url-input')?.value.trim()));
    if (allEmpty) list.innerHTML = '';

    uniqueIds.forEach(id => {
      createBatchRowElement(list, `https://suno.com/song/${id}`);
    });
    renumberBatchRows();
    updateBatchBadgeCount();

    if (statusEl) {
      statusEl.textContent = `✨ ${uniqueIds.length}개 곡 링크 일괄 추가 완료!`;
      statusEl.className = 'text-[10px] font-mono text-emerald-400 font-bold';
      statusEl.classList.remove('hidden');
    }
    inp.value = '';
    if (window.showToast) {
      showToast(`🎵 ${uniqueIds.length}개의 곡이 일괄 등록되었습니다!`, 'success');
    }
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>목록 파싱 중...</span>`;
  }
  if (statusEl) {
    statusEl.textContent = '⏳ 플레이리스트 분석 중...';
    statusEl.className = 'text-[10px] font-mono text-cyan-300 font-bold';
    statusEl.classList.remove('hidden');
  }

  try {
    const list = document.getElementById('batch-urls-list');
    const resp = await fetch('/api/suno/playlist/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: rawText })
    });
    const data = await resp.json();
    if (!data.ok || !data.songs || data.songs.length === 0) {
      throw new Error(playlistResolveError(data.error));
    }

    const currentRows = list.querySelectorAll('.batch-url-row');
    const allEmpty = Array.from(currentRows).every(r => !(r.querySelector('.batch-url-input')?.value.trim()));
    if (allEmpty) {
      list.innerHTML = '';
    }

    data.songs.forEach(song => {
      createBatchRowElement(list, song.url, song.title, song.image_url);
    });

    renumberBatchRows();
    updateBatchBadgeCount();

    if (statusEl) {
      statusEl.textContent = `✨ [${data.name || '플레이리스트'}] ${data.total}곡 추가 완료!`;
      statusEl.className = 'text-[10px] font-mono text-emerald-400 font-bold';
      statusEl.classList.remove('hidden');
    }
    inp.value = '';
    if (window.showToast) {
      showToast(`🎵 [${data.name || '플레이리스트'}] ${data.total}곡이 추가되었습니다.`, 'success');
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = `❌ ${err.message || err}`;
      statusEl.className = 'text-[10.5px] font-mono text-rose-400 font-medium whitespace-pre-line leading-relaxed';
      statusEl.classList.remove('hidden');
    }
    // A deleted, missing, or temporarily unavailable playlist cannot be
    // repaired by importing login credentials. Keep that panel closed.
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
};

window.toggleSunoCookieInline = function() {
  const box = document.getElementById('suno-cookie-box');
  if (box) box.classList.toggle('hidden');
};

window.copySunoSyncCode = async function() {
  const code = document.getElementById('suno-sync-code')?.textContent || '';
  if (!code) return;
  try {
    await navigator.clipboard.writeText(code);
    alert('📋 1초 연동 코드가 복사되었습니다!\n\n1. Suno 사이트(suno.com) 탭으로 이동\n2. 키보드 [F12] 키 누르고 상단 [Console(콘솔)] 클릭\n3. 마우스 클릭 후 Ctrl+V 붙여넣고 [Enter(엔터)]\n\n연동 완료 창이 뜬 뒤 스튜디오에서 [전체 곡 목록 추가]를 다시 누르시면 됩니다!');
  } catch (e) {
    prompt('아래 코드를 복사하세요:', code);
  }
};

window.handleImportedSongs = function(songIdsOrUrls) {
  if (!Array.isArray(songIdsOrUrls) || songIdsOrUrls.length === 0) return;
  const list = document.getElementById('batch-urls-list');
  if (!list) return;
  const currentRows = list.querySelectorAll('.batch-url-row');
  const allEmpty = Array.from(currentRows).every(r => !(r.querySelector('.batch-url-input')?.value.trim()));
  if (allEmpty) list.innerHTML = '';

  songIdsOrUrls.forEach(item => {
    let url = item.startsWith('http') ? item : `https://suno.com/song/${item}`;
    createBatchRowElement(list, url);
  });
  renumberBatchRows();
  updateBatchBadgeCount();
  if (window.showToast) {
    showToast(`🎵 ${songIdsOrUrls.length}개의 곡이 스튜디오에 자동 등록되었습니다!`, 'success');
  }
};

window.addEventListener('message', (ev) => {
  if (ev.data === 'suno_cookie_synced') {
    if (window.showToast) {
      showToast('🎉 Suno 로그인 인증이 연동되었습니다! 플레이리스트를 다시 불러옵니다.', 'success');
    }
    const inp = document.getElementById('batch-playlist-input');
    if (inp && inp.value.trim()) {
      importPlaylistFromInput();
    }
  }
});

window.saveSunoCookieInline = async function() {
  const inp = document.getElementById('suno-cookie-input');
  if (!inp) return;
  const cookie = inp.value.trim();
  try {
    const res = await fetch('/api/suno/cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie })
    });
    const data = await res.json();
    if (data.ok) {
      alert('✅ Suno 쿠키가 저장되었습니다. 이제 비공개 플레이리스트도 불러올 수 있습니다!');
      const box = document.getElementById('suno-cookie-box');
      if (box) box.classList.add('hidden');
    }
  } catch (err) {
    alert('저장 실패: ' + err);
  }
};

window.importSunoPlaylistDialog = function(defaultUrl = '') {
  focusPlaylistInput();
};

window.loadSunoPlaylistIntoBatch = async function(playlistUrl, replaceRow = null) {
  toggleBatchMode(true);
  const list = document.getElementById('batch-urls-list');
  if (!list) return;

  const statusEl = document.getElementById('playlist-inline-status');
  if (statusEl) {
    statusEl.textContent = '⏳ 플레이리스트 분석 중...';
    statusEl.className = 'text-[10px] font-mono text-cyan-300 font-bold';
    statusEl.classList.remove('hidden');
  }

  const badge = document.getElementById('batch-count-badge');
  if (badge) badge.textContent = '🎵 플레이리스트 분석 중...';

  try {
    const resp = await fetch('/api/suno/playlist/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: playlistUrl })
    });
    const data = await resp.json();
    if (!data.ok || !data.songs || data.songs.length === 0) {
      const errMsg = playlistResolveError(data.error);
      if (statusEl) {
        statusEl.textContent = `❌ ${errMsg}`;
        statusEl.className = 'text-[10.5px] font-mono text-rose-400 font-medium whitespace-pre-line leading-relaxed';
        statusEl.classList.remove('hidden');
      }
      updateBatchBadgeCount();
      return;
    }

    if (replaceRow) {
      replaceRow.remove();
    } else {
      const currentRows = list.querySelectorAll('.batch-url-row');
      const allEmpty = Array.from(currentRows).every(r => !(r.querySelector('.batch-url-input')?.value.trim()));
      if (allEmpty) {
        list.innerHTML = '';
      }
    }

    data.songs.forEach(song => {
      createBatchRowElement(list, song.url, song.title, song.image_url);
    });

    renumberBatchRows();
    updateBatchBadgeCount();

    if (statusEl) {
      statusEl.textContent = `✨ [${data.name || '플레이리스트'}] ${data.total}곡 추가 완료!`;
      statusEl.className = 'text-[10px] font-mono text-emerald-400 font-bold';
      statusEl.classList.remove('hidden');
    }
    if (window.showToast) {
      showToast(`🎵 [${data.name || '플레이리스트'}] ${data.total}곡을 배치 작업 목록에 성공적으로 불러왔습니다!`, 'success');
    }
  } catch (err) {
    console.error('Playlist resolve error:', err);
    if (statusEl) {
      statusEl.textContent = `❌ ${err.message || err}`;
      statusEl.className = 'text-[10.5px] font-mono text-rose-400 font-medium whitespace-pre-line leading-relaxed';
      statusEl.classList.remove('hidden');
    }
    updateBatchBadgeCount();
  }
};

window.toggleBatchMode = function(forceOpen = null) {
  const container = document.getElementById('batch-container');
  const badge = document.getElementById('batch-toggle-badge');
  if (!container) return;
  
  const shouldOpen = forceOpen !== null ? forceOpen : container.classList.contains('hidden');
  if (shouldOpen) {
    container.classList.remove('hidden');
    if (badge) {
      badge.textContent = '닫기';
      badge.className = 'text-[9px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-mono';
    }
    const list = document.getElementById('batch-urls-list');
    if (list && list.children.length === 0) {
      createBatchRowElement(list, '');
      createBatchRowElement(list, '');
      updateBatchBadgeCount();
    }
  } else {
    container.classList.add('hidden');
    if (badge) {
      badge.textContent = '열기';
      badge.className = 'text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono';
    }
  }
};

window.addBatchUrlRow = function(val = '') {
  const container = document.getElementById('batch-container');
  if (container && container.classList.contains('hidden')) {
    toggleBatchMode(true);
    return;
  }

  const list = document.getElementById('batch-urls-list');
  if (!list) return;

  const row = createBatchRowElement(list, val);
  updateBatchBadgeCount();

  const input = row.querySelector('input');
  if (input && !val) input.focus();
};

window.removeBatchUrlRow = function(btn) {
  const row = btn.closest('.batch-url-row');
  if (row) {
    row.remove();
    renumberBatchRows();
  }
};

window.pasteToBatchRow = async function(btn) {
  const row = btn.closest('.batch-url-row');
  if (!row) return;
  const input = row.querySelector('input');
  if (!input) return;
  try {
    const text = await navigator.clipboard.readText();
    if (!text) return;
    const lines = text.split(/[\r\n]+/).map(s => s.trim()).filter(Boolean);
    if (lines.length > 1) {
      input.value = lines[0];
      handleBatchUrlInput(input);
      const list = document.getElementById('batch-urls-list');
      for (let i = 1; i < lines.length; i++) {
        createBatchRowElement(list, lines[i]);
      }
      renumberBatchRows();
      updateBatchBadgeCount();
      if (window.showToast) {
        showToast(`📋 ${lines.length}개의 URL이 일괄 추가되었습니다.`, 'success');
      }
    } else {
      input.value = text.trim();
      handleBatchUrlInput(input);
    }
  } catch (err) {
    console.warn('Clipboard read failed:', err);
  }
};

function renumberBatchRows() {
  const list = document.getElementById('batch-urls-list');
  if (!list) return;
  const rows = list.querySelectorAll('.batch-url-row');
  rows.forEach((r, i) => {
    const numEl = r.querySelector('.batch-row-num');
    if (numEl) numEl.textContent = (i + 1);
  });
  updateBatchBadgeCount();
}

window.updateBatchBadgeCount = function() {
  const list = document.getElementById('batch-urls-list');
  const badge = document.getElementById('batch-count-badge');
  if (!list || !badge) return;
  const inputs = list.querySelectorAll('.batch-url-input');
  let filled = 0;
  inputs.forEach(inp => {
    if (inp.value && inp.value.trim()) filled++;
  });
  badge.textContent = `${filled} / ${inputs.length}개 URL`;
};

window.clearBatchUrls = function() {
  const list = document.getElementById('batch-urls-list');
  if (list) list.innerHTML = '';
  addBatchUrlRow();
  addBatchUrlRow();
  updateBatchBadgeCount();
};

window.updatePureYoutubeBadge = function() {
  const mp3 = document.getElementById('batch-opt-mp3')?.checked;
  const mp4 = document.getElementById('batch-opt-mp4')?.checked;
  const yt = document.getElementById('batch-opt-youtube')?.checked;
  const badge = document.getElementById('batch-pure-yt-badge');
  if (!badge) return;
  if (!mp3 && !mp4 && yt) {
    badge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 text-[#3182f6] border border-[#3182f6]/30 font-semibold font-sans';
    badge.textContent = '⚡ 순수 유튜브 전송 (PC 저장 0MB)';
    badge.style.display = 'inline-block';
  } else if (yt) {
    badge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-sans';
    badge.textContent = 'PC 저장 + 유튜브 동시 업로드';
    badge.style.display = 'inline-block';
  } else {
    badge.style.display = 'none';
  }
};

window.startBatchJob = async function() {
  const list = document.getElementById('batch-urls-list');
  if (!list) return;

  const inputs = list.querySelectorAll('.batch-url-input');
  const urls = [];
  inputs.forEach(inp => {
    const val = inp.value.trim();
    if (val) urls.push(val);
  });

  if (urls.length === 0) {
    alert('최소 1개 이상의 YouTube 또는 Suno URL을 입력해주세요.');
    return;
  }

  const exportMp3 = document.getElementById('batch-opt-mp3')?.checked ?? false;
  const exportMp4 = document.getElementById('batch-opt-mp4')?.checked ?? false;
  const applyMastering = document.getElementById('batch-opt-mastering')?.checked ?? false;
  const uploadYoutube = document.getElementById('batch-opt-youtube')?.checked ?? true;
  const useCooldown = document.getElementById('batch-opt-cooldown')?.checked ?? true;

  if (!exportMp3 && !exportMp4 && !uploadYoutube) {
    alert('MP3 저장, MP4 저장, 또는 유튜브 자동 업로드 중 최소 하나를 선택해주세요.');
    return;
  }

  const btnStart = document.getElementById('btn-start-batch');
  const btnCancel = document.getElementById('btn-cancel-batch');
  const resultsPanel = document.getElementById('batch-results-panel');
  const zipBtn = document.getElementById('btn-batch-download-zip');

  if (btnStart) {
    btnStart.disabled = true;
    btnStart.classList.add('opacity-50', 'pointer-events-none');
  }
  if (btnCancel) btnCancel.classList.remove('hidden');
  if (resultsPanel) resultsPanel.classList.remove('hidden');
  if (zipBtn) zipBtn.classList.add('hidden');
  batchAutoDownloadedUrls.clear();

  try {
    const resp = await fetch('/api/batch/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        urls,
        export_mp3: exportMp3,
        export_mp4: exportMp4,
        apply_mastering: applyMastering,
        upload_youtube: uploadYoutube,
        youtube_privacy: 'unlisted',
        use_cooldown: useCooldown
      })
    });
    const data = await resp.json();
    if (!data.ok) {
      alert(data.error || '배치 작업 시작 실패');
      if (btnStart) {
        btnStart.disabled = false;
        btnStart.classList.remove('opacity-50', 'pointer-events-none');
      }
      if (btnCancel) btnCancel.classList.add('hidden');
      return;
    }

    currentBatchId = data.batch_id;
    pollBatchJob();
  } catch (err) {
    console.error('Batch start failed:', err);
    alert('배치 작업 요청 중 통신 오류가 발생했습니다: ' + err);
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.classList.remove('opacity-50', 'pointer-events-none');
    }
  }
};

async function pollBatchJob() {
  if (!currentBatchId) return;
  try {
    const resp = await fetch(`/api/batch/status/${currentBatchId}`);
    if (!resp.ok) {
      console.warn(`Batch status HTTP ${resp.status}, retrying in 2s...`);
      if (batchPollTimer) clearTimeout(batchPollTimer);
      batchPollTimer = setTimeout(pollBatchJob, 2000);
      return;
    }
    const batch = await resp.json();
    renderBatchStatus(batch);

    if (batch.status === 'processing') {
      if (batchPollTimer) clearTimeout(batchPollTimer);
      batchPollTimer = setTimeout(pollBatchJob, 1000);
    } else {
      const btnStart = document.getElementById('btn-start-batch');
      const btnCancel = document.getElementById('btn-cancel-batch');
      const zipBtn = document.getElementById('btn-batch-download-zip');
      const spinner = document.getElementById('batch-status-spinner');

      if (btnStart) {
        btnStart.disabled = false;
        btnStart.classList.remove('opacity-50', 'pointer-events-none');
      }
      if (btnCancel) btnCancel.classList.add('hidden');
      if (spinner) spinner.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i>';

      if (batch.completed > 0 && zipBtn && (batch.export_mp3 || batch.export_mp4)) {
        zipBtn.classList.remove('hidden');
      }
    }
  } catch (err) {
    console.warn('Poll batch error:', err);
    if (batchPollTimer) clearTimeout(batchPollTimer);
    batchPollTimer = setTimeout(pollBatchJob, 2000);
  }
}

function renderBatchStatus(batch) {
  const summaryEl = document.getElementById('batch-summary-text');
  if (summaryEl) {
    if (batch.status === 'completed') {
      summaryEl.textContent = `🎉 전체 완료! (${batch.completed}/${batch.total}개 성공)`;
      summaryEl.className = 'text-xs font-bold text-emerald-400';
    } else if (batch.status === 'cancelled') {
      summaryEl.textContent = `🛑 사용자에 의해 중단됨 (${batch.completed}/${batch.total}개 완료)`;
      summaryEl.className = 'text-xs font-bold text-rose-400';
    } else if (batch.cooldown_remaining > 0) {
      summaryEl.innerHTML = `<span class="flex items-center gap-1.5 text-amber-300 font-bold"><i class="fa-solid fa-shield-halved animate-pulse text-amber-400"></i><span>유튜브 안티-스팸 쿨다운 중... (다음 곡까지 ${batch.cooldown_remaining}초)</span></span>`;
      summaryEl.className = 'text-xs font-bold text-amber-300';
    } else {
      summaryEl.textContent = `⚡ 고속 처리 중... (${batch.completed}/${batch.total} 완료)`;
      summaryEl.className = 'text-xs font-bold text-amber-300';
    }
  }

  // Auto-download mechanism: Automatically triggers browser download as each item completes
  const autoDownload = document.getElementById('batch-opt-autodownload')?.checked ?? true;
  if (autoDownload && batch.items) {
    batch.items.forEach(it => {
      if (it.status === 'completed') {
        // Auto-download MP4 if available
        if (it.mp4_url && !batchAutoDownloadedUrls.has(it.mp4_url)) {
          batchAutoDownloadedUrls.add(it.mp4_url);
          triggerAutoDownload(it.mp4_url, it.mp4_name);
        }
        // Auto-download MP3 if available
        if (it.mp3_url && !batchAutoDownloadedUrls.has(it.mp3_url)) {
          batchAutoDownloadedUrls.add(it.mp3_url);
          const delay = it.mp4_url ? 500 : 50;
          setTimeout(() => triggerAutoDownload(it.mp3_url, it.mp3_name), delay);
        }
      }
    });
  }

  const container = document.getElementById('batch-items-container');
  if (!container) return;

  container.innerHTML = batch.items.map(it => {
    const isDone = it.status === 'completed';
    const isErr = it.status === 'error';
    const isWorking = it.status === 'processing';
    const statusColor = isDone ? 'text-emerald-400' : (isErr ? 'text-rose-400' : (isWorking ? 'text-amber-400' : 'text-slate-500'));
    const title = it.title || it.url;
    const wasAutoDownloaded = isDone && ((it.mp4_url && batchAutoDownloadedUrls.has(it.mp4_url)) || (it.mp3_url && batchAutoDownloadedUrls.has(it.mp3_url)));

    let thumbUrl = it.image_url || null;
    let sunoId = null;
    if (it.url) {
      const sm = it.url.match(/(?:suno\.(?:com|ai)\/song\/|\b)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b/i);
      if (sm) {
        sunoId = sm[1];
        if (!thumbUrl) thumbUrl = `https://cdn2.suno.ai/image_${sunoId}.jpeg`;
      } else {
        const ym = it.url.match(/(?:youtu\.be\/|v=|\/embed\/|\/v\/)([a-zA-Z0-9_-]{11})/);
        if (ym && !thumbUrl) {
          thumbUrl = `https://img.youtube.com/vi/${ym[1]}/mqdefault.jpg`;
        }
      }
    }

    return `
      <div class="daw-inset p-2.5 rounded-xl flex items-center gap-3 bg-[#090d14] border ${isDone ? 'border-emerald-500/30' : (isErr ? 'border-rose-500/30' : 'border-slate-800')} hover:border-slate-700/80 transition-all shadow-sm">
        <!-- Suno Song Thumbnail (Album Art) -->
        <div class="relative w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden bg-slate-900 border border-white/10 shrink-0 flex items-center justify-center shadow-md group">
          ${thumbUrl ? `
            <img src="${thumbUrl}" referrerpolicy="no-referrer" alt="Thumbnail" class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" onerror="if(!this.dataset.f1 && '${sunoId || ''}'){ this.dataset.f1='1'; this.src='https://cdn1.suno.ai/image_${sunoId}.png'; } else if(!this.dataset.f2 && '${sunoId || ''}'){ this.dataset.f2='1'; this.src='https://cdn2.suno.ai/image_large_${sunoId}.jpeg'; } else { this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.classList.remove('hidden'); }">
            <div class="hidden w-full h-full flex flex-col items-center justify-center bg-slate-800/80 text-slate-400">
              <i class="fa-solid fa-music text-base text-slate-500"></i>
              <span class="text-[8px] font-mono text-slate-500 mt-0.5">Suno</span>
            </div>
          ` : `
            <div class="w-full h-full flex flex-col items-center justify-center bg-slate-800/80 text-slate-400">
              <i class="fa-solid fa-music text-base text-slate-500"></i>
              <span class="text-[8.5px] font-mono text-slate-500 mt-0.5">Suno</span>
            </div>
          `}
          <span class="absolute bottom-1 right-1 px-1.5 py-0.2 rounded bg-black/80 backdrop-blur-xs text-[9px] font-mono font-bold text-amber-300 select-none shadow border border-white/10">
            [${it.index + 1}]
          </span>
        </div>

        <!-- Info, Progress & Action Hub -->
        <div class="flex-1 min-w-0 flex flex-col gap-1.5 justify-center">
          <div class="flex items-center justify-between text-xs gap-2">
            <div class="flex items-center gap-1.5 truncate">
              <span class="font-bold text-white truncate text-[11.5px]" title="${title.replace(/"/g, '&quot;')}">${title}</span>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              ${wasAutoDownloaded ? `<span class="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">✨ 자동 다운로드됨</span>` : ''}
              <span class="text-[10px] font-mono font-bold ${statusColor}">${it.message || it.status}</span>
            </div>
          </div>
          
          <div class="w-full bg-slate-900 rounded-full h-1 overflow-hidden">
            <div class="h-1 rounded-full transition-all duration-300 ${isDone ? 'bg-emerald-400 w-full' : (isErr ? 'bg-rose-500 w-full' : 'bg-amber-400')}" style="width: ${it.progress}%"></div>
          </div>

          ${isDone ? `
            <div class="flex items-center justify-end gap-2 pt-1 border-t border-white/5 flex-wrap">
              ${it.youtube_url ? `
                <a href="${it.youtube_url}" target="_blank" rel="noopener noreferrer" class="btn-yt-view px-3 py-1.5 rounded-xl text-[11px] font-bold font-sans transition flex items-center gap-1.5 shadow-sm active:scale-[0.98]" style="background-color: #f04452 !important; color: #ffffff !important; border: none !important; text-decoration: none !important;">
                  <i class="fa-brands fa-youtube text-xs" style="color: #ffffff !important;"></i>
                  <span style="color: #ffffff !important; font-weight: 700 !important;">YouTube 보기</span>
                </a>
              ` : (it.youtube_error ? `
                <span class="text-[10px] text-rose-300 font-sans font-medium px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20" title="${(it.youtube_error || '').replace(/"/g, '&quot;')}">⚠️ ${it.youtube_error}</span>
              ` : '')}
              ${it.mp3_url ? `
                <a href="${it.mp3_url}" download="${(it.mp3_name || 'audio.mp3').replace(/"/g, '&quot;')}" class="btn-toss-secondary px-3 py-1.5 rounded-xl text-[11px] font-semibold font-sans transition flex items-center gap-1.5 active:scale-[0.98]">
                  <i class="fa-solid fa-music"></i> MP3 다운로드
                </a>
              ` : ''}
              ${it.mp4_url ? `
                <a href="${it.mp4_url}" download="${(it.mp4_name || 'video.mp4').replace(/"/g, '&quot;')}" class="btn-toss-secondary px-3 py-1.5 rounded-xl text-[11px] font-semibold font-sans transition flex items-center gap-1.5 active:scale-[0.98]" title="원본 고화질 MP4 파일 다운로드">
                  <i class="fa-solid fa-file-video text-rose-500"></i> 원본 MP4 다운로드
                </a>
              ` : ''}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

window.downloadBatchZip = function() {
  if (!currentBatchId) return;
  window.location.href = `/api/batch/zip/${currentBatchId}`;
};

window.cancelBatchJob = async function() {
  if (!currentBatchId) return;
  try {
    await fetch(`/api/batch/cancel/${currentBatchId}`, { method: 'POST' });
  } catch (err) {
    console.error('Cancel batch error:', err);
  }
};

// =====================================================================
// YouTube Channel Auto-Upload & OAuth Settings Modal Logic
// =====================================================================

window.openYouTubeSettingsModal = function() {
  const modal = document.getElementById('youtube-settings-modal');
  if (modal) {
    modal.classList.remove('hidden');
    refreshYouTubeStatus();
  }
};

window.closeYouTubeSettingsModal = function() {
  const modal = document.getElementById('youtube-settings-modal');
  if (modal) modal.classList.add('hidden');
};

window.toggleYtCredsSection = function() {
  const section = document.getElementById('yt-creds-section');
  if (!section) return;
  section.classList.toggle('hidden');
};

window.refreshYouTubeStatus = async function() {
  try {
    const res = await fetch('/api/youtube/status');
    const data = await res.json();
    if (!data.ok) return;

    // Badges & text
    const badge = document.getElementById('yt-conn-badge');
    const channelName = document.getElementById('yt-channel-name-text');
    const channelId = document.getElementById('yt-channel-id-text');
    const channelDesc = document.getElementById('yt-channel-desc-text');
    const avatar = document.getElementById('yt-channel-avatar');
    const btnConnect = document.getElementById('btn-yt-connect');
    const btnDisconnect = document.getElementById('btn-yt-disconnect');
    const batchBadge = document.getElementById('batch-yt-status-badge');

    if (data.authenticated) {
      if (badge) {
        badge.textContent = '🟢 연동 완료';
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
      }
      if (channelName) channelName.textContent = data.channel_title || '내 유튜브 채널';
      if (channelId) channelId.textContent = data.channel_id ? `(ID: ${data.channel_id.slice(0, 12)}...)` : '';
      if (channelDesc) channelDesc.textContent = 'MP4 저장 시 비공개/공개 설정에 따라 유튜브에 자동 업로드됩니다.';
      if (btnConnect) btnConnect.classList.add('hidden');
      if (btnDisconnect) btnDisconnect.classList.remove('hidden');

      if (avatar && data.channel_thumbnail) {
        avatar.innerHTML = `<img src="${data.channel_thumbnail}" alt="Avatar" class="w-full h-full object-cover">`;
      }

      if (batchBadge) {
        batchBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse"></span> <span class="text-emerald-300 font-bold">${data.channel_title || '연동됨'}</span>`;
        batchBadge.className = 'text-[9.5px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 font-sans';
      }

      // Automatically check YouTube upload checkboxes when channel is connected
      const batchYtCheck = document.getElementById('batch-opt-youtube');
      if (batchYtCheck) batchYtCheck.checked = true;
      const exportYtCheck = document.getElementById('export-opt-youtube');
      if (exportYtCheck) exportYtCheck.checked = true;
      if (typeof updatePureYoutubeBadge === 'function') updatePureYoutubeBadge();
    } else {
      if (badge) {
        badge.textContent = '⚪ 미연동';
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700';
      }
      if (channelName) channelName.textContent = '유튜브 계정이 연결되지 않았습니다';
      if (channelId) channelId.textContent = '';
      if (channelDesc) channelDesc.textContent = 'Google 계정 로그인으로 내 채널을 연결하세요.';
      if (btnConnect) btnConnect.classList.remove('hidden');
      if (btnDisconnect) btnDisconnect.classList.add('hidden');
      if (avatar) avatar.innerHTML = `<i class="fa-brands fa-youtube text-2xl text-slate-500"></i>`;

      if (batchBadge) {
        batchBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-slate-500 inline-block"></span> <span>미연동</span>`;
        batchBadge.className = 'text-[9.5px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1 font-sans';
      }
    }

    // Inputs sync
    const selPrivacy = document.getElementById('yt-cfg-privacy');
    if (selPrivacy && data.privacy_status) selPrivacy.value = data.privacy_status;

    const chkAuto = document.getElementById('yt-cfg-auto-upload');
    if (chkAuto) chkAuto.checked = !!data.auto_upload;

    const inpClient = document.getElementById('yt-cfg-client-id');
    if (inpClient && data.client_id) inpClient.value = data.client_id;
    if (typeof updatePureYoutubeBadge === 'function') updatePureYoutubeBadge();
  } catch (err) {
    console.warn('refreshYouTubeStatus warning:', err);
  }
};

window.startYouTubeOAuth = async function() {
  try {
    const res = await fetch('/api/youtube/auth-url');
    const data = await res.json();
    if (!data.ok || !data.auth_url) {
      alert(data.error || 'Google OAuth 인증 URL 생성 실패. 먼저 client_secret.json 파일 또는 Client ID를 등록해주세요.');
      const credsSec = document.getElementById('yt-creds-section');
      if (credsSec) credsSec.classList.remove('hidden');
      return;
    }
    // Redirect to Google OAuth consent screen
    window.location.href = data.auth_url;
  } catch (err) {
    console.error('startYouTubeOAuth error:', err);
    alert('유튜브 로그인 요청 중 오류가 발생했습니다: ' + err);
  }
};

window.disconnectYouTubeAccount = async function() {
  if (!confirm('정말 유튜브 계정 연동을 해제하시겠습니까?')) return;
  try {
    await fetch('/api/youtube/disconnect', { method: 'POST' });
    alert('유튜브 연동이 해제되었습니다.');
    refreshYouTubeStatus();
  } catch (err) {
    console.error('disconnect error:', err);
  }
};

window.handleYouTubeSecretsUpload = async function(file) {
  if (!file) return;
  const label = document.getElementById('yt-json-filename');
  if (label) label.textContent = `업로드 중: ${file.name}...`;

  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/api/youtube/upload-credentials', {
      method: 'POST',
      body: fd
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.detail || data.error || '업로드 실패');
    }
    if (label) label.textContent = `✅ 등록 완료: ${file.name}`;
    alert('🎉 Google OAuth 클라이언트 인증 정보가 성공적으로 등록되었습니다!\n\n이제 [Google 계정 로그인] 버튼을 눌러 채널을 연결하세요.');
    refreshYouTubeStatus();
  } catch (err) {
    console.error('Secrets upload error:', err);
    if (label) label.textContent = `❌ 오류: ${err.message}`;
    alert('인증 파일 등록 실패:\n' + err.message);
  }
};

window.saveYouTubeSettings = async function() {
  const privacy = document.getElementById('yt-cfg-privacy')?.value || 'private';
  const autoUpload = document.getElementById('yt-cfg-auto-upload')?.checked || false;
  const tagsStr = document.getElementById('yt-cfg-tags')?.value || '';
  const tags = tagsStr.split(',').map(s => s.trim()).filter(Boolean);

  try {
    await fetch('/api/youtube/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        privacy_status: privacy,
        auto_upload: autoUpload,
        default_tags: tags.length ? tags : undefined
      })
    });
  } catch (err) {
    console.warn('saveYouTubeSettings error:', err);
  }
};

window.saveYouTubeCredentialsManual = async function() {
  const clientId = document.getElementById('yt-cfg-client-id')?.value?.trim();
  const clientSecret = document.getElementById('yt-cfg-client-secret')?.value?.trim();
  if (!clientId || !clientSecret) {
    alert('Client ID와 Client Secret을 모두 입력해주세요.');
    return;
  }
  try {
    const res = await fetch('/api/youtube/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret
      })
    });
    const data = await res.json();
    if (data.ok) {
      alert('인증 정보가 저장되었습니다. 이제 [Google 계정 로그인]을 눌러 연동을 진행하세요.');
      refreshYouTubeStatus();
    }
  } catch (err) {
    alert('저장 실패: ' + err);
  }
};

// Check OAuth callback parameters on page load
document.addEventListener('DOMContentLoaded', () => {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get('youtube_auth') === 'success') {
      alert('🎉 축하합니다! 유튜브 채널 연동이 성공적으로 완료되었습니다.\n\n이제 MP4 저장 시 자동으로 유튜브 채널에 비공개/공개 영상으로 업로드됩니다.');
      history.replaceState(null, '', window.location.pathname);
    } else if (params.get('youtube_auth') === 'error') {
      const msg = params.get('msg') || '인증 과정에서 오류가 발생했습니다.';
      alert('❌ 유튜브 연동 실패:\n' + decodeURIComponent(msg));
      history.replaceState(null, '', window.location.pathname);
    }
    // Refresh status badge on init
    refreshYouTubeStatus();
  } catch (e) {
    console.warn('YouTube init error:', e);
  }
});
