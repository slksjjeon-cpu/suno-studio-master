"""
음악 유사성 참고 진단 엔진 (비공식, Non-official Reference Check)
- 공식 YouTube Content ID 조회가 아니며 저작권 판정/수익화 가능성을 보장하지 않습니다.
- Shazamio(비공식) 음향 인식, faster-whisper 가사 전사, Apple iTunes 검색 기반 후보 탐색을 조합합니다.
- 검사 엔진이 없거나 오류가 나면 결과를 SAFE로 바꾸지 않고 UNVERIFIED(검사 미완료)로 표시합니다.
- 단일 쿼리 우연 일치와 흔한 한국어 클리셰는 오탐 방지를 위해 제외합니다.
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import re
import json
import time
import asyncio
import tempfile
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple, Set

import soundfile as sf
import numpy as np

try:
    from shazamio import Shazam
    HAS_SHAZAM = True
except ImportError:
    HAS_SHAZAM = False

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

# Common Korean lyric cliches that must NEVER trigger a false-positive cover match
COMMON_CLICHES = {
    "사랑해", "사랑해요", "사랑했는지", "사랑하는", "사랑이란", "사랑", "내사랑",
    "눈물이", "눈물이흘러", "눈물이나", "눈물", "기억해", "기억해요", "기억", "추억",
    "그대여", "그대가", "그대의", "그대를", "너를위해", "너에게", "너를", "너의",
    "어디에", "언제나", "영원히", "함께해", "시간이", "바람이", "하늘을", "하늘",
    "어두운", "빛나는", "미안해", "행복해", "떠나가지마", "보고싶어", "보고싶다",
    "꿈속에", "마음이", "가슴이", "아파", "안녕", "오늘도", "내일도", "그날", "그때"
}

# Global persistent Whisper model cache to avoid reloading overhead
_CACHED_WHISPER_MODEL = None


def get_whisper_model() -> Optional[Any]:
    global _CACHED_WHISPER_MODEL
    if not HAS_WHISPER:
        return None
    if _CACHED_WHISPER_MODEL is None:
        try:
            _CACHED_WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as e:
            print(f"[CopyrightChecker] Whisper load error: {e}")
            return None
    return _CACHED_WHISPER_MODEL


def extract_audio_if_video(file_path: str) -> str:
    """If file is video (.mp4, .mkv, .mov), extract audio to a temp wav."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".mp4", ".mkv", ".mov", ".webm", ".avi"]:
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav.close()
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            tmp_wav.name
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return tmp_wav.name
        except Exception:
            return file_path
    return file_path


