import os
import json
import time
import shutil
import threading
import tempfile
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from scipy import signal

from core.humify_v3 import grain_smear, smooth_env

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".hum_cache"
CACHE_DIR.mkdir(exist_ok=True)
PRESETS_FILE = BASE_DIR / "data" / "hum_presets.json"
PRESETS_FILE.parent.mkdir(exist_ok=True)

SR = 22050
HOP = 512

DEFAULTS = {
    "hum": 0.0,
    "bed": 0.0,
    "bed_lp": 800,
    "leak": 1.0,
    "leak_lp": 20000,
    "pitch": 0.0,
    "speed": 1.0,
    "vocal_cut": 0.0,
    "wobble": 0.0,
    "reverb": 0.0,
    "saturation": 0.0,
    "formant": 0.0,
    "preview_start": 30.0,
    "preview_len": 15.0
}

SPEED_PRESETS = [100, 95, 90, 85, 80, 75, 70, 50]

def apply_audio_modulation(
    seg: np.ndarray,
    pitch: float = 0.0,
    speed: float = 1.0,
    wobble: float = 0.0,
    reverb: float = 0.0,
    saturation: float = 0.0,
    formant: float = 0.0
) -> np.ndarray:
    """
    Apply studio-grade audio modulation:
    - Soft analog saturation & harmonic excitation
    - FFmpeg high-speed rubberband pitch & tempo
    - Micro-pitch flutter / tape wobble (anti-fingerprint)
    - Formant / timbre shift
    - Spacial acoustic reverb & diffusion
    """
    # 1. Analog tape saturation (warm harmonic excitation)
    if saturation > 0.005:
        drive = 1.0 + saturation * 2.0
        seg = np.tanh(seg * drive) / np.tanh(drive)

    needs_filter = (
        abs(speed - 1.0) >= 1e-6 or
        abs(pitch) >= 1e-6 or
        wobble > 0.005 or
        reverb > 0.005 or
        abs(formant) >= 0.1
    )
    if not needs_filter:
        peak = max(np.max(np.abs(seg)), 1e-9)
        if peak > 0.95:
            seg = seg * (0.95 / peak)
        return seg

    ffmpeg = get_ffmpeg_bin()
    if ffmpeg:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in, \
                 tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
                in_p, out_p = f_in.name, f_out.name
            try:
                sf.write(in_p, seg, SR)
                filters = []

                # Pitch & Speed via Rubberband / atempo
                if abs(pitch) >= 1e-6:
                    pitch_scale = 2.0 ** (float(pitch) / 12.0)
                    filters.append(f"rubberband=pitch={pitch_scale:.8f}:tempo={float(speed):.6f}")
                elif abs(speed - 1.0) >= 1e-6:
                    filters.append(f"atempo={float(speed):.6f}")

                # Formant / Timbre Shift via Parametric Vocal Tract Resonator
                if abs(formant) >= 0.1:
                    if formant > 0:
                        filters.append(f"equalizer=f=3200:t=q:w=1.2:g={formant * 1.5:.2f},equalizer=f=400:t=q:w=1.0:g={-formant * 1.2:.2f}")
                    else:
                        filters.append(f"equalizer=f=350:t=q:w=1.0:g={-formant * 1.5:.2f},equalizer=f=3500:t=q:w=1.2:g={formant * 1.2:.2f}")

                # Tape Wobble (Dynamic Micro-Pitch Flutter)
                if wobble > 0.005:
                    depth = min(0.5, wobble * 0.35)
                    filters.append(f"vibrato=f=4.8:d={depth:.3f}")

                # Spacial Reverb & Acoustic Diffusion (Diffuses sharp spectral constellation points)
                # CRITICAL: Highpass at 350Hz prevents low-frequency comb resonance (speaker blowout)
                if reverb > 0.005:
                    in_g = max(0.60, 1.0 - reverb * 0.25)
                    out_g = min(0.85, 0.50 + reverb * 0.30)
                    d1, d2 = int(120 + reverb * 30), int(240 + reverb * 50)
                    dec1 = min(0.25, 0.10 + reverb * 0.12)
                    dec2 = min(0.18, 0.06 + reverb * 0.08)
                    filters.append(f"highpass=f=350,aecho={in_g:.2f}:{out_g:.2f}:{d1}|{d2}:{dec1:.2f}|{dec2:.2f},lowpass=f=7500")

                af_str = ",".join(filters) if filters else "anull"
                cmd = [ffmpeg, "-y", "-i", in_p, "-filter:a", af_str, "-c:a", "pcm_s16le", out_p]
                subprocess.run(cmd, capture_output=True, check=True)
                res, _ = sf.read(out_p)
                # CEILING LIMITER: DO NOT BOOST QUIET OR MUTED STEMS!
                peak = max(np.max(np.abs(res)), 1e-9)
                if peak > 0.95:
                    res = res * (0.95 / peak)
                return res.astype(np.float64)
            finally:
                for p in [in_p, out_p]:
                    if os.path.exists(p):
                        try: os.remove(p)
                        except Exception: pass
        except Exception:
            pass

    # Fallback to librosa
    out = seg
    if abs(speed - 1.0) >= 1e-6:
        rate = float(speed)
        chs = [librosa.effects.time_stretch(out[:, c].astype(np.float32), rate=rate)
               for c in range(out.shape[1])]
        m = min(len(c) for c in chs)
        out = np.stack([c[:m] for c in chs], 1)
    if abs(pitch) >= 1e-6:
        out = np.stack([librosa.effects.pitch_shift(out[:, c].astype(np.float32),
                        sr=SR, n_steps=float(pitch)) for c in range(out.shape[1])], 1)
    peak = max(np.max(np.abs(out)), 1e-9)
    if peak > 0.95:
        out = out * (0.95 / peak)
    return out.astype(np.float64)

