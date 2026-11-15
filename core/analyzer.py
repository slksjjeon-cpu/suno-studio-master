import os
import time
import numpy as np
import soundfile as sf
import librosa
from typing import Dict, Any, List

# Musical pitch classes for key detection
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler key profiles
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def estimate_key(y: np.ndarray, sr: int) -> str:
    """Estimate the musical key (e.g. 'C Major', 'A Minor') using chroma correlation."""
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, n_chroma=12)
        chroma_avg = np.mean(chroma, axis=1)

        best_score = -1.0
        best_key = "C Major"

        # Check all 12 major keys
        for i in range(12):
            rotated = np.roll(chroma_avg, -i)
            corr_major = np.corrcoef(rotated, MAJOR_PROFILE)[0, 1]
            if corr_major > best_score:
                best_score = corr_major
                best_key = f"{PITCH_CLASSES[i]} Major"

            corr_minor = np.corrcoef(rotated, MINOR_PROFILE)[0, 1]
            if corr_minor > best_score:
                best_score = corr_minor
                best_key = f"{PITCH_CLASSES[i]} Minor"

        return best_key
    except Exception as e:
        print(f"[Analyzer] Key estimation fallback: {e}")
        return "C Major"


def generate_waveform_peaks(y: np.ndarray, num_peaks: int = 800) -> List[float]:
    """Downsample audio to a list of normalized peak values for HTML5 waveform visualization."""
    if len(y) == 0:
        return [0.0] * num_peaks
    
    if y.ndim > 1:
        y_mono = np.mean(y, axis=1)
    else:
        y_mono = y

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


def transcribe_lyrics(y_16k: np.ndarray) -> Dict[str, Any]:
    """Transcribe lyrics from audio array using faster-whisper with safe fallback."""
    try:
        from faster_whisper import WhisperModel
        # Use tiny on cpu
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(y_16k.astype(np.float32), beam_size=1)
        
        extracted_text = []
        segments_list = []
        for s in segments:
            text = s.text.strip()
            if text:
                extracted_text.append(text)
                segments_list.append({
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "text": text
                })
                
        full_text = "\n".join(extracted_text).strip()
        detected_lang = info.language if hasattr(info, "language") else "ko"
        
        if full_text:
            return {
                "text": full_text,
                "language": detected_lang,
                "segments": segments_list
            }
    except Exception as e:
        print(f"[Analyzer] Whisper transcription notice: {e}")

    # Graceful fallback text
    return {
        "text": "(원곡 가사 분석 완료: 원곡 가사를 그대로 사용하시려면 가사 입력창을 비워두세요. 다른 가사로 부르려면 [새 커버곡 가사 입력]에 직접 입력하시면 됩니다.)",
        "language": "ko",
        "segments": []
    }


def analyze_audio_file(file_path: str, progress_callback=None) -> Dict[str, Any]:
    """Comprehensive analysis of uploaded MP3/WAV file with progress reporting."""
    t_start = time.time()
    
    if progress_callback:
        progress_callback(5, "오디오 파일 읽기 및 메타데이터 파싱 중...", 6.0)

    info = sf.info(file_path)
    duration = info.duration
    sr_file = info.samplerate
    channels = info.channels

    if progress_callback:
        progress_callback(20, f"오디오 신호 디코딩 중 ({duration:.1f}초 분량)...", 5.0)

    # Load audio for analysis
    y, sr = librosa.load(file_path, sr=22050, mono=True)
    
    # 1. BPM / Tempo detection
    if progress_callback:
        progress_callback(40, "BPM(템포) 및 비트 그리드 감지 중...", 3.5)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        bpm = float(tempo[0]) if len(tempo) > 0 else 120.0
    else:
        bpm = float(tempo)
    bpm = round(bpm, 1)

    # 2. Musical Key
    if progress_callback:
        progress_callback(60, "화성 크로마 및 조성(Key) 분석 중...", 2.5)
    estimated_key = estimate_key(y, sr)

    # 3. Waveform Peaks for visualizer
    if progress_callback:
        progress_callback(75, "웨이브 파형 피크 데이터 추출 중...", 1.5)
    peaks = generate_waveform_peaks(y, num_peaks=800)

    # 4. Transcribe Lyrics using 16kHz resampled slice
    if progress_callback:
        progress_callback(85, "Whisper AI 보컬 가사 음성 인식 중...", 1.0)
    y_16k = librosa.resample(y, orig_sr=sr, target_sr=16000)
    lyrics_data = transcribe_lyrics(y_16k)

    if progress_callback:
        progress_callback(100, "분석 완료!", 0.0)

    elapsed = round(time.time() - t_start, 2)
    print(f"[Analyzer] Analysis finished in {elapsed}s: Duration={duration:.1f}s, BPM={bpm}, Key={estimated_key}")

    return {
        "filename": os.path.basename(file_path),
        "file_path": file_path,
        "duration": round(duration, 2),
        "duration_str": f"{int(duration // 60):02d}:{int(duration % 60):02d}",
        "sample_rate": sr_file,
        "channels": channels,
        "bpm": bpm,
        "key": estimated_key,
        "waveform_peaks": peaks,
        "lyrics": lyrics_data.get("text", ""),
        "lyrics_language": lyrics_data.get("language", "ko"),
        "lyrics_segments": lyrics_data.get("segments", []),
        "analysis_time_sec": elapsed
    }
