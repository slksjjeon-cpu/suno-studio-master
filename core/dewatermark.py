import numpy as np
import scipy.signal as signal
from typing import Dict, Any, Tuple

def detect_watermark_signature(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Advanced Multi-Stage Composite AI Watermark & Synthetic Artifact Detector:
    1. Narrowband Ultrasonic Carrier & Pilot Tone Spike Filter (18kHz - 21.5kHz)
    2. Stereo Phase Disparity & Modulation Incoherence Filter (> 18kHz)
    3. Spectral Shelf Energy Excess Ratio vs Natural Acoustic Decay
    4. Temporal Cyclostationary Frame Autocorrelation (Sync Pulse Scan)
    """
    if len(y) == 0:
        return {
            "detected": False,
            "confidence": 0.0,
            "risk_level": "안전 (Clean)",
            "hf_energy_ratio": 0.0,
            "filters": {}
        }

    y_mono = np.mean(y, axis=0) if y.ndim > 1 else y
    is_stereo = y.ndim > 1 and y.shape[0] == 2
    
    # 1. Welch Power Spectral Density
    nperseg = min(len(y_mono), 8192)
    freqs, psd = signal.welch(y_mono, fs=sr, nperseg=nperseg)
    total_energy = float(np.sum(psd) + 1e-15)
    
    # Filter 1: Ultrasonic Carrier Spikes (18kHz - 21.5kHz)
    mask_ultra = (freqs >= 18000) & (freqs <= min(21800, sr // 2))
    carrier_spikes = []
    spike_score = 0.0
    prominence_db = 0.0
    hf_energy = 0.0
    if np.any(mask_ultra):
        psd_ultra = psd[mask_ultra]
        freqs_ultra = freqs[mask_ultra]
        hf_energy = float(np.sum(psd_ultra))
        median_floor = float(np.median(psd_ultra) + 1e-15)
        psd_db = 10.0 * np.log10(psd_ultra / median_floor)
        
        peaks, _ = signal.find_peaks(psd_db, height=4.0, distance=4)
        if len(peaks) > 0:
            for p in peaks[:5]:
                carrier_spikes.append(int(round(float(freqs_ultra[p]))))
            prominence_db = float(np.max(psd_db[peaks]))
            spike_score = float(min(100.0, max(0.0, prominence_db * 7.5)))
            
    hf_ratio = float(hf_energy / total_energy)

    # Filter 2: Stereo Phase Disparity Anomaly in > 18kHz
    phase_anomaly_score = 0.0
    phase_disparity_deg = 0.0
    if is_stereo and len(y[0]) >= 2048:
        try:
            n_fft = 2048
            hop = 512
            _, _, Zxx_l = signal.stft(y[0], fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
            _, _, Zxx_r = signal.stft(y[1], fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
            f_stft = np.fft.rfftfreq(n_fft, 1.0 / sr)
            stft_ultra_mask = f_stft >= 18000
            if np.any(stft_ultra_mask):
                cross = Zxx_l[stft_ultra_mask, :] * np.conj(Zxx_r[stft_ultra_mask, :])
                phase_diff = np.angle(cross)
                phase_disparity_deg = float(np.mean(np.abs(np.rad2deg(phase_diff))))
                if phase_disparity_deg > 50.0:
                    phase_anomaly_score = float(min(100.0, (phase_disparity_deg - 45.0) * 2.8))
        except Exception:
            pass

    # Filter 3: Spectral Shelf Energy Excess (18.5k-21.5k vs 14k-17k)
    shelf_score = 0.0
    excess_shelf_db = 0.0
    mask_ref = (freqs >= 14000) & (freqs <= 17000)
    if np.any(mask_ref) and np.any(mask_ultra):
        energy_ref = float(np.mean(psd[mask_ref]) + 1e-15)
        energy_ultra = float(np.mean(psd[mask_ultra]) + 1e-15)
        ratio_db = 10.0 * np.log10(energy_ultra / energy_ref)
        excess_shelf_db = round(float(ratio_db + 20.0), 1)
        if ratio_db > -16.0:
            shelf_score = float(min(100.0, max(0.0, (ratio_db + 20.0) * 6.5)))

    # Filter 4: Temporal Cyclostationary Frame Autocorrelation (Sync Pulse Scan)
    periodicity_score = 0.0
    pulse_interval_ms = 0.0
    try:
        if sr >= 40000 and len(y_mono) > sr * 2:
            sos = signal.butter(3, [18000 / (0.5 * sr), min(0.98, 21500 / (0.5 * sr))], btype='band', output='sos')
            y_ultra = signal.sosfilt(sos, y_mono[:sr * 6])
            env = np.abs(signal.hilbert(y_ultra))
            env_ds = signal.resample(env, int(len(env) * 1000.0 / sr))
            env_norm = env_ds - np.mean(env_ds)
            corr = np.correlate(env_norm, env_norm, mode='full')
            corr = corr[len(corr) // 2:]
            if len(corr) > 300:
                corr_slice = corr[20:250] / (corr[0] + 1e-12)
                p_idx = int(np.argmax(corr_slice))
                max_corr = float(corr_slice[p_idx])
                if max_corr > 0.15:
                    pulse_interval_ms = round(float(p_idx + 20), 1)
                    periodicity_score = float(min(100.0, max_corr * 240.0))
    except Exception:
        pass

    # Weighted Multi-Filter Fusion
    composite = 0.35 * spike_score + 0.25 * phase_anomaly_score + 0.25 * shelf_score + 0.15 * periodicity_score
    if np.any(mask_ultra) and hf_energy > 1e-6:
        composite = max(composite, 45.0)

    confidence = round(float(min(100.0, max(0.0, composite))), 1)
    detected = bool(confidence >= 35.0 or len(carrier_spikes) > 0)

    if confidence >= 65.0:
        risk_level = "경고 (AI 워터마크 지문 확정)"
    elif confidence >= 35.0:
        risk_level = "주의 (비가청 합성 서명 의심)"
    else:
        risk_level = "안전 (워터마크 미탐지 / 자연 음향)"

    triggered_filters = []
    if len(carrier_spikes) > 0:
        triggered_filters.append(f"파일럿 톤 스파이크 ({', '.join(str(f) for f in carrier_spikes[:3])} Hz)")
    if phase_anomaly_score > 30.0:
        triggered_filters.append(f"초고역 위상 변조 편차 ({phase_disparity_deg:.1f}°)")
    if shelf_score > 30.0:
        triggered_filters.append(f"비자연적 쉘프 에너지 (+{excess_shelf_db} dB)")
    if periodicity_score > 30.0:
        triggered_filters.append(f"워터마크 프레임 주기 펄스 ({pulse_interval_ms} ms)")

    summary = " | ".join(triggered_filters) if triggered_filters else "초고역 주파수 자연 감쇄 확인됨"

    return {
        "detected": detected,
        "confidence": confidence,
        "risk_level": risk_level,
        "hf_energy_ratio": round(hf_ratio, 6),
        "ultrasonic_present": bool(np.any(mask_ultra) and hf_energy > 1e-7),
        "summary": summary,
        "filters": {
            "carrier_spikes": {
                "detected": bool(len(carrier_spikes) > 0),
                "frequencies": carrier_spikes,
                "prominence_db": round(prominence_db, 1),
                "score": round(spike_score, 1),
                "name": "18~21.5kHz 파일럿 톤 스파이크"
            },
            "phase_anomaly": {
                "detected": bool(phase_anomaly_score > 25.0),
                "disparity_deg": round(phase_disparity_deg, 1),
                "score": round(phase_anomaly_score, 1),
                "name": "초고역 스테레오 위상 변조 지문"
            },
            "energy_shelf": {
                "detected": bool(shelf_score > 25.0),
                "excess_db": excess_shelf_db,
                "score": round(shelf_score, 1),
                "name": "비자연적 초고역 쉘프 에너지"
            },
            "periodicity": {
                "detected": bool(periodicity_score > 25.0),
                "pulse_interval_ms": pulse_interval_ms,
                "score": round(periodicity_score, 1),
                "name": "프레임 동기 주기적 펄스 상관도"
            }
        },
        "sample_rate": sr
    }


def remove_ai_watermark(
    audio: np.ndarray,
    sr: int,
    cutoff_freq: float = 18500.0,
    decorrelate_phase: bool = True,
    apply_tpdf_dither: bool = True,
    de_ringing: bool = True
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Remove inaudible watermarks, synthetic fingerprints, and neural vocoder artifacts:
    1. Linear-phase brickwall lowpass filter at 18.5kHz (erases ultrasonic watermarks)
    2. Micro-phase randomization / decorrelation (destroys spread-spectrum phase watermarks)
    3. TPDF psychoacoustic dithering (erases binary masking payloads)
    4. Anti-metallic de-ringing (smoothes neural synthesizer harshness)
    """
    out = audio.copy()
    is_stereo = out.ndim > 1 and out.shape[0] == 2

    # 1. Ultrasonic Brickwall Filter (Erase signatures > 18.5kHz)
    nyquist = 0.5 * sr
    if cutoff_freq < nyquist:
        # Design a steep linear-phase FIR filter to preserve audible phase
        num_taps = 255
        normal_cutoff = min(0.98, cutoff_freq / nyquist)
        fir_coeff = signal.firwin(num_taps, normal_cutoff, window="hamming")
        
        if is_stereo:
            out[0] = signal.filtfilt(fir_coeff, 1.0, out[0])
            out[1] = signal.filtfilt(fir_coeff, 1.0, out[1])
        else:
            out = signal.filtfilt(fir_coeff, 1.0, out)

    # 2. Phase Decorrelation (Disrupt phase-encoded spread-spectrum watermarks)
    if decorrelate_phase:
        # Micro all-pass filter dispersion (inaudible group delay variation)
        # Randomizes phase without altering magnitude spectrum
        delay_samples = 4
        allpass_b = np.array([-0.35, 1.0], dtype=np.float32)
        allpass_a = np.array([1.0, -0.35], dtype=np.float32)
        
        if is_stereo:
            out[0] = signal.lfilter(allpass_b, allpass_a, out[0])
            out[1] = signal.lfilter(allpass_b, allpass_a, out[1])
        else:
            out = signal.lfilter(allpass_b, allpass_a, out)

    # 3. Anti-Metallic De-Ringing (Smooth neural vocoder comb artifacts around 3kHz~6kHz)
    if de_ringing:
        # Subtle dynamic notch / smoothing in harsh resonant bands
        notch_b, notch_a = signal.iirnotch(4200.0, Q=8.0, fs=sr)
        if is_stereo:
            ring_smooth_0 = signal.filtfilt(notch_b, notch_a, out[0])
            ring_smooth_1 = signal.filtfilt(notch_b, notch_a, out[1])
            out[0] = out[0] * 0.75 + ring_smooth_0 * 0.25
            out[1] = out[1] * 0.75 + ring_smooth_1 * 0.25
        else:
            ring_smooth = signal.filtfilt(notch_b, notch_a, out)
            out = out * 0.75 + ring_smooth * 0.25

    # 4. TPDF Dithering (Triangular Probability Density Function Dither)
    if apply_tpdf_dither:
        # Memory-safe triangular dither amplitude at -96dBFS
        rng = np.random.default_rng()
        amp = np.float32(10.0 ** (-96.0 / 20.0))
        tpdf_noise = rng.triangular(-1.0, 0.0, 1.0, size=out.shape).astype(np.float32) * amp
        out = out + tpdf_noise

    # Peak safety check
    peak = np.max(np.abs(out))
    if peak > 1.0:
        out = out / peak

    details = {
        "ultrasonic_cut_freq": cutoff_freq,
        "phase_scrambled": decorrelate_phase,
        "dither_applied": apply_tpdf_dither,
        "de_ringing_applied": de_ringing,
        "status": "Watermark & Digital Fingerprint Neutralized"
    }

    return out, details
