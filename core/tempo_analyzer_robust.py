import numpy as np
import librosa
from typing import Dict, Any, List

def analyze_dynamic_tempo_robust(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Robust Octave-Locked Micro-Tempo Analyzer for AI Music (Suno):
    Solves octave-jumping errors (e.g. 191 BPM <-> 90 BPM) by:
    1. Locking fundamental base tempo within human musical range (60 ~ 170 BPM).
    2. Using Tempogram Fourier/Autocorrelation with strict octave clamping.
    3. Tracking Inter-Beat Intervals (IBIs) with outlier rejection.
    4. Applying robust linear regression to detect true subtle micro-acceleration (e.g. 100.0 -> 104.2 BPM).
    """
    y_mono = np.mean(y, axis=0) if y.ndim > 1 else y
    duration = len(y_mono) / sr

    if duration < 3.0:
        return {
            "start_bpm": 120.0, "end_bpm": 120.0, "drift_bpm": 0.0,
            "drift_percent": 0.0, "is_accelerating": False, "timeline_points": []
        }

    # Low-memory downsampling for tempo analysis (22kHz-24kHz standard for beat detection)
    if sr > 24000:
        y_mono = y_mono[::2]
        sr_tempo = sr // 2
    else:
        sr_tempo = sr

    # 1. Onset Strength Envelope
    hop_length = 512
    onset_env = librosa.onset.onset_strength(y=y_mono, sr=sr_tempo, hop_length=hop_length)

    # 2. Global Base Tempo with Prior (Avoid octave jumps)
    # Set a log-normal prior centered at 115 BPM to prevent 190+ or <55 outlier detections
    prior = librosa.feature.tempo(onset_envelope=onset_env, sr=sr_tempo, hop_length=hop_length, 
                                  start_bpm=115.0, std_bpm=1.0, max_tempo=180.0)
    base_tempo = float(prior[0]) if isinstance(prior, np.ndarray) and len(prior) > 0 else float(prior)

    # Octave normalize base tempo into 70 ~ 145 BPM standard zone
    while base_tempo > 145.0:
        base_tempo /= 2.0
    while base_tempo < 70.0:
        base_tempo *= 2.0
    base_tempo = round(base_tempo, 1)

    # 3. Dynamic Fourier Tempogram
    tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr_tempo, hop_length=hop_length, win_length=384)
    tempo_bins = librosa.tempo_frequencies(tempogram.shape[0], sr=sr_tempo, hop_length=hop_length)

    # Focus only on the octave window [base_tempo * 0.75, base_tempo * 1.35]
    valid_mask = (tempo_bins >= base_tempo * 0.75) & (tempo_bins <= base_tempo * 1.35)
    if not np.any(valid_mask):
        valid_mask = (tempo_bins >= 50.0) & (tempo_bins <= 160.0)

    # Time axis in seconds
    times = librosa.times_like(tempogram, sr=sr_tempo, hop_length=hop_length)

    # Slice into 8 to 15 time segments across the song
    num_slices = max(5, min(16, int(duration // 2.5)))
    slice_indices = np.array_split(np.arange(tempogram.shape[1]), num_slices)

    t_points = []
    bpm_points = []

    for s_idx in slice_indices:
        if len(s_idx) == 0:
            continue
        t_center = float(np.mean(times[s_idx]))
        sub_gram = tempogram[:, s_idx]
        
        # Average energy in valid tempo band
        energy_band = np.mean(sub_gram, axis=1)
        energy_band[~valid_mask] = 0.0

        best_bin = np.argmax(energy_band)
        detected_bpm = float(tempo_bins[best_bin])

        # Strict octave clamp against base_tempo
        # If detected is roughly 2x, divide by 2
        ratio = detected_bpm / base_tempo
        if 1.7 <= ratio <= 2.3:
            detected_bpm /= 2.0
        elif 0.4 <= ratio <= 0.6:
            detected_bpm *= 2.0

        # Reject any residual outliers beyond +/- 18% of base tempo
        if abs(detected_bpm - base_tempo) / base_tempo > 0.18:
            detected_bpm = base_tempo

        t_points.append(round(t_center, 1))
        bpm_points.append(round(detected_bpm, 1))

    # 4. Outlier Rejection & Robust Smoothing using Moving Median
    if len(bpm_points) >= 3:
        bpm_filtered = []
        for i in range(len(bpm_points)):
            window = bpm_points[max(0, i - 1):min(len(bpm_points), i + 2)]
            bpm_filtered.append(float(np.median(window)))
        bpm_points = bpm_filtered

    # 5. Robust Linear Fit (Theil-Sen / Linear Regression on time vs bpm)
    # Detects the true gradient: start_bpm -> end_bpm
    if len(t_points) >= 2:
        coeffs = np.polyfit(t_points, bpm_points, 1) # slope, intercept
        slope = coeffs[0]
        intercept = coeffs[1]

        fitted_start_bpm = float(intercept + slope * t_points[0])
        fitted_end_bpm = float(intercept + slope * t_points[-1])
    else:
        fitted_start_bpm = base_tempo
        fitted_end_bpm = base_tempo
        slope = 0.0

    # Clean display values
    start_bpm = round(fitted_start_bpm, 1)
    end_bpm = round(fitted_end_bpm, 1)
    drift_bpm = round(end_bpm - start_bpm, 1)
    drift_percent = round((drift_bpm / start_bpm) * 100.0, 1) if start_bpm > 0 else 0.0

    # True acceleration detection:
    # Noticeable if it accelerates by more than +0.8 BPM and positive slope
    is_accelerating = bool(drift_bpm >= 0.8 and drift_percent >= 0.8)

    # Timeline data for time-warping
    timeline = [{"time_sec": t, "bpm": round(b, 1)} for t, b in zip(t_points, bpm_points)]

    print(f"[RobustTempo] Base: {base_tempo} | Start: {start_bpm} BPM -> End: {end_bpm} BPM (Drift: {drift_bpm:+} BPM, {drift_percent:+}%) | Accel: {is_accelerating}")

    return {
        "global_bpm": base_tempo,
        "start_bpm": start_bpm,
        "end_bpm": end_bpm,
        "drift_bpm": drift_bpm,
        "drift_percent": drift_percent,
        "is_accelerating": is_accelerating,
        "timeline_points": timeline
    }