# Keep alias for backwards compatibility
apply_pitch_speed = apply_audio_modulation

def load_hum_presets() -> dict:
    presets = {}
    if PRESETS_FILE.exists():
        try:
            presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            presets = {}

    default_suite = {
        "💿 원곡 그대로 100% (Original Clean)": {
            "hum": 0.0, "bed": 0.0, "leak": 1.0,
            "bed_lp": 1000, "leak_lp": 20000, "pitch": 0.0, "speed": 1.0,
            "vocal_cut": 0.0, "wobble": 0.0, "reverb": 0.0, "saturation": 0.0, "formant": 0.0
        },
        "🛡️ Suno 우회: 자연스러운 보컬 허밍 (Natural Blend)": {
            "hum": 0.65, "bed": 0.0, "leak": 0.55,
            "bed_lp": 800, "leak_lp": 20000, "pitch": 0.5, "speed": 1.02,
            "vocal_cut": 0.85, "wobble": 0.12, "reverb": 0.08, "saturation": 0.15, "formant": 0.8
        },
        "🎤 Suno 우회: 클로킹 멜로디 보코더 (Melodic Cloak Lead)": {
            "hum": 0.85, "bed": 0.10, "leak": 0.40,
            "bed_lp": 900, "leak_lp": 12000, "pitch": -1.0, "speed": 0.98,
            "vocal_cut": 1.0, "wobble": 0.18, "reverb": 0.12, "saturation": 0.20, "formant": -1.0
        },
        "📻 Suno 우회: 로파이 어쿠스틱 스미어 (Lo-Fi Vintage Acoustic)": {
            "hum": 0.50, "bed": 0.30, "leak": 0.45,
            "bed_lp": 750, "leak_lp": 6500, "pitch": 1.0, "speed": 1.04,
            "vocal_cut": 0.75, "wobble": 0.35, "reverb": 0.18, "saturation": 0.30, "formant": 1.5
        },
        "🛡️ Suno AI 안전 안티-필터링 (Safe Default)": {
            "hum": 0.0, "bed": 0.0, "leak": 1.0,
            "bed_lp": 900, "leak_lp": 20000, "pitch": 0.0, "speed": 1.0,
            "vocal_cut": 0.80, "wobble": 0.12, "reverb": 0.0, "saturation": 0.15, "formant": 1.0
        },
        "🎤 보컬 100% 컷 & 허밍 보코더 (Vocal Cloak)": {
            "hum": 0.80, "bed": 0.0, "leak": 0.70,
            "bed_lp": 800, "leak_lp": 20000, "pitch": 0.0, "speed": 1.0,
            "vocal_cut": 1.0, "wobble": 0.10, "reverb": 0.0, "saturation": 0.15, "formant": 0.0
        },
        "📻 빈티지 테이프 워블 변조 (Lo-Fi Tape)": {
            "hum": 0.0, "bed": 0.0, "leak": 1.0,
            "bed_lp": 700, "leak_lp": 20000, "pitch": 0.0, "speed": 0.98,
            "vocal_cut": 0.60, "wobble": 0.35, "reverb": 0.0, "saturation": 0.25, "formant": -0.6
        },
        "🎭 포먼트/음색 톤 변조 (Formant Warp)": {
            "hum": 0.0, "bed": 0.0, "leak": 1.0,
            "bed_lp": 850, "leak_lp": 20000, "pitch": 1.0, "speed": 1.0,
            "vocal_cut": 0.60, "wobble": 0.10, "reverb": 0.0, "saturation": 0.15, "formant": 2.5
        },
        "🎵 원곡 + 허밍 조화 믹스": {
            "hum": 0.80, "bed": 0.0, "leak": 0.85,
            "bed_lp": 800, "leak_lp": 20000, "pitch": 0.0, "speed": 1.0,
            "vocal_cut": 0.0, "wobble": 0.0, "reverb": 0.0, "saturation": 0.0, "formant": 0.0
        },
        "✨ 몽환적인 배경 허밍": {
            "hum": 0.60, "bed": 0.15, "leak": 0.50,
            "bed_lp": 800, "leak_lp": 8000, "pitch": 0.0, "speed": 1.0,
            "vocal_cut": 0.50, "wobble": 0.12, "reverb": 0.10, "saturation": 0.10, "formant": 0.0
        }
    }

    # Ensure "💿 원곡 그대로 100% (Original Clean)" and default suite exist
    for k, v in default_suite.items():
        if k not in presets:
            presets[k] = v

    return presets