async def _run_shazam_recognition(audio_path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Runs Shazamio recognition with an 8s timeout.

    Returns (result, status) where status is one of:
    "matched", "no_match", "unavailable", "timeout", "error".
    """
    if not HAS_SHAZAM:
        return None, "unavailable"
    try:
        shazam = Shazam()
        res = await asyncio.wait_for(shazam.recognize(audio_path), timeout=8.0)
        if res and "track" in res:
            return res, "matched"
        return None, "no_match"
    except asyncio.TimeoutError:
        print("[CopyrightChecker] Shazam recognition timed out (8s)")
        return None, "timeout"
    except Exception as e:
        print(f"[CopyrightChecker] Shazam recognition error: {e}")
        return None, "error"


def _extract_lyrics_sync(audio_path: str) -> Tuple[List[str], str, str]:
    """Extracts lyrics from up to 45 seconds of audio using faster-whisper.

    Returns (lines, language, status) where status is one of:
    "ok", "no_speech", "unavailable", "error".
    """
    if not HAS_WHISPER or not HAS_LIBROSA:
        return [], "ko", "unavailable"

    model = get_whisper_model()
    if not model:
        return [], "ko", "error"

    try:
        y, _ = librosa.load(audio_path, sr=16000, mono=True, offset=5.0, duration=45.0)
        if len(y) < 16000 * 3:
            return [], "ko", "no_speech"

        segments, info = model.transcribe(y, beam_size=1)
        lang = getattr(info, "language", "ko")

        lines = []
        for s in segments:
            t = s.text.strip()
            # Clean punctuation
            clean_t = re.sub(r'^[^\w가-힣a-zA-Z0-9]+|[^\w가-힣a-zA-Z0-9]+$', '', t).strip()
            if len(clean_t) >= 3 and not re.match(r'^(yeah|la|oh|baby|ah|uh|hey|wow|woo|음|아|오|예|라)+$', clean_t, re.I):
                lines.append(clean_t)

        return lines, lang, ("ok" if lines else "no_speech")
    except Exception as e:
        print(f"[CopyrightChecker] Whisper lyrics extraction error: {e}")
        return [], "ko", "error"


def _search_itunes_music(query: str, limit: int = 4) -> Tuple[List[Dict[str, Any]], bool]:
    """Searches Apple iTunes Search API for commercially published music candidates.

    Returns (results, request_ok). request_ok is False when the catalog could not
    actually be queried (network/API failure), so callers never mistake a failed
    request for a clean "no match" result.
    """
    results = []
    try:
        clean_q = re.sub(r'[\r\n\t]+', ' ', query).strip()
        if not clean_q or len(clean_q) < 2:
            return [], False
        encoded = urllib.parse.quote(clean_q)
        url = f"https://itunes.apple.com/search?term={encoded}&entity=song&limit={limit}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for item in data.get('results', []):
                results.append({
                    "title": item.get('trackName', ''),
                    "artist": item.get('artistName', ''),
                    "album": item.get('collectionName', 'Single'),
                    "genre": item.get('primaryGenreName', 'Pop'),
                    "cover_art": item.get('artworkUrl100', '').replace('100x100bb', '600x600bb'),
                    "external_url": item.get('trackViewUrl', ''),
                    "preview_url": item.get('previewUrl', '')
                })
        return results, True
    except Exception as e:
        print(f"[CopyrightChecker] iTunes search error for query '{query}': {e}")
        return [], False


def _calculate_cover_match_score(
    candidate: Dict[str, Any],
    matched_queries: Set[str],
    transcribed_lines: List[str],
    title_hint: Optional[str]
) -> Tuple[int, List[str]]:
    """
    Bulletproof multi-factor scoring (0 to 100 points).
    Strictly eliminates false positives from common words or random single-query hits.
    Threshold: 60 points required to confirm copyright match.
    """
    track_title = candidate.get("title", "")
    artist_name = candidate.get("artist", "")

    clean_cand_title = re.sub(r'[^가-힣a-zA-Z0-9]', '', track_title).lower()
    clean_title_hint = re.sub(r'[^가-힣a-zA-Z0-9]', '', title_hint or '').lower()

    # Rule 1: Ignore candidates whose titles are just common cliches (e.g. '사랑', '눈물')
    clean_korean_title = re.sub(r'[^가-힣]', '', clean_cand_title)
    if clean_korean_title in COMMON_CLICHES:
        return 0, ["기성곡 제목이 흔한 일상 관용구(Cliche)이므로 오탐 방지 제외"]

    # Rule 2: Title Match Analysis
    title_hit = False
    reasons = []
    score = 0

    if clean_title_hint and len(clean_title_hint) >= 2:
        if clean_cand_title in clean_title_hint or clean_title_hint in clean_cand_title:
            score += 45
            title_hit = True
            reasons.append(f"곡 제목 힌트('{title_hint}')와 기성곡명('{track_title}') 일치")
        else:
            # Check meaningful non-cliche sub-tokens
            tokens_hint = [t for t in re.findall(r'[가-힣a-zA-Z0-9]{3,}', clean_title_hint) if t not in COMMON_CLICHES]
            for tok in tokens_hint:
                if tok in clean_cand_title:
                    score += 35
                    title_hit = True
                    reasons.append(f"곡 제목 고유 핵심어('{tok}')와 기성곡명('{track_title}') 일치")
                    break

    # Rule 3: Single-query hits WITHOUT title hit are ALWAYS REJECTED
    # (Completely blocks false-positives like SHINee or random unrelated songs)
    q_count = len(matched_queries)
    if not title_hit and q_count < 2:
        return 0, ["독립 쿼리 합의 부족 및 제목 불일치 (우연 일치 기각)"]

    # Rule 4: Multi-Query Independent Consensus
    if q_count >= 3:
        score += 35
        reasons.append(f"3개 이상 독립 구절 교차 합의 ({q_count}개 쿼리)")
    elif q_count == 2:
        score += 25
        reasons.append(f"2개 독립 구절 교차 합의 ({q_count}개 쿼리)")

    # Rule 5: Direct Distinctive Title Sung in Lyrics (Only non-cliche titles with >= 4 chars)
    if not title_hit and clean_cand_title and len(clean_cand_title) >= 4 and clean_korean_title not in COMMON_CLICHES:
        for line in transcribed_lines:
            clean_l = re.sub(r'[^가-힣a-zA-Z0-9]', '', line).lower()
            if clean_cand_title in clean_l:
                score += 30
                reasons.append(f"가사에서 고유 곡명('{track_title}') 가창 감지")
                break

    return score, reasons


def _detect_cover_song_from_lyrics_and_title(
    lyrics_lines: List[str], title_hint: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Reference-only similarity analysis on transcribed lyrics & title hints.

    Returns (match_or_none, meta). meta["status"] is one of:
    "matched", "no_match", "no_query", "error". A failed catalog query is reported
    as "error" rather than being treated as a clean no-match.
    """
    candidate_queries = []

    # 1. Clean title hint (e.g. "모아 - 당신은모르실까.mp3" -> "당신은모르실까")
    clean_title = None
    if title_hint:
        t_sub = title_hint
        if ' - ' in t_sub:
            t_sub = t_sub.split(' - ', 1)[1]
        t_sub = re.sub(r'^\d+_|[\[\(].*?[\]\)]|\.mp3|\.wav|\.m4a', '', t_sub).strip()
        t_sub = re.sub(r'커버|리메이크|cover|remake|acoustic|ver|suno|draft|remastered', '', t_sub, flags=re.I).strip()
        if len(t_sub) >= 2:
            clean_title = t_sub

    # 2. Prioritize clean title query if available
    if clean_title:
        candidate_queries.append(clean_title)

    # 3. Select meaningful Korean/distinct lyric lines (Filter out pure cliches)
    korean_lines = [l for l in lyrics_lines if re.search(r'[가-힣]', l)]
    target_lines = korean_lines if korean_lines else lyrics_lines

    for l in target_lines[:3]:
        cl = l.strip()
        clean_only_kor = re.sub(r'[^가-힣]', '', cl)
        # Skip trivial single-word cliches
        if len(cl) >= 4 and clean_only_kor not in COMMON_CLICHES:
            if cl not in candidate_queries:
                candidate_queries.append(cl[:50])

    if not candidate_queries:
        return None, {"status": "no_query", "queries": 0, "requests_ok": 0}

    # 4. Query iTunes with strict per-query attribution
    votes: Dict[str, Dict[str, Any]] = {}
    requests_ok = 0
    for q in candidate_queries:
        if not q or len(q.strip()) < 2:
            continue
        items, ok = _search_itunes_music(q, limit=4)
        if ok:
            requests_ok += 1
        for song in items:
            key = f"{song['title']}___{song['artist']}".lower()
            if key not in votes:
                votes[key] = {
                    "song": song,
                    "matched_queries": set()
                }
            votes[key]["matched_queries"].add(q)

    meta = {
        "status": "no_match" if requests_ok > 0 else "error",
        "queries": len(candidate_queries),
        "requests_ok": requests_ok
    }

    if not votes:
        return None, meta

    # 5. Score every candidate and enforce strict 60-point gate
    scored_candidates = []
    for cand_info in votes.values():
        song = cand_info["song"]
        q_set = cand_info["matched_queries"]
        score, reasons = _calculate_cover_match_score(song, q_set, lyrics_lines, clean_title)
        if score >= 60:  # Strict anti-false-positive threshold
            scored_candidates.append({
                "score": score,
                "reasons": reasons,
                "song": song,
                "matched_queries": list(q_set)
            })

    if not scored_candidates:
        # None passed the strict threshold -> no confident reference candidate
        return None, meta

    # Pick the highest-scoring candidate
    best = sorted(scored_candidates, key=lambda x: x["score"], reverse=True)[0]
    best_song = best["song"]
    primary_query = best["matched_queries"][0] if best["matched_queries"] else (clean_title or lyrics_lines[0])

    confidence_level = "HIGH" if best["score"] >= 75 else "MEDIUM"
    meta["status"] = "matched"

    return {
        "matched": True,
        "match_type": "COVER_COMPOSITION",
        "confidence": confidence_level,
        "match_score": best["score"],
        "detected_lyrics": primary_query,
        "match_reasons": best["reasons"],
        "all_transcribed_lyrics": "\n".join(lyrics_lines[:6]),
        "track_info": best_song
    }, meta


def analyze_audio_properties(audio_path: str) -> Dict[str, Any]:
    """Extract acoustic metrics: duration, sample rate, peak, RMS, LUFS, clipping, and musical key."""
    duration = 0.0
    sr = 44100
    peak_db = 0.0
    est_lufs = -14.0
    crest_factor = 2.0
    clipping = False
    bpm = 120
    key_str = "C Major"

    try:
        data, sr = sf.read(audio_path, frames=int(44100 * 30), always_2d=True)
        try:
            info = sf.info(audio_path)
            duration = info.duration
        except Exception:
            duration = len(data) / sr

        peak = float(np.max(np.abs(data))) if len(data) > 0 else 0.0
        rms = float(np.sqrt(np.mean(data**2))) if len(data) > 0 else 0.0
        crest_factor = (peak / (rms + 1e-9)) if rms > 0 else 1.0
        est_lufs = -0.691 + 10 * np.log10(rms**2 + 1e-9)
        peak_db = 20 * np.log10(max(peak, 1e-5))
        clipping = peak >= 0.999
    except Exception as e:
        print(f"[CopyrightChecker] Soundfile read error: {e}")

    # Librosa quick BPM & Key estimate
    if HAS_LIBROSA:
        try:
            y, sr_lb = librosa.load(audio_path, sr=22050, mono=True, duration=25.0)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr_lb)
            bpm = int(round(float(np.atleast_1d(tempo)[0])))

            chroma = librosa.feature.chroma_cqt(y=y, sr=sr_lb)
            chroma_mean = np.mean(chroma, axis=1)
            notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            key_idx = int(np.argmax(chroma_mean))
            key_str = f"{notes[key_idx]} Major"
        except Exception as e:
            pass

    return {
        "duration": round(duration, 2),
        "sample_rate": sr,
        "peak_db": round(peak_db, 1),
        "est_lufs": round(est_lufs, 1),
        "crest_factor": round(crest_factor, 2),
        "clipping_detected": clipping,
        "bpm": bpm,
        "key": key_str
    }


