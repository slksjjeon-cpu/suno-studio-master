import os
import gc
import re
import time
import unicodedata
import numpy as np
import soundfile as sf
import scipy.signal as signal
import librosa
from typing import Dict, Any, List, Optional

from core.dewatermark import detect_watermark_signature
from core.tempo_analyzer_robust import analyze_dynamic_tempo_robust
from core.master_pro import calculate_integrated_lufs
from core.suno_prompt_reverse_engineer import (
    detect_musical_key_and_scale,
    analyze_vocal_and_instrumental_spectrum,
    analyze_song_dynamic_structure,
    generate_suno_v6_prompt_deep
)

def compute_frequency_curve(y: np.ndarray, sr: int, num_bands: int = 32) -> List[float]:
    """Compute normalized 32-band log-frequency energy spectrum (0.0 to 1.0) for visual EQ curve."""
    if len(y) == 0:
        return [0.5] * num_bands
    y_mono = np.mean(y, axis=0) if y.ndim > 1 else y
    if len(y_mono) > sr * 30:
        y_mono = y_mono[:int(sr * 30)]
    nperseg = min(len(y_mono), 4096)
    freqs, psd = signal.welch(y_mono, fs=sr, nperseg=nperseg)
    
    bands = np.geomspace(30, min(20000, sr // 2), num_bands + 1)
    curve = []
    for i in range(num_bands):
        mask = (freqs >= bands[i]) & (freqs < bands[i + 1])
        val = float(np.mean(psd[mask])) if np.any(mask) else 1e-12
        db = 10.0 * np.log10(max(1e-12, val))
        # Map roughly -75dB ~ -15dB to 0.0 ~ 1.0
        norm_val = np.clip((db + 75.0) / 60.0, 0.0, 1.0)
        curve.append(round(float(norm_val), 3))
    return curve


def compute_smart_mastering_recommendations(y: np.ndarray, sr: int, watermark_info: dict, tempo_info: dict, input_lufs: float) -> dict:
    """
    Intelligent Audio Profiling:
    Analyzes frequency balance, dynamic consistency, stereo width, and AI artifacts,
    computing optimal professional mastering recommendations with Korean rationales.
    """
    y_mono = np.mean(y, axis=0) if y.ndim > 1 else y
    is_stereo = y.ndim > 1 and y.shape[0] == 2
    
    # 1. Welch PSD for Band Energies (on representative 30s slice to keep cloud memory < 60MB)
    y_slice = y_mono[:int(sr * 30)] if len(y_mono) > sr * 30 else y_mono
    nperseg = min(len(y_slice), 4096)
    freqs, psd = signal.welch(y_slice, fs=sr, nperseg=nperseg)
    total_energy = float(np.sum(psd) + 1e-15)
    
    mask_sub = (freqs >= 30) & (freqs < 120)
    mask_mid = (freqs >= 1500) & (freqs < 4500)
    mask_air = (freqs >= 10000) & (freqs < 18000)
    
    e_sub = float(np.sum(psd[mask_sub])) / total_energy
    e_mid = float(np.sum(psd[mask_mid])) / total_energy
    e_air = float(np.sum(psd[mask_air])) / total_energy
    
    # 2. Air Band Decision (Restoring muffled AI MP3 roll-off)
    if e_air < 0.015:
        rec_air = 2.5
        air_reason = "초고역 롤오프 심각 (에어 복원 +2.5dB 강력 추천)"
    elif e_air < 0.035:
        rec_air = 1.5
        air_reason = "초고역 공기감 보강 (+1.5dB 추천)"
    else:
        rec_air = 0.5
        air_reason = "고역대 균형 양호 (+0.5dB 미세 보정)"
        
    # 3. Bass Punch Decision (Sub/Bass 80~120Hz)
    if e_sub < 0.08:
        rec_bass = 2.0
        bass_reason = "서브/저역대 타격감 보강 (+2.0dB 추천)"
    elif e_sub < 0.18:
        rec_bass = 1.0
        bass_reason = "자연스러운 저역 펀치 (+1.0dB 추천)"
    else:
        rec_bass = 0.0
        bass_reason = "저역 에너지 충분 (0.0dB 유지)"

    # 4. Mid Presence Decision (2.5~3.5kHz Vocal / Clarity)
    if e_mid < 0.10:
        rec_mid = 1.0
        mid_reason = "보컬/악기 명료도 개선 (+1.0dB 추천)"
    elif e_mid > 0.28:
        rec_mid = 0.0
        mid_reason = "중역대 과다 방지 (0.0dB 유지)"
    else:
        rec_mid = 0.5
        mid_reason = "자연스러운 보컬 전진감 (+0.5dB 추천)"

    # 5. Stereo Spatial Width (Mid/Side Ratio)
    rec_width = 1.15
    width_reason = "자연스러운 입체 음장 확장 (115%)"
    if is_stereo:
        # Use 10s representative slice to avoid 400MB memory spike on 12M audio samples
        y_slice_stereo = y[:, :int(sr * 10)] if y.shape[1] > sr * 10 else y
        mid = 0.5 * (y_slice_stereo[0] + y_slice_stereo[1])
        side = 0.5 * (y_slice_stereo[0] - y_slice_stereo[1])
        side_ratio = float(np.sum(side**2) / (np.sum(mid**2) + 1e-12))
        del mid, side
        gc.collect()
        if side_ratio < 0.12:
            rec_width = 1.30
            width_reason = "모노에 가까운 좁은 공간감 확장 (130% 추천)"
        elif side_ratio > 0.40:
            rec_width = 1.10
            width_reason = "이미 넓은 스테레오 필드 정돈 (110%)"
        else:
            rec_width = 1.20
            width_reason = "황금비율 입체 음장 확장 (120% 추천)"

    # 6. Tape Warmth Decision
    rec_warmth = 0.12
    warmth_reason = "디지털 질감 완화 및 아날로그 배음 (12%)"
    if watermark_info.get("detected", False):
        rec_warmth = 0.18
        warmth_reason = "AI 합성 노이즈 중화 및 따뜻한 배음 강화 (18% 추천)"

    # 7. Dewatermark & Tempo Drift
    rec_dewatermark = bool(watermark_info.get("detected", True))
    rec_tempo_stabilize = bool(tempo_info.get("is_accelerating", False))
    
    # 8. Target LUFS
    rec_lufs = -14.0
    lufs_reason = "글로벌 스트리밍 표준 음압 (-14.0 LUFS)"

    reasons_list = [air_reason, bass_reason, mid_reason, width_reason]
    if rec_tempo_stabilize:
        reasons_list.append(f"템포 가속 드리프트 감지 ({tempo_info.get('start_bpm')} BPM 평탄화 고정)")
    if rec_dewatermark:
        reasons_list.append("18kHz+ 비가청 워터마크 탐지 (뉴트럴라이즈 제거)")

    return {
        "profile_name": "AI 스마트 맞춤 프로필",
        "reason_summary": " | ".join(reasons_list),
        "target_lufs": rec_lufs,
        "auto_leveling": True,
        "bass_boost_db": rec_bass,
        "mid_presence_db": rec_mid,
        "air_band_boost_db": rec_air,
        "stereo_width": rec_width,
        "tape_warmth": rec_warmth,
        "dewatermark_enabled": rec_dewatermark,
        "tempo_stabilize_enabled": rec_tempo_stabilize,
        "limiter_ceiling_db": -1.0,
        "details": {
            "air_reason": air_reason,
            "bass_reason": bass_reason,
            "mid_reason": mid_reason,
            "width_reason": width_reason,
            "warmth_reason": warmth_reason,
            "lufs_reason": lufs_reason,
            "spectral_balance": {
                "sub_energy_pct": round(float(e_sub * 100), 1),
                "mid_energy_pct": round(float(e_mid * 100), 1),
                "air_energy_pct": round(float(e_air * 100), 1),
            }
        }
    }

def generate_waveform_peaks(y: np.ndarray, num_peaks: int = 800) -> List[float]:
    """Downsample audio to a list of normalized peak values for HTML5 waveform."""
    if len(y) == 0:
        return [0.0] * num_peaks
    
    y_mono = np.mean(y, axis=0) if y.ndim > 1 else y
    chunk_size = max(1, len(y_mono) // num_peaks)
    peaks = []
    for i in range(num_peaks):
        start = i * chunk_size
        end = min(len(y_mono), start + chunk_size)
        if start >= len(y_mono):
            peaks.append(0.0)
        else:
            chunk = y_mono[start:end]
            peak = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
            peaks.append(round(peak, 4))
    
    max_val = max(peaks) if peaks else 1.0
    if max_val > 0:
        peaks = [round(p / max_val, 4) for p in peaks]
    return peaks


def generate_spectrogram_summary(y: np.ndarray, sr: int, num_frames: int = 64) -> List[List[float]]:
    """Generate compact 2D spectrogram matrix (time x frequency bins) for visual comparison."""
    y_mono = np.mean(y, axis=0) if y.ndim > 1 else y
    # Ultra-low memory melspectrogram on downsampled mono
    y_sub = y_mono[::2] if sr > 22050 else y_mono
    sr_sub = sr // 2 if sr > 22050 else sr
    hop_length = max(512, len(y_sub) // (num_frames * 2))
    mel = librosa.feature.melspectrogram(y=y_sub, sr=sr_sub, n_fft=1024, hop_length=hop_length, n_mels=24)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    
    # Normalize 0.0 ~ 1.0
    mel_norm = np.clip((mel_db + 80.0) / 80.0, 0.0, 1.0)
    
    # Downsample time to num_frames
    step = max(1, mel_norm.shape[1] // num_frames)
    reduced = mel_norm[:, ::step][:, :num_frames]
    
    # Return as list of floats
    return [[round(float(val), 3) for val in row] for row in reduced]


def analyze_suno_track(file_path: str, progress_callback=None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Comprehensive analysis of Suno AI / YouTube audio track:
    - Dynamic tempo drift detection (e.g. 100 -> 106 BPM)
    - High-frequency inaudible watermark signature detection
    - Integrated LUFS loudness & true-peak
    - Waveform peaks & spectrogram data
    - Suno v6 Reverse Prompt Engineering (Styles < 1,000 chars, Exclude, Advanced Params)
    """
    t_start = time.time()
    
    if progress_callback:
        progress_callback(10, "오디오 디코딩 및 메타데이터 읽기...", 5.0)

    info = sf.info(file_path)
    duration = info.duration
    sr_file = info.samplerate
    channels = info.channels

    if progress_callback:
        progress_callback(20, f"오디오 신호 로드 중 ({duration:.1f}초)...", 4.0)

    # Fast & low-memory audio loading via soundfile (prevents Render 512MB RAM OOM)
    try:
        data, sr = sf.read(file_path, dtype='float32')
        if data.ndim == 1:
            y = np.stack([data, data], axis=0)
        else:
            y = data.T  # Shape: (channels, samples)
    except Exception:
        y, sr = librosa.load(file_path, sr=None, mono=False)
        if y.ndim == 1:
            y = np.stack([y, y], axis=0)

    # 1. Inaudible Watermark & High-Frequency Signature
    if progress_callback:
        progress_callback(35, "18kHz+ 초고역대 비가청 워터마크 및 AI 지문 탐지 중...", 3.0)
    watermark_info = detect_watermark_signature(y, sr)
    gc.collect()

    # 2. Dynamic Tempo & Acceleration Drift Analysis (Octave-Locked Robust Engine)
    if progress_callback:
        progress_callback(50, "비트 트래킹 및 옥타브 락킹 기반 템포 가속 곡선 계산 중...", 2.0)
    tempo_info = analyze_dynamic_tempo_robust(y, sr)
    gc.collect()

    # 3. Loudness Analysis (LUFS)
    if progress_callback:
        progress_callback(65, "통합 라우드니스(LUFS) 및 다이내믹 레인지 정밀 측정 중...", 1.2)
    lufs = calculate_integrated_lufs(y, sr)
    gc.collect()
    peak = float(np.max(np.abs(y)))
    peak_db = round(20.0 * np.log10(max(1e-6, peak)), 2)

    # 4. Waveform, Spectrogram & Frequency Response Curve
    if progress_callback:
        progress_callback(75, "스펙트로그램 및 주파수 반응 커브 생성 중...", 0.8)
    peaks = generate_waveform_peaks(y, num_peaks=800)
    spec_data = generate_spectrogram_summary(y, sr, num_frames=60)
    freq_curve = compute_frequency_curve(y, sr, num_bands=32)

    # 5. Smart Mastering Recommendations
    if progress_callback:
        progress_callback(85, "AI 음향 밸런스 프로파일링 및 마스터링 최적 추천값 산출 중...", 0.5)
    smart_rec = compute_smart_mastering_recommendations(y, sr, watermark_info, tempo_info, lufs)
    gc.collect()

    # 6. Deep Suno v6 Reverse Prompt Engineering
    if progress_callback:
        progress_callback(92, "Suno v6 역설계 프롬프트 분석 및 보컬/편곡 심층 아키텍처 산출 중...", 0.4)
    
    # Key detection & acoustic profile
    key_name, key_conf = detect_musical_key_and_scale(y, sr)
    gc.collect()
    acoustic_profile = analyze_vocal_and_instrumental_spectrum(y, sr)
    gc.collect()
    structure_profile = analyze_song_dynamic_structure(y, sr)
    gc.collect()
    
    song_title = (metadata or {}).get("title") or os.path.splitext(os.path.basename(file_path))[0]
    # Clean up yt_ prefixes or timestamps and normalize Unicode font variants (e.g. mathematical bold) to standard text
    song_title_clean = unicodedata.normalize('NFKC', re.sub(r'^(yt_|check_|url_check_|\d+_)+', '', song_title)).strip()
    
    suno_v6_prompt = generate_suno_v6_prompt_deep(
        title=song_title_clean,
        raw_info=metadata or {},
        tempo_bpm=tempo_info.get("start_bpm", 120.0),
        musical_key=key_name,
        acoustic=acoustic_profile,
        structure=structure_profile,
        audio_path=file_path
    )

    if progress_callback:
        progress_callback(100, "분석 완료!", 0.0)

    elapsed = round(time.time() - t_start, 2)
    try:
        print(f"[AnalyzerSuno] Analysis completed in {elapsed}s | Start BPM: {tempo_info['start_bpm']} -> End: {tempo_info['end_bpm']} | LUFS: {lufs:.1f} | Key: {key_name} | Suno v6 Styles chars: {suno_v6_prompt['styles_char_count']}")
    except Exception:
        pass

    return {
        "filename": os.path.basename(file_path),
        "file_path": file_path,
        "duration": round(duration, 2),
        "duration_str": f"{int(duration // 60):02d}:{int(duration % 60):02d}",
        "sample_rate": sr_file,
        "channels": channels,
        "input_lufs": round(lufs, 1),
        "input_peak_db": peak_db,
        "musical_key": key_name,
        "musical_key_confidence": key_conf,
        "watermark_analysis": watermark_info,
        "tempo_analysis": tempo_info,
        "waveform_peaks": peaks,
        "spectrogram_matrix": spec_data,
        "frequency_curve": freq_curve,
        "smart_recommendations": smart_rec,
        "suno_v6_prompt": suno_v6_prompt,
        "acoustic_profile": acoustic_profile,
        "analysis_time_sec": elapsed
    }
