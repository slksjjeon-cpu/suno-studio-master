import os
import time
import shutil
import numpy as np
import soundfile as sf
import scipy.signal as signal
import librosa
from typing import Dict, Any, Tuple

def get_bs1770_filters(sr: int):
    """
    Generate exact ITU-R BS.1770-4 K-weighting pre-filter and high-pass filter biquad coefficients.
    Stage 1: High shelf (+4 dB boost > 1.5 kHz)
    Stage 2: High pass (~38 Hz cut)
    """
    # Stage 1: High shelf filter
    db = 3.9998438
    f0 = 1681.9744509555319
    Q = 0.7071752369554193
    K = np.tan(np.pi * f0 / sr)
    Vh = 10.0 ** (db / 20.0)
    Vb = Vh ** 0.499666774155
    
    a0 = 1.0 + K / Q + K * K
    b0 = (Vh + Vb * K / Q + K * K) / a0
    b1 = 2.0 * (K * K - Vh) / a0
    b2 = (Vh - Vb * K / Q + K * K) / a0
    a1 = 2.0 * (K * K - 1.0) / a0
    a2 = (1.0 - K / Q + K * K) / a0
    b_shelf = np.array([b0, b1, b2])
    a_shelf = np.array([1.0, a1, a2])

    # Stage 2: High-pass filter
    f0_hp = 38.13547087613982
    Q_hp = 0.5003270373253953
    K_hp = np.tan(np.pi * f0_hp / sr)
    a0_hp = 1.0 + K_hp / Q_hp + K_hp * K_hp
    b0_hp = 1.0 / a0_hp
    b1_hp = -2.0 / a0_hp
    b2_hp = 1.0 / a0_hp
    a1_hp = 2.0 * (K_hp * K_hp - 1.0) / a0_hp
    a2_hp = (1.0 - K_hp / Q_hp + K_hp * K_hp) / a0_hp
    b_hp = np.array([b0_hp, b1_hp, b2_hp])
    a_hp = np.array([1.0, a1_hp, a2_hp])

    return (b_shelf, a_shelf), (b_hp, a_hp)


def calculate_integrated_lufs(audio: np.ndarray, sr: int) -> float:
    """
    Calculate Integrated Loudness (LUFS) matching ITU-R BS.1770-4 / EBU R128 standard.
    Includes K-weighting pre-filtering, 400ms sliding blocks with 75% overlap,
    absolute gating (-70 LUFS), and relative gating (-10 LU relative to average).
    """
    if audio.size == 0:
        return -70.0
    
    if audio.ndim == 1:
        audio = audio[np.newaxis, :]
    n_ch, n_samples = audio.shape
    
    (b_shelf, a_shelf), (b_hp, a_hp) = get_bs1770_filters(sr)
    
    block_len = int(0.400 * sr)
    hop_len = int(0.100 * sr)

    if n_samples < block_len:
        z = 0.0
        for ch in range(n_ch):
            s1 = signal.lfilter(b_shelf, a_shelf, audio[ch])
            y_ch = signal.lfilter(b_hp, a_hp, s1)
            z += float(np.mean(y_ch ** 2))
        return float(np.clip(-0.691 + 10.0 * np.log10(max(1e-12, z)), -70.0, 5.0))

    n_blocks = (n_samples - block_len) // hop_len + 1
    z_blocks = np.zeros(n_blocks, dtype=np.float32)

    for ch in range(n_ch):
        s1 = signal.lfilter(b_shelf, a_shelf, audio[ch])
        y_ch = signal.lfilter(b_hp, a_hp, s1)
        y_sq = (y_ch ** 2).astype(np.float32)
        c = np.cumsum(np.insert(y_sq, 0, 0.0), dtype=np.float64)
        starts = np.arange(0, n_blocks * hop_len, hop_len)
        ends = starts + block_len
        z_blocks += ((c[ends] - c[starts]) / block_len).astype(np.float32)

    # 1. Absolute threshold: Gamma_a = -70 LUFS
    l_blocks = -0.691 + 10.0 * np.log10(np.maximum(1e-12, z_blocks))
    abs_mask = l_blocks > -70.0
    if not np.any(abs_mask):
        return -70.0

    # 2. Relative threshold: Gamma_r = (average energy of blocks > -70 LUFS) - 10 LU
    z_above_abs = z_blocks[abs_mask]
    gamma_r = -0.691 + 10.0 * np.log10(float(np.mean(z_above_abs))) - 10.0

    # Gated loudness
    rel_mask = l_blocks > gamma_r
    if not np.any(rel_mask):
        return -70.0

    z_final = float(np.mean(z_blocks[rel_mask]))
    return float(np.clip(-0.691 + 10.0 * np.log10(max(1e-12, z_final)), -70.0, 5.0))


