import sys
"""
Suno AI Song Downloader & Eden Audio Decryptor
Extracts metadata and downloads high-quality audio streams from Suno.com song links.
Handles modern Suno encrypted progressive streams (Eden / Mango protocol).
"""

import os
import re
import json
import time
import base64
import hashlib
import tempfile
import subprocess
import unicodedata
import urllib.request
import urllib.parse
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from core.hum_engine import get_ffmpeg_bin

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def extract_suno_id(url_or_id: str) -> str | None:
    """Extract UUID song ID from Suno song link or raw string. Resolves short URLs (/s/...) if needed."""
    text = str(url_or_id).strip()
    m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', text, re.I)
    if m:
        return m.group(1).lower()

    if re.search(r'suno\.(com|ai)', text, re.I):
        try:
            req = urllib.request.Request(text, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                final_url = resp.geturl()
                m2 = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', final_url, re.I)
                if m2:
                    return m2.group(1).lower()
                # If short URL (e.g. /s/...) didn't redirect with UUID in path, inspect HTML content
                # But do NOT inspect if redirected to root home page (meaning link is invalid/expired)
                if not re.search(r'suno\.(com|ai)/?$', final_url, re.I):
                    content = resp.read().decode("utf-8", errors="replace")
                    m3 = re.search(r'/song/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', content, re.I)
                    if m3:
                        return m3.group(1).lower()
                    m4 = re.search(r'["\'](?:clip_id|song_id|id)["\']\s*:\s*["\']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["\']', content, re.I)
                    if m4:
                        return m4.group(1).lower()
        except Exception as e:
            print(f"[SunoDownloader] Warning resolving suno link '{text}': {e}")
    return None


def fetch_suno_metadata(song_id: str) -> dict:
    """Fetch clip metadata from Suno public studio API and oEmbed."""
    meta = {
        "id": song_id,
        "title": f"Suno_{song_id[:8]}",
        "image_url": None,
        "duration": None
    }
    
    # 1. Studio Clip API
    try:
        api_url = f"https://studio-api-prod.suno.com/api/clip/{song_id}"
        req = urllib.request.Request(api_url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("title"):
                meta["title"] = data["title"]
            if data.get("image_url"):
                meta["image_url"] = data["image_url"]
            if data.get("duration"):
                meta["duration"] = data["duration"]
            return meta
    except Exception:
        pass

    # 2. oEmbed fallback
    try:
        oembed_url = f"https://studio-api-prod.suno.com/api/oembed?url=https%3A%2F%2Fsuno.com%2Fsong%2F{song_id}"
        req = urllib.request.Request(oembed_url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("title"):
                meta["title"] = data["title"]
    except Exception:
        pass

    return meta


def extract_playlist_id(url_or_id: str) -> str | None:
    """
    Extracts standard UUID playlist ID from any Suno playlist URL, short link, or raw ID.
    Handles standard dashes, spaces, underscores, and 32-character hex strings without delimiters.
    """
    text = str(url_or_id).strip()
    if re.search(r'suno\.(com|ai)/s/', text, re.I):
        try:
            req = urllib.request.Request(text, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                text = resp.geturl()
        except Exception:
            pass

    m = re.search(r'([0-9a-f]{8})[-_\s]?([0-9a-f]{4})[-_\s]?([0-9a-f]{4})[-_\s]?([0-9a-f]{4})[-_\s]?([0-9a-f]{12})', text, re.I)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}-{m.group(5)}".lower()
    return None


def is_suno_playlist_url(url_or_id: str) -> bool:
    """Check if the given string represents a Suno playlist URL or ID."""
    text = str(url_or_id).strip()
    return "playlist" in text.lower() and bool(extract_playlist_id(text))



def auto_extract_browser_suno_token(test_playlist_id: str = None) -> str | None:
    """
    Scans running browser process memory (Opera, Chrome, Edge, Brave) for active Suno JWT session tokens.
    Automatically verifies and saves the working token if found.
    """
    if sys.platform != "win32":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_VM_READ = 0x0010
        PROCESS_QUERY_INFORMATION = 0x0400
        TH32CS_SNAPPROCESS = 0x00000002
        MEM_COMMIT = 0x1000
        PAGE_READWRITE = 0x04
        PAGE_READONLY = 0x02

        class MEMORY_BASIC_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("PartitionId", wintypes.WORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD),
            ]

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_char * 260)
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        kernel32.VirtualQueryEx.restype = ctypes.c_size_t
        kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        kernel32.ReadProcessMemory.restype = wintypes.BOOL

        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)

        browser_pids = []
        target_names = ("opera", "chrome", "msedge", "brave", "whale")
        if kernel32.Process32First(snap, ctypes.byref(pe)):
            while True:
                name = pe.szExeFile.decode('ansi', 'ignore').lower()
                if any(b in name for b in target_names) and 'crash' not in name:
                    # Prioritize Opera, then Chrome/Edge
                    pri = 0 if 'opera' in name else (1 if 'chrome' in name else 2)
                    browser_pids.append((pri, pe.th32ProcessID))
                if not kernel32.Process32Next(snap, ctypes.byref(pe)):
                    break
        kernel32.CloseHandle(snap)
        browser_pids.sort(key=lambda x: x[0])
        pids_to_scan = [p[1] for p in browser_pids]

        jwt_pattern = re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')
        candidate_tokens = set()

        for pid in pids_to_scan:
            h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
            if not h:
                continue

            addr = 0
            mbi = MEMORY_BASIC_INFORMATION()

            while kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                if mbi.State == MEM_COMMIT and (mbi.Protect & (PAGE_READWRITE | PAGE_READONLY)):
                    size = mbi.RegionSize
                    if 4096 <= size <= 4 * 1024 * 1024:
                        buf = (ctypes.c_char * size)()
                        bytes_read = ctypes.c_size_t()
                        if kernel32.ReadProcessMemory(h, mbi.BaseAddress, buf, size, ctypes.byref(bytes_read)):
                            raw = bytes(buf)[:bytes_read.value]
                            if b'suno' in raw.lower() or b'clerk' in raw.lower():
                                for m in jwt_pattern.findall(raw):
                                    t = m.decode('ascii', 'ignore')
                                    if t not in candidate_tokens:
                                        candidate_tokens.add(t)
                                        # Verify token with quick request
                                        try:
                                            verify_url = f"https://studio-api-prod.suno.com/api/playlist/{test_playlist_id}?page=1" if test_playlist_id else "https://studio-api-prod.suno.com/api/billing/info"
                                            req = urllib.request.Request(
                                                verify_url,
                                                headers={
                                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                                    'Authorization': f'Bearer {t}',
                                                    'Origin': 'https://suno.com',
                                                    'Referer': f'https://suno.com/playlist/{test_playlist_id}' if test_playlist_id else 'https://suno.com/'
                                                }
                                            )
                                            with urllib.request.urlopen(req, timeout=3) as resp:
                                                if resp.status == 200:
                                                    kernel32.CloseHandle(h)
                                                    token_path = BASE_DIR / "data" / "suno_token.txt"
                                                    token_path.parent.mkdir(parents=True, exist_ok=True)
                                                    token_path.write_text(t, encoding="utf-8")
                                                    print(f"[AutoBrowserToken] Successfully extracted active Suno token from PID {pid}!")
                                                    return t
                                        except Exception:
                                            pass
                addr += mbi.RegionSize
                if addr >= 0x7FFFFFFF0000:
                    break
            kernel32.CloseHandle(h)
    except Exception as e:
        print(f"[AutoBrowserToken] Warning: {e}")
    return None


