import os
import time
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, lfilter, resample_poly
from typing import Dict, Any, Tuple

def _butter_lowpass(data, cutoff, fs, order=4):
    nyq = 0.5 * fs
    norm = min(0.99, max(0.01, cutoff / nyq))
    b, a = butter(order, norm, btype='low', analog=False)
    return lfilter(b, a, data, axis=-1)

def _butter_highpass(data, cutoff, fs, order=4):
    nyq = 0.5 * fs
    norm = min(0.99, max(0.01, cutoff / nyq))
    b, a = butter(order, norm, btype='high', analog=False)
    return lfilter(b, a, data, axis=-1)

def _butter_bandpass(data, low, high, fs, order=3):
    nyq = 0.5 * fs
    lo = max(0.01, low / nyq)
    hi = min(0.99, high / nyq)
    if lo >= hi:
        return data
    b, a = butter(order, [lo, hi], btype='band', analog=False)
    return lfilter(b, a, data, axis=-1)

# ─────────────────────────────────────────────────────
# Chord / Harmony generators for genre-specific accompaniment
# ─────────────────────────────────────────────────────

# Note frequency table (A4 = 440 Hz)
def _note_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

# Common chord progressions by genre (MIDI note lists per bar)
GENRE_CHORD_PROGRESSIONS = {
    "city_pop_80s": [
        [60, 64, 67, 72],   # Cmaj7-ish
        [65, 69, 72, 76],   # Fmaj7
        [67, 71, 74, 78],   # G7
        [64, 67, 71, 74],   # Em7
    ],
    "lofi_chill_jazz": [
        [57, 60, 64, 67],   # Am7
        [62, 65, 69, 72],   # Dm7
        [67, 71, 74, 77],   # G7
        [60, 64, 67, 71],   # Cmaj7
    ],
    "cyberpunk_synthwave": [
        [57, 60, 64, 69],   # Am
        [65, 69, 72, 77],   # F
        [60, 64, 67, 72],   # C
        [67, 71, 74, 79],   # G
    ],
    "acoustic_indie_folk": [
        [60, 64, 67, 72],   # C
        [67, 71, 74, 79],   # G
        [57, 60, 64, 69],   # Am
        [65, 69, 72, 77],   # F
    ],
    "cinematic_rnb": [
        [57, 60, 64, 69],   # Am
        [55, 58, 62, 67],   # Gm
        [53, 57, 60, 65],   # Fm
        [60, 63, 67, 72],   # Cm
    ],
    "festival_edm": [
        [57, 60, 64, 69],   # Am
        [65, 69, 72, 77],   # F
        [60, 64, 67, 72],   # C
        [67, 71, 74, 79],   # G
    ],
    "k_trot_classic": [
        [60, 64, 67, 72],   # C
        [57, 60, 64, 69],   # Am
        [62, 65, 69, 74],   # Dm
        [67, 71, 74, 79],   # G7
    ],
}