def check_youtube_copyright_sync(file_path: str, song_title: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous wrapper for the non-official music similarity reference check."""
    return asyncio.run(check_youtube_copyright(file_path, song_title))


async def check_youtube_copyright(file_path: str, song_title: Optional[str] = None) -> Dict[str, Any]:
    """
    비공식 음악 유사성 참고 진단.

    - Shazamio(비공식) 음향 인식 + Apple iTunes 카탈로그 검색 + 선택적 Whisper 가사 전사를 사용합니다.
    - 엔진이 없거나 실패하면 UNVERIFIED를 반환하며 SAFE로 대체하지 않습니다.
    - 공식 YouTube Content ID 조회/법적 판정/수익화 보장이 아닙니다.
    """
    if not os.path.exists(file_path):
        return {
            "ok": False,
            "error": f"파일을 찾을 수 없습니다: {file_path}"
        }

    clean_path = extract_audio_if_video(file_path)
    is_temp_extracted = (clean_path != file_path)

    # Derive song title hint from filename if not provided
    effective_title = song_title
    if not effective_title:
        base_name = os.path.basename(file_path)
        effective_title = re.sub(r'^\d+_|[\[\(].*?[\]\)]|\.mp3|\.wav|\.m4a', '', base_name).strip()

    try:
        # Step 1: Acoustic Properties & Dynamic Range
        acoustic = analyze_audio_properties(clean_path)

        # Step 2: Master Sound Recording Fingerprint Scan (Shazamio, unofficial)
        shazam_res, shazam_status = await _run_shazam_recognition(clean_path)

        matched_sound_recording = False
        track_info = {}

        if shazam_res and "track" in shazam_res:
            track = shazam_res["track"]
            matched_sound_recording = True

            title = track.get("title", "알 수 없는 곡명")
            artist = track.get("subtitle", "알 수 없는 아티스트")
            genres = track.get("genres", {}).get("primary", "일반 음악")
            album_name = None
            label = None

            for sec in track.get("sections", []):
                if sec.get("type") == "SONG":
                    for meta in sec.get("metadata", []):
                        if meta.get("title") == "Album":
                            album_name = meta.get("text")
                        elif meta.get("title") == "Label":
                            label = meta.get("text")

            images = track.get("images", {})
            cover_art = images.get("coverart") or images.get("coverarthq") or images.get("background")
            share_url = track.get("url") or track.get("share", {}).get("href")

            track_info = {
                "title": title,
                "artist": artist,
                "album": album_name or "Single",
                "label": label or "Commercial Record Label",
                "genre": genres,
                "cover_art": cover_art,
                "external_url": share_url
            }

        # Step 3: Lyrics transcription + catalog reference search
        lyrics_lines = []
        detected_lang = "ko"
        lyrics_lines, detected_lang, lyrics_status = await asyncio.to_thread(
            _extract_lyrics_sync, clean_path
        )

        lyrics_cover_result = None
        comp_meta = {"status": "no_query", "queries": 0, "requests_ok": 0}
        if lyrics_lines or effective_title:
            lyrics_cover_result, comp_meta = await asyncio.to_thread(
                _detect_cover_song_from_lyrics_and_title, lyrics_lines, effective_title
            )

        # Step 4: Multi-Layer Decision Matrix
        matched = False
        match_category = "NONE"  # "SOUND_RECORDING", "COVER_COMPOSITION", "NONE"
        detected_lyrics_snippet = None

        if matched_sound_recording:
            matched = True
            match_category = "SOUND_RECORDING"
        elif lyrics_cover_result and lyrics_cover_result.get("matched"):
            matched = True
            match_category = "COVER_COMPOSITION"
            track_info = lyrics_cover_result["track_info"]
            detected_lyrics_snippet = lyrics_cover_result.get("detected_lyrics")

        # Step 5: Verification coverage + risk label (no SAFE guarantee)
        sound_checked = shazam_status in ("matched", "no_match")
        comp_checked = comp_meta.get("status") in ("matched", "no_match")
        coverage_pct = int(round(((1 if sound_checked else 0) + (1 if comp_checked else 0)) / 2.0 * 100))

        checks = [
            {
                "id": "sound_recording",
                "label": "음향 지문 인식 (Shazam, 비공식)",
                "status": shazam_status,
                "checked": sound_checked,
            },
            {
                "id": "composition_catalog",
                "label": "작곡/가사 카탈로그 검색 (iTunes)",
                "status": comp_meta.get("status", "no_query"),
                "checked": comp_checked,
                "queries": comp_meta.get("queries", 0),
                "requests_ok": comp_meta.get("requests_ok", 0),
            },
            {
                "id": "lyrics_transcription",
                "label": "가사 전사 (faster-whisper, 선택)",
                "status": lyrics_status,
                "checked": lyrics_status == "ok",
            },
        ]

        if match_category == "SOUND_RECORDING":
            risk_level = "CRITICAL"
            risk_label = "🚨 음향 지문 일치 (위험 신호)"
            color = "#ef4444"
            monetization = "권리자 허가 없이 업로드하면 Content ID 클레임/차단 가능성이 높습니다. 공식 YouTube 도구와 권리자에게 확인하세요."
            claim_probability = "음향 지문 일치 (공식 Content ID 조회 아님)"
            verdict = (
                f"비공식 음악 인식(Shazam)에서 상용 음원 '{track_info['title']}' - {track_info['artist']}와 "
                f"음향 지문이 일치했습니다. 이는 참고용 결과이며 공식 Content ID 판정이 아닙니다."
            )
            recommendations = [
                "🚨 원곡의 사용 권한/라이선스를 먼저 확인하고, 허가 없이 업로드하지 마세요.",
                "🏢 공식 YouTube Content ID 도구 또는 원권리자(레이블/출판사)에게 직접 확인하세요.",
                "ℹ️ 이 결과는 Shazam(비공식) 인식 기반이며 법적 판정이나 수익화 보장이 아닙니다.",
            ]

        elif match_category == "COVER_COMPOSITION":
            risk_level = "HIGH"
            risk_label = "⚠️ 유사 후보 감지 (추가 확인 필요)"
            color = "#f97316"
            monetization = "작곡/작사 권리자와 커버 라이선스를 확인해야 합니다. 수익화 가능 여부는 공식 절차로만 확인할 수 있습니다."
            claim_probability = "가사/제목 기반 유사 후보 (자동 확정 아님)"
            snippet_str = f" [검색 근거: \"{detected_lyrics_snippet}\"]" if detected_lyrics_snippet else ""
            verdict = (
                f"가사/제목 검색에서 상용곡 '{track_info['title']}' - {track_info['artist']}와 "
                f"유사한 후보가 감지되었습니다.{snippet_str} 실제 커버/편곡 여부와 권리 관계는 추가 확인이 필요합니다."
            )
            recommendations = [
                "⚠️ 원곡의 작곡/작사 권리자(출판사)와 커버 라이선스 적용 여부를 확인하세요.",
                "💡 YouTube 커버곡 수익 공유 프로그램 대상인지 공식 정책을 확인하세요.",
                "ℹ️ 이 결과는 제목/가사 기반 참고 진단이며 멜로디 지문을 공식 검증한 것이 아닙니다.",
            ]

        elif coverage_pct >= 100:
            risk_level = "NO_MATCH"
            risk_label = "ℹ️ 검사 범위 내 일치 항목 없음 (공식 판정 아님)"
            color = "#38bdf8"
            monetization = "검사 범위 내에서는 위험 신호가 발견되지 않았습니다. 다만 공식 Content ID 조회가 아니므로 수익화/안전을 보장하지 않습니다."
            claim_probability = "검사 범위 내 미일치 (공식 Content ID 조회 아님)"
            verdict = (
                "비공식 음향 인식과 작곡/가사 카탈로그 검색에서 일치 항목이 발견되지 않았습니다. "
                "이는 참고 진단이며 100% 안전을 의미하지 않습니다. 업로드 전 공식 YouTube 저작권 도구로 추가 확인하세요."
            )
            recommendations = [
                "✅ 검사 범위 내 일치 항목은 없었지만, 공식 Content ID 판정이 아니므로 '안전 보장'으로 해석하지 마세요.",
                "🔎 업로드 전 YouTube 저작권 도구와 원권리자 정보를 추가로 확인하세요.",
                f"🔊 현재 추정 음량: {acoustic.get('est_lufs', -14)} LUFS (스트리밍 권장 -14 LUFS 내외).",
            ]

        else:
            risk_level = "UNVERIFIED"
            risk_label = "⚠️ 검사 미완료 (UNVERIFIED)"
            color = "#f59e0b"
            monetization = "판단 불가 — 검사 엔진이 없거나 오류가 발생했습니다. '안전'으로 해석하지 마세요."
            claim_probability = "검사 불가 (엔진 미설치/오류)"
            verdict = (
                "필수 검사 엔진(Shazam 또는 카탈로그 검색)이 실행되지 않아 저작권 위험을 판단할 수 없습니다. "
                "선택 기능을 설치하거나 공식 YouTube Content ID 도구로 확인하세요."
            )
            recommendations = [
                "⚠️ 이 상태는 '안전'이 아니라 '검사하지 못함'입니다.",
                "🛠️ 터미널에서 `pip install shazamio faster-whisper` 후 다시 검사하거나, 공식 YouTube 저작권 도구를 사용하세요.",
                "🌐 네트워크/방화벽으로 외부 검색이 차단되지 않았는지 확인하세요.",
            ]

        # Step 6: Clipping & Dynamic Warnings
        lufs_warning = None
        if acoustic.get("clipping_detected"):
            lufs_warning = "디지털 피크 클리핑(0dBFS 초과)이 감지되었습니다. 마스터링 볼륨을 살짝 낮추는 것을 권장합니다."

        filename = os.path.basename(file_path)
        all_lyrics_preview = "\n".join(lyrics_lines[:6]) if lyrics_lines else None
        verification_status = (
            "MATCHED" if matched else ("NO_MATCH_DETECTED" if risk_level == "NO_MATCH" else "UNVERIFIED")
        )

        return {
            "ok": True,
            "filename": filename,
            "file_path": file_path,
            "risk_level": risk_level,
            "risk_label": risk_label,
            "match_category": match_category,
            "verification_status": verification_status,
            "coverage_pct": coverage_pct,
            "safety_score": coverage_pct,  # backwards-compatible; now means verification coverage
            "color": color,
            "claim_probability": claim_probability,
            "monetization": monetization,
            "verdict": verdict,
            "matched": matched,
            "track_info": track_info if matched else None,
            "detected_lyrics": detected_lyrics_snippet,
            "transcribed_lyrics": all_lyrics_preview,
            "detected_language": detected_lang,
            "acoustic": acoustic,
            "lufs_warning": lufs_warning,
            "checks": checks,
            "engines": {
                "shazam": HAS_SHAZAM,
                "whisper": HAS_WHISPER,
                "librosa": HAS_LIBROSA,
            },
            "disclaimer": "이 진단은 비공식 음악 인식/카탈로그 검색 기반 참고 자료이며, 공식 YouTube Content ID 판정이나 법적·수익화 보장이 아닙니다.",
            "recommendations": recommendations
        }

    finally:
        if is_temp_extracted and os.path.exists(clean_path):
            try:
                os.remove(clean_path)
            except Exception:
                pass
