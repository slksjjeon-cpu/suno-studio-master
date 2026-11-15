import os
import time
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter
from typing import Dict, Any

def _biquad_highpass(y: np.ndarray, cutoff: float, sr: int) -> np.ndarray:
    nyq = 0.5 * sr
    norm = max(0.001, min(0.99, cutoff / nyq))
    b, a = butter(2, norm, btype='high')
    return lfilter(b, a, y, axis=-1)


def _biquad_lowpass(y: np.ndarray, cutoff: float, sr: int) -> np.ndarray:
    nyq = 0.5 * sr
    norm = max(0.001, min(0.99, cutoff / nyq))
    b, a = butter(2, norm, btype='low')
    return lfilter(b, a, y, axis=-1)


def _apply_eq_profile(audio: np.ndarray, sr: int, profile: str) -> np.ndarray:
    """Apply mastering EQ shaping."""
    out = audio.copy()
    
    # 1. Clean sub rumble below 30Hz always
    out = _biquad_highpass(out, 30.0, sr)

    if profile == "crisp":
        # Boost highs (>8kHz) and tight bass (70Hz)
        highs = _biquad_highpass(out, 8500.0, sr)
        lows = _biquad_lowpass(out, 120.0, sr)
        out = out + (highs * 0.28) + (lows * 0.20)

    elif profile == "punchy_bass":
        # Deep club punch (50Hz ~ 110Hz)
        lows = _biquad_lowpass(out, 110.0, sr)
        out = out + (lows * 0.40)
        # Mid scoop around 350Hz
        mids = _biquad_lowpass(_biquad_highpass(out, 250.0, sr), 600.0, sr)
        out = out - (mids * 0.12)

    elif profile == "warm_low":
        # Vintage tape warmth (boost 200Hz, roll off > 16kHz)
        out = _biquad_lowpass(out, 15500.0, sr)
        warm_mids = _biquad_lowpass(_biquad_highpass(out, 180.0, sr), 500.0, sr)
        out = out + (warm_mids * 0.25)

    return out


def _apply_stereo_imager(audio: np.ndarray, width: float) -> np.ndarray:
    """Mid/Side processing to enhance stereo field width."""
    if audio.shape[0] < 2:
        return audio
    
    left = audio[0]
    right = audio[1]

    # Mid = (L + R) / 2, Side = (L - R) / 2
    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)

    # Scale side channel
    side_widened = side * width

    # Reconstruct L and R
    new_left = mid + side_widened
    new_right = mid - side_widened

    return np.stack([new_left, new_right], axis=0)


def _soft_clip_limiter(audio: np.ndarray, ceiling_db: float = -0.3) -> np.ndarray:
    """Soft analog-style limiter to prevent clipping and maximize loudness."""
    ceiling_linear = 10.0 ** (ceiling_db / 20.0)
    
    # Smooth tanh saturation for peaks
    normalized = audio / ceiling_linear
    compressed = np.tanh(normalized)
    
    return compressed * ceiling_linear


def _calculate_rms(audio: np.ndarray) -> float:
    """Calculate root mean square of audio."""
    return float(np.sqrt(np.mean(audio ** 2)))


def master_audio(
    audio_data: np.ndarray,
    sr: int,
    mastering_options: Dict[str, Any],
    output_filepath: str
) -> Dict[str, Any]:
    """Execute complete mastering chain and write final file."""
    t_start = time.time()
    
    is_enabled = mastering_options.get("enabled", True)
    if not is_enabled:
        # Save unmastered raw audio
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        # Ensure (channels, samples) -> (samples, channels) for soundfile
        save_data = audio_data.T if audio_data.ndim > 1 else audio_data
        sf.write(output_filepath, save_data, sr)
        return {
            "output_filepath": output_filepath,
            "mastered": False,
            "duration": round(audio_data.shape[-1] / sr, 2),
            "process_time_sec": round(time.time() - t_start, 2)
        }

    target_lufs = float(mastering_options.get("target_lufs", -14.0))
    eq_profile = mastering_options.get("eq_profile", "crisp")
    stereo_width = float(mastering_options.get("stereo_width", 1.20))
    ceiling_db = float(mastering_options.get("limiter_ceiling_db", -0.3))

    # 1. Apply Mastering EQ
    mastered = _apply_eq_profile(audio_data, sr, eq_profile)

    # 2. Apply Stereo Width Imager
    mastered = _apply_stereo_imager(mastered, width=stereo_width)

    # 3. Loudness Normalization
    # Approximate target RMS based on LUFS target
    # -14 LUFS is roughly equivalent to ~0.14 - 0.17 RMS in music material
    target_rms = 10.0 ** ((target_lufs + 3.0) / 20.0)
    current_rms = _calculate_rms(mastered)
    
    if current_rms > 1e-6:
        gain_multiplier = target_rms / current_rms
        mastered = mastered * min(3.5, max(0.5, gain_multiplier))

    # 4. Soft Saturation & Limiter
    mastered = _soft_clip_limiter(mastered, ceiling_db=ceiling_db)

    # Ensure shape for soundfile: (N, 2)
    save_data = mastered.T if mastered.ndim > 1 else mastered
    
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    sf.write(output_filepath, save_data, sr, format="WAV")

    elapsed = round(time.time() - t_start, 2)
    print(f"[Mastering] Mastered audio saved to {output_filepath} in {elapsed}s (LUFS: {target_lufs}, EQ: {eq_profile})")

    return {
        "output_filepath": output_filepath,
        "filename": os.path.basename(output_filepath),
        "mastered": True,
        "target_lufs": target_lufs,
        "eq_profile": eq_profile,
        "stereo_width": stereo_width,
        "limiter_ceiling_db": ceiling_db,
        "duration": round(mastered.shape[-1] / sr, 2),
        "process_time_sec": elapsed
    }