def _generate_chord_pad(chord_midi, duration_sec, sr, timbre="pad"):
    """Generate a sustained chord tone layer."""
    t = np.arange(int(duration_sec * sr)) / sr
    out = np.zeros(len(t), dtype=np.float32)
    for midi_note in chord_midi:
        freq = _note_freq(midi_note)
        if timbre == "pad":
            # Warm analog pad with slow attack
            tone = np.sin(2 * np.pi * freq * t) * 0.5
            tone += np.sin(2 * np.pi * freq * 2.0 * t) * 0.2
            tone += np.sin(2 * np.pi * freq * 0.5 * t) * 0.15
            # Slow ADSR
            attack = np.minimum(1.0, t / 0.3)
            decay = np.minimum(1.0, np.maximum(0.0, (duration_sec - t) / 0.2))
            tone *= attack * decay
        elif timbre == "electric_piano":
            # DX7-like bell electric piano
            tone = np.sin(2 * np.pi * freq * t + 2.5 * np.sin(2 * np.pi * freq * 3.5 * t)) * 0.5
            tone *= np.exp(-t * 2.5)
        elif timbre == "organ":
            # Drawbar organ
            tone = (np.sin(2 * np.pi * freq * t) * 0.5 +
                    np.sin(2 * np.pi * freq * 2 * t) * 0.35 +
                    np.sin(2 * np.pi * freq * 3 * t) * 0.2 +
                    np.sin(2 * np.pi * freq * 4 * t) * 0.1)
            attack = np.minimum(1.0, t / 0.02)
            decay = np.minimum(1.0, (duration_sec - t) / 0.05)
            tone *= attack * np.maximum(0.0, decay)
        elif timbre == "acoustic_guitar":
            # Plucked string harmonic
            tone = (np.sin(2 * np.pi * freq * t) * 0.6 +
                    np.sin(2 * np.pi * freq * 2 * t) * 0.3 +
                    np.sin(2 * np.pi * freq * 3 * t) * 0.15 +
                    np.sin(2 * np.pi * freq * 5 * t) * 0.05)
            tone *= np.exp(-t * 4.0)
        elif timbre == "trot_accordion":
            # Accordion: odd harmonics with slight tremolo
            tremolo = 1.0 + 0.15 * np.sin(2 * np.pi * 5.5 * t)
            tone = (np.sin(2 * np.pi * freq * t) * 0.5 +
                    np.sin(2 * np.pi * freq * 3 * t) * 0.25 +
                    np.sin(2 * np.pi * freq * 5 * t) * 0.12)
            tone *= tremolo
            attack = np.minimum(1.0, t / 0.08)
            decay = np.minimum(1.0, (duration_sec - t) / 0.1)
            tone *= attack * np.maximum(0.0, decay)
        else:
            tone = np.sin(2 * np.pi * freq * t) * 0.4 * np.exp(-t * 3.0)
        out += tone * 0.25
    return out


def _generate_bass_line(root_midi, bpm, duration_sec, sr, style="straight"):
    """Generate a bass line synced to beat grid."""
    t_all = np.arange(int(duration_sec * sr)) / sr
    out = np.zeros(len(t_all), dtype=np.float32)
    beat_dur = 60.0 / max(40.0, bpm)
    num_beats = int(duration_sec / beat_dur) + 1
    freq = _note_freq(root_midi - 12)  # one octave lower
    
    for b in range(num_beats):
        idx = int(b * beat_dur * sr)
        if idx >= len(t_all):
            break
        
        note_len = min(int(beat_dur * 0.8 * sr), len(t_all) - idx)
        nt = np.arange(note_len) / sr
        
        if style == "slap":
            # City pop funky slap bass
            bass = np.sin(2 * np.pi * freq * nt) * 0.7
            bass += np.sin(2 * np.pi * freq * 2.0 * nt) * 0.35
            click = np.random.normal(0, 0.3, min(int(sr * 0.01), note_len))
            bass[:len(click)] += click
            bass *= np.exp(-nt * 6.0)
            if b % 2 == 1:
                bass *= 1.3  # accent offbeat
                
        elif style == "sub_808":
            # Deep 808 sub bass
            sweep = freq * (1.0 + 0.5 * np.exp(-nt * 20.0))
            bass = np.sin(2 * np.pi * sweep * nt) * 0.9
            bass *= np.exp(-nt * 3.0)
            
        elif style == "ppongjjak":
            # Trot "oom-pah" bass: root on 1,3 + fifth on 2,4
            if b % 2 == 0:
                f = freq  # root
            else:
                f = freq * 1.5  # fifth
            bass = np.sin(2 * np.pi * f * nt) * 0.7
            bass += np.sin(2 * np.pi * f * 2.0 * nt) * 0.25
            bass *= np.exp(-nt * 5.0)
            
        elif style == "fingerpick":
            bass = np.sin(2 * np.pi * freq * nt) * 0.5
            bass += np.sin(2 * np.pi * freq * 2.0 * nt) * 0.2
            bass *= np.exp(-nt * 4.0)
            if b % 4 in [0, 2]:
                bass *= 1.2
        else:
            bass = np.sin(2 * np.pi * freq * nt) * 0.6
            bass *= np.exp(-nt * 5.0)
            
        out[idx:idx + note_len] += bass * 0.55
    return out


