import os
import sys
import time
import tempfile
import subprocess
import numpy as np
import soundfile as sf
import librosa
from typing import Dict, Any

from core.dewatermark import remove_ai_watermark
from core.tempo_stabilizer import stabilize_audio_tempo
from core.master_pro import master_audio_pro, calculate_integrated_lufs
from core.analyzer_suno import generate_spectrogram_summary, compute_frequency_curve
from core.hum_engine import get_ffmpeg_bin

def safe_print(*args, **kwargs):
    """Crash-proof print for any Unicode characters on Windows."""
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            enc = sys.stdout.encoding or "utf-8"
            safe_args = [str(a).encode(enc, errors="replace").decode(enc, errors="replace") for a in args]
            print(*safe_args, **kwargs)
        except Exception:
            pass

def process_suno_mastering(
    source_audio_path: str,
    output_filepath: str,
    options: Dict[str, Any],
    start_sec: float = 0.0,
    duration_sec: float = None
) -> Dict[str, Any]:
    """
    Execute complete Suno AI De-Watermarking, Tempo Drift Correction & Pro Mastering Pipeline:
    1. Slice audio (if preview range specified)
    2. Remove AI Inaudible Watermark & Ultrasonic Signatures
    3. Stabilize & Flatten Dynamic Tempo Acceleration (preserve pitch)
    4. Apply Professional Mastering (Auto-leveling, 4-Band EQ, Mid/Side, Tape warmth, LUFS Normalizing, Limiter)
    5. Save mastered audio and generate Before/After metrics
    """
    t_start = time.time()
    sr = 44100

    info = sf.info(source_audio_path)
    file_duration = info.duration

    start_sec = max(0.0, min(start_sec, file_duration - 0.5))
    if duration_sec is None or duration_sec <= 0 or (start_sec + duration_sec) > file_duration:
        duration_sec = file_duration - start_sec

    # Load audio slice
    y, _ = librosa.load(source_audio_path, sr=sr, offset=start_sec, duration=duration_sec, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y], axis=0)

    # Initial measurements
    orig_lufs = calculate_integrated_lufs(y, sr)
    orig_peak = float(np.max(np.abs(y)))
    orig_spec = generate_spectrogram_summary(y, sr, num_frames=48)

    cur_audio = y.copy()

    # ── Step 1: Remove AI Inaudible Watermark ──
    dewatermark_enabled = bool(options.get("dewatermark_enabled", True))
    watermark_report = {}
    if dewatermark_enabled:
        cur_audio, watermark_report = remove_ai_watermark(
            cur_audio,
            sr=sr,
            cutoff_freq=float(options.get("ultrasonic_cut_freq", 18500.0)),
            decorrelate_phase=bool(options.get("decorrelate_phase", True)),
            apply_tpdf_dither=bool(options.get("tpdf_dither", True)),
            de_ringing=bool(options.get("de_ringing", True))
        )

    # ── Step 2: Dynamic Tempo Acceleration Correction ──
    tempo_stabilize_enabled = bool(options.get("tempo_stabilize_enabled", True))
    tempo_report = {}
    if tempo_stabilize_enabled and "tempo_info" in options:
        cur_audio, tempo_report = stabilize_audio_tempo(
            cur_audio,
            sr=sr,
            tempo_info=options["tempo_info"],
            target_bpm=options.get("target_bpm"),
            pitch_shift_semitones=0.0  # Pitch shift handled cleanly in Step 2.5
        )

    # ── Step 2.5: Pitch Shift & Speed Adjustment via High-Precision FFmpeg rubberband ──
    pitch_shift = float(options.get("pitch_shift", 0.0))
    speed_ratio = float(options.get("speed_ratio", 1.0))
    keep_pitch = bool(options.get("keep_pitch", True))

    has_pitch = abs(pitch_shift) > 0.005
    has_speed = abs(speed_ratio - 1.0) > 0.005

    if has_pitch or has_speed:
        safe_print(f"[PipelineSuno] Applying Pitch & Speed: pitch={pitch_shift:+.2f}st, speed={speed_ratio:.2f}x (keep_pitch={keep_pitch})")
        applied_ffmpeg = False
        if keep_pitch or has_pitch:
            try:
                ffmpeg = get_ffmpeg_bin()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in, \
                     tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
                    in_tmp = f_in.name
                    out_tmp = f_out.name
                
                sf.write(in_tmp, cur_audio.T if cur_audio.ndim > 1 else cur_audio, sr)
                
                if has_pitch:
                    pitch_scale = 2.0 ** (pitch_shift / 12.0)
                    af_str = f"rubberband=pitch={pitch_scale:.8f}:tempo={speed_ratio:.6f}"
                else:
                    atempo_filters = []
                    cur_spd = speed_ratio
                    while cur_spd > 2.0:
                        atempo_filters.append("atempo=2.0")
                        cur_spd /= 2.0
                    while cur_spd < 0.5:
                        atempo_filters.append("atempo=0.5")
                        cur_spd /= 0.5
                    atempo_filters.append(f"atempo={cur_spd:.6f}")
                    af_str = ",".join(atempo_filters)
                
                cmd = [ffmpeg, "-y", "-i", in_tmp, "-filter:a", af_str, out_tmp]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                stretched_data, _ = sf.read(out_tmp, dtype="float32")
                cur_audio = stretched_data.T if stretched_data.ndim > 1 else stretched_data
                applied_ffmpeg = True
                for p in [in_tmp, out_tmp]:
                    try:
                        if os.path.exists(p): os.unlink(p)
                    except Exception: pass
            except Exception as ex:
                safe_print(f"[PipelineSuno] FFmpeg rubberband error: {ex}")
                applied_ffmpeg = False

            if not applied_ffmpeg:
                stretched_chans = [
                    librosa.effects.time_stretch(np.ascontiguousarray(ch, dtype=np.float32), rate=speed_ratio)
                    for ch in cur_audio
                ]
                cur_audio = np.stack(stretched_chans, axis=0)
        else:
            # Vinyl / Tape speed adjustment (resampling naturally alters pitch)
            resampled_sr = int(round(sr * speed_ratio))
            resampled_chans = [
                librosa.resample(np.ascontiguousarray(ch, dtype=np.float32), orig_sr=resampled_sr, target_sr=sr)
                for ch in cur_audio
            ]
            cur_audio = np.stack(resampled_chans, axis=0)

    # ── Step 3: Professional Mastering Suite ──
    master_result = master_audio_pro(
        cur_audio,
        sr=sr,
        mastering_options=options,
        output_filepath=output_filepath
    )

    # After measurements
    mastered_data, _ = sf.read(output_filepath)
    mastered_data = mastered_data.T if mastered_data.ndim > 1 else mastered_data
    final_spec = generate_spectrogram_summary(mastered_data, sr, num_frames=48)

    orig_curve = compute_frequency_curve(y, sr, num_bands=32)
    final_curve = compute_frequency_curve(mastered_data, sr, num_bands=32)

    is_stereo_orig = y.ndim > 1 and y.shape[0] == 2
    is_stereo_final = mastered_data.ndim > 1 and mastered_data.shape[0] == 2

    orig_width = round(float(np.sum((y[0] - y[1])**2) / (np.sum((y[0] + y[1])**2) + 1e-12) * 100), 1) if is_stereo_orig else 0.0
    final_width = round(float(np.sum((mastered_data[0] - mastered_data[1])**2) / (np.sum((mastered_data[0] + mastered_data[1])**2) + 1e-12) * 100), 1) if is_stereo_final else 0.0

    elapsed = round(time.time() - t_start, 2)
    safe_print(f"[PipelineSuno] Mastered file created: {output_filepath} in {elapsed}s")

    actual_duration = round(float(mastered_data.shape[1] if mastered_data.ndim > 1 else len(mastered_data)) / float(sr), 2)
    return {
        "output_filepath": output_filepath,
        "filename": os.path.basename(output_filepath),
        "start_sec": start_sec,
        "duration_sec": actual_duration,
        "is_preview": duration_sec < (file_duration - 1.0),
        "speed_ratio": speed_ratio,
        "keep_pitch": keep_pitch,
        "metrics_before": {
            "lufs": round(orig_lufs, 1),
            "peak_db": round(20.0 * np.log10(max(1e-6, orig_peak)), 2),
            "spectrogram": orig_spec,
            "frequency_curve": orig_curve,
            "stereo_width_pct": orig_width
        },
        "metrics_after": {
            "lufs": master_result["output_lufs"],
            "peak_db": round(master_result["ceiling_db"], 2),
            "spectrogram": final_spec,
            "frequency_curve": final_curve,
            "stereo_width_pct": final_width
        },
        "watermark_removed": dewatermark_enabled,
        "tempo_stabilized": tempo_stabilize_enabled,
        "tempo_report": tempo_report,
        "process_time_sec": elapsed
    }