def resolve_suno_playlist(url_or_id: str) -> dict:
    """
    Resolves a Suno Playlist URL or UUID and returns all songs in the playlist.
    """
    pl_id = extract_playlist_id(url_or_id)
    if not pl_id:
        return {"ok": False, "error": "유효한 Suno 플레이리스트 ID를 찾을 수 없습니다."}

    # Check for optional custom Suno Cookie/Token
    cookie_file = BASE_DIR / "data" / "suno_cookie.txt"
    token_file = BASE_DIR / "data" / "suno_token.txt"
    custom_cookie = ""
    custom_token = ""
    if cookie_file.exists():
        try:
            custom_cookie = cookie_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    if token_file.exists():
        try:
            custom_token = token_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    req_headers = dict(DEFAULT_HEADERS)
    req_headers["Accept"] = "application/json, text/plain, */*"
    req_headers["Origin"] = "https://suno.com"
    req_headers["Referer"] = f"https://suno.com/playlist/{pl_id}"

    # Handle JWT token
    token = custom_token
    if not token and custom_cookie and (custom_cookie.startswith("eyJ") or custom_cookie.startswith("Bearer eyJ")):
        token = custom_cookie
        custom_cookie = ""

    if token:
        token_clean = token.strip()
        if not token_clean.startswith("Bearer "):
            token_clean = f"Bearer {token_clean}"
        req_headers["Authorization"] = token_clean

    if custom_cookie:
        sanitized = custom_cookie.encode('ascii', 'ignore').decode('ascii').strip()
        if sanitized and not sanitized.startswith("fetch(") and not sanitized.startswith("<"):
            req_headers["Cookie"] = sanitized

    songs = []
    page = 1
    retried = False
    pl_name = "Suno Playlist"
    base_api = "https://studio-api-prod.suno.com/api/playlist"

    # Test which domain responds
    for domain in ["https://studio-api-prod.suno.com/api/playlist", "https://studio-api.prod.suno.com/api/playlist"]:
        try:
            test_req = urllib.request.Request(f"{domain}/{pl_id}?page=1", headers=req_headers)
            with urllib.request.urlopen(test_req, timeout=6) as test_resp:
                if test_resp.status == 200:
                    base_api = domain
                    break
        except Exception:
            continue

    while True:
        api = f"{base_api}/{pl_id}?page={page}"
        req = urllib.request.Request(api, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if page == 1 and data.get("name"):
                    pl_name = data["name"]
                clips = data.get("playlist_clips", [])
                if not clips:
                    break
                for item in clips:
                    clip = item.get("clip") or {}
                    cid = clip.get("id")
                    ctitle = clip.get("title") or f"Suno_{cid[:8]}"
                    if cid:
                        songs.append({
                            "id": cid,
                            "title": ctitle,
                            "url": f"https://suno.com/song/{cid}",
                            "image_url": clip.get("image_url")
                        })
                num_total = data.get("num_total_results", len(songs))
                if len(songs) >= num_total or len(clips) == 0:
                    break
                page += 1
                if page > 20:
                    break
        except urllib.error.HTTPError as e:
            # If request failed with 401/403/404 or trashed, try auto-extracting fresh token from browser once
            if page == 1 and not retried:
                extracted = auto_extract_browser_suno_token(pl_id)
                if extracted:
                    retried = True
                    req_headers["Authorization"] = f"Bearer {extracted}"
                    continue

            err_detail = ""
            err_type = ""
            try:
                raw_body = e.read().decode("utf-8", "ignore")
                err_json = json.loads(raw_body)
                err_detail = str(err_json.get("detail") or err_json.get("detail_fallback") or "")
                err_type = str(err_json.get("error_type") or "")
            except Exception:
                pass

            if err_type == "trashed" or "deleted" in err_detail.lower():
                return {
                    "ok": False,
                    "error": (
                        "❌ Suno에서 [삭제된 플레이리스트]입니다.\n\n"
                        "🗑️ Suno 서버 확인 결과: 해당 플레이리스트는 삭제되었거나 휴지통에 있습니다.\n"
                        "💡 해결 방법: Suno 웹사이트(suno.com)의 Library에서 현재 정상 보관 중인 새 플레이리스트 URL을 복사하여 입력해주세요!"
                    )
                }

            if err_type == "not_found" or "not found" in err_detail.lower():
                return {
                    "ok": False,
                    "error": (
                        "❌ Suno에서 [플레이리스트를 찾을 수 없습니다].\n\n"
                        "🔍 플레이리스트 ID 또는 주소가 맞는지 확인해주세요.\n"
                        "🔒 비공개 플레이리스트인 경우, 아래 [Suno 쿠키 연동]을 통해 로그인 정보를 연동하시면 전곡 로드됩니다."
                    )
                }

            if e.code in (401, 403):
                return {
                    "ok": False,
                    "error": (
                        f"🔒 플레이리스트 접근 권한이 없습니다 (HTTP {e.code}).\n\n"
                        "Suno 비공개 플레이리스트는 로그인이 필요합니다.\n"
                        "아래 [Suno 쿠키 연동]을 1회 진행하시면 비공개 곡 목록도 즉시 불러올 수 있습니다."
                    )
                }

            if e.code == 404:
                return {
                    "ok": False,
                    "error": (
                        f"❌ 플레이리스트를 찾을 수 없습니다 (Suno 404 Not Found).\n\n"
                        f"{err_detail or '플레이리스트가 존재하지 않거나 삭제되었을 수 있습니다.'}\n\n"
                        "💡 해결 방법:\n"
                        "1) Suno(suno.com)에서 플레이리스트 URL을 다시 확인해주세요.\n"
                        "2) 비공개 플레이리스트인 경우 아래 [Suno 쿠키 연동]을 실행해주세요.\n"
                        "3) 또는 플레이리스트 안의 곡 링크들을 복사해 붙여넣으시면 자동 일괄 등록됩니다."
                    )
                }

            if page == 1:
                msg = err_detail or e.reason or f"HTTP {e.code}"
                return {"ok": False, "error": f"플레이리스트 로드 실패 (HTTP {e.code}): {msg}"}
            break
        except Exception as e:
            if page == 1:
                return {"ok": False, "error": f"플레이리스트 로드 실패: {e}"}
            break

    return {
        "ok": True,
        "playlist_id": pl_id,
        "name": pl_name,
        "total": len(songs),
        "songs": songs
    }


def decrypt_suno_audio(song_id: str, encrypted_bytes: bytes) -> bytes:
    """
    Decrypts Suno Eden / Mango encrypted progressive stream.
    1. Query /api/mango/rights for key, iv, and glt.
    2. glt_key = sha256(glt)
    3. real_key & real_iv = AESGCM.decrypt(iv, ct, aad=song_id)
    4. decrypted_audio = AES-128-CTR(key=real_key, iv=real_iv).decrypt(encrypted_bytes)
    """
    rights_url = "https://studio-api-prod.suno.com/api/mango/rights"
    payload = json.dumps({
        "content_params": {
            "content_id": song_id,
            "content_type": "clip"
        }
    }).encode("utf-8")
    
    headers = {
        **DEFAULT_HEADERS,
        "Content-Type": "application/json",
        "Origin": "https://suno.com",
        "Referer": f"https://suno.com/song/{song_id}"
    }
    
    req = urllib.request.Request(rights_url, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        rights = json.loads(resp.read().decode("utf-8"))

    glt = rights["glt"]
    glt_key = hashlib.sha256(glt.encode("utf-8")).digest()
    aesgcm = AESGCM(glt_key)
    aad = song_id.encode("utf-8")

    # Decrypt real key
    raw_key_enc = base64.b64decode(rights["key"])
    real_key = aesgcm.decrypt(raw_key_enc[:12], raw_key_enc[12:], aad)

    # Decrypt real iv
    raw_iv_enc = base64.b64decode(rights["iv"])
    real_iv = aesgcm.decrypt(raw_iv_enc[:12], raw_iv_enc[12:], aad)

    # Decrypt stream using AES-CTR
    cipher = Cipher(algorithms.AES(real_key), modes.CTR(real_iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(encrypted_bytes) + decryptor.finalize()


def download_suno_song(url_or_id: str, progress_cb=None) -> dict:
    """
    Complete download pipeline:
    1. Resolves Suno song ID & title.
    2. Fetches audio stream (decrypts if Eden protected).
    3. Converts to high-quality 320kbps MP3 in uploads folder.
    4. Returns metadata dict for instant mastering.
    """
    song_id = extract_suno_id(url_or_id)
    if not song_id:
        raise ValueError("올바른 Suno 곡 링크가 아닙니다. (예: https://suno.com/song/...)")

    if progress_cb:
        progress_cb(10, "Suno 음원 정보 조회 중...")

    meta = fetch_suno_metadata(song_id)
    title = meta.get("title") or f"Suno_{song_id[:8]}"
    clean_title = title.replace("‘", "'").replace("’", "'").replace("“", "'").replace("”", "'")
    norm = unicodedata.normalize('NFKC', str(clean_title))
    clean_title = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f\uff5c]', "", norm).strip(". \t\r\n")[:80].strip(". \t\r\n") or f"Suno_{song_id[:8]}"

    if progress_cb:
        progress_cb(20, f"'{clean_title}' 스트림 경로 탐색 중...")

    # Find media URL from song page
    audio_url = None
    try:
        page_url = f"https://suno.com/song/{song_id}"
        req_page = urllib.request.Request(page_url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req_page, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            m_audio = re.search(r'https://[^"\'\\]+\.cloudfront\.net/[^"\'\\]+\.m4a', html)
            if m_audio:
                audio_url = m_audio.group(0)
    except Exception:
        pass

    if not audio_url:
        audio_url = f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{song_id}.m4a"

    if progress_cb:
        progress_cb(35, "Suno 오디오 데이터 다운로드 중...")

    req_audio = urllib.request.Request(audio_url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req_audio, timeout=30) as resp:
        raw_audio = resp.read()

    # Check if stream is encrypted
    # Valid MP4 containers start with ftyp box at offset 4
    is_mp4 = len(raw_audio) > 8 and raw_audio[4:8] == b"ftyp"
    is_mp3 = len(raw_audio) > 3 and (raw_audio[:3] == b"ID3" or raw_audio[:2] == b"\xff\xfb")
    
    decrypted_bytes = raw_audio
    if not is_mp4 and not is_mp3:
        if progress_cb:
            progress_cb(50, "Suno 고음질 Eden 오디오 복호화 중...")
        try:
            decrypted_bytes = decrypt_suno_audio(song_id, raw_audio)
        except Exception as e:
            # If decryption fails, attempt to save as-is
            decrypted_bytes = raw_audio

    if progress_cb:
        progress_cb(65, "고음질 320kbps MP3 변환 및 정규화 중...")

    # Write temporary file
    tmp_in = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
    tmp_in.write(decrypted_bytes)
    tmp_in.close()

    # Generate final filename directly matching the Suno song title
    final_filename = f"{clean_title}.mp3"
    final_path = UPLOADS_DIR / final_filename

    ffmpeg = get_ffmpeg_bin()
    subprocess.run([
        ffmpeg, "-y", "-v", "error",
        "-i", tmp_in.name,
        "-c:a", "libmp3lame",
        "-b:a", "320k",
        str(final_path)
    ], check=True)

    try:
        os.unlink(tmp_in.name)
    except Exception:
        pass

    if progress_cb:
        progress_cb(80, "Suno 음원 준비 완료! 정밀 음향 분석 시작...")

    return {
        "ok": True,
        "song_id": song_id,
        "title": clean_title,
        "filename": final_filename,
        "filepath": str(final_path),
        "file_path": str(final_path),
        "audio_url": f"/uploads/{urllib.parse.quote(final_filename)}",
        "image_url": meta.get("image_url")
    }
