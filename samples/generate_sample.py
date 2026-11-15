import os
import numpy as np
import soundfile as sf

def generate_demo_track(output_path: str, duration_sec: float = 32.0, sr: int = 44100):
    """Generate a high-quality multi-instrument 32-second pop ballad audio sample."""
    total_samples = int(duration_sec * sr)
    t = np.arange(total_samples) / sr
    
    # 90 BPM Pop Ballad in C Major
    bpm = 90.0
    beat_dur = 60.0 / bpm
    bar_dur = beat_dur * 4.0
    
    # Chord progression: C - G - Am - F (4 bars loop)
    # C: C4, E4, G4 (261.63, 329.63, 392.00) + C2 bass (65.41)
    # G: G3, B3, D4 (196.00, 246.94, 293.66) + G2 bass (98.00)
    # Am: A3, C4, E4 (220.00, 261.63, 329.63) + A2 bass (110.00)
    # F: F3, A3, C4 (174.61, 220.00, 261.63) + F2 bass (87.31)
    chords = [
        {"root": 65.41, "tones": [261.63, 329.63, 392.00, 523.25]},
        {"root": 98.00, "tones": [196.00, 246.94, 293.66, 392.00]},
        {"root": 110.00, "tones": [220.00, 261.63, 329.63, 440.00]},
        {"root": 87.31, "tones": [174.61, 220.00, 261.63, 349.23]}
    ]
    
    left = np.zeros(total_samples, dtype=np.float32)
    right = np.zeros(total_samples, dtype=np.float32)
    
    num_bars = int(duration_sec / bar_dur) + 1
    
    # 1. Piano and Bass accompaniment
    for bar_idx in range(num_bars):
        chord = chords[bar_idx % 4]
        bar_start_sample = int(bar_idx * bar_dur * sr)
        
        # 4 beats in bar
        for beat in range(4):
            beat_start = bar_start_sample + int(beat * beat_dur * sr)
            if beat_start >= total_samples:
                break
            
            # Bass on beat 1 and 3
            if beat in [0, 2]:
                bass_len = min(int(beat_dur * 1.8 * sr), total_samples - beat_start)
                bass_t = np.arange(bass_len) / sr
                bass_note = np.sin(2 * np.pi * chord["root"] * bass_t) * np.exp(-bass_t * 2.2)
                bass_note += 0.3 * np.sin(2 * np.pi * chord["root"] * 2.0 * bass_t) * np.exp(-bass_t * 3.0)
                left[beat_start:beat_start + bass_len] += bass_note * 0.35
                right[beat_start:beat_start + bass_len] += bass_note * 0.35
            
            # Piano chord arpeggiation
            for t_idx, freq in enumerate(chord["tones"]):
                note_offset = beat_start + int(t_idx * (beat_dur / 4.0) * sr)
                if note_offset >= total_samples:
                    continue
                note_len = min(int(beat_dur * 1.5 * sr), total_samples - note_offset)
                note_t = np.arange(note_len) / sr
                
                # Piano timbre with harmonics
                piano = (
                    np.sin(2 * np.pi * freq * note_t) * 0.6 +
                    np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.25 +
                    np.sin(2 * np.pi * freq * 3.0 * note_t) * 0.12
                ) * np.exp(-note_t * 3.5)
                
                # Stereo spread
                pan_l = 0.6 + 0.3 * (t_idx % 2)
                pan_r = 0.6 - 0.3 * (t_idx % 2)
                left[note_offset:note_offset + note_len] += piano * pan_l * 0.22
                right[note_offset:note_offset + note_len] += piano * pan_r * 0.22

    # 2. Vocal Lead Melody (catchy emotional vocal line)
    # Notes in C: E4, G4, A4, G4, E4, D4, C4...
    melody_notes = [
        (0.0, 1.0, 329.63),   # E4
        (1.0, 1.0, 392.00),   # G4
        (2.0, 1.5, 440.00),   # A4
        (3.5, 0.5, 392.00),   # G4
        (4.0, 1.0, 329.63),   # E4
        (5.0, 1.0, 293.66),   # D4
        (6.0, 2.0, 261.63),   # C4
        (8.0, 1.0, 329.63),   # E4
        (9.0, 1.0, 349.23),   # F4
        (10.0, 1.5, 392.00),  # G4
        (11.5, 0.5, 440.00),  # A4
        (12.0, 1.5, 392.00),  # G4
        (13.5, 0.5, 329.63),  # E4
        (14.0, 2.0, 293.66),  # D4
    ]
    
    # Repeat melody for the second half
    full_melody = list(melody_notes)
    for start_b, dur_b, f in melody_notes:
        full_melody.append((start_b + 16.0, dur_b, f * (1.0 if start_b < 12 else 1.12)))

    for start_beat, dur_beats, freq in full_melody:
        start_sample = int(start_beat * beat_dur * sr)
        if start_sample >= total_samples:
            continue
        dur_samples = min(int(dur_beats * beat_dur * sr), total_samples - start_sample)
        v_t = np.arange(dur_samples) / sr
        
        # Vocal formant simulation with vibrato
        vibrato = 1.0 + 0.015 * np.sin(2 * np.pi * 5.5 * v_t)
        vocal = (
            np.sin(2 * np.pi * freq * vibrato * v_t) * 0.7 +
            np.sin(2 * np.pi * freq * 2.0 * vibrato * v_t) * 0.35 +
            np.sin(2 * np.pi * freq * 3.0 * vibrato * v_t) * 0.15 +
            np.sin(2 * np.pi * freq * 4.0 * vibrato * v_t) * 0.08
        )
        # Envelope: soft attack, sustained body, decay
        attack = np.minimum(1.0, v_t / 0.08)
        decay = np.minimum(1.0, (dur_samples / sr - v_t) / 0.12)
        env = attack * decay
        vocal_sound = vocal * env * 0.40
        
        left[start_sample:start_sample + dur_samples] += vocal_sound * 0.5
        right[start_sample:start_sample + dur_samples] += vocal_sound * 0.5

    # Master normalization
    mix = np.stack([left, right], axis=1)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = (mix / peak) * 0.90
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sf.write(output_path, mix, sr)
    print(f"[DemoGenerator] Demo track generated at {output_path} ({duration_sec}s)")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "demo_pop_ballad.wav")
    generate_demo_track(out)
