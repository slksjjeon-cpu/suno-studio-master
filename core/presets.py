import json
import os
from typing import Dict, List, Any

PRESETS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "presets.json")

DEFAULT_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "city_pop_80s",
        "name": "시티팝 (80s City Pop)",
        "icon": "🌴",
        "description": "세련된 펑키 베이스, 레트로 신스 브라스, 청량한 80년대 일본/한국 시티팝 그루브",
        "prompt": "80s retro Japanese City Pop, funky slap bass, sparkling DX7 electric piano, nostalgic brass hits, driving drum groove, breezy summer night vibe",
        "tempo_scale": 1.05,
        "pitch_shift": 0,
        "instrumentation": "slap_bass, electric_piano, brass_synth, funk_drums",
        "vocal_mood": "청아하고 세련된 80s 팝 보컬 (Airy & Bright)",
        "mastering_preset": "modern_crisp",
        "is_custom": False
    },
    {
        "id": "lofi_chill_jazz",
        "name": "로파이 칠 재즈 (Lo-Fi Chill Jazz)",
        "icon": "☕",
        "description": "따뜻한 로즈 피아노, 어쿠스틱 콘트라베이스, 비닐 잡음과 칠한 비트",
        "prompt": "Cozy lofi chillhop jazz, warm Rhodes keys, smoky upright bass, mellow brushed swing drums, subtle vinyl crackle, nostalgic cafe atmosphere",
        "tempo_scale": 0.85,
        "pitch_shift": -1,
        "instrumentation": "rhodes, upright_bass, vinyl_lofi, brush_drums",
        "vocal_mood": "나른하고 감미로운 허스키 재즈 톤 (Husky & Intimate)",
        "mastering_preset": "warm_vintage",
        "is_custom": False
    },
    {
        "id": "cyberpunk_synthwave",
        "name": "사이버펑크 신스웨이브 (Synthwave / Retrowave)",
        "icon": "⚡",
        "description": "질주하는 아날로그 아르페지오, 강력한 808 킥, 네온 도시의 레트로 퓨처 사운드",
        "prompt": "High-octane cyberpunk synthwave, driving analog bass arpeggiator, gated reverb snare, powerful 808 kicks, neon futuristic synth lead, 128 bpm",
        "tempo_scale": 1.15,
        "pitch_shift": 0,
        "instrumentation": "analog_arp, gated_snare, heavy_808, retro_lead",
        "vocal_mood": "공간감 넘치는 레트로 신스 보컬 (Reverb & Vocoder Touch)",
        "mastering_preset": "club_punchy",
        "is_custom": False
    },
    {
        "id": "acoustic_indie_folk",
        "name": "어쿠스틱 인디 포크 (Acoustic Folk)",
        "icon": "🎸",
        "description": "따뜻한 통기타 핑거피킹, 잔잔한 카혼 리듬, 자연스럽고 서정적인 사운드",
        "prompt": "Warm organic indie acoustic folk, fingerpicked steel string guitars, gentle cajon percussion, resonant cello swells, intimate wooden room acoustic",
        "tempo_scale": 0.95,
        "pitch_shift": 0,
        "instrumentation": "acoustic_guitar, cello, cajon, ambient_room",
        "vocal_mood": "맑고 꾸밈없는 담백한 어쿠스틱 보컬 (Pure & Natural)",
        "mastering_preset": "acoustic_natural",
        "is_custom": False
    },
    {
        "id": "cinematic_rnb",
        "name": "시네마틱 네오 소울 R&B (Neo-Soul R&B)",
        "icon": "🌙",
        "description": "묵직한 808 서브 베이스, 그루비한 하이햇 트랩 비트, 몽환적인 일렉트릭 피아노",
        "prompt": "Dark sultry cinematic neo-soul R&B, deep 808 sub bass, crisp rolling hi-hats, reverb-washed jazz chords, sensual midnight slow jam",
        "tempo_scale": 0.90,
        "pitch_shift": -2,
        "instrumentation": "sub_bass, trap_percussion, lush_pads, electric_piano",
        "vocal_mood": "소울풀하고 끈적한 그루브 보컬 (Deep Soul & Velvet)",
        "mastering_preset": "club_punchy",
        "is_custom": False
    },
    {
        "id": "festival_edm",
        "name": "페스티벌 EDM (Bigroom / Future Bass)",
        "icon": "🔥",
        "description": "폭발적인 슈퍼쏘우 드롭, 사이드체인 펌핑, 페스티벌 앤섬 스타일",
        "prompt": "Huge festival EDM future bass, wide detuned supersaw chords, massive sidechain pumping, energetic build-up, punchy electronic drums",
        "tempo_scale": 1.20,
        "pitch_shift": 2,
        "instrumentation": "supersaw, sidechain_lead, edm_drop, riser",
        "vocal_mood": "파워풀하고 시원한 페스티벌 팝 보컬 (Powerful & Bright)",
        "mastering_preset": "club_punchy",
        "is_custom": False
    },
    {
        "id": "k_trot_classic",
        "name": "정통 한국 트로트 (K-Trot)",
        "icon": "🎤",
        "description": "꺾기와 바이브레이션이 살아있는 정통 한국 트로트. 뽕짝 리듬, 색소폰, 아코디언, 신디사이저 트럼펫 반주",
        "prompt": "Traditional Korean Trot ppongjjak rhythm, bouncy oom-pah bass, saxophone melody, accordion fills, synth trumpet, dramatic vibrato vocal, festive Korean enka style, 2-beat rhythm pattern",
        "tempo_scale": 1.10,
        "pitch_shift": 0,
        "instrumentation": "ppongjjak_bass, saxophone, accordion, synth_trumpet, trot_drums",
        "vocal_mood": "트로트 꺾기와 바이브레이션이 깊은 정통 트로트 보컬 (Trot Vibrato & Kkeokkgi)",
        "mastering_preset": "modern_crisp",
        "is_custom": False
    }
]