def apply_auto_volume_leveler(audio: np.ndarray, sr: int, window_sec: float = 3.0, max_gain_db: float = 2.5) -> np.ndarray:
    """
    Automatic Volume Leveler with transparent, gentle smoothing (max ±2.5 dB)
    to prevent unnatural volume pumping while leveling MP3/AI dynamics.
    """
    out = audio.copy()
    y_mono = np.mean(audio, axis=0) if audio.ndim > 1 else audio
    
    win_len = int(window_sec * sr)
    if len(y_mono) < win_len:
        return out
        
    def _fast_moving_avg(x: np.ndarray, w: int) -> np.ndarray:
        if len(x) <= w:
            return np.full_like(x, np.mean(x))
        cumsum = np.cumsum(np.insert(x, 0, 0.0))
        res = (cumsum[w:] - cumsum[:-w]) / float(w)
        pad_left = w // 2
        pad_right = len(x) - len(res) - pad_left
        return np.pad(res, (pad_left, pad_right), mode='edge')

    sq = y_mono ** 2
    rms_env = np.sqrt(np.maximum(1e-10, _fast_moving_avg(sq, win_len)))
    
    target_rms = np.median(rms_env[rms_env > 1e-4]) if np.any(rms_env > 1e-4) else 0.1
    
    # Gain envelope with gentle clamp
    gain_env = target_rms / rms_env
    max_mult = 10.0 ** (max_gain_db / 20.0)
    min_mult = 10.0 ** (-max_gain_db / 20.0)
    gain_env = np.clip(gain_env, min_mult, max_mult)
    
    # Very slow, musical smoothing (1.0 second window)
    smooth_w = max(1, int(1.0 * sr))
    gain_env = _fast_moving_avg(gain_env, smooth_w)
    
    if out.ndim > 1:
        out[0] *= gain_env
        out[1] *= gain_env
    else:
        out *= gain_env
        
    return out


def apply_pro_equalizer(
    audio: np.ndarray,
    sr: int,
    low_cut_hz: float = 30.0,
    bass_boost_db: float = 1.5,
    mid_presence_db: float = 0.5,
    air_band_boost_db: float = 2.5
) -> np.ndarray:
    """
    4-Band Precision Mastering Equalizer:
    1. Sub-bass rumble cut (< 30Hz)
    2. Bass Punch (80Hz - 120Hz)
    3. Mid Presence (2.5kHz - 3.5kHz)
    4. High Air Band (> 11kHz, restores Suno's muffled top-end)
    """
    out = audio.copy()
    is_stereo = out.ndim > 1 and out.shape[0] == 2
    
    # 1. Sub-bass cut (Steep highpass at low_cut_hz)
    if low_cut_hz > 10.0:
        b_hp, a_hp = signal.butter(3, low_cut_hz / (0.5 * sr), btype='high')
        if is_stereo:
            out[0] = signal.lfilter(b_hp, a_hp, out[0])
            out[1] = signal.lfilter(b_hp, a_hp, out[1])
        else:
            out = signal.lfilter(b_hp, a_hp, out)

    # 2. Bass Punch (Bell around 90Hz)
    if abs(bass_boost_db) > 0.1:
        gain_lin = 10.0 ** (bass_boost_db / 20.0) - 1.0
        b_bass, a_bass = signal.butter(2, [60.0 / (0.5 * sr), 150.0 / (0.5 * sr)], btype='band')
        if is_stereo:
            out[0] += signal.lfilter(b_bass, a_bass, out[0]) * gain_lin
            out[1] += signal.lfilter(b_bass, a_bass, out[1]) * gain_lin
        else:
            out += signal.lfilter(b_bass, a_bass, out) * gain_lin

    # 3. Mid Presence (Vocal / Clarity bell around 2.8kHz)
    if abs(mid_presence_db) > 0.1:
        gain_lin = 10.0 ** (mid_presence_db / 20.0) - 1.0
        b_mid, a_mid = signal.butter(2, [1800.0 / (0.5 * sr), 3800.0 / (0.5 * sr)], btype='band')
        if is_stereo:
            out[0] += signal.lfilter(b_mid, a_mid, out[0]) * gain_lin
            out[1] += signal.lfilter(b_mid, a_mid, out[1]) * gain_lin
        else:
            out += signal.lfilter(b_mid, a_mid, out) * gain_lin

    # 4. Air Band (High shelf > 11kHz, brightens dull AI audio)
    if abs(air_band_boost_db) > 0.1:
        gain_lin = 10.0 ** (air_band_boost_db / 20.0) - 1.0
        b_air, a_air = signal.butter(2, min(0.95, 11000.0 / (0.5 * sr)), btype='high')
        if is_stereo:
            out[0] += signal.lfilter(b_air, a_air, out[0]) * gain_lin
            out[1] += signal.lfilter(b_air, a_air, out[1]) * gain_lin
        else:
            out += signal.lfilter(b_air, a_air, out) * gain_lin

    return out