def _generate_drum_pattern(bpm, duration_sec, sr, style="pop"):
    """Generate genre-specific drum pattern."""
    t_all = np.arange(int(duration_sec * sr)) / sr
    out = np.zeros(len(t_all), dtype=np.float32)
    beat_dur = 60.0 / max(40.0, bpm)
    beat_samples = int(beat_dur * sr)
    num_beats = int(duration_sec / beat_dur) + 1
    
    def _kick(idx, intensity=1.0):
        k_len = min(int(sr * 0.15), len(out) - idx)
        if k_len <= 0: return
        kt = np.arange(k_len) / sr
        k = np.sin(2 * np.pi * (150 * np.exp(-kt * 30) + 45) * kt) * intensity
        k *= np.exp(-kt * 12.0)
        out[idx:idx + k_len] += k * 0.65
    
    def _snare(idx, intensity=1.0):
        s_len = min(int(sr * 0.12), len(out) - idx)
        if s_len <= 0: return
        st = np.arange(s_len) / sr
        s = (np.random.normal(0, 0.35, s_len) + 
             np.sin(2 * np.pi * 200 * st) * 0.3)
        s *= np.exp(-st / 0.06) * intensity
        out[idx:idx + s_len] += s * 0.50
    
    def _hihat(idx, closed=True, intensity=1.0):
        dur = 0.03 if closed else 0.12
        h_len = min(int(sr * dur), len(out) - idx)
        if h_len <= 0: return
        ht = np.arange(h_len) / sr
        h = np.random.normal(0, 0.2, h_len)
        h = _butter_highpass(h, 6000.0, sr, order=2)
        decay = 0.015 if closed else 0.08
        h *= np.exp(-ht / decay) * intensity
        out[idx:idx + h_len] += h * 0.35
    
    sub_16th = beat_samples // 4
    
    if style == "city_pop":
        for b in range(num_beats):
            idx = b * beat_samples
            _kick(idx)
            if b % 2 == 1:
                _snare(idx, 0.9)
            # Funky 16th hi-hats with offbeat accent
            for s in range(4):
                hi_idx = idx + s * sub_16th
                accent = 1.3 if s % 2 == 1 else 0.7
                _hihat(hi_idx, closed=True, intensity=accent)
                
    elif style == "lofi_hiphop":
        # Lazy boom-bap with swing
        swing = int(sub_16th * 0.15)
        for b in range(num_beats):
            idx = b * beat_samples
            if b % 4 in [0, 2]:
                _kick(idx)
            if b % 4 in [1, 3]:
                _snare(idx + swing)
            _hihat(idx, closed=True, intensity=0.6)
            _hihat(idx + 2 * sub_16th + swing, closed=True, intensity=0.4)
    
    elif style == "four_on_floor":
        for b in range(num_beats):
            idx = b * beat_samples
            _kick(idx, 1.2)
            if b % 2 == 1:
                _snare(idx, 0.7)
            for s in range(4):
                _hihat(idx + s * sub_16th, closed=(s != 2), intensity=0.8)
    
    elif style == "ppongjjak":
        # Trot 2-beat: kick on 1, snare on 2, repeat
        for b in range(num_beats):
            idx = b * beat_samples
            if b % 2 == 0:
                _kick(idx, 1.0)
            else:
                _snare(idx, 1.0)
            # Off-beat cymbal / hi-hat with trot feel
            _hihat(idx + sub_16th * 2, closed=True, intensity=0.9)
            
    elif style == "acoustic_brush":
        for b in range(num_beats):
            idx = b * beat_samples
            # Soft cajon body
            if b % 4 in [0, 2]:
                k_len = min(int(sr * 0.08), len(out) - idx)
                if k_len > 0:
                    kt = np.arange(k_len) / sr
                    out[idx:idx+k_len] += np.sin(2*np.pi*80*kt) * np.exp(-kt*15) * 0.35
            # Shaker
            for s in range(2):
                si = idx + s * (beat_samples // 2)
                sh_len = min(int(sr * 0.04), len(out) - si)
                if sh_len > 0:
                    out[si:si+sh_len] += np.random.normal(0,0.1,sh_len) * np.exp(-np.arange(sh_len)/(sr*0.02)) * 0.25

    elif style == "synthwave":
        for b in range(num_beats):
            idx = b * beat_samples
            _kick(idx, 1.1)
            if b % 2 == 1:
                # Gated reverb snare
                s_len = min(int(sr * 0.25), len(out) - idx)
                if s_len > 0:
                    st = np.arange(s_len) / sr
                    gate = (st < 0.18).astype(float)
                    s = np.random.normal(0, 0.4, s_len) * gate
                    s += np.sin(2*np.pi*180*st) * 0.3 * gate
                    s *= np.exp(-st / 0.15)
                    out[idx:idx+s_len] += s * 0.55
            for s in range(4):
                _hihat(idx + s * sub_16th, closed=True, intensity=0.5)
    
    return out


def _generate_lead_melody(genre_id, bpm, duration_sec, sr):
    """Generate a genre-specific melodic lead instrument."""
    t_all = np.arange(int(duration_sec * sr)) / sr
    out = np.zeros(len(t_all), dtype=np.float32)
    beat_dur = 60.0 / max(40.0, bpm)
    
    if "trot" in genre_id or "k_trot" in genre_id:
        # Saxophone-like lead with vibrato (trot signature)
        melody_notes = [72, 74, 76, 79, 76, 74, 72, 71, 72, 74, 76, 79, 81, 79, 76, 74]
        note_dur = beat_dur * 0.9
        for i, midi in enumerate(melody_notes):
            idx = int(i * beat_dur * sr)
            if idx >= len(t_all): break
            n_len = min(int(note_dur * sr), len(t_all) - idx)
            nt = np.arange(n_len) / sr
            freq = _note_freq(midi)
            # Saxophone timbre: fundamental + odd harmonics + vibrato
            vibrato = 1.0 + 0.025 * np.sin(2 * np.pi * 5.8 * nt)
            sax = (np.sin(2 * np.pi * freq * vibrato * nt) * 0.5 +
                   np.sin(2 * np.pi * freq * 3 * vibrato * nt) * 0.2 +
                   np.sin(2 * np.pi * freq * 5 * vibrato * nt) * 0.08)
            attack = np.minimum(1.0, nt / 0.04)
            release = np.minimum(1.0, (note_dur - nt) / 0.06)
            sax *= attack * np.maximum(0.0, release)
            out[idx:idx+n_len] += sax * 0.35

    elif "synthwave" in genre_id or "cyberpunk" in genre_id:
        # Synth arpeggiator
        arp_notes = [57, 60, 64, 69, 72, 69, 64, 60]
        sub_16th = beat_dur / 4
        for i, midi in enumerate(arp_notes * int(duration_sec / (sub_16th * len(arp_notes)) + 1)):
            idx = int(i * sub_16th * sr)
            if idx >= len(t_all): break
            n_len = min(int(sub_16th * 0.8 * sr), len(t_all) - idx)
            nt = np.arange(n_len) / sr
            freq = _note_freq(midi)
            arp = np.sin(2 * np.pi * freq * nt + 1.5 * np.sin(2*np.pi*freq*2*nt)) * 0.4
            arp *= np.exp(-nt * 10.0)
            out[idx:idx+n_len] += arp * 0.30
            
    elif "city_pop" in genre_id:
        # Sparkly electric piano riff
        riff_notes = [72, 76, 79, 84, 79, 76, 72, 74]
        note_dur = beat_dur * 0.7
        for i, midi in enumerate(riff_notes * max(1, int(duration_sec / (beat_dur * len(riff_notes))))):
            idx = int(i * beat_dur * sr)
            if idx >= len(t_all): break
            n_len = min(int(note_dur * sr), len(t_all) - idx)
            nt = np.arange(n_len) / sr
            freq = _note_freq(midi)
            ep = np.sin(2*np.pi*freq*nt + 3.0*np.sin(2*np.pi*freq*4*nt)) * 0.4
            ep *= np.exp(-nt * 5.0)
            out[idx:idx+n_len] += ep * 0.25

    return out


def _add_vinyl_crackle(length, sr, intensity=0.012):
    noise = np.random.normal(0, intensity, length).astype(np.float32)
    pops = (np.random.random(length) > 0.9997).astype(np.float32) * np.random.uniform(-0.08, 0.08, length).astype(np.float32)
    return noise + pops


# ─────────────────────────────────────────────────────
# Vocal Processing
# ─────────────────────────────────────────────────────

def process_vocal_tone(vocal, sr, mood_style):
    """Apply vocal tone shaping based on genre mood."""
    out = vocal.copy()

    if "airy" in mood_style.lower() or "bright" in mood_style.lower() or "청아" in mood_style:
        highs = _butter_highpass(out, 8000, sr, order=2)
        out = out + highs * 0.5
        out = np.tanh(out * 1.15)

    elif "husky" in mood_style.lower() or "soul" in mood_style.lower() or "허스키" in mood_style:
        low_mids = _butter_bandpass(out, 250, 900, sr)
        out = out + low_mids * 0.4
        out = np.tanh(out * 1.3) * 0.85

    elif "synth" in mood_style.lower() or "vocoder" in mood_style.lower() or "레트로" in mood_style:
        t = np.arange(out.shape[-1]) / sr
        mod = np.sin(2 * np.pi * 2.0 * t) * 0.2
        out = out * (1.0 + mod)
        mids = _butter_bandpass(out, 500, 4000, sr)
        out = mids * 1.3

    elif "trot" in mood_style.lower() or "트로트" in mood_style or "꺾기" in mood_style:
        # Trot vocal: heavy vibrato + mid-range emphasis + slight distortion
        t = np.arange(out.shape[-1]) / sr
        # Deep vibrato (꺾기 effect)
        vibrato = 1.0 + 0.04 * np.sin(2 * np.pi * 6.0 * t)
        # Apply pitch modulation via phase
        out = out * vibrato
        # Mid-range nasal emphasis (800Hz~2.5kHz boost)
        mids = _butter_bandpass(out, 800, 2800, sr)
        out = out + mids * 0.5
        # Slight warm saturation
        out = np.tanh(out * 1.4) * 0.9

    elif "powerful" in mood_style.lower() or "파워" in mood_style:
        out = np.tanh(out * 1.5) * 0.9
        highs = _butter_highpass(out, 6000, sr, order=2)
        out = out + highs * 0.35

    else:
        # Natural / clean
        out = np.clip(out, -1.0, 1.0)

    return out


# ─────────────────────────────────────────────────────
# Main Rearrangement Engine
# ─────────────────────────────────────────────────────

GENRE_DRUM_STYLES = {
    "city_pop_80s": "city_pop",
    "lofi_chill_jazz": "lofi_hiphop",
    "cyberpunk_synthwave": "synthwave",
    "acoustic_indie_folk": "acoustic_brush",
    "cinematic_rnb": "lofi_hiphop",
    "festival_edm": "four_on_floor",
    "k_trot_classic": "ppongjjak",
}

GENRE_BASS_STYLES = {
    "city_pop_80s": "slap",
    "lofi_chill_jazz": "fingerpick",
    "cyberpunk_synthwave": "sub_808",
    "acoustic_indie_folk": "fingerpick",
    "cinematic_rnb": "sub_808",
    "festival_edm": "sub_808",
    "k_trot_classic": "ppongjjak",
}

GENRE_CHORD_TIMBRES = {
    "city_pop_80s": "electric_piano",
    "lofi_chill_jazz": "electric_piano",
    "cyberpunk_synthwave": "pad",
    "acoustic_indie_folk": "acoustic_guitar",
    "cinematic_rnb": "pad",
    "festival_edm": "organ",
    "k_trot_classic": "trot_accordion",
}


def rearrange_audio_segment(
    source_audio_path: str,
    start_sec: float,
    duration_sec: float,
    genre_params: Dict[str, Any],
    custom_lyrics: str = "",
    original_lyrics: str = "",
    output_path: str = ""
) -> Dict[str, Any]:
    """Rearrange and transform a segment into the desired genre."""
    t_start = time.time()
    sr = 44100
    info = sf.info(source_audio_path)
    file_duration = info.duration

    start_sec = max(0.0, min(start_sec, file_duration - 1.0))
    if duration_sec <= 0 or (start_sec + duration_sec) > file_duration:
        duration_sec = file_duration - start_sec

    # Load segment
    y_seg, _ = librosa.load(source_audio_path, sr=sr, offset=start_sec, duration=duration_sec, mono=True)
    length = len(y_seg)

    # ── 1. Extract melody contour from original (HPSS harmonic) ──
    y_harm, y_perc = librosa.effects.hpss(y_seg)

    # ── 2. Pitch shift the melody ──
    pitch_shift = int(genre_params.get("pitch_shift", 0))
    if pitch_shift != 0:
        y_harm = librosa.effects.pitch_shift(y_harm, sr=sr, n_steps=pitch_shift)

    # ── 3. Tempo stretch ──
    tempo_scale = float(genre_params.get("tempo_scale", 1.0))
    if abs(tempo_scale - 1.0) > 0.03:
        y_harm = librosa.effects.time_stretch(y_harm, rate=tempo_scale)
        # Align length
        if len(y_harm) > length:
            y_harm = y_harm[:length]
        elif len(y_harm) < length:
            y_harm = np.pad(y_harm, (0, length - len(y_harm)))

    # ── 4. Apply vocal tone processing to the harmonic melody ──
    vocal_mood = genre_params.get("vocal_mood", "자연스러운 보컬")
    y_vocal = process_vocal_tone(y_harm, sr, vocal_mood)
    # Ensure same length
    if len(y_vocal) != length:
        y_vocal = y_vocal[:length] if len(y_vocal) > length else np.pad(y_vocal, (0, length - len(y_vocal)))

    # ── 5. Generate NEW accompaniment from scratch ──
    genre_id = genre_params.get("id", "city_pop_80s")
    bpm = float(genre_params.get("bpm", 120.0)) * tempo_scale
    render_duration = length / sr

    # 5a. Chord pad / harmony layer
    chords = GENRE_CHORD_PROGRESSIONS.get(genre_id, GENRE_CHORD_PROGRESSIONS["city_pop_80s"])
    timbre = GENRE_CHORD_TIMBRES.get(genre_id, "pad")
    beat_dur = 60.0 / max(40, bpm)
    bar_dur = beat_dur * 4
    num_bars = int(render_duration / bar_dur) + 1
    
    chord_layer = np.zeros(length, dtype=np.float32)
    for bar_i in range(num_bars):
        chord = chords[bar_i % len(chords)]
        bar_start = int(bar_i * bar_dur * sr)
        bar_len_samples = min(int(bar_dur * sr), length - bar_start)
        if bar_start >= length or bar_len_samples <= 0:
            break
        pad_audio = _generate_chord_pad(chord, bar_dur, sr, timbre=timbre)
        actual_len = min(bar_len_samples, len(pad_audio))
        chord_layer[bar_start:bar_start + actual_len] += pad_audio[:actual_len]

    # 5b. Bass line
    bass_style = GENRE_BASS_STYLES.get(genre_id, "straight")
    bass_layer = np.zeros(length, dtype=np.float32)
    for bar_i in range(num_bars):
        chord = chords[bar_i % len(chords)]
        root_note = chord[0]
        bar_start = int(bar_i * bar_dur * sr)
        bar_len_sec = min(bar_dur, (length - bar_start) / sr)
        if bar_start >= length or bar_len_sec <= 0:
            break
        bass = _generate_bass_line(root_note, bpm, bar_len_sec, sr, style=bass_style)
        actual_len = min(len(bass), length - bar_start)
        bass_layer[bar_start:bar_start + actual_len] += bass[:actual_len]

    # 5c. Drum pattern
    drum_style = GENRE_DRUM_STYLES.get(genre_id, "pop")
    drum_layer = _generate_drum_pattern(bpm, render_duration, sr, style=drum_style)
    if len(drum_layer) > length:
        drum_layer = drum_layer[:length]
    elif len(drum_layer) < length:
        drum_layer = np.pad(drum_layer, (0, length - len(drum_layer)))

    # 5d. Lead melody instrument
    lead_layer = _generate_lead_melody(genre_id, bpm, render_duration, sr)
    if len(lead_layer) > length:
        lead_layer = lead_layer[:length]
    elif len(lead_layer) < length:
        lead_layer = np.pad(lead_layer, (0, length - len(lead_layer)))

    # 5e. Genre-specific texture
    texture_layer = np.zeros(length, dtype=np.float32)
    if "lofi" in genre_id:
        texture_layer = _add_vinyl_crackle(length, sr, intensity=0.015)

    # ── 6. MIX: dramatically emphasize NEW genre layers, reduce original ──
    # Original melody/vocal: 25% (just enough to carry the tune)
    # New accompaniment: 75% (the genre transformation)
    mix_mono = (
        y_vocal * 0.30 +        # processed vocal/melody from original
        chord_layer * 0.50 +     # new genre chord pad
        bass_layer * 0.55 +      # new genre bass
        drum_layer * 0.60 +      # new genre drums
        lead_layer * 0.45 +      # new genre lead instrument
        texture_layer * 0.20     # texture/crackle
    )

    # ── 7. Normalize to prevent clipping ──
    peak = np.max(np.abs(mix_mono))
    if peak > 0.001:
        mix_mono = (mix_mono / peak) * 0.85
    else:
        # If somehow silent, generate a tone to indicate something happened
        t = np.arange(length) / sr
        mix_mono = np.sin(2 * np.pi * 440 * t) * 0.3

    # ── 8. Convert to stereo with slight width ──
    # Slight stereo spread: pan drums/bass center, chords/lead slightly wide
    left = mix_mono.copy()
    right = mix_mono.copy()
    # Add subtle stereo difference from chord and lead layers
    left += chord_layer * 0.08
    right -= chord_layer * 0.08
    left -= lead_layer * 0.06
    right += lead_layer * 0.06

    stereo = np.stack([left, right], axis=0)
    # Final stereo normalization
    peak_s = np.max(np.abs(stereo))
    if peak_s > 0.001:
        stereo = (stereo / peak_s) * 0.88

    # Active lyrics
    active_lyrics = custom_lyrics.strip() if custom_lyrics.strip() else original_lyrics.strip()
    lyrics_source = "custom" if custom_lyrics.strip() else "original"

    elapsed = round(time.time() - t_start, 2)
    print(f"[Arranger] Segment transformed ({duration_sec:.1f}s) in {elapsed}s for genre: {genre_id}")

    return {
        "audio_data": stereo,
        "sample_rate": sr,
        "duration_rendered": round(stereo.shape[1] / sr, 2),
        "start_sec": start_sec,
        "active_lyrics": active_lyrics,
        "lyrics_source": lyrics_source,
        "genre_id": genre_id,
        "genre_name": genre_params.get("name", ""),
        "vocal_mood": vocal_mood,
        "process_time_sec": elapsed
    }