DEFAULT_MASTERING_PRESETS = [
    {
        "id": "modern_crisp",
        "name": "모던 크리스프 (Streaming Standard)",
        "description": "선명한 고음역, 단단한 저음, 스포티파이/유튜브 권장 음압 (-14 LUFS)",
        "target_lufs": -14.0,
        "eq_profile": "crisp",
        "stereo_width": 1.25,
        "limiter_ceiling_db": -0.3
    },
    {
        "id": "club_punchy",
        "name": "클럽 & 펀치 (High Loudness & Bass)",
        "description": "단단한 킥/베이스 타격감, 높은 음압 (-9 LUFS), 클럽/댄스 최적화",
        "target_lufs": -9.5,
        "eq_profile": "punchy_bass",
        "stereo_width": 1.35,
        "limiter_ceiling_db": -0.1
    },
    {
        "id": "warm_vintage",
        "name": "웜 빈티지 (Warm Tape & Vinyl)",
        "description": "부드러운 아날로그 테이프 포화감, 자극 없는 고역대, 자연스러운 다이내믹스 (-16 LUFS)",
        "target_lufs": -16.0,
        "eq_profile": "warm_low",
        "stereo_width": 1.10,
        "limiter_ceiling_db": -0.5
    },
    {
        "id": "acoustic_natural",
        "name": "어쿠스틱 내추럴 (High Dynamic Range)",
        "description": "과도한 압축 없이 원음의 숨소리와 악기 울림을 최대한 살린 자연스러운 마스터링 (-15 LUFS)",
        "target_lufs": -15.0,
        "eq_profile": "flat_transparent",
        "stereo_width": 1.15,
        "limiter_ceiling_db": -0.8
    }
]


def load_presets() -> List[Dict[str, Any]]:
    """Load presets combining default ones and custom user saved presets."""
    if not os.path.exists(PRESETS_FILE):
        save_presets(DEFAULT_PRESETS)
        return DEFAULT_PRESETS
    
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"[Presets] Error reading presets file: {e}")
        return DEFAULT_PRESETS


def save_presets(presets: List[Dict[str, Any]]) -> bool:
    """Save preset list to disk."""
    try:
        os.makedirs(os.path.dirname(PRESETS_FILE), exist_ok=True)
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Presets] Error saving presets: {e}")
        return False


def add_custom_preset(preset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new custom preset."""
    presets = load_presets()
    import time
    custom_id = f"custom_{int(time.time())}"
    new_preset = {
        "id": custom_id,
        "name": preset_data.get("name", "커스텀 프리셋"),
        "icon": preset_data.get("icon", "🎵"),
        "description": preset_data.get("description", "사용자 정의 프리셋"),
        "prompt": preset_data.get("prompt", ""),
        "tempo_scale": float(preset_data.get("tempo_scale", 1.0)),
        "pitch_shift": int(preset_data.get("pitch_shift", 0)),
        "instrumentation": preset_data.get("instrumentation", "custom"),
        "vocal_mood": preset_data.get("vocal_mood", "자연스러운 보컬"),
        "mastering_preset": preset_data.get("mastering_preset", "modern_crisp"),
        "is_custom": True
    }
    presets.append(new_preset)
    save_presets(presets)
    return new_preset


def delete_custom_preset(preset_id: str) -> bool:
    """Delete a custom preset by ID."""
    presets = load_presets()
    filtered = [p for p in presets if not (p["id"] == preset_id and p.get("is_custom", False))]
    if len(filtered) != len(presets):
        save_presets(filtered)
        return True
    return False