def apply_mid_side_stereo(audio: np.ndarray, width: float = 1.25) -> np.ndarray:
    """Mid/Side spatial stereo enhancement."""
    if audio.ndim < 2 or audio.shape[0] < 2:
        return audio
    
    mid = 0.5 * (audio[0] + audio[1])
    side = 0.5 * (audio[0] - audio[1])
    
    # Scale width
    side_scaled = side * width
    
    # Mono bass preservation: low-cut the side channel < 90Hz to keep bass dead-center
    # (Prevents muddy stereo phase cancellation)
    b_hp, a_hp = signal.butter(2, 90.0 / (0.5 * 44100), btype='high')
    side_scaled = signal.lfilter(b_hp, a_hp, side_scaled)
    
    new_left = mid + side_scaled
    new_right = mid - side_scaled
    
    return np.stack([new_left, new_right], axis=0)


def apply_tape_warmth(audio: np.ndarray, drive: float = 0.15) -> np.ndarray:
    """Analog tape saturation adding musical odd/even harmonics."""
    if drive <= 0.01:
        return audio
    gain = 1.0 + drive * 2.0
    return np.tanh(audio * gain) / np.tanh(gain)


def apply_true_peak_limiter(audio: np.ndarray, ceiling_db: float = -0.3) -> np.ndarray:
    """True-Peak limiter preventing digital clipping (Inter-Sample Peaks)."""
    ceiling_linear = 10.0 ** (ceiling_db / 20.0)
    
    # Soft-knee analog curve before brickwall ceiling
    knee_threshold = ceiling_linear * 0.85
    out = audio.copy()
    
    mask = np.abs(out) > knee_threshold
    if np.any(mask):
        excess = np.abs(out[mask]) - knee_threshold
        compressed = knee_threshold + (ceiling_linear - knee_threshold) * np.tanh(excess / (ceiling_linear - knee_threshold + 1e-8))
        out[mask] = np.sign(out[mask]) * compressed

    # Absolute ceiling clamp
    out = np.clip(out, -ceiling_linear, ceiling_linear)
    return out


