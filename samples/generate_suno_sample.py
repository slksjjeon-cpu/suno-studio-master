import os
import numpy as np
import soundfile as sf

def generate_suno_drift_sample(output_path: str, duration_sec: float = 30.0, sr: int = 44100):
    """
    Generate realistic Suno AI demo sample:
    1. Base tempo accelerates gradually (e.g. 100 -> 106 BPM over 30 seconds)
    2. Ultrasonic inaudible watermark pattern injected above 19kHz (amplitude ~ -45dBFS)
    3. Uneven section volume and dull high-mids typical of AI vocoders
    """
    total_samples = int(duration_sec * sr)
    t = np.arange(total_samples) / sr
    
    # Gradual accelerating BPM curve: 100 BPM at t=0, ~107 BPM at t=30
    # Phase phi(t) = integral of (2 * pi * bpm(t) / 60) dt
    start_bpm = 100.0
    drift_slope = 0.22 # BPM per second
    # bpm(t) = start_bpm + drift_slope * t
    bpm_t = start_bpm + drift_slope * t
    # phi(t) in beats
    phi_beats = (start_bpm * t + 0.5 * drift_slope * (t ** 2)) / 60.0
    
    left = np.zeros(total_samples, dtype=np.float32)
    right = np.zeros(total_samples, dtype=np.float32)
    
    # 1. Rhythmic Beats (Kick & Snare accelerating with phi_beats)
    # Beat on integer phi_beats
    beat_phase = phi_beats % 1.0
    beat_triggers = np.diff(beat_phase) < -0.5
    beat_indices = np.where(beat_triggers)[0]
    
    for i, idx in enumerate(beat_indices):
        if idx >= total_samples: break
        
        # Kick on 1 and 3 (every 2 beats)
        if i % 2 == 0:
            k_len = min(int(sr * 0.15), total_samples - idx)
            kt = np.arange(k_len) / sr
            kick = np.sin(2 * np.pi * (140 * np.exp(-kt * 28) + 48) * kt) * np.exp(-kt * 10.0)
            left[idx:idx + k_len] += kick * 0.6
            right[idx:idx + k_len] += kick * 0.6
        else:
            # Snare on 2 and 4
            s_len = min(int(sr * 0.12), total_samples - idx)
            st = np.arange(s_len) / sr
            snare = (np.random.normal(0, 0.3, s_len) + np.sin(2 * np.pi * 190 * st) * 0.25) * np.exp(-st / 0.05)
            left[idx:idx + s_len] += snare * 0.45
            right[idx:idx + s_len] += snare * 0.45

    # 2. Chord Harmony (Am - F - C - G loop)
    chords = [
        [220.0, 261.63, 329.63], # Am
        [174.61, 220.0, 261.63], # F
        [261.63, 329.63, 392.0], # C
        [196.0, 246.94, 293.66], # G
    ]
    bar_phase = (phi_beats / 4.0) % 4.0
    current_chord_idx = (bar_phase.astype(int)) % 4
    
    # Generate pad sound
    for c_idx in range(4):
        mask = (current_chord_idx == c_idx)
        if not np.any(mask): continue
        tones = chords[c_idx]
        for tone_f in tones:
            synth = (np.sin(2 * np.pi * tone_f * t) * 0.15 +
                     np.sin(2 * np.pi * tone_f * 2 * t) * 0.08)
            left[mask] += synth[mask] * 0.4
            right[mask] += synth[mask] * 0.45

    # 3. Simulate Suno Ultrasonic Inaudible Watermark Signature (> 19.5kHz)
    # Binary spread-spectrum chirps and tone peaks at 19.8kHz, 20.4kHz, 21.1kHz
    watermark_chirp = (
        np.sin(2 * np.pi * 19800.0 * t) * 0.008 +
        np.sin(2 * np.pi * 20500.0 * t + np.sin(2 * np.pi * 12.0 * t)) * 0.006 +
        np.sin(2 * np.pi * 21200.0 * t) * 0.005
    )
    left += watermark_chirp
    right += watermark_chirp

    # Uneven section volume typical of MP3/Suno (quieter in middle, loud at end)
    vol_envelope = 0.75 + 0.25 * (t / duration_sec) + 0.1 * np.sin(2 * np.pi * 0.1 * t)
    left *= vol_envelope
    right *= vol_envelope

    # Peak normalization
    peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
    if peak > 0:
        left = (left / peak) * 0.88
        right = (right / peak) * 0.88

    stereo = np.stack([left, right], axis=1)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sf.write(output_path, stereo, sr)
    print(f"[SampleGen] Generated Suno demo sample with tempo drift (100->107 BPM) and ultrasonic watermark at {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(__file__), "demo_suno_drift.wav")
    generate_suno_drift_sample(out_file)