def save_hum_presets(d: dict):
    PRESETS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def file_key(p: Path) -> str:
    st = p.stat()
    # File names can repeat across uploads, outputs and samples.  Include the
    # full resolved path and nanosecond timestamp so stems never cross tracks.
    import hashlib
    identity = f"{p.resolve()}\0{st.st_size}\0{st.st_mtime_ns}".encode("utf-8")
    return "v2_" + hashlib.sha256(identity).hexdigest()

def get_ffmpeg_bin() -> str:
    env_path = os.environ.get("STUDIO_FFMPEG_PATH", "").strip()
    if env_path and Path(env_path).is_file():
        return env_path
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    for c in (BASE_DIR / "tools" / "ffmpeg.exe", BASE_DIR / "tools" / "ffmpeg"):
        if c.is_file():
            return str(c)
    return "ffmpeg"


class HumStems:
    """Cache for Hum Studio: hum / smeared bed / original audio at 22050Hz."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.ready = False
        self.hum = None
        self.bedL = None
        self.bedR = None
        self.origL = None
        self.origR = None
        self.n = 0
        self.dur = 0.0

    def load_cache(self, path: Path) -> bool:
        try:
            ck = CACHE_DIR / file_key(path)
            if (ck / "hum.wav").exists() and (ck / "bed.wav").exists() and (ck / "orig.wav").exists():
                try:
                    with open(ck / "hum.wav", "rb") as f_h, \
                         open(ck / "bed.wav", "rb") as f_b, \
                         open(ck / "orig.wav", "rb") as f_o:
                        hum, _ = sf.read(f_h)
                        bed, _ = sf.read(f_b, always_2d=True)
                        ori, _ = sf.read(f_o, always_2d=True)
                except Exception:
                    hum, _ = sf.read(str(ck / "hum.wav"))
                    bed, _ = sf.read(str(ck / "bed.wav"), always_2d=True)
                    ori, _ = sf.read(str(ck / "orig.wav"), always_2d=True)
                self.hum = hum
                self.bedL, self.bedR = bed[:, 0], bed[:, 1]
                self.origL, self.origR = ori[:, 0], ori[:, 1]
                self.n, self.dur, self.ready = len(hum), len(hum) / SR, True
                return True
        except Exception as e:
            print(f"[HumStems] load_cache warning (will re-analyze): {e}")
            try:
                ck = CACHE_DIR / file_key(path)
                if ck.exists():
                    shutil.rmtree(ck, ignore_errors=True)
            except Exception:
                pass
            self.reset()
            return False
        self.reset()
        return False

    def analyze(self, path: Path, status_cb, syll: float = 3.2, prog_cb=None):
        def rep(pct, msg):
            if prog_cb:
                prog_cb(int(pct), msg)
            status_cb(msg)

        rep(2, "오디오 파일 읽기 중...")
        y = None
        sr0 = None

        # Robust multi-strategy audio loading (handles Windows locks, UTF-8 paths, libsndfile errors)
        try:
            with open(path, "rb") as f_obj:
                y, sr0 = sf.read(f_obj, always_2d=True)
        except Exception:
            pass

        if y is None:
            try:
                y, sr0 = sf.read(str(path), always_2d=True)
            except Exception:
                pass

        if y is None:
            try:
                y_data, sr0 = librosa.load(str(path), sr=None, mono=False)
                if y_data.ndim == 1:
                    y = np.stack([y_data, y_data], axis=1)
                else:
                    y = y_data.T
            except Exception as e:
                raise RuntimeError(f"오디오 파일 로드 실패: {e}")

        mono = librosa.to_mono(y.T) if y.shape[1] == 2 else y[:, 0].copy()
        if sr0 != SR:
            mono = librosa.resample(mono, orig_sr=sr0, target_sr=SR)
            oL = librosa.resample(y[:, 0], orig_sr=sr0, target_sr=SR)
            oR = librosa.resample(y[:, 1], orig_sr=sr0, target_sr=SR) if y.shape[1] == 2 else oL.copy()
        else:
            oL = y[:, 0].copy()
            oR = y[:, 1].copy() if y.shape[1] == 2 else y[:, 0].copy()

        n = len(mono)
        audio_sec = n / SR
        rep(8, "하모닉(Harmonic) 보컬 성분 분리 중...")
        harm = librosa.effects.harmonic(mono, margin=5.0)

        # YIN pitch tracking calibration
        rate_file = CACHE_DIR / "yin_rate.json"
        try:
            rate = float(json.loads(rate_file.read_text())["rate"])
        except Exception:
            rate = 5.0
        pred = max(5.0, audio_sec / rate)
        done = threading.Event()
        t0 = time.time()

        def _beat():
            while not done.wait(2.0):
                el = time.time() - t0
                eta = max(0.0, pred - el)
                pct = 15 + min(0.95, el / pred) * 50
                rep(pct, f"음정 추적 중… {pct:.0f}% (남은 약 {eta:.0f}초)")

        rep(15, "F0 음정 추적 시작...")
        threading.Thread(target=_beat, daemon=True).start()
        try:
            f0 = librosa.yin(harm, fmin=65, fmax=880, sr=SR, frame_length=2048, hop_length=HOP)
        finally:
            done.set()

        el = time.time() - t0
        if el > 1:
            try:
                rate_file.write_text(json.dumps({"rate": audio_sec / el}))
            except Exception:
                pass

        rep(65, f"음정 추적 완료 ({el:.0f}초 소요)")
        nf = len(f0)
        rms = librosa.feature.rms(y=mono, frame_length=2048, hop_length=HOP)[0][:nf]
        thr = np.quantile(rms, 0.25) * 1.2 + 1e-6
        voiced = (rms > thr) & np.isfinite(f0)
        f0s = f0.copy().astype(float)
        f0s[~voiced] = np.nan
        x = np.arange(nf)
        ok = ~np.isnan(f0s)
        f0s[~ok] = np.interp(x[~ok], x[ok], f0s[ok])
        f0s = signal.medfilt(f0s, kernel_size=7)

        t_f = np.arange(nf) * HOP / SR
        t_s = np.arange(n) / SR
        f0samp = np.interp(t_s, t_f, f0s)
        f0samp *= 1.0 + 0.006 * np.sin(2 * np.pi * 5.5 * t_s)

        env = smooth_env(rms, tau=0.14)
        es = np.interp(t_s, t_f, env)
        es /= (np.max(es) + 1e-9)
        vs = np.interp(t_s, t_f, voiced.astype(float))
        es *= (0.15 + 0.85 * vs)
        es *= 1.0 - 0.28 * (0.5 - 0.5 * np.sin(2 * np.pi * syll * t_s)) * vs

        rep(72, "허밍 보코더 합성 중...")
        phase = np.cumsum(2 * np.pi * f0samp / SR)
        hum = (np.sin(phase) + 0.32 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase + 0.5)) * es
        sos = signal.butter(4, 750, btype="low", fs=SR, output="sos")
        hum = signal.sosfiltfilt(sos, hum)
        b, a = signal.iirpeak(260, 1.2, fs=SR)
        hum = signal.lfilter(b, a, hum)

        rep(80, "반주 그레인 스미어(Smear) 진행 중...")
        self.bedL = grain_smear(oL, seed=11, prog_cb=lambda f: rep(80 + f * 9, f"반주 스미어… {80 + f * 9:.0f}%"))
        self.bedR = grain_smear(oR, seed=23, prog_cb=lambda f: rep(89 + f * 9, f"반주 스미어… {89 + f * 9:.0f}%"))
        self.hum, self.origL, self.origR = hum, oL, oR
        self.n, self.dur, self.ready = n, n / SR, True

        # Save cache with auto-pruning to protect disk space
        try:
            old_caches = sorted([p for p in CACHE_DIR.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
            if len(old_caches) > 12:
                for c in old_caches[:-12]:
                    shutil.rmtree(c, ignore_errors=True)
        except Exception:
            pass

        ck = CACHE_DIR / file_key(path)
        ck.mkdir(parents=True, exist_ok=True)
        rep(98, "캐시 저장 중...")
        try:
            with open(ck / "hum.wav", "wb") as f_h:
                sf.write(f_h, hum, SR, format="WAV")
            with open(ck / "bed.wav", "wb") as f_b:
                sf.write(f_b, np.stack([self.bedL, self.bedR], 1), SR, format="WAV")
            with open(ck / "orig.wav", "wb") as f_o:
                sf.write(f_o, np.stack([oL, oR], 1), SR, format="WAV")
        except Exception:
            sf.write(str(ck / "hum.wav"), hum, SR)
            sf.write(str(ck / "bed.wav"), np.stack([self.bedL, self.bedR], 1), SR)
            sf.write(str(ck / "orig.wav"), np.stack([oL, oR], 1), SR)
        rep(100, "분석 완료")


def mix_hum_segment(st: HumStems, start: float, length: float, p: dict) -> np.ndarray:
    """Mix hum, smeared bed, and vocal leak with filters, pitch, speed, and anti-filtering modulation."""
    s0 = int(max(0, start) * SR)
    s1 = int(min(st.n, (start + length) * SR))
    sl = slice(s0, s1)

    hum = st.hum[sl]
    bL, bR = st.bedL[sl].copy(), st.bedR[sl].copy()
    oL, oR = st.origL[sl].copy(), st.origR[sl].copy()

    # Vocal Cut / Mid-Channel Vocal Attenuation
    # User requirement: 보컬을 컷해서 0까지 만들 수 있게 함 (0% vocal mute)
    vocal_cut = float(p.get("vocal_cut", 0.0))
    if vocal_cut > 0.005:
        mid = 0.5 * (oL + oR)
        side = 0.5 * (oL - oR)
        if vocal_cut >= 0.98:
            # 100% vocal cut: eliminate center mid vocal completely (110Hz~8500Hz), retaining clean sub-bass (<110Hz) & air (>8500Hz) + stereo accompaniment
            sos_bass = signal.butter(2, 110, btype="low", fs=SR, output="sos")
            sos_air = signal.butter(2, 8500, btype="high", fs=SR, output="sos")
            sub_bass = signal.sosfilt(sos_bass, mid)
            air = signal.sosfilt(sos_air, mid)
            mid_attenuated = sub_bass * 0.75 + air * 0.5
        else:
            # Smooth mid vocal band elimination (120Hz ~ 7500Hz)
            sos_voc = signal.butter(2, [120, 7500], btype="bandpass", fs=SR, output="sos")
            mid_voc = signal.sosfilt(sos_voc, mid)
            mid_attenuated = mid - vocal_cut * mid_voc
        oL = mid_attenuated + side
        oR = mid_attenuated - side

    # Bed lowpass (safe check below Nyquist frequency)
    bed_lp = float(p.get("bed_lp", 800))
    if bed_lp < (SR / 2 - 100):
        sos_b = signal.butter(4, bed_lp, btype="low", fs=SR, output="sos")
        bL = signal.sosfilt(sos_b, bL)
        bR = signal.sosfilt(sos_b, bR)

    # Leak lowpass:
    # If leak_lp >= 10,000Hz or leak_bypass is active, bypass filter completely to preserve original pristine sound!
    leak_lp = float(p.get("leak_lp", 20000))
    leak_bypass = bool(p.get("leak_bypass", False)) or (leak_lp >= 10000)
    if not leak_bypass and leak_lp < (SR / 2 - 100):
        sos_l = signal.butter(2, leak_lp, btype="low", fs=SR, output="sos")
        oL = signal.sosfilt(sos_l, oL)
        oR = signal.sosfilt(sos_l, oR)

    hum_gain = float(p.get("hum", 0.0))
    bed_gain = float(p.get("bed", 0.0))
    leak_gain = float(p.get("leak", 1.0))

    # Strict Zero checks: if gain is <= 1e-4, guarantee exact 0 silence for that stem!
    if hum_gain < 1e-4:
        hL = np.zeros_like(oL)
        hR = np.zeros_like(oR)
    else:
        hL = hum * 0.9 + 0.25 * np.roll(hum, int(SR * 0.012))
        hR = hum * 0.9 + 0.25 * np.roll(hum, int(SR * 0.017))

    if bed_gain < 1e-4:
        bL = np.zeros_like(oL)
        bR = np.zeros_like(oR)

    if leak_gain < 1e-4:
        oL = np.zeros_like(oL)
        oR = np.zeros_like(oR)

    mL = hum_gain * hL + bed_gain * bL + leak_gain * oL
    mR = hum_gain * hR + bed_gain * bR + leak_gain * oR

    # CEILING LIMITER: Only scale down if peak exceeds 0.95! Never auto-boost quiet or muted stems!
    peak = max(np.max(np.abs(mL)), np.max(np.abs(mR)), 1e-9)
    if peak > 0.95:
        g = 0.95 / peak
        seg = np.stack([mL * g, mR * g], 1)
    else:
        seg = np.stack([mL, mR], 1)

    return apply_audio_modulation(
        seg,
        pitch=float(p.get("pitch", 0.0)),
        speed=float(p.get("speed", 1.0)),
        wobble=float(p.get("wobble", 0.0)),
        reverb=float(p.get("reverb", 0.0)),
        saturation=float(p.get("saturation", 0.0)),
        formant=float(p.get("formant", 0.0))
    )