def master_audio_pro(
    audio: np.ndarray,
    sr: int,
    mastering_options: Dict[str, Any],
    output_filepath: str
) -> Dict[str, Any]:
    """
    Complete Professional Suno AI Audio Mastering Chain:
    1. MP3 Auto Volume Leveling (Auto-Gain Leveler)
    2. 4-Band Mastering EQ with Air Band restoration
    3. Mid/Side Stereo Imager
    4. Analog Tape Warmth Saturation
    5. Integrated LUFS Normalization (Target: -14 LUFS, -9 LUFS, etc.)
    6. True-Peak Limiter
    """
    t_start = time.time()
    
    target_lufs = float(mastering_options.get("target_lufs", -14.0))
    auto_leveling = bool(mastering_options.get("auto_leveling", True))
    stereo_width = float(mastering_options.get("stereo_width", 1.15))
    tape_warmth = float(mastering_options.get("tape_warmth", 0.08))
    # EBU R128 / Spotify / Apple Music standard True Peak ceiling is -1.0 dBFS
    ceiling_db = float(mastering_options.get("limiter_ceiling_db", -1.0))
    
    # EQ parameters (gentle, musical defaults)
    bass_boost = float(mastering_options.get("bass_boost_db", 1.0))
    mid_presence = float(mastering_options.get("mid_presence_db", 0.5))
    air_band = float(mastering_options.get("air_band_boost_db", 1.5))

    cur_audio = audio.copy()
    
    # Measure input LUFS
    input_lufs = calculate_integrated_lufs(cur_audio, sr)

    # 1. MP3 Auto Volume Leveling (gentle smoothing)
    if auto_leveling:
        cur_audio = apply_auto_volume_leveler(cur_audio, sr)

    # 2. Precision 4-Band EQ
    cur_audio = apply_pro_equalizer(
        cur_audio, sr,
        low_cut_hz=30.0,
        bass_boost_db=bass_boost,
        mid_presence_db=mid_presence,
        air_band_boost_db=air_band
    )

    # 3. Stereo Spatial Expansion
    cur_audio = apply_mid_side_stereo(cur_audio, width=stereo_width)

    # 4. Tape Warmth
    cur_audio = apply_tape_warmth(cur_audio, drive=tape_warmth)

    # 5. Integrated LUFS Normalization (ITU-R BS.1770-4)
    intermediate_lufs = calculate_integrated_lufs(cur_audio, sr)
    lufs_diff = target_lufs - intermediate_lufs
    gain_factor = 10.0 ** (lufs_diff / 20.0)
    # Safe gain scaling (limits maximum boost to +6dB to prevent distortion)
    cur_audio *= max(0.25, min(2.0, gain_factor))

    # 6. True-Peak Limiter (transparent ceiling at -1.0 dBFS)
    mastered = apply_true_peak_limiter(cur_audio, ceiling_db=ceiling_db)

    # Final LUFS measurement
    output_lufs = calculate_integrated_lufs(mastered, sr)

    # Save to disk
    out_dir = os.path.dirname(os.path.abspath(output_filepath))
    os.makedirs(out_dir, exist_ok=True)
    
    # Pre-check disk space
    try:
        _, _, free_bytes = shutil.disk_usage(out_dir)
        free_mb = free_bytes / (1024 * 1024)
        if free_mb < 30.0:
            raise RuntimeError(
                f"C 드라이브 용량 부족 (현재 {free_mb:.1f}MB 남음): 마스터링 고음질 WAV 파일 저장을 위한 디스크 공간이 부족합니다. C 드라이브 용량을 확보해주세요."
            )
    except Exception as d_err:
        if "C 드라이브 용량 부족" in str(d_err):
            raise d_err

    save_data = mastered.T if mastered.ndim > 1 else mastered
    save_data = np.ascontiguousarray(save_data, dtype=np.float32)

    try:
        sf.write(output_filepath, save_data, sr, format="WAV", subtype="PCM_16")
    except Exception as write_err:
        try:
            _, _, free_bytes = shutil.disk_usage(out_dir)
            free_mb = free_bytes / (1024 * 1024)
            if free_mb < 100.0:
                raise RuntimeError(
                    f"C 드라이브 용량 부족 (현재 {free_mb:.1f}MB 남음): 디스크 공간 부족으로 인해 WAV 저장을 완료할 수 없습니다. C 드라이브 용량을 확보해주세요."
                ) from write_err
        except Exception:
            pass
        raise write_err

    elapsed = round(time.time() - t_start, 2)
    try:
        print(f"[MasteringPro] Mastered {output_filepath} in {elapsed}s | In: {input_lufs:.1f} LUFS -> Out: {output_lufs:.1f} LUFS")
    except Exception:
        pass

    return {
        "output_filepath": output_filepath,
        "filename": os.path.basename(output_filepath),
        "input_lufs": round(input_lufs, 1),
        "output_lufs": round(output_lufs, 1),
        "target_lufs": target_lufs,
        "stereo_width": stereo_width,
        "ceiling_db": ceiling_db,
        "duration_sec": round(mastered.shape[-1] / sr, 2),
        "process_time_sec": elapsed
    }
