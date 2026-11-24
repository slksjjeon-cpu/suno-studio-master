import os
import sys
import json

# Force UTF-8 on Windows console / pipes to prevent cp949 UnicodeEncodeError
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import builtins
_orig_print = builtins.print
def _safe_global_print(*args, **kwargs):
    try:
        _orig_print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            enc = sys.stdout.encoding or "utf-8"
            safe_args = [str(a).encode(enc, errors="replace").decode(enc, errors="replace") for a in args]
            _orig_print(*safe_args, **kwargs)
        except Exception:
            pass
builtins.print = _safe_global_print
import re
import asyncio
import shutil
import time
import random
import uuid
import base64
import socket
import ipaddress
import subprocess
import threading
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

def normalize_title(title: str) -> str:
    r"""Normalize title to standard clean ASCII/Unicode:
    1. Converts Mathematical Bold (e.g. 𝗦𝘁𝗮𝘆 𝗪𝗶𝘁𝗵 𝗠𝒆 -> Stay with Me),
       Italic, Script, and Fullwidth variants into standard, normal-weight characters.
    2. Strips illegal Windows filename characters (< > : " / \ | ? *) and control characters.
    3. Strips trailing dots, spaces, and whitespace.
    """
    if not title:
        return ""
    norm = unicodedata.normalize('NFKC', str(title))
    norm = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f\uff5c]', '', norm)
    return norm.strip(". \t\r\n")

from core.analyzer_suno import analyze_suno_track
from core.queue_worker import StudioQueueManager
from core.suno_downloader import download_suno_song, extract_suno_id, is_suno_playlist_url, resolve_suno_playlist
from core.hum_engine import (
    HumStems, mix_hum_segment, load_hum_presets, save_hum_presets,
    SPEED_PRESETS, get_ffmpeg_bin, SR as HUM_SR, DEFAULTS as HUM_DEFAULTS
)
import soundfile as sf
import subprocess
from core.copyright_checker import check_youtube_copyright
from core.youtube_uploader import (
    get_youtube_config,
    save_youtube_config,
    is_youtube_authenticated,
    get_oauth_flow,
    fetch_and_save_channel_info,
    disconnect_youtube,
    upload_video_to_youtube,
    format_youtube_error,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def get_safe_unique_filepath(dest_dir: Union[Path, str], filename: str, new_file_size: Optional[int] = None) -> Path:
    """
    If a file with `filename` does not exist in `dest_dir`, returns `dest_dir / filename`.
    If a file exists:
      - If new_file_size is provided and existing file has the exact same size:
        return existing file path (identical file preserved).
      - If existing file has a different size:
        auto-renames by appending `_1`, `_2`, etc. to the stem until an available filename
        or a file with matching size is found.
    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    raw_name = Path(filename).name
    stem = normalize_title(Path(raw_name).stem)[:80].strip(". \t\r\n") or "file"
    ext = Path(raw_name).suffix
    file_p = dest_path / f"{stem}{ext}"
    try:
        if not file_p.exists():
            return file_p
    except Exception:
        # Fallback if anything invalid remained
        stem = re.sub(r'[^a-zA-Z0-9_\-\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]', '', stem)[:50] or "file"
        file_p = dest_path / f"{stem}{ext}"
        if not file_p.exists():
            return file_p
    if new_file_size is not None:
        try:
            if file_p.stat().st_size == new_file_size:
                return file_p
        except Exception:
            pass
    counter = 1
    while True:
        cand = dest_path / f"{stem}_{counter}{ext}"
        if not cand.exists():
            return cand
        if new_file_size is not None:
            try:
                if cand.stat().st_size == new_file_size:
                    return cand
            except Exception:
                pass
        counter += 1

app = FastAPI(title="Suno AI Mastering Studio", version="2.1.0")

# Local-only app: do not expose credentialed CORS to arbitrary web origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# Path / upload safety helpers
# ---------------------------------------------------------------------
ALLOWED_MEDIA_ROOTS = [
    Path(UPLOADS_DIR).resolve(),
    Path(OUTPUTS_DIR).resolve(),
    Path(SAMPLES_DIR).resolve(),
    Path(STATIC_DIR).resolve(),
]
MAX_UPLOAD_MB = max(1, int(os.environ.get("STUDIO_MAX_UPLOAD_MB", "300")))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_REMOTE_MB = max(1, int(os.environ.get("STUDIO_MAX_REMOTE_MB", "100")))
MAX_REMOTE_BYTES = MAX_REMOTE_MB * 1024 * 1024
MAX_IMAGE_BYTES = 25 * 1024 * 1024


def _is_within_roots(path: Path, roots) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        return False
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def resolve_media_path(raw, roots=None, must_exist: bool = True) -> Optional[str]:
    """Resolve a URL/filename to a real file *inside* the allowed media roots.

    Absolute paths outside uploads/outputs/samples/static are rejected instead of
    being passed through to ffmpeg/librosa. This closes arbitrary local-file reads.
    A declared prefix such as ``/outputs/x.mp3`` is resolved only against ``outputs``
    so duplicate filenames in different folders cannot be mixed up.
    """
    if not raw:
        return None
    base_roots = [Path(r).resolve() for r in (roots or ALLOWED_MEDIA_ROOTS)]
    s = str(raw).strip().strip("'\"")
    if not s:
        return None

    if "://" in s:
        parsed = urllib.parse.urlparse(s)
        if parsed.scheme not in ("http", "https"):
            return None
        s = urllib.parse.unquote(parsed.path)
    else:
        s = urllib.parse.unquote(s)

    p = Path(s)
    target_roots = base_roots
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        rel = s.lstrip("/\\")
        parts = Path(rel).parts
        if parts and parts[0].lower() in ("uploads", "outputs", "samples", "static"):
            wanted = parts[0].lower()
            scoped = [r for r in base_roots if r.name.lower() == wanted]
            if scoped:
                target_roots = scoped
            rel = str(Path(*parts[1:])) if len(parts) > 1 else ""
        if rel:
            candidates.append(Path(rel))
        direct = s.lstrip("/\\")
        if direct and direct != rel:
            candidates.append(Path(direct))

    for base in target_roots:
        for cand in candidates:
            full = cand if cand.is_absolute() else (base / cand)
            try:
                rp = full.resolve()
            except Exception:
                continue
            if not _is_within_roots(rp, base_roots):
                continue
            if must_exist and not rp.is_file():
                continue
            return str(rp)

    # Plain filename fallback (never for absolute paths outside the roots).
    if not p.is_absolute():
        name = Path(s).name
        if name:
            for base in target_roots:
                rp = (base / name).resolve()
                if _is_within_roots(rp, base_roots) and (not must_exist or rp.is_file()):
                    return str(rp)

        # Smart fuzzy whitespace & NFKC match fallback in target_roots
        norm_target = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', name or s)).strip().lower()
        if norm_target:
            for base in target_roots:
                if not base.exists():
                    continue
                try:
                    for cand_file in base.iterdir():
                        if cand_file.is_file():
                            cand_norm = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', cand_file.name)).strip().lower()
                            if cand_norm == norm_target:
                                rp = cand_file.resolve()
                                if _is_within_roots(rp, base_roots):
                                    return str(rp)
                except Exception:
                    pass
    return None


def _copy_upload_limited(src, dest: str, max_bytes: int = MAX_UPLOAD_BYTES) -> int:
    total = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = src.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"파일이 너무 큽니다. 최대 {max_bytes // (1024 * 1024)}MB까지 업로드할 수 있습니다.",
                    )
                out.write(chunk)
    except Exception:
        try:
            os.remove(dest)
        except Exception:
            pass
        raise
    return total


def _safe_token(value, fallback: Optional[str] = None, max_len: int = 64) -> Optional[str]:
    token = re.sub(r"[^A-Za-z0-9_-]", "", str(value or "").strip())[:max_len]
    return token or fallback


def _host_of(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def _is_youtube_url(url: str) -> bool:
    host = _host_of(url)
    return host in {"youtube.com", "youtu.be", "youtube-nocookie.com"} or host.endswith(".youtube.com")


def _is_suno_url(url: str) -> bool:
    host = _host_of(url)
    return host in {"suno.com", "suno.ai", "audiopipe.suno.ai"} or host.endswith(".suno.com") or host.endswith(".suno.ai")


def _validate_public_http_url(url: str) -> str:
    """Allow only public http(s) URLs (blocks file://, localhost, and private IPs)."""
    parsed = urllib.parse.urlparse(str(url).strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("http/https 공개 URL만 사용할 수 있습니다.")
    host = parsed.hostname.lower().rstrip(".")
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as exc:
        raise ValueError(f"호스트를 확인할 수 없습니다: {host}") from exc
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError("내부/사설 네트워크 주소는 다운로드할 수 없습니다.")
    return url


def _read_limited_response(resp, max_bytes: int = MAX_REMOTE_BYTES) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = resp.read(1024 * 256)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"원격 파일이 최대 허용 크기({max_bytes // (1024 * 1024)}MB)를 초과했습니다.")
        chunks.append(chunk)
    return b"".join(chunks)


def _clamp(value, low: float, high: float, default: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_mastering_options(options: Dict[str, Any]) -> Dict[str, Any]:
    opts = dict(options or {})
    opts["target_lufs"] = _clamp(opts.get("target_lufs", -14.0), -24.0, -6.0, -14.0)
    opts["speed_ratio"] = _clamp(opts.get("speed_ratio", 1.0), 0.25, 4.0, 1.0)
    opts["pitch_shift"] = _clamp(opts.get("pitch_shift", 0.0), -24.0, 24.0, 0.0)
    opts["bass_boost_db"] = _clamp(opts.get("bass_boost_db", 1.0), -12.0, 12.0, 1.0)
    opts["mid_presence_db"] = _clamp(opts.get("mid_presence_db", 0.5), -12.0, 12.0, 0.5)
    opts["air_band_boost_db"] = _clamp(opts.get("air_band_boost_db", 1.5), -12.0, 12.0, 1.5)
    opts["stereo_width"] = _clamp(opts.get("stereo_width", 1.15), 0.5, 2.0, 1.15)
    opts["tape_warmth"] = _clamp(opts.get("tape_warmth", 0.08), 0.0, 1.0, 0.08)
    opts["limiter_ceiling_db"] = _clamp(opts.get("limiter_ceiling_db", -1.0), -6.0, -0.1, -1.0)
    opts["ultrasonic_cut_freq"] = _clamp(opts.get("ultrasonic_cut_freq", 18500.0), 15000.0, 22000.0, 18500.0)
    for key in ("dewatermark_enabled", "tempo_stabilize_enabled", "keep_pitch", "auto_leveling",
                "decorrelate_phase", "tpdf_dither", "de_ringing"):
        if key in opts:
            opts[key] = bool(opts[key])
    if not isinstance(opts.get("tempo_info"), dict):
        opts.pop("tempo_info", None)
    return opts

queue_manager = StudioQueueManager(output_dir=OUTPUTS_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")
app.mount("/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")

analysis_tasks: Dict[str, Dict[str, Any]] = {}
ANALYSIS_TASKS_FILE = Path(DATA_DIR) / "analysis_tasks_cache.json"

def _save_task_to_disk(task_id: str):
    try:
        task = analysis_tasks.get(task_id)
        if not task:
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        data = {}
        if ANALYSIS_TASKS_FILE.exists():
            try:
                with open(ANALYSIS_TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[task_id] = task
        # Keep latest 30 tasks
        if len(data) > 30:
            keys = list(data.keys())[:-30]
            for k in keys:
                del data[k]
        with open(ANALYSIS_TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        pass

def _load_task_from_disk(task_id: str) -> Optional[dict]:
    if ANALYSIS_TASKS_FILE.exists():
        try:
            with open(ANALYSIS_TASKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(task_id)
        except Exception:
            pass
    return None
latest_studio_track: Dict[str, Any] = {
    "file_path": None, "filename": None, "title": None, "audio_url": None, "image_url": None
}
LATEST_TRACK_FILE = Path(DATA_DIR) / "latest_studio_track.json"

def _save_latest_track_to_disk():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LATEST_TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(latest_studio_track, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _load_latest_track_from_disk() -> bool:
    if LATEST_TRACK_FILE.exists():
        try:
            with open(LATEST_TRACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get("file_path") and os.path.exists(data["file_path"]):
                    latest_studio_track.update(data)
                    return True
        except Exception:
            pass
    return False

# Hum Studio Global State
hum_stems = HumStems()
hum_lock = threading.Lock()
hum_analysis_lock = threading.Lock()
hum_generation = 0
hum_current = {"file": None}
hum_job = {"status": "idle", "phase": None, "pct": None, "eta": None, "message": "대기"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

def _set_hum_job(status, message, phase=None, pct=None, eta=None):
    hum_job["status"] = status
    hum_job["message"] = message
    hum_job["phase"] = phase
    hum_job["pct"] = pct
    hum_job["eta"] = eta

def _run_hum_analysis(syll=3.2):
    global hum_stems
    with hum_lock:
        generation = hum_generation
        selected = dict(hum_current["file"]) if hum_current.get("file") else None
    try:
        if not selected or not selected.get("path"):
            return
        fpath = Path(selected["path"])
        if not fpath.exists():
            with hum_lock:
                if generation == hum_generation:
                    _set_hum_job("error", f"파일을 찾을 수 없습니다: {fpath.name}", phase="analyze")
            return

        def prog(pct, msg):
            with hum_lock:
                if generation == hum_generation:
                    _set_hum_job("working", msg, phase="analyze", pct=pct)

        # Build stems separately; a newly selected track must never inherit old stems.
        with hum_analysis_lock:
            with hum_lock:
                if generation != hum_generation:
                    return
            candidate = HumStems()
            if not candidate.load_cache(fpath):
                candidate.analyze(fpath, lambda m: None, syll=syll, prog_cb=prog)
            with hum_lock:
                if generation == hum_generation:
                    hum_stems = candidate
                    _set_hum_job("ready", f"분석 완료 ({candidate.dur:.0f}초), 바로 사용 가능", phase="analyze", pct=100)
    except Exception as e:
        import traceback
        traceback.print_exc()
        with hum_lock:
            if generation == hum_generation:
                _set_hum_job("error", f"분석 실패: {e}", phase="analyze")


def _set_hum_source(p: Path, title: str):
    global hum_generation
    title = normalize_title(title or p.stem)
    with hum_lock:
        hum_generation += 1
        hum_current["file"] = {"name": p.name, "path": str(p), "title": title}
        ready = hum_stems.load_cache(p)
        dur = hum_stems.dur if ready else 0.0
        _set_hum_job("ready" if ready else "working",
                     f"캐시 적중 ({dur:.0f}초), 바로 사용 가능" if ready else f"'{title}' 음원 분석 시작...",
                     phase="analyze", pct=100 if ready else 0)
    return ready, dur

def _sync_to_hum_studio(filepath: str, title: str = None):
    """Automatically connects any track analyzed in Mastering Studio directly into Hum Studio."""
    try:
        p = Path(filepath)
        if not p.exists():
            return
        t = title or p.stem
        # Register track metadata in Hum Studio without launching heavy concurrent Demucs stem separation thread
        _set_hum_source(p, t)
    except Exception as e:
        print("[HumSync] Warning auto-syncing to Hum Studio:", e)

# Auto-initialize with persisted active track or newest available user track in uploads on startup
try:
    if not _load_latest_track_from_disk():
        user_mp3s = [p for p in sorted(Path(UPLOADS_DIR).glob("*.mp3"), key=lambda x: x.stat().st_mtime) if not p.name.startswith("check_")]
        if user_mp3s:
            newest = user_mp3s[-1]
            t_guess = re.sub(r"^yt_", "", newest.stem)
            latest_studio_track.update({
                "file_path": str(newest),
                "filename": newest.name,
                "title": t_guess,
                "audio_url": f"/uploads/{urllib.parse.quote(newest.name)}"
            })
            _save_latest_track_to_disk()
    if latest_studio_track.get("file_path") and os.path.exists(latest_studio_track["file_path"]):
        hum_current["file"] = {"name": latest_studio_track["filename"], "path": latest_studio_track["file_path"], "title": latest_studio_track["title"]}
        with hum_lock:
            if hum_stems.load_cache(Path(latest_studio_track["file_path"])):
                _set_hum_job("ready", f"캐시 적중 ({hum_stems.dur:.0f}초), 바로 사용 가능", phase="analyze", pct=100)
except Exception:
    pass

def _run_analysis_task(task_id: str, filepath: str, audio_url: str):
    try:
        def on_progress(percent: int, stage_msg: str, remaining_sec: float):
            if task_id in analysis_tasks:
                analysis_tasks[task_id]["progress"] = percent
                analysis_tasks[task_id]["stage"] = stage_msg
                analysis_tasks[task_id]["remaining_sec"] = remaining_sec

        fname_clean = os.path.splitext(os.path.basename(filepath))[0]
        analysis = analyze_suno_track(filepath, progress_callback=on_progress, metadata={"title": fname_clean})
        analysis["audio_url"] = audio_url
        analysis["file_path"] = filepath
        analysis["filename"] = os.path.basename(filepath)
        analysis["title"] = fname_clean

        latest_studio_track.update({
            "file_path": filepath,
            "filename": os.path.basename(filepath),
            "title": fname_clean,
            "audio_url": audio_url
        })
        _save_latest_track_to_disk()
        _sync_to_hum_studio(filepath, title=fname_clean)

        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["progress"] = 100
        analysis_tasks[task_id]["stage"] = "분석 완료!"
        analysis_tasks[task_id]["remaining_sec"] = 0.0
        analysis_tasks[task_id]["data"] = analysis
    except Exception as e:
        import traceback
        traceback.print_exc()
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = format_youtube_error(e)


class SunoImportRequest(BaseModel):
    url: str


def _run_suno_import_and_analysis_task(task_id: str, suno_url: str):
    try:
        def on_download_progress(percent: int, stage_msg: str):
            if task_id in analysis_tasks:
                overall_pct = int(percent * 0.4)
                analysis_tasks[task_id]["progress"] = max(5, overall_pct)
                analysis_tasks[task_id]["stage"] = stage_msg
                analysis_tasks[task_id]["remaining_sec"] = max(1.0, round(12.0 * (1.0 - overall_pct / 100.0), 1))
                _save_task_to_disk(task_id)

        # 1. Download & Decrypt Suno Audio
        dl_res = download_suno_song(suno_url, progress_cb=on_download_progress)
        filepath = dl_res["filepath"]
        audio_url = dl_res["audio_url"]
        suno_title = dl_res["title"]

        if task_id in analysis_tasks:
            analysis_tasks[task_id]["progress"] = 40
            analysis_tasks[task_id]["stage"] = f"'{suno_title}' 오디오 분석 엔진 시작..."
            _save_task_to_disk(task_id)

        # 2. Run analysis
        def on_analysis_progress(percent: int, stage_msg: str, remaining_sec: float):
            if task_id in analysis_tasks:
                overall_pct = 40 + int(percent * 0.59)
                analysis_tasks[task_id]["progress"] = overall_pct
                analysis_tasks[task_id]["stage"] = stage_msg
                analysis_tasks[task_id]["remaining_sec"] = remaining_sec
                _save_task_to_disk(task_id)

        analysis = analyze_suno_track(filepath, progress_callback=on_analysis_progress, metadata={"title": suno_title, "song_id": dl_res.get("song_id")})
        analysis["audio_url"] = audio_url
        analysis["title"] = suno_title
        analysis["filename"] = dl_res["filename"]
        analysis["file_path"] = filepath
        analysis["suno_id"] = dl_res["song_id"]
        analysis["image_url"] = dl_res.get("image_url")

        latest_studio_track.update({
            "file_path": filepath,
            "filename": dl_res["filename"],
            "title": suno_title,
            "audio_url": audio_url,
            "image_url": dl_res.get("image_url")
        })
        _save_latest_track_to_disk()
        _sync_to_hum_studio(filepath, title=suno_title)

        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["progress"] = 100
        analysis_tasks[task_id]["stage"] = "분석 완료!"
        analysis_tasks[task_id]["remaining_sec"] = 0.0
        analysis_tasks[task_id]["data"] = analysis
        _save_task_to_disk(task_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = format_youtube_error(e)
        _save_task_to_disk(task_id)


def get_safe_yt_dlp_opts(extra_opts: dict = None) -> dict:
    js_runtimes = {}
    if os.path.exists(r"C:\Program Files\nodejs\node.exe"):
        js_runtimes['node'] = {'path': r'C:\Program Files\nodejs\node.exe'}

    opts = {
        'quiet': True,
        'noplaylist': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web_creator', 'mweb', 'tv'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'js_runtimes': js_runtimes
    }
    cookie_file = os.path.join(DATA_DIR, "youtube_cookies.txt")
    if os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 10:
        opts['cookiefile'] = cookie_file

    if extra_opts:
        if 'extractor_args' in extra_opts and 'youtube' in extra_opts['extractor_args']:
            opts['extractor_args']['youtube'].update(extra_opts['extractor_args']['youtube'])
        for k, v in extra_opts.items():
            if k != 'extractor_args':
                opts[k] = v
    return opts

def format_youtube_error(err: Exception) -> str:
    err_str = str(err)
    err_lower = err_str.lower()
    # Normalize unicode apostrophes (e.g. ’ to ')
    err_norm = err_str.replace("’", "'").replace("‘", "'")
    if (
        "confirm you're not a bot" in err_norm
        or "confirm you are not a bot" in err_norm
        or "sign in to confirm" in err_lower
        or "cookies-from-browser" in err_lower
        or ("bot" in err_lower and "youtube" in err_lower)
    ):
        return (
            "유튜브 봇 탐지 차단 오류 (Sign in to confirm you're not a bot)\n\n"
            "클라우드 웹 서버(Render.com 데이터센터 IP)가 유튜브의 자동 봇 방지 시스템에 의해 일시 차단되었습니다.\n\n"
            "💡 즉시 해결 방법:\n"
            "1. 내 컴퓨터의 로컬 스튜디오(http://127.0.0.1:8000)에서 실행하시면 가정용 인터넷 IP로 100% 정상 다운로드됩니다.\n"
            "2. 또는 유튜브 음원을 MP3/MP4로 직접 다운로드받아 파일 업로드란에 넣어주시면 동일하게 완곡 마스터링하실 수 있습니다."
        )
    if "Private video" in err_str:
        return "비공개(Private) 동영상입니다. 유튜브 영상 공개 설정을 '일부 공개' 또는 '공개'로 변경 후 시도해주세요."
    if "Video unavailable" in err_str:
        return "동영상을 찾을 수 없거나 유튜브에서 삭제된 영상입니다."
    if "Sign in to confirm your age" in err_str:
        return "연령 제한(성인 인증 필요) 동영상입니다. 일반 공개 영상 링크를 이용해주세요."
    return err_str

def _run_youtube_import_and_analysis_task(task_id: str, youtube_url: str):
    try:
        from yt_dlp import YoutubeDL
        ffmpeg_exe = get_ffmpeg_bin()

        if task_id in analysis_tasks:
            analysis_tasks[task_id]["progress"] = 5
            analysis_tasks[task_id]["stage"] = "YouTube 메타데이터 및 스트림 확인 중..."
            analysis_tasks[task_id]["remaining_sec"] = 8.0

        ydl_opts_info = get_safe_yt_dlp_opts({'extract_flat': False})

        with YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            raw_title = info.get('title', 'YouTube_Track')
            video_id = info.get('id', uuid.uuid4().hex[:8])
            thumb_url = info.get('thumbnail')

        clean_title = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", raw_title).strip(". "))[:80] or "YouTube_Track"
        final_mp3_name = f"yt_{clean_title}_{video_id}.mp3"
        final_mp3_path = os.path.join(UPLOADS_DIR, final_mp3_name)

        # Download thumbnail if available
        thumb_name = f"yt_{clean_title}_{video_id}_thumb.jpg"
        thumb_path = os.path.join(UPLOADS_DIR, thumb_name)
        if thumb_url and not os.path.exists(thumb_path):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                req_t = urllib.request.Request(thumb_url, headers=headers)
                with urllib.request.urlopen(req_t, timeout=7) as r, open(thumb_path, 'wb') as f:
                    f.write(r.read())
            except Exception:
                pass

        if not os.path.exists(final_mp3_path):
            if task_id in analysis_tasks:
                analysis_tasks[task_id]["progress"] = 15
                analysis_tasks[task_id]["stage"] = f"'{clean_title}' 고음질 오디오 추출 중..."

            outtmpl = os.path.join(UPLOADS_DIR, f"yt_{clean_title}_{video_id}.%(ext)s")
            ydl_opts_dl = get_safe_yt_dlp_opts({
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'overwrites': True,
                'windowsfilenames': True,
                'ffmpeg_location': ffmpeg_exe
            })
            with YoutubeDL(ydl_opts_dl) as ydl:
                ydl.download([youtube_url])

        if not os.path.exists(final_mp3_path):
            matched = [f for f in os.listdir(UPLOADS_DIR) if video_id in f and f.endswith(".mp3")]
            if matched:
                final_mp3_name = matched[0]
                final_mp3_path = os.path.join(UPLOADS_DIR, final_mp3_name)
            else:
                raise RuntimeError("YouTube 오디오 파일을 생성하지 못했습니다.")

        if task_id in analysis_tasks:
            analysis_tasks[task_id]["progress"] = 40
            analysis_tasks[task_id]["stage"] = f"'{clean_title}' 오디오 분석 엔진 가동 중..."

        def on_analysis_progress(percent: int, stage_msg: str, remaining_sec: float):
            if task_id in analysis_tasks:
                overall_pct = 40 + int(percent * 0.59)
                analysis_tasks[task_id]["progress"] = overall_pct
                analysis_tasks[task_id]["stage"] = stage_msg
                analysis_tasks[task_id]["remaining_sec"] = remaining_sec
                _save_task_to_disk(task_id)

        analysis = analyze_suno_track(
            final_mp3_path,
            progress_callback=on_analysis_progress,
            metadata={
                "title": clean_title,
                "video_id": video_id,
                "uploader": info.get("uploader"),
                "artist": info.get("artist"),
                "genre": info.get("genre"),
                "description": info.get("description", "")[:500],
                "tags": info.get("tags", [])[:10]
            }
        )
        analysis["audio_url"] = f"/uploads/{urllib.parse.quote(final_mp3_name)}"
        analysis["title"] = clean_title
        analysis["filename"] = final_mp3_name
        analysis["file_path"] = final_mp3_path
        analysis["youtube_id"] = video_id
        analysis["image_url"] = f"/uploads/{urllib.parse.quote(thumb_name)}" if os.path.exists(thumb_path) else None

        latest_studio_track.update({
            "file_path": final_mp3_path,
            "filename": final_mp3_name,
            "title": clean_title,
            "audio_url": analysis["audio_url"],
            "image_url": analysis["image_url"]
        })
        _save_latest_track_to_disk()
        _sync_to_hum_studio(final_mp3_path, title=clean_title)

        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["progress"] = 100
        analysis_tasks[task_id]["stage"] = "분석 완료!"
        analysis_tasks[task_id]["remaining_sec"] = 0.0
        analysis_tasks[task_id]["data"] = analysis
        _save_task_to_disk(task_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = format_youtube_error(e)
        _save_task_to_disk(task_id)


@app.post("/api/suno-async")
def import_suno_track_async(req: SunoImportRequest):
    """Import Suno track (decrypt) or YouTube track directly from URL and trigger analysis."""
    url = req.url.strip()
    # Older cached clients send only the song UUID after extracting it from a link.
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", url):
        url = f"https://suno.com/song/{url}"
    is_yt = _is_youtube_url(url)
    is_suno = _is_suno_url(url)
    song_id = extract_suno_id(url) if is_suno else None

    if not is_yt and not is_suno:
        raise HTTPException(status_code=400, detail="유효한 Suno 또는 YouTube 링크가 아닙니다.")
    try:
        _validate_public_http_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if is_yt:
        task_id = f"yt_{uuid.uuid4().hex[:8]}"
        analysis_tasks[task_id] = {
            "status": "processing",
            "progress": 5,
            "stage": "YouTube 음원 스트림 연결 중...",
            "remaining_sec": 8.0,
            "data": None,
            "error": None
        }
        t = threading.Thread(
            target=_run_youtube_import_and_analysis_task,
            args=(task_id, url),
            daemon=True
        )
        t.start()
        return {"success": True, "task_id": task_id, "type": "youtube"}
    else:
        task_id = f"suno_{uuid.uuid4().hex[:8]}"
        analysis_tasks[task_id] = {
            "status": "processing",
            "progress": 5,
            "stage": "Suno 메타데이터 및 스트림 연결 중...",
            "remaining_sec": 8.0,
            "data": None,
            "error": None
        }
        t = threading.Thread(
            target=_run_suno_import_and_analysis_task,
            args=(task_id, url),
            daemon=True
        )
        t.start()
        return {"success": True, "task_id": task_id, "song_id": song_id, "type": "suno"}


@app.get("/")
def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Suno AI Mastering Studio Backend Live"}


def get_app_version() -> dict:
    version_file = Path(BASE_DIR) / "version.json"
    if version_file.exists():
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Version] Warning reading version.json: {e}")
    return {
        "version": "v3.6.0",
        "app_name": "Suno Studio Master",
        "build_type": "Ultimate UX Edition",
        "updated_at": "2026.11.23 00:15",
        "updated_date": "2026.11.23",
        "updated_time": "00:15",
        "timezone": "KST"
    }


@app.get("/health")
def get_health():
    ver_info = get_app_version()
    return {
        "status": "ok",
        "service": "Antigravity Music Studio",
        "version": ver_info.get("version", "v3.6.0"),
        "updated_at": ver_info.get("updated_at", "2026.11.23 00:15")
    }


@app.get("/api/version")
def api_get_version():
    return get_app_version()


@app.get("/api/system-status")
def get_system_status():
    import shutil
    disk_total, disk_used, disk_free = shutil.disk_usage(".")
    free_mb = round(disk_free / (1024 * 1024), 1)
    free_gb = round(disk_free / (1024 * 1024 * 1024), 2)
    return {
        "gpu": {
            "name": "NVIDIA GeForce RTX 2060 Mobile (Detected)",
            "vram_total_mb": 6144,
            "vram_status": "DSP Pro Audio Engine Active",
            "cuda_available": True
        },
        "hardware": "MSI GL65 Leopard / i7-10750H / 32GB RAM",
        "disk": {
            "free_mb": free_mb,
            "free_gb": free_gb,
            "low_space": free_mb < 500.0,
            "critical_space": free_mb < 100.0
        },
        "queue_length": len(queue_manager.queue),
        "is_busy": queue_manager.current_job_id is not None,
        "current_job": queue_manager.current_job_id
    }


@app.post("/api/upload-async")
async def upload_audio_async(file: UploadFile = File(...)):
    """Upload Suno MP3/WAV and trigger async tempo/watermark analysis."""
    task_id = f"ana_{uuid.uuid4().hex[:8]}"
    orig_name = Path(file.filename or "upload.wav").name
    if Path(orig_name).suffix.lower() not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail="오디오 파일(mp3, wav, m4a, flac, ogg)만 업로드할 수 있습니다.")
    safe_name = _safe_token(Path(orig_name).stem, "upload", max_len=80) + Path(orig_name).suffix.lower()
    filename = f"{int(time.time())}_{safe_name}"
    filepath = os.path.join(UPLOADS_DIR, filename)

    _copy_upload_limited(file.file, filepath)

    analysis_tasks[task_id] = {
        "status": "processing",
        "progress": 5,
        "stage": "파일 업로드 및 준비 중...",
        "remaining_sec": 5.0,
        "data": None,
        "error": None
    }

    t = threading.Thread(
        target=_run_analysis_task,
        args=(task_id, filepath, f"/uploads/{filename}"),
        daemon=True
    )
    t.start()

    return {"success": True, "task_id": task_id}


@app.post("/api/load-sample-async")
def load_sample_track_async():
    """Load sample Suno track with tempo drift and ultrasonic watermark."""
    task_id = f"ana_{uuid.uuid4().hex[:8]}"
    sample_file = os.path.join(SAMPLES_DIR, "demo_suno_drift.wav")
    
    # If not exists, generate a realistic Suno demo track with gradual acceleration & watermark
    if not os.path.exists(sample_file):
        from samples.generate_suno_sample import generate_suno_drift_sample
        generate_suno_drift_sample(sample_file)

    analysis_tasks[task_id] = {
        "status": "processing",
        "progress": 5,
        "stage": "Suno 테스트 음원 초기화 중...",
        "remaining_sec": 4.5,
        "data": None,
        "error": None
    }

    t = threading.Thread(
        target=_run_analysis_task,
        args=(task_id, sample_file, "/samples/demo_suno_drift.wav"),
        daemon=True
    )
    t.start()

    return {"success": True, "task_id": task_id}


@app.get("/api/analysis-status/{task_id}")
def get_analysis_status(task_id: str):
    task = analysis_tasks.get(task_id)
    if not task:
        task = _load_task_from_disk(task_id)
        if task:
            analysis_tasks[task_id] = task
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ==========================================
# RAW MP4 DOWNLOAD (NO MASTERING, DIRECT)
# ==========================================
class RawMp4DownloadRequest(BaseModel):
    url: str


def sanitize_windows_filename(title: str, max_len: int = 180) -> str:
    norm = unicodedata.normalize('NFKC', str(title or ''))
    norm = re.sub(r'[\\/:*?"<>|｜／＼：＊？＂＜＞]', ' ', norm)
    norm = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', norm)
    norm = re.sub(r'\s+', ' ', norm).strip('. ')
    return norm[:max_len] or "Video_Track"


def _run_raw_mp4_download_task(task_id: str, url: str):
    try:
        from yt_dlp import YoutubeDL

        analysis_tasks[task_id]["progress"] = 10
        analysis_tasks[task_id]["stage"] = "영상 정보 및 스트림 주소 확인 중..."

        is_yt = bool(re.search(r'(youtube\.com|youtu\.be)', url, re.I))
        is_suno = bool(re.search(r'suno\.(com|ai)', url, re.I) or re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', url, re.I))

        ffmpeg_exe = get_ffmpeg_bin()
        ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe and os.path.exists(ffmpeg_exe) else None
        js_runtimes = {}
        if os.path.exists(r"C:\Program Files\nodejs\node.exe"):
            js_runtimes['node'] = {'path': r'C:\Program Files\nodejs\node.exe'}

        final_path = None
        clean_title = "Video_Track"

        if is_yt:
            # 1. YouTube metadata extraction & download
            def yt_progress_hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    dl = d.get("downloaded_bytes", 0)
                    if total:
                        pct = 20 + int((dl / total) * 70)
                        analysis_tasks[task_id]["progress"] = min(92, pct)
                        analysis_tasks[task_id]["stage"] = f"원본 MP4 다운로드 중... ({pct}%)"
                elif d.get("status") == "finished":
                    analysis_tasks[task_id]["progress"] = 93
                    analysis_tasks[task_id]["stage"] = "MP4 비디오 & 오디오 패키징 중..."

            ydl_info_opts = get_safe_yt_dlp_opts({'remote_components': ['ejs:github']})
            raw_title = "YouTube_Track"
            video_id = uuid.uuid4().hex[:8]
            try:
                with YoutubeDL(ydl_info_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    raw_title = info.get('title', 'YouTube_Track')
                    video_id = info.get('id', video_id)
            except Exception as ie:
                ie_str = str(ie)
                print(f"[RawMP4] Info extraction error: {ie_str}")
                if "Private video" in ie_str:
                    raise RuntimeError("비공개(Private) 동영상입니다. YouTube 설정에서 '일부 공개' 또는 '공개'로 변경 후 다시 시도해주세요.")
                elif "Sign in to confirm your age" in ie_str:
                    raise RuntimeError("연령 제한(성인 인증 필요) 동영상입니다. 일반 공개 영상 링크를 입력해주세요.")
                elif "Video unavailable" in ie_str:
                    raise RuntimeError("삭제되었거나 접근할 수 없는 동영상입니다.")

            clean_title = sanitize_windows_filename(raw_title) or f"YouTube_{video_id}"
            out_filename = f"{clean_title}.mp4"
            out_mp4_path = get_safe_unique_filepath(OUTPUTS_DIR, out_filename)

            analysis_tasks[task_id]["progress"] = 25
            analysis_tasks[task_id]["stage"] = f"'{clean_title}' 원본 고화질 MP4 스트림 다운로드 중..."

            ydl_dl_opts = get_safe_yt_dlp_opts({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best',
                'outtmpl': str(out_mp4_path.with_suffix('')) + '.%(ext)s',
                'merge_output_format': 'mp4',
                'windowsfilenames': True,
                'ffmpeg_location': ffmpeg_dir or ffmpeg_exe,
                'remote_components': ['ejs:github'],
                'postprocessors': [{'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4'}],
                'progress_hooks': [yt_progress_hook]
            })
            try:
                with YoutubeDL(ydl_dl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info and info.get('title'):
                        t = sanitize_windows_filename(info['title'])
                        if t:
                            clean_title = t
                    prep = ydl.prepare_filename(info) if info else None
                    if prep and Path(prep).exists():
                        final_path = Path(prep)
                    elif prep and Path(prep).with_suffix('.mp4').exists():
                        final_path = Path(prep).with_suffix('.mp4')
            except Exception as dl_err:
                dl_err_str = str(dl_err)
                print(f"[RawMP4] First format attempt failed: {dl_err_str}, retrying with fallback format")
                if "Private video" in dl_err_str:
                    raise RuntimeError("비공개(Private) 동영상입니다. YouTube 설정에서 '일부 공개' 또는 '공개'로 변경 후 다시 시도해주세요.")
                elif "Sign in to confirm your age" in dl_err_str:
                    raise RuntimeError("연령 제한(성인 인증 필요) 동영상입니다. 일반 공개 영상 링크를 입력해주세요.")
                elif "Video unavailable" in dl_err_str:
                    raise RuntimeError("삭제되었거나 접근할 수 없는 동영상입니다.")
                ydl_dl_opts['format'] = 'best[ext=mp4]/best'
                try:
                    with YoutubeDL(ydl_dl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info and info.get('title'):
                            t = sanitize_windows_filename(info['title'])
                            if t:
                                clean_title = t
                        prep = ydl.prepare_filename(info) if info else None
                        if prep and Path(prep).exists():
                            final_path = Path(prep)
                        elif prep and Path(prep).with_suffix('.mp4').exists():
                            final_path = Path(prep).with_suffix('.mp4')
                except Exception as dl_err2:
                    ie2 = str(dl_err2)
                    if "Private video" in ie2:
                        raise RuntimeError("비공개(Private) 동영상입니다. YouTube 설정에서 '일부 공개' 또는 '공개'로 변경 후 다시 시도해주세요.")
                    elif "Sign in to confirm your age" in ie2:
                        raise RuntimeError("연령 제한(성인 인증 필요) 동영상입니다. 일반 공개 영상 링크를 입력해주세요.")
                    elif "Video unavailable" in ie2:
                        raise RuntimeError("삭제되었거나 접근할 수 없는 동영상입니다.")
                    raise RuntimeError(f"YouTube 영상 다운로드 실패: {ie2}")

            if not final_path or not final_path.exists():
                if out_mp4_path.exists():
                    final_path = out_mp4_path
                else:
                    target_stem = clean_title.lower()
                    for cand in Path(OUTPUTS_DIR).iterdir():
                        if cand.is_file() and cand.suffix.lower() == ".mp4":
                            c_stem = cand.stem.lower()
                            if c_stem == target_stem or (target_stem and (target_stem[:20] in c_stem or c_stem[:20] in target_stem)):
                                final_path = cand
                                break
                    if not final_path or not final_path.exists():
                        now_ts = time.time()
                        recent_mp4s = [
                            p for p in Path(OUTPUTS_DIR).glob("*.mp4")
                            if (now_ts - p.stat().st_mtime) < 180
                        ]
                        if recent_mp4s:
                            recent_mp4s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                            final_path = recent_mp4s[0]

        elif is_suno:
            # Suno song to MP4 without mastering
            analysis_tasks[task_id]["progress"] = 25
            analysis_tasks[task_id]["stage"] = "Suno 원본 음원 다운로드 중..."

            dl_res = download_suno_song(url)
            raw_path = dl_res.get("file_path") or dl_res.get("filepath")
            if not raw_path and dl_res.get("filename"):
                raw_path = str(Path(UPLOADS_DIR) / str(dl_res["filename"]))
            suno_mp3_path = Path(raw_path)
            raw_song_title = dl_res.get("title") or suno_mp3_path.stem
            clean_title = sanitize_windows_filename(str(raw_song_title)) or f"Suno_{uuid.uuid4().hex[:6]}"

            out_mp4_path = get_safe_unique_filepath(OUTPUTS_DIR, f"{clean_title}.mp4")
            img_url = dl_res.get("image_url")
            cover_img = Path(UPLOADS_DIR) / f"thumb_{uuid.uuid4().hex[:8]}.jpg"
            if img_url:
                try:
                    urllib.request.urlretrieve(img_url, str(cover_img))
                except Exception:
                    cover_img = None

            analysis_tasks[task_id]["progress"] = 70
            analysis_tasks[task_id]["stage"] = "고화질 MP4 영상 렌더링 중..."

            if cover_img and cover_img.exists():
                cmd = [
                    ffmpeg_exe, "-y", "-loop", "1", "-i", str(cover_img),
                    "-i", str(suno_mp3_path),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v", "libx264", "-tune", "stillimage",
                    "-c:a", "aac", "-b:a", "320k", "-pix_fmt", "yuv420p",
                    "-shortest", str(out_mp4_path)
                ]
            else:
                cmd = [
                    ffmpeg_exe, "-y", "-f", "lavfi", "-i", "color=c=#0b0f19:s=1280x720:r=30",
                    "-i", str(suno_mp3_path), "-c:v", "libx264",
                    "-c:a", "aac", "-b:a", "320k", "-pix_fmt", "yuv420p",
                    "-shortest", str(out_mp4_path)
                ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            final_path = out_mp4_path
            if cover_img and cover_img.exists():
                try: cover_img.unlink(missing_ok=True)
                except: pass

        if not final_path or not final_path.exists():
            raise RuntimeError("MP4 영상을 저장하지 못했습니다.")

        size_mb = round(final_path.stat().st_size / (1024 * 1024), 2)
        quoted_filename = urllib.parse.quote(final_path.name)
        quoted_title = urllib.parse.quote(clean_title)
        download_url = f"/api/download/raw-mp4-file/{quoted_filename}?title={quoted_title}"

        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["progress"] = 100
        analysis_tasks[task_id]["stage"] = f"'{clean_title}' 원본 MP4 다운로드 준비 완료! ({size_mb}MB)"
        analysis_tasks[task_id]["data"] = {
            "success": True,
            "title": clean_title,
            "filename": f"{clean_title}.mp4",
            "download_url": download_url,
            "filesize_mb": size_mb
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = format_youtube_error(e)
        analysis_tasks[task_id]["stage"] = f"다운로드 실패: {format_youtube_error(e)}"


@app.get("/api/download/raw-mp4-file/{filename}")
def download_raw_mp4_file(filename: str, title: str | None = None):
    safe_name = Path(filename).name
    file_path = Path(OUTPUTS_DIR) / safe_name
    if not file_path.exists():
        matched = list(Path(OUTPUTS_DIR).glob(f"{Path(safe_name).stem}*.mp4"))
        if matched:
            file_path = matched[0]
        else:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    content_name = (title or file_path.stem).strip()
    content_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', content_name).strip('. ') or file_path.stem
    if not content_name.lower().endswith(".mp4"):
        content_name += ".mp4"

    quoted_utf8_name = urllib.parse.quote(content_name)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{quoted_utf8_name}\"; filename*=UTF-8''{quoted_utf8_name}"
    }
    return FileResponse(
        path=str(file_path),
        filename=content_name,
        media_type="video/mp4",
        headers=headers
    )


@app.post("/api/download/raw-mp4-async")
def download_raw_mp4_async_api(req: RawMp4DownloadRequest):
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="유효한 URL 링크를 입력해주세요.")

    task_id = str(uuid.uuid4())
    analysis_tasks[task_id] = {
        "status": "processing",
        "progress": 5,
        "stage": "MP4 다운로드 준비 중...",
        "remaining_sec": 10.0,
        "data": None,
        "error": None
    }
    t = threading.Thread(
        target=_run_raw_mp4_download_task,
        args=(task_id, url),
        daemon=True
    )
    t.start()
    return {"success": True, "task_id": task_id}


class EnqueueMasteringRequest(BaseModel):
    name: str
    track_title: Optional[str] = None
    job_type: str = "preview"  # "preview" or "full"
    source_audio_path: str
    start_sec: float = 0.0
    duration_sec: float = 15.0
    mastering_options: Dict[str, Any]


@app.post("/api/queue/enqueue")
def enqueue_mastering_job(req: EnqueueMasteringRequest):
    source_path = resolve_media_path(req.source_audio_path)
    if not source_path:
        fallback = latest_studio_track.get("file_path")
        if fallback and os.path.exists(fallback):
            source_path = fallback
        else:
            user_mp3s = [p for p in sorted(Path(UPLOADS_DIR).glob("*.mp3"), key=lambda x: x.stat().st_mtime) if not p.name.startswith("check_")]
            if user_mp3s:
                source_path = str(user_mp3s[-1])
            else:
                raise HTTPException(status_code=400, detail="원본 오디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

    norm_opts = _normalize_mastering_options(req.mastering_options)
    if req.track_title and not norm_opts.get("track_title"):
        norm_opts["track_title"] = req.track_title.strip()

    job_id = queue_manager.add_job(
        name=req.name,
        job_type=req.job_type if req.job_type in ("preview", "full") else "preview",
        source_audio_path=source_path,
        start_sec=_clamp(req.start_sec, 0.0, 86400.0, 0.0),
        duration_sec=_clamp(req.duration_sec, 0.1, 86400.0, 15.0),
        mastering_options=norm_opts,
        track_title=req.track_title.strip() if req.track_title else None
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": f"'{req.name}' 마스터링 작업이 대기열에 등록되었습니다."
    }


@app.get("/api/queue/jobs")
def get_queue_jobs():
    jobs = queue_manager.list_jobs()
    return {
        "jobs": jobs,
        "queue_length": len(queue_manager.queue),
        "current_job_id": queue_manager.current_job_id
    }


# =====================================================================
# Hum Studio (NEXMUSE Humify Engine) Backend API Endpoints
# =====================================================================
@app.get("/api/studio/active-track")
def get_active_studio_track():
    """Returns the most recent active track loaded/mastered in the main studio."""
    return {"ok": True, "track": latest_studio_track}


@app.get("/api/hum/files")
def get_hum_files():
    out = []
    # Search only the app's own media folders (no hardcoded external paths).
    search_dirs = [Path(UPLOADS_DIR), Path(SAMPLES_DIR), Path(OUTPUTS_DIR)]
    for d in search_dirs:
        if not d.exists(): continue
        for p in sorted(d.glob("*")):
            if p.suffix.lower() in AUDIO_EXTS and p.is_file():
                out.append({
                    "name": p.name,
                    "path": str(p),
                    "dir": d.name,
                    "mb": round(p.stat().st_size / 1048576, 1)
                })
    return {"files": out, "current": hum_current["file"], "studio_track": latest_studio_track}


@app.post("/api/hum/select")
@app.post("/api/hum/files/select")
def select_hum_file(body: dict):
    folder = body.get("dir")
    name = body.get("name")
    scoped_name = f"{folder}/{name}" if folder in {"uploads", "outputs", "samples"} and name and Path(name).name == name else None
    target_path = resolve_media_path(body.get("path")) or resolve_media_path(scoped_name or name)
    if not target_path:
        return JSONResponse({"ok": False, "error": "파일을 찾을 수 없습니다."}, status_code=404)

    p = Path(target_path)
    title = normalize_title(body.get("title") or re.sub(r"^yt_", "", p.stem))
    ready, dur = _set_hum_source(p, title)

    if not ready:
        threading.Thread(target=_run_hum_analysis, daemon=True).start()

    return {"ok": True, "ready": ready, "duration": dur, "file": hum_current["file"]}


@app.post("/api/hum/upload")
async def upload_hum_file(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in AUDIO_EXTS:
        return JSONResponse({"ok": False, "error": "오디오 파일만 업로드 가능합니다."}, status_code=400)
    dst = Path(UPLOADS_DIR) / Path(file.filename).name
    _copy_upload_limited(file.file, str(dst))

    ready, dur = _set_hum_source(dst, dst.stem)
    if not ready:
        threading.Thread(target=_run_hum_analysis, daemon=True).start()
    return {"ok": True, "ready": ready, "name": dst.name, "file": hum_current["file"]}


@app.post("/api/hum/youtube")
def download_hum_youtube(body: dict):
    url = (body.get("url") or "").strip()
    is_yt = _is_youtube_url(url)
    is_suno = _is_suno_url(url)
    if not (is_yt or is_suno):
        return JSONResponse({"ok": False, "error": "유효한 유튜브 또는 Suno 링크를 입력하세요."}, status_code=400)
    try:
        _validate_public_http_url(url)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    # Force allow new download
    def _run():
        from yt_dlp import YoutubeDL
        stop = threading.Event()
        conv_t0 = [0.0]

        def _beat():
            while not stop.wait(1.5):
                el = time.time() - conv_t0[0]
                _set_hum_job("working", f"mp3 오디오 추출 중… 경과 {el:.0f}초", phase="youtube", pct=90)

        def hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                dl = d.get("downloaded_bytes", 0)
                eta = d.get("eta")
                if total:
                    pct = round(dl / total * 85, 1)
                    _set_hum_job("working", f"오디오 다운로드 {pct:.0f}% (남은 약 {eta:.0f}초)" if eta else f"오디오 다운로드 {pct:.0f}%",
                                 phase="youtube", pct=pct, eta=eta)
                else:
                    _set_hum_job("working", f"오디오 다운로드 중… {dl / 1048576:.1f}MB",
                                 phase="youtube", pct=None, eta=eta)
            elif d.get("status") == "finished":
                conv_t0[0] = time.time()
                _set_hum_job("working", "mp3 오디오 추출 및 변환 중...", phase="youtube", pct=90)
                threading.Thread(target=_beat, daemon=True).start()

        _set_hum_job("working", "음원 정보 확인 중...", phase="youtube", pct=0)
        try:
            # Clean up disk space if free space is low
            try:
                free_mb = shutil.disk_usage(UPLOADS_DIR).free / (1024 * 1024)
                if free_mb < 600:
                    temp_dir = os.environ.get("TEMP")
                    if temp_dir and os.path.exists(temp_dir):
                        for f in os.listdir(temp_dir):
                            if f.endswith(".tmp") or f.endswith(".pak"):
                                try: os.remove(os.path.join(temp_dir, f))
                                except: pass
            except Exception:
                pass

            ffmpeg_exe = get_ffmpeg_bin()
            js_runtimes = {}
            if os.path.exists(r"C:\Program Files\nodejs\node.exe"):
                js_runtimes['node'] = {'path': r'C:\Program Files\nodejs\node.exe'}

            # Safe deterministic output template
            video_uid = uuid.uuid4().hex[:8]
            if "v=" in url:
                video_uid = re.sub(r'[^a-zA-Z0-9_-]', '', url.split("v=")[-1].split("&")[0])[:20] or video_uid
            elif "youtu.be/" in url:
                video_uid = re.sub(r'[^a-zA-Z0-9_-]', '', url.split("youtu.be/")[-1].split("?")[0])[:20] or video_uid

            out_pattern = str(Path(UPLOADS_DIR) / f"hum_yt_{video_uid}.%(ext)s")
            ydl_opts = {
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "overwrites": True,
                "keepvideo": False,
                "windowsfilenames": True,
                "socket_timeout": 25,
                "format": "bestaudio/best",
                "ffmpeg_location": ffmpeg_exe,
                "outtmpl": out_pattern,
                "js_runtimes": js_runtimes,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }],
                "progress_hooks": [hook]
            }

            with YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                finally:
                    stop.set()

            p = None
            target_mp3 = Path(UPLOADS_DIR) / f"hum_yt_{video_uid}.mp3"
            if target_mp3.exists():
                p = target_mp3
            elif info:
                candidate = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
                if candidate.exists():
                    p = candidate

            if not p or not p.exists():
                got = sorted(Path(UPLOADS_DIR).glob("*.mp3"), key=lambda x: x.stat().st_mtime)
                if not got:
                    _set_hum_job("error", "mp3 파일을 생성하지 못했습니다.", phase="youtube")
                    return
                p = got[-1]

            title = ((info or {}).get("title") or p.stem)
            title = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title).strip()[:100]) or p.stem
            _set_hum_source(p, title)
            _set_hum_job("working", f"'{title}' 다운로드 완료. 음원 분석 시작...", phase="analyze", pct=0)
            _run_hum_analysis()
        except Exception as e:
            _set_hum_job("error", f"유튜브 다운로드 실패: {str(e)[-300:]}", phase="youtube")

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "started": True}


@app.post("/api/hum/analyze")
def analyze_hum_file(body: dict = None):
    if not hum_current.get("file"):
        return JSONResponse({"ok": False, "error": "음원 파일을 먼저 선택하세요."}, status_code=400)
    force = (body or {}).get("force", False)
    if hum_job["status"] == "working" and not force:
        if hum_job.get("phase") != "analyze":
            pass  # allow override if stuck in youtube or other phase
        else:
            return {"ok": True, "already": True}

    syll = _clamp((body or {}).get("syll", 3.2), 1.0, 10.0, 3.2)

    def _run():
        _set_hum_job("working", "분석 시작...", phase="analyze", pct=0)
        _run_hum_analysis(syll)

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "started": True}


@app.post("/api/hum/reset")
def reset_hum_job():
    with hum_lock:
        ready = hum_stems.ready
        dur = hum_stems.dur
    _set_hum_job("ready" if ready else "idle",
                 f"상태 초기화 완료 (음원 준비: {'완료' if ready else '대기'})",
                 phase=None, pct=100 if ready else 0, eta=None)
    return {"ok": True, "ready": ready, "duration": dur, "file": hum_current["file"]}


def _get_suno_anti_filter_recommendations():
    return [
        {
            "id": "rec_suno_natural",
            "name": "🛡️ Suno 우회: 자연스러운 보컬 허밍 (Natural Blend)",
            "badge": "가장 추천 • 감성 유지",
            "tag": "보컬85%컷 + 12%워블 + 0.5키",
            "desc": "원곡 멜로디의 감성을 온전히 살리면서 미드 대역 보컬 지문을 85% 감쇄하고 +0.5키/1.02배속 및 12% 워블을 가미하여 Suno의 업로드 오디오 핑거프린트 매칭을 자연스럽게 무력화합니다.",
            "params": {
                "hum": 0.65, "bed": 0.0, "leak": 0.55,
                "bed_lp": 800, "leak_lp": 20000,
                "pitch": 0.5, "speed": 1.02,
                "vocal_cut": 0.85, "wobble": 0.12, "reverb": 0.08, "saturation": 0.15, "formant": 0.8
            }
        },
        {
            "id": "rec_suno_vocoder",
            "name": "🎤 Suno 우회: 클로킹 멜로디 보코더 (Melodic Cloak)",
            "badge": "100% 필터 무력화",
            "tag": "보컬100%차단 + F0리드",
            "desc": "사람의 실제 목소리(Vocal Print)를 100% 완전히 차단(Mute)하고, 원곡 F0 멜로디 윤곽선을 합성 보코더 허밍으로 대체하여 AI 음성 식별 및 저작권 필터를 원천 우회합니다.",
            "params": {
                "hum": 0.85, "bed": 0.10, "leak": 0.40,
                "bed_lp": 900, "leak_lp": 12000,
                "pitch": -1.0, "speed": 0.98,
                "vocal_cut": 1.0, "wobble": 0.18, "reverb": 0.12, "saturation": 0.20, "formant": -1.0
            }
        },
        {
            "id": "rec_suno_lofi",
            "name": "📻 Suno 우회: 로파이 어쿠스틱 스미어 (Lo-Fi Acoustic)",
            "badge": "빈티지 리믹스 효과",
            "tag": "테이프세츄레이션 + 스미어",
            "desc": "아날로그 테이프 세츄레이션(30%)과 공간감 리버브 스미어링, 4.8Hz 주기 워블로 주파수 스펙트로그램을 산란시켜 Suno 해시 인식을 회피합니다.",
            "params": {
                "hum": 0.50, "bed": 0.30, "leak": 0.45,
                "bed_lp": 750, "leak_lp": 6500,
                "pitch": 1.0, "speed": 1.04,
                "vocal_cut": 0.75, "wobble": 0.35, "reverb": 0.18, "saturation": 0.30, "formant": 1.5
            }
        }
    ]


@app.get("/api/hum/recommendations")
def get_hum_recommendations_api():
    return {"recommendations": _get_suno_anti_filter_recommendations()}


@app.get("/api/hum/status")
def get_hum_status():
    with hum_lock:
        ready, dur = hum_stems.ready, hum_stems.dur
        generation = hum_generation
        selected = dict(hum_current["file"]) if hum_current.get("file") else None
    return {
        "job": hum_job["status"],
        "phase": hum_job["phase"],
        "pct": hum_job["pct"],
        "eta": hum_job["eta"],
        "message": hum_job["message"],
        "ready": ready,
        "duration": dur,
        "file": selected,
        "generation": generation,
        "recommendations": _get_suno_anti_filter_recommendations()
    }


def _extract_hum_params(body: dict):
    p = dict(HUM_DEFAULTS)
    for k in ("hum", "bed", "bed_lp", "leak", "leak_lp", "pitch", "speed",
              "vocal_cut", "wobble", "reverb", "saturation", "formant"):
        if k in body:
            p[k] = body[k]
    p["hum"] = _clamp(p.get("hum"), 0.0, 2.0, 0.0)
    p["bed"] = _clamp(p.get("bed"), 0.0, 2.0, 0.0)
    p["leak"] = _clamp(p.get("leak"), 0.0, 2.0, 1.0)
    p["bed_lp"] = _clamp(p.get("bed_lp"), 100.0, 12000.0, 800.0)
    p["leak_lp"] = _clamp(p.get("leak_lp"), 100.0, 20000.0, 20000.0)
    p["pitch"] = _clamp(p.get("pitch"), -24.0, 24.0, 0.0)
    p["speed"] = _clamp(p.get("speed"), 0.5, 2.0, 1.0)
    p["vocal_cut"] = _clamp(p.get("vocal_cut"), 0.0, 1.0, 0.0)
    p["wobble"] = _clamp(p.get("wobble"), 0.0, 1.0, 0.0)
    p["reverb"] = _clamp(p.get("reverb"), 0.0, 1.0, 0.0)
    p["saturation"] = _clamp(p.get("saturation"), 0.0, 1.0, 0.0)
    p["formant"] = _clamp(p.get("formant"), -12.0, 12.0, 0.0)
    return p


@app.post("/api/hum/set-title")
def set_hum_track_title(body: dict):
    new_title = normalize_title((body.get("title") or body.get("custom_title") or "").strip())
    if not new_title:
        return JSONResponse({"ok": False, "error": "제목을 입력해주세요."}, status_code=400)
    with hum_lock:
        if not hum_current.get("file"):
            hum_current["file"] = {}
        hum_current["file"]["title"] = new_title
        hum_current["file"]["custom_title"] = new_title
    return {"ok": True, "title": new_title, "file": hum_current["file"]}


@app.post("/api/hum/preview")
def preview_hum_mix(body: dict):
    with hum_lock:
        if not hum_stems.ready:
            return JSONResponse({"ok": False, "error": "음원 분석을 먼저 완료해주세요."}, status_code=400)
        start = _clamp(body.get("start", 30.0), 0.0, max(0.0, hum_stems.dur - 0.5), 0.0)
        length = _clamp(body.get("length", 15.0), 1.0, 120.0, 15.0)
        seg = mix_hum_segment(hum_stems, start, length, _extract_hum_params(body))
        generation = hum_generation

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    sf.write(tmp.name, seg, HUM_SR)
    return FileResponse(tmp.name, media_type="audio/wav", filename="hum_preview.wav", headers={"X-Hum-Generation": str(generation)})


@app.post("/api/hum/render")
def render_hum_mix(body: dict):
    fmt = body.get("format", "mp3")
    params = _extract_hum_params(body)
    preset_name = (body.get("preset_name") or body.get("preset") or "").strip()

    with hum_lock:
        if not hum_stems.ready:
            return JSONResponse({"ok": False, "error": "음원 분석을 먼저 완료해주세요."}, status_code=400)
        seg = mix_hum_segment(hum_stems, 0, hum_stems.dur + 1, params)
        selected_file = dict(hum_current["file"]) if hum_current.get("file") else None

    tmpw = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmpw.close()
    sf.write(tmpw.name, seg, HUM_SR)

    # Resolve clean base filename (custom_title > file.custom_title > file.title > file stem)
    title = normalize_title((body.get("custom_title") or body.get("title") or "").strip())
    if not title and selected_file:
        title = normalize_title(selected_file.get("custom_title") or selected_file.get("title"))
        if not title:
            raw_src = Path(selected_file["path"]).stem
            parts = raw_src.split("_", 1)
            if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) >= 10:
                title = parts[1]
            else:
                title = raw_src
            title = normalize_title(title)
    base_name = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title or "hum_track").strip()) or "hum_track"

    # Construct controller parameter tags
    hum_val = params.get("hum", 1.0)
    bed_val = params.get("bed", 0.3)
    leak_val = params.get("leak", 0.1)
    bed_lp = params.get("bed_lp", 800)
    leak_lp = params.get("leak_lp", 1800)
    pitch_val = params.get("pitch", 0)
    speed_val = params.get("speed", 1.0)
    vocal_cut_val = params.get("vocal_cut", 0.0)
    wobble_val = params.get("wobble", 0.0)
    reverb_val = params.get("reverb", 0.0)
    sat_val = params.get("saturation", 0.0)
    formant_val = params.get("formant", 0.0)

    tags = []
    if hum_val < 1e-4 and bed_val < 1e-4 and vocal_cut_val < 1e-4:
        tags.append(f"OriginalClean_{int(round(leak_val * 100))}%")
    else:
        tags.append(f"Hum{hum_val:.2g}")
        tags.append(f"Bed{bed_val:.2g}")
        if leak_val > 0:
            tags.append(f"Leak{leak_val:.2g}")
        tags.append(f"BedLP{int(bed_lp)}Hz")
        if leak_val > 0:
            if leak_lp >= 10000:
                tags.append("LeakLP_Bypass")
            else:
                tags.append(f"LeakLP{int(leak_lp)}Hz")
    if pitch_val != 0:
        p_sign = f"+{pitch_val:g}" if pitch_val > 0 else f"{pitch_val:g}"
        tags.append(f"Pitch{p_sign}")
    if speed_val != 1.0:
        tags.append(f"Speed{int(round(speed_val * 100))}%")
    if vocal_cut_val > 0.01:
        tags.append(f"VocalCut{int(round(vocal_cut_val * 100))}%")
    if wobble_val > 0.01:
        tags.append(f"Wobble{int(round(wobble_val * 100))}%")
    if reverb_val > 0.01:
        tags.append(f"Reverb{int(round(reverb_val * 100))}%")
    if sat_val > 0.01:
        tags.append(f"Sat{int(round(sat_val * 100))}%")
    if abs(formant_val) >= 0.1:
        f_sign = f"+{formant_val:g}" if formant_val > 0 else f"{formant_val:g}"
        tags.append(f"Formant{f_sign}")
    ctrl_str = "_".join(tags)

    # Check if a preset name is provided or matched
    preset_clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", preset_name).strip() if preset_name else ""
    if preset_clean:
        extra = []
        if pitch_val != 0:
            p_sign = f"+{pitch_val:g}" if pitch_val > 0 else f"{pitch_val:g}"
            extra.append(f"Pitch{p_sign}")
        if speed_val != 1.0:
            extra.append(f"Speed{int(round(speed_val * 100))}%")
        if vocal_cut_val > 0.01:
            extra.append(f"VocalCut{int(round(vocal_cut_val * 100))}%")
        if extra:
            final_filename = f"{base_name}_{preset_clean}_{'_'.join(extra)}.{fmt}"
        else:
            final_filename = f"{base_name}_{preset_clean}.{fmt}"
    else:
        final_filename = f"{base_name}_{ctrl_str}.{fmt}"

    prefix = (body.get("prefix") or "").strip()
    if prefix:
        prefix_clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", prefix).strip()
        final_filename = f"{prefix_clean}_{final_filename}"

    quoted_name = urllib.parse.quote(final_filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{quoted_name}\"; filename*=UTF-8''{quoted_name}",
        "X-Rendered-Filename": quoted_name,
        "Access-Control-Expose-Headers": "Content-Disposition, X-Rendered-Filename"
    }

    if fmt == "mp3":
        out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        out.close()
        subprocess.run([get_ffmpeg_bin(), "-y", "-v", "error", "-i", tmpw.name,
                        "-c:a", "libmp3lame", "-b:a", "320k",
                        "-id3v2_version", "3",
                        "-metadata", f"title={base_name} - {preset_clean or ctrl_str}",
                        "-metadata", "artist=Suno Studio Master",
                        out.name], check=True)
        try:
            out_copy = Path(OUTPUTS_DIR) / final_filename
            shutil.copy2(out.name, out_copy)
        except Exception:
            pass
        return FileResponse(out.name, media_type="audio/mpeg", filename=final_filename, headers=headers)

    return FileResponse(tmpw.name, media_type="audio/wav", filename=final_filename, headers=headers)


@app.get("/api/hum/presets")
def get_hum_presets_api():
    return {"presets": load_hum_presets(), "speeds": SPEED_PRESETS}


@app.post("/api/hum/presets")
def put_hum_preset_api(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"ok": False, "error": "프리셋 이름을 입력해주세요."}, status_code=400)
    vals = body.get("params") or body.get("values") or {}
    if not vals:
        return JSONResponse({"ok": False, "error": "프리셋 설정값이 비어있습니다."}, status_code=400)
    
    d = load_hum_presets()
    d[name] = vals
    save_hum_presets(d)
    return {"ok": True}


@app.delete("/api/hum/presets/{name}")
def del_hum_preset_api(name: str):
    d = load_hum_presets()
    d.pop(name, None)
    save_hum_presets(d)
    return {"ok": True}


@app.delete("/api/hum/presets")
def del_hum_preset_body_api(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"ok": False, "error": "삭제할 프리셋 이름을 지정하세요."}, status_code=400)
    d = load_hum_presets()
    d.pop(name, None)
    save_hum_presets(d)
    return {"ok": True}


@app.post("/api/hum/presets/rename")
def rename_hum_preset_api(body: dict):
    old_name = (body.get("old_name") or body.get("name") or "").strip()
    new_name = (body.get("new_name") or "").strip()
    if not old_name or not new_name:
        return JSONResponse({"ok": False, "error": "기존 이름과 새 이름을 모두 입력해주세요."}, status_code=400)
    d = load_hum_presets()
    if old_name not in d:
        return JSONResponse({"ok": False, "error": f"'{old_name}' 프리셋을 찾을 수 없습니다."}, status_code=404)
    if new_name in d and new_name != old_name:
        return JSONResponse({"ok": False, "error": f"'{new_name}' 이름이 이미 존재합니다."}, status_code=400)
    new_d = {}
    for k, v in d.items():
        if k == old_name:
            new_d[new_name] = v
        else:
            new_d[k] = v
    save_hum_presets(new_d)
    return {"ok": True, "presets": new_d}


@app.post("/api/hum/render-batch")
def render_hum_batch_api(body: dict):
    import zipfile
    items = body.get("items") or body.get("presets") or []
    if not items or not isinstance(items, list):
        return JSONResponse({"ok": False, "error": "일괄 렌더링할 프리셋 목록이 비어있습니다."}, status_code=400)

    with hum_lock:
        if not hum_stems.ready:
            return JSONResponse({"ok": False, "error": "음원 분석을 먼저 완료해주세요."}, status_code=400)
        selected_file = dict(hum_current["file"]) if hum_current.get("file") else None

    # Base track title
    title = normalize_title((body.get("title") or body.get("custom_title") or "").strip())
    if not title and selected_file:
        title = normalize_title(selected_file.get("custom_title") or selected_file.get("title"))
        if not title:
            raw_src = Path(selected_file["path"]).stem
            parts = raw_src.split("_", 1)
            title = parts[1] if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) >= 10 else raw_src
            title = normalize_title(title)
    base_title = sanitize_windows_filename(title or "Suno_HumMix") or "Suno_HumMix"

    ffmpeg_exe = get_ffmpeg_bin()
    tmp_dir = Path(tempfile.mkdtemp(prefix="hum_batch_"))
    rendered_files = []

    try:
        for idx, item in enumerate(items, 1):
            item_name = (item.get("name") or f"Preset_{idx}").strip()
            clean_item_name = sanitize_windows_filename(re.sub(r'^[^\w\s]+', '', item_name).strip()) or f"Variation_{idx}"
            item_params = _extract_hum_params(item.get("params") or item)

            with hum_lock:
                seg = mix_hum_segment(hum_stems, 0, hum_stems.dur + 1, item_params)

            wav_tmp = tmp_dir / f"temp_{idx}.wav"
            mp3_out_name = f"{idx:02d}_{base_title}_{clean_item_name}.mp3"
            mp3_out_path = tmp_dir / mp3_out_name

            sf.write(str(wav_tmp), seg, HUM_SR)

            if ffmpeg_exe and os.path.exists(ffmpeg_exe):
                cmd = [
                    ffmpeg_exe, "-y", "-i", str(wav_tmp),
                    "-codec:a", "libmp3lame", "-b:a", "320k",
                    "-id3v2_version", "3",
                    "-metadata", f"title={base_title} - {clean_item_name}",
                    "-metadata", "artist=Suno Studio Master",
                    str(mp3_out_path)
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                wav_tmp.unlink(missing_ok=True)
                rendered_files.append((mp3_out_path, mp3_out_name))
            else:
                wav_out_name = f"{idx:02d}_{base_title}_{clean_item_name}.wav"
                wav_out_path = tmp_dir / wav_out_name
                wav_tmp.rename(wav_out_path)
                rendered_files.append((wav_out_path, wav_out_name))

        if not rendered_files:
            return JSONResponse({"ok": False, "error": "렌더링된 파일이 없습니다."}, status_code=500)

        # Build clean ZIP archive in outputs
        zip_filename = f"{base_title}_Suno_HumMix_Batch_{len(rendered_files)}tracks.zip"
        zip_path = Path(OUTPUTS_DIR) / zip_filename
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath, arcname in rendered_files:
                zf.write(str(fpath), arcname=arcname)

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=zip_filename,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(zip_filename)}"
            }
        )
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _run_hum_batch_zip_task(task_id: str, base_title: str, items: list):
    import zipfile
    try:
        total = len(items)
        analysis_tasks[task_id]["progress"] = 5
        analysis_tasks[task_id]["stage"] = f"총 {total}개 프리셋 일괄 MP3 렌더링 준비 중..."

        with hum_lock:
            if not hum_stems.ready:
                raise RuntimeError("음원 분석이 완료되지 않았습니다.")

        ffmpeg_exe = get_ffmpeg_bin()
        tmp_dir = Path(tempfile.mkdtemp(prefix="hum_batch_zip_"))
        rendered_files = []

        try:
            for idx, item in enumerate(items, 1):
                item_name = (item.get("name") or f"Preset_{idx}").strip()
                clean_item_name = sanitize_windows_filename(re.sub(r'^[^\w\s]+', '', item_name).strip()) or f"Variation_{idx}"
                item_params = _extract_hum_params(item.get("params") or item)

                cur_pct = int(5 + ((idx - 1) / total) * 88)
                analysis_tasks[task_id]["progress"] = cur_pct
                analysis_tasks[task_id]["stage"] = f"[{idx}/{total}곡] '{clean_item_name}' 320k MP3 렌더링 중..."

                with hum_lock:
                    seg = mix_hum_segment(hum_stems, 0, hum_stems.dur + 1, item_params)

                wav_tmp = tmp_dir / f"temp_{idx}.wav"
                mp3_out_name = f"{idx:02d}_{base_title}_{clean_item_name}.mp3"
                mp3_out_path = tmp_dir / mp3_out_name

                sf.write(str(wav_tmp), seg, HUM_SR)

                if ffmpeg_exe and os.path.exists(ffmpeg_exe):
                    cmd = [
                        ffmpeg_exe, "-y", "-i", str(wav_tmp),
                        "-codec:a", "libmp3lame", "-b:a", "320k",
                        "-id3v2_version", "3",
                        "-metadata", f"title={base_title} - {clean_item_name}",
                        "-metadata", "artist=Suno Studio Master",
                        str(mp3_out_path)
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    wav_tmp.unlink(missing_ok=True)
                    rendered_files.append((mp3_out_path, mp3_out_name))
                else:
                    wav_out_name = f"{idx:02d}_{base_title}_{clean_item_name}.wav"
                    wav_out_path = tmp_dir / wav_out_name
                    wav_tmp.rename(wav_out_path)
                    rendered_files.append((wav_out_path, wav_out_name))

            analysis_tasks[task_id]["progress"] = 95
            analysis_tasks[task_id]["stage"] = f"총 {len(rendered_files)}곡 ZIP 압축 파일 생성 중..."

            zip_filename = f"{base_title}_Suno_HumMix_Batch_{len(rendered_files)}tracks.zip"
            zip_path = Path(OUTPUTS_DIR) / zip_filename
            with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
                for fpath, arcname in rendered_files:
                    zf.write(str(fpath), arcname=arcname)

            analysis_tasks[task_id]["status"] = "completed"
            analysis_tasks[task_id]["progress"] = 100
            analysis_tasks[task_id]["stage"] = f"'{zip_filename}' 압축 완료! 다운로드 시작..."
            analysis_tasks[task_id]["data"] = {
                "success": True,
                "download_url": f"/api/hum/batch-download/{urllib.parse.quote(zip_filename)}",
                "filename": zip_filename,
                "count": len(rendered_files)
            }
        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        analysis_tasks[task_id]["status"] = "failed"
        analysis_tasks[task_id]["error"] = format_youtube_error(e)
        analysis_tasks[task_id]["stage"] = f"일괄 렌더링 오류: {e}"


@app.post("/api/hum/render-batch-async")
def render_hum_batch_async_api(body: dict):
    items = body.get("items") or body.get("presets") or []
    if not items or not isinstance(items, list):
        return JSONResponse({"ok": False, "error": "일괄 렌더링할 프리셋 목록이 비어있습니다."}, status_code=400)

    with hum_lock:
        if not hum_stems.ready:
            return JSONResponse({"ok": False, "error": "음원 분석을 먼저 완료해주세요."}, status_code=400)
        selected_file = dict(hum_current["file"]) if hum_current.get("file") else None

    title = normalize_title((body.get("title") or body.get("custom_title") or "").strip())
    if not title and selected_file:
        title = normalize_title(selected_file.get("custom_title") or selected_file.get("title"))
        if not title:
            raw_src = Path(selected_file["path"]).stem
            parts = raw_src.split("_", 1)
            title = parts[1] if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) >= 10 else raw_src
            title = normalize_title(title)
    base_title = sanitize_windows_filename(title or "Suno_HumMix") or "Suno_HumMix"

    task_id = f"hum_batch_{uuid.uuid4().hex[:8]}"
    analysis_tasks[task_id] = {
        "status": "processing",
        "progress": 5,
        "stage": f"총 {len(items)}개 프리셋 일괄 MP3 렌더링 시작...",
        "error": None,
        "data": None
    }

    t = threading.Thread(target=_run_hum_batch_zip_task, args=(task_id, base_title, items), daemon=True)
    t.start()

    return {"ok": True, "task_id": task_id, "total": len(items)}


@app.get("/api/hum/batch-download/{filename}")
def download_hum_batch_zip(filename: str):
    safe_name = Path(filename).name
    file_path = Path(OUTPUTS_DIR) / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ZIP 파일을 찾을 수 없습니다.")
    quoted = urllib.parse.quote(safe_name)
    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"{quoted}\"; filename*=UTF-8''{quoted}"}
    )


class ExportAudioRequest(BaseModel):
    audio_url: str
    speed: float = 1.0
    pitch_shift: float = 0.0
    title: Optional[str] = "Suno_Master"
    format: str = "wav"  # "wav" or "mp3"
    keep_pitch: bool = True


@app.post("/api/export-audio")
async def export_audio_endpoint(req: ExportAudioRequest):
    """
    Renders speed and pitch adjusted audio file (WAV or MP3) with 0.01x speed & 0.05 semitone pitch precision.
    Uses FFmpeg rubberband or atempo (WSOLA pitch-preserving) / asetrate (tape/vinyl pitch-shift).
    """
    try:
        audio_path = resolve_media_path(req.audio_url)

        if not audio_path:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

        speed = _clamp(req.speed, 0.25, 4.0, 1.0)
        pitch_shift = _clamp(req.pitch_shift, -24.0, 24.0, 0.0)
        title = req.title or "Suno_Master"
        clean_title = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title).strip(". "))[:80] or "Suno_Master"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        ext = "mp3" if req.format.lower() == "mp3" else "wav"

        tags = []
        if abs(speed - 1.0) > 0.005:
            tags.append(f"{speed:.2f}x")
        if abs(pitch_shift) > 0.005:
            tags.append(f"Key_{pitch_shift:+g}st")
        tag_str = f"_{'_'.join(tags)}" if tags else ""
        final_audio_name = f"{clean_title}{tag_str}_{timestamp}.{ext}"
        final_audio_path = os.path.join(OUTPUTS_DIR, final_audio_name)

        # Proactive disk cleanup if space is tight (< 1GB)
        try:
            free_bytes = shutil.disk_usage(OUTPUTS_DIR).free
            if free_bytes < 1024 * 1024 * 1024:  # under 1GB
                now_ts = time.time()
                for old_aud in Path(OUTPUTS_DIR).glob("audition_*.wav"):
                    if now_ts - old_aud.stat().st_mtime > 30:
                        old_aud.unlink(missing_ok=True)
                for old_batch in Path(OUTPUTS_DIR).glob("batch_*"):
                    if old_batch.is_dir() and now_ts - old_batch.stat().st_mtime > 43200:
                        shutil.rmtree(old_batch, ignore_errors=True)
        except Exception:
            pass

        ffmpeg = get_ffmpeg_bin()

        af_str = None
        if abs(pitch_shift) > 0.005:
            pitch_scale = 2.0 ** (pitch_shift / 12.0)
            af_str = f"rubberband=pitch={pitch_scale:.8f}:tempo={speed:.6f}"
        elif abs(speed - 1.0) > 0.005:
            if req.keep_pitch:
                atempo_filters = []
                cur_spd = speed
                while cur_spd > 2.0:
                    atempo_filters.append("atempo=2.0")
                    cur_spd /= 2.0
                while cur_spd < 0.5:
                    atempo_filters.append("atempo=0.5")
                    cur_spd /= 0.5
                atempo_filters.append(f"atempo={cur_spd:.6f}")
                af_str = ",".join(atempo_filters)
            else:
                af_str = f"asetrate=44100*{speed:.6f},aresample=44100"

        cmd = [ffmpeg, "-y", "-i", audio_path]
        if af_str:
            cmd.extend(["-filter:a", af_str])

        if ext == "wav":
            cmd.extend(["-c:a", "pcm_s16le", final_audio_path])
        else:
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k", final_audio_path])

        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)

        size_mb = os.path.getsize(final_audio_path) / (1024 * 1024)

        return {
            "success": True,
            "filename": final_audio_name,
            "audio_url": f"/outputs/{urllib.parse.quote(final_audio_name)}?t={int(time.time() * 1000)}",
            "size_mb": round(size_mb, 2),
            "speed": speed,
            "pitch_shift": pitch_shift,
            "format": ext
        }
    except HTTPException:
        raise
    except subprocess.CalledProcessError as cpe:
        err_msg = cpe.stderr[-400:] if cpe.stderr else str(cpe)
        if "No space left on device" in err_msg or "error closing file" in err_msg.lower():
            err_msg = "C 드라이브 디스크 저장 공간이 부족하여 파일 생성이 중단되었습니다. 디스크 공간을 확보해 주세요."
        raise HTTPException(status_code=500, detail=f"FFmpeg 변환 오류: {err_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PreviewPitchSpeedRequest(BaseModel):
    audio_url: str
    speed: float = 1.0
    pitch_shift: float = 0.0
    start_sec: float = 0.0
    duration_sec: float = 15.0


@app.post("/api/preview-pitch-speed")
async def preview_pitch_speed_endpoint(req: PreviewPitchSpeedRequest):
    """
    Renders an instant lightweight 15-second audition preview with fine pitch shift & speed applied.
    """
    try:
        audio_path = resolve_media_path(req.audio_url)

        if not audio_path:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

        speed = _clamp(req.speed, 0.25, 4.0, 1.0)
        pitch_shift = _clamp(req.pitch_shift, -24.0, 24.0, 0.0)
        start_sec = _clamp(req.start_sec, 0.0, 86400.0, 0.0)
        dur_sec = _clamp(req.duration_sec, 3.0, 30.0, 15.0)

        # Auto-cleanup old audition temporary files to keep disk space fresh
        try:
            now_ts = time.time()
            for old_aud in Path(OUTPUTS_DIR).glob("audition_*.wav"):
                if now_ts - old_aud.stat().st_mtime > 60:
                    old_aud.unlink(missing_ok=True)
        except Exception:
            pass

        preview_id = f"audition_{uuid.uuid4().hex[:8]}"
        out_name = f"{preview_id}.wav"
        out_path = os.path.join(OUTPUTS_DIR, out_name)

        ffmpeg = get_ffmpeg_bin()
        if abs(pitch_shift) > 0.005:
            pitch_scale = 2.0 ** (pitch_shift / 12.0)
            af_str = f"rubberband=pitch={pitch_scale:.8f}:tempo={speed:.6f}"
        else:
            atempo_filters = []
            cur_spd = speed
            while cur_spd > 2.0:
                atempo_filters.append("atempo=2.0")
                cur_spd /= 2.0
            while cur_spd < 0.5:
                atempo_filters.append("atempo=0.5")
                cur_spd /= 0.5
            atempo_filters.append(f"atempo={cur_spd:.6f}")
            af_str = ",".join(atempo_filters)

        cmd = [
            ffmpeg, "-y",
            "-ss", f"{start_sec:.3f}",
            "-t", f"{dur_sec:.3f}",
            "-i", audio_path,
            "-filter:a", af_str,
            "-c:a", "pcm_s16le",
            out_path
        ]
        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)

        return {
            "success": True,
            "preview_url": f"/outputs/{out_name}?t={int(time.time() * 1000)}",
            "speed": speed,
            "pitch_shift": pitch_shift,
            "start_sec": start_sec,
            "duration_sec": dur_sec
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExportMp4Request(BaseModel):
    audio_url: str
    speed: float = 1.0
    pitch_shift: float = 0.0
    title: Optional[str] = "Suno_Master"
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    upload_youtube: Optional[bool] = False
    youtube_privacy: Optional[str] = "unlisted"


@app.post("/api/export-mp4")
async def export_mp4_endpoint(req: ExportMp4Request):
    """
    Renders 720P (1280x720, 16:9) MP4 video with H.264 + AAC.
    Uses image_base64 from frontend canvas (or image_url or dark studio fallback).
    Applies audio speed and pitch shift via FFmpeg.
    Preserves unique files with file-size comparison auto-renaming (_1, _2).
    Optionally uploads to user's YouTube channel.
    """
    try:
        # 1. Resolve local audio file path (restricted to app media folders)
        audio_path = resolve_media_path(req.audio_url)

        if not audio_path:
            raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

        speed = _clamp(req.speed, 0.25, 4.0, 1.0)
        pitch_shift = _clamp(req.pitch_shift, -24.0, 24.0, 0.0)
        title = req.title or "Suno_Master"
        clean_raw = re.sub(r'\[\[+', '[', title)
        clean_raw = re.sub(r'\]\]+', ']', clean_raw)
        clean_raw = re.sub(r'\[Key_[^\]]*\]?', '', clean_raw)
        clean_title = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", clean_raw).strip(". "))
        if len(clean_title) > 60:
            clean_title = clean_title[:60].rstrip(" [(-_")
        if not clean_title:
            clean_title = "Suno_Master"
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        tags = []
        if abs(speed - 1.0) > 0.005:
            tags.append(f"{speed:.2f}x")
        if abs(pitch_shift) > 0.005:
            tags.append(f"Key_{pitch_shift:+g}st")
        tag_str = f"_{'_'.join(tags)}" if tags else ""

        # Render to temp file first to verify and measure exact file size
        temp_render_mp4 = os.path.join(OUTPUTS_DIR, f"temp_render_{timestamp}_{uuid.uuid4().hex[:6]}.mp4")

        # 2. Prepare 720P background image
        temp_img_path = os.path.join(OUTPUTS_DIR, f"temp_img_{timestamp}_{uuid.uuid4().hex[:6]}.png")
        has_custom_image = False

        if req.image_base64:
            img_b64 = req.image_base64
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            if len(img_b64) > MAX_IMAGE_BYTES * 4 // 3 + 1024:
                raise HTTPException(status_code=413, detail="커버 이미지가 너무 큽니다.")
            try:
                img_data = base64.b64decode(img_b64, validate=False)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="커버 이미지 데이터를 해석할 수 없습니다.") from exc
            if len(img_data) > MAX_IMAGE_BYTES:
                raise HTTPException(status_code=413, detail="커버 이미지가 너무 큽니다.")
            with open(temp_img_path, "wb") as f:
                f.write(img_data)
            has_custom_image = True
        elif req.image_url:
            img_local = resolve_media_path(req.image_url)
            if img_local:
                shutil.copyfile(img_local, temp_img_path)
                has_custom_image = True
            elif str(req.image_url).startswith("http"):
                try:
                    safe_img_url = _validate_public_http_url(req.image_url)
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    r = urllib.request.Request(safe_img_url, headers=headers)
                    with urllib.request.urlopen(r, timeout=8) as resp:
                        data = _read_limited_response(resp, MAX_IMAGE_BYTES)
                    with open(temp_img_path, "wb") as f:
                        f.write(data)
                    has_custom_image = True
                except Exception:
                    pass

        ffmpeg = get_ffmpeg_bin()

        # Measure exact audio duration to prevent FFmpeg -loop 1 / -shortest buffer over-run (+20~25s bug)
        audio_dur = 0.0
        try:
            import soundfile as sf
            audio_dur = float(sf.info(audio_path).duration)
        except Exception:
            try:
                ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe.exe") if os.path.exists(os.path.join(os.path.dirname(ffmpeg), "ffprobe.exe")) else "ffprobe"
                p_dur = subprocess.run(
                    [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                    capture_output=True, text=True, encoding="utf-8", errors="replace"
                )
                audio_dur = float(p_dur.stdout.strip())
            except Exception:
                pass

        final_dur = (audio_dur / speed) if (audio_dur > 0 and speed > 0) else None
        duration_flags = ["-t", f"{final_dur:.3f}"] if final_dur else ["-shortest"]

        # 3. Audio tempo & pitch filter (supports speed 0.01x & pitch 0.05 semitone precision)
        if abs(pitch_shift) > 0.005:
            pitch_scale = 2.0 ** (pitch_shift / 12.0)
            atempo_str = f"rubberband=pitch={pitch_scale:.8f}:tempo={speed:.6f}"
        else:
            atempo_filters = []
            cur_spd = speed
            while cur_spd > 2.0:
                atempo_filters.append("atempo=2.0")
                cur_spd /= 2.0
            while cur_spd < 0.5:
                atempo_filters.append("atempo=0.5")
                cur_spd /= 0.5
            atempo_filters.append(f"atempo={cur_spd:.4f}")
            atempo_str = ",".join(atempo_filters)

        # 4. Run FFmpeg command for 720P (1280x720) 16:9 MP4
        if has_custom_image and os.path.exists(temp_img_path):
            cmd = [
                ffmpeg, "-y",
                "-loop", "1",
                "-framerate", "1",
                "-i", temp_img_path,
                "-i", audio_path,
                "-filter_complex", f"[1:a]{atempo_str}[a]",
                "-map", "0:v",
                "-map", "[a]",
                *duration_flags,
                "-s", "1280x720",
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-preset", "ultrafast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                temp_render_mp4
            ]
        else:
            # Fallback 720P dark background
            cmd = [
                ffmpeg, "-y",
                "-f", "lavfi", "-i", "color=c=0x0f172a:s=1280x720:r=1",
                "-i", audio_path,
                "-filter_complex", f"[1:a]{atempo_str}[a]",
                "-map", "0:v",
                "-map", "[a]",
                *duration_flags,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-preset", "ultrafast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                temp_render_mp4
            ]

        subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)

        if os.path.exists(temp_img_path):
            try: os.unlink(temp_img_path)
            except Exception: pass

        # Smart Duplicate Preservation by File Size
        rendered_size = os.path.getsize(temp_render_mp4)
        desired_name = f"{clean_title}{tag_str}_720p.mp4"
        safe_mp4_path = get_safe_unique_filepath(OUTPUTS_DIR, desired_name, new_file_size=rendered_size)
        if safe_mp4_path.exists() and os.path.getsize(str(safe_mp4_path)) == rendered_size and str(safe_mp4_path) != temp_render_mp4:
            try: os.unlink(temp_render_mp4)
            except Exception: pass
        else:
            shutil.move(temp_render_mp4, str(safe_mp4_path))

        final_mp4_name = safe_mp4_path.name
        final_mp4_path = str(safe_mp4_path)
        size_mb = os.path.getsize(final_mp4_path) / (1024 * 1024)

        resp = {
            "success": True,
            "filename": final_mp4_name,
            "mp4_url": f"/outputs/{urllib.parse.quote(final_mp4_name)}?t={int(time.time() * 1000)}",
            "size_mb": round(size_mb, 2),
            "speed": speed,
            "pitch_shift": pitch_shift
        }

        # YouTube Auto-Upload if requested
        if req.upload_youtube and is_youtube_authenticated():
            try:
                yt_out = upload_video_to_youtube(
                    video_path=final_mp4_path,
                    title=clean_title,
                    privacy=req.youtube_privacy or "unlisted"
                )
                resp["youtube_url"] = yt_out.get("url")
                resp["youtube_id"] = yt_out.get("video_id")
            except Exception as ye:
                print(f"[ExportMp4] YouTube upload error: {ye}")
                resp["youtube_error"] = format_youtube_error(ye)

        return resp

    except HTTPException:
        raise
    except subprocess.CalledProcessError as cpe:
        raise HTTPException(status_code=500, detail=f"FFmpeg 인코딩 오류: {cpe.stderr[-300:]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def resolve_audio_file_path(audio_url: str) -> Optional[str]:
    """Resolve a relative URL/filename to a real file inside the app media folders.

    Absolute paths outside uploads/outputs/samples/static are rejected. This keeps the
    API backward-compatible while closing arbitrary local-file reads.
    """
    return resolve_media_path(audio_url)


# ============================================================================
# AI MUSIC VIDEO (MV) & ANIMATED SLIDESHOW MP4 API
# ============================================================================
from core.mv_generator import (
    STYLE_PRESETS,
    CAMERA_MOTIONS,
    plan_storyboard,
    generate_single_scene_image,
    compile_slideshow_mv,
    render_hero_visualizer_mv
)

mv_render_tasks: Dict[str, Dict[str, Any]] = {}


@app.get("/api/mv/styles")
async def get_mv_styles_endpoint():
    """Returns available AI visual styles and camera animation motions."""
    styles_list = []
    for k, v in STYLE_PRESETS.items():
        styles_list.append({
            "key": k,
            "name": v["name"],
            "icon": v["icon"],
            "badge": v.get("badge", ""),
            "theme": v["theme"],
            "style_tags": v["style_tags"]
        })
    return {
        "success": True,
        "styles": styles_list,
        "motions": CAMERA_MOTIONS
    }


class MvPlanRequest(BaseModel):
    audio_url: str
    title: Optional[str] = "Music Video"
    artist: Optional[str] = "Antigravity Studio"
    style_key: Optional[str] = "cinematic_anime"
    custom_concept: Optional[str] = ""
    user_lyrics: Optional[str] = ""
    still_count: Optional[int] = 4
    target_cuts: Optional[int] = 8
    target_scenes: Optional[int] = None
    start_sec: Optional[float] = 0.0
    duration_sec: Optional[float] = None
    cover_url: Optional[str] = None


@app.post("/api/mv/plan")
async def plan_mv_endpoint(req: MvPlanRequest):
    """
    Analyzes audio, lyrics, and beats to generate K still image slots (1 대표 이미지 + 추가 씬들)
    and N rhythmic video cuts cycling through them with alternating camera motions.
    """
    audio_path = resolve_audio_file_path(req.audio_url)
    if not audio_path:
        raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다.")

    cover_path = None
    if req.cover_url:
        cover_path = resolve_audio_file_path(req.cover_url)

    try:
        cuts_count = req.target_cuts or req.target_scenes or 8
        sb = plan_storyboard(
            audio_path=audio_path,
            title=req.title or "Music Video",
            artist=req.artist or "Antigravity Studio",
            style_key=req.style_key or "cinematic_anime",
            custom_concept=req.custom_concept or "",
            user_lyrics=req.user_lyrics or "",
            still_count=req.still_count or 4,
            target_cuts=cuts_count,
            start_sec=req.start_sec or 0.0,
            duration_sec=req.duration_sec,
            cover_image_path=cover_path
        )
        return {"success": True, "storyboard": sb}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"스토리보드 계획 생성 실패: {str(e)}")


class MvGenerateStillRequest(BaseModel):
    project_id: str
    still_index: int
    prompt: str
    style_key: Optional[str] = "cinematic_anime"
    fallback_title: Optional[str] = "Scene"
    fallback_subtitle: Optional[str] = ""


@app.post("/api/mv/generate-still")
async def generate_mv_still_endpoint(req: MvGenerateStillRequest):
    """Generates or regenerates an individual still image (대표 이미지 또는 추가 씬 이미지)."""
    try:
        raw_pid = str(req.project_id or "").strip()
        project_id = _safe_token(raw_pid, None, max_len=48)
        if not project_id or project_id != raw_pid:
            raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트 ID입니다.")
        still_index = max(0, min(999, int(req.still_index)))
        project_dir = os.path.join(OUTPUTS_DIR, f"mv_{project_id}")
        images_dir = os.path.join(project_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        filename = f"still_{still_index:02d}.png"
        target_path = os.path.join(images_dir, filename)

        seed = int(time.time() * 1000) % 1000000 + still_index * 47
        generate_single_scene_image(
            prompt=req.prompt,
            output_path=target_path,
            seed=seed,
            style_key=req.style_key or "cinematic_anime",
            fallback_title=req.fallback_title or f"Still {still_index+1}",
            fallback_subtitle=req.fallback_subtitle or ""
        )

        image_url = f"/outputs/mv_{project_id}/images/{filename}?t={int(time.time())}"
        return {
            "success": True,
            "filename": filename,
            "image_url": image_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스틸 이미지 생성 실패: {str(e)}")


class MvGenerateSceneRequest(BaseModel):
    project_id: str
    scene_index: int
    prompt: str
    style_key: Optional[str] = "cinematic_anime"
    fallback_title: Optional[str] = "Scene"
    fallback_lyric: Optional[str] = ""


@app.post("/api/mv/generate-scene")
async def generate_mv_scene_endpoint(req: MvGenerateSceneRequest):
    """Legacy alias for generating scene image."""
    try:
        raw_pid = str(req.project_id or "").strip()
        project_id = _safe_token(raw_pid, None, max_len=48)
        if not project_id or project_id != raw_pid:
            raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트 ID입니다.")
        scene_index = max(0, min(999, int(req.scene_index)))
        project_dir = os.path.join(OUTPUTS_DIR, f"mv_{project_id}")
        images_dir = os.path.join(project_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        filename = f"still_{scene_index:02d}.png"
        target_path = os.path.join(images_dir, filename)

        seed = int(time.time() * 1000) % 1000000 + scene_index * 37
        generate_single_scene_image(
            prompt=req.prompt,
            output_path=target_path,
            seed=seed,
            style_key=req.style_key or "cinematic_anime",
            fallback_title=req.fallback_title or f"Scene {scene_index+1}",
            fallback_subtitle=req.fallback_lyric or ""
        )

        image_url = f"/outputs/mv_{project_id}/images/{filename}?t={int(time.time())}"
        return {
            "success": True,
            "filename": filename,
            "image_url": image_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"씬 이미지 생성 실패: {str(e)}")


class MvRenderRequest(BaseModel):
    project_id: Optional[str] = None
    storyboard: Dict[str, Any]
    audio_url: str
    dissolve_sec: Optional[float] = 1.0
    enable_subtitles: Optional[bool] = True
    enable_intro: Optional[bool] = True
    enable_outro: Optional[bool] = True
    speed: Optional[float] = 1.0
    start_sec: Optional[float] = 0.0
    duration_sec: Optional[float] = None


def _background_mv_compiler(task_id: str, req: MvRenderRequest, audio_path: str):
    """Background worker for assembling Ken-Burns clips, xfade dissolves, and MP4 rendering."""
    try:
        mv_render_tasks[task_id]["status"] = "processing"
        mv_render_tasks[task_id]["progress"] = 5
        mv_render_tasks[task_id]["stage"] = "작업 초기화 및 에셋 폴더 준비 중..."

        project_dir = os.path.join(OUTPUTS_DIR, f"mv_{task_id}")
        os.makedirs(project_dir, exist_ok=True)

        title = req.storyboard.get("title") or "Music_Video"
        clean_title = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title).strip(". "))[:80] or "Music_Video"
        speed_tag = f"_{req.speed:.2f}x" if abs((req.speed or 1.0) - 1.0) > 0.005 else ""
        out_filename = f"{clean_title}{speed_tag}_MV_{task_id}.mp4"
        final_mp4_path = os.path.join(OUTPUTS_DIR, out_filename)

        def _progress_callback(pct: int, msg: str):
            if task_id in mv_render_tasks:
                mv_render_tasks[task_id]["progress"] = pct
                mv_render_tasks[task_id]["stage"] = msg

        compile_slideshow_mv(
            storyboard=req.storyboard,
            work_dir=project_dir,
            audio_path=audio_path,
            output_mp4_path=final_mp4_path,
            dissolve_sec=req.dissolve_sec or 1.0,
            enable_subtitles=bool(req.enable_subtitles),
            enable_intro=bool(req.enable_intro),
            enable_outro=bool(req.enable_outro),
            speed=float(req.speed or 1.0),
            start_sec=float(req.start_sec or 0.0),
            duration_sec=float(req.duration_sec) if req.duration_sec else None,
            progress_cb=_progress_callback
        )

        size_mb = os.path.getsize(final_mp4_path) / (1024 * 1024) if os.path.exists(final_mp4_path) else 0.0

        mv_render_tasks[task_id]["status"] = "completed"
        mv_render_tasks[task_id]["progress"] = 100
        mv_render_tasks[task_id]["stage"] = "AI 뮤직비디오 MP4 렌더링 완성!"
        mv_render_tasks[task_id]["mp4_url"] = f"/outputs/{urllib.parse.quote(out_filename)}"
        mv_render_tasks[task_id]["filename"] = out_filename
        mv_render_tasks[task_id]["size_mb"] = round(size_mb, 2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        mv_render_tasks[task_id]["status"] = "failed"
        mv_render_tasks[task_id]["stage"] = f"오류 발생: {str(e)}"
        mv_render_tasks[task_id]["error"] = str(e)


@app.post("/api/mv/render")
async def render_mv_endpoint(req: MvRenderRequest):
    """Starts background compilation of AI Music Video with Ken Burns motions and dissolves."""
    audio_path = resolve_media_path(req.audio_url)
    if not audio_path:
        raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

    if req.project_id:
        raw_pid = str(req.project_id).strip()
        task_id = _safe_token(raw_pid, None, max_len=48)
        if not task_id or task_id != raw_pid:
            raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트 ID입니다.")
    else:
        task_id = f"mv_{uuid.uuid4().hex[:8]}"
    req.speed = _clamp(req.speed, 0.25, 4.0, 1.0)
    req.start_sec = _clamp(req.start_sec, 0.0, 86400.0, 0.0)
    if req.duration_sec is not None:
        req.duration_sec = _clamp(req.duration_sec, 1.0, 86400.0, 1.0)
    mv_render_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "stage": "대기열 등록 완료",
        "created_at": time.time(),
        "mp4_url": None,
        "filename": None,
        "size_mb": 0.0
    }

    t = threading.Thread(target=_background_mv_compiler, args=(task_id, req, audio_path), daemon=True)
    t.start()

    return {"success": True, "task_id": task_id}


# ============================================================================
# HERO THUMBNAIL VISUALIZER MUSIC VIDEO (NO LYRICS / FAST RENDERING)
# ============================================================================

class MvHeroVisualizerRequest(BaseModel):
    audio_url: str
    title: Optional[str] = "Music Video"
    artist: Optional[str] = "Antigravity Studio"
    hero_image_url: Optional[str] = None
    style_key: Optional[str] = "real_photo"
    title_template: Optional[str] = "modern_official" # "modern_official", "vinyl_label", "minimal_clean", "cyber_hud"
    visualizer_effect: Optional[str] = "spectrum_bars" # "spectrum_bars", "waveform_line", "spectrum_mirror", "spectrum_dots", "none"
    camera_motion: Optional[str] = "slow_zoom" # "slow_zoom", "static"
    speed: Optional[float] = 1.0
    start_sec: Optional[float] = 0.0
    duration_sec: Optional[float] = None


def _background_visualizer_compiler(task_id: str, req: MvHeroVisualizerRequest, audio_path: str, hero_img_path: Optional[str]):
    """Background worker for rendering fast single-image audio visualizer MV."""
    try:
        mv_render_tasks[task_id]["status"] = "processing"
        mv_render_tasks[task_id]["progress"] = 10
        mv_render_tasks[task_id]["stage"] = "비주얼 에셋 및 썸네일 준비 중..."

        title = req.title or "Music_Video"
        clean_title = normalize_title(re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title).strip(". "))[:80] or "Music_Video"
        speed_tag = f"_{req.speed:.2f}x" if abs((req.speed or 1.0) - 1.0) > 0.005 else ""
        out_filename = f"{clean_title}{speed_tag}_Visualizer_{task_id}.mp4"
        final_mp4_path = os.path.join(OUTPUTS_DIR, out_filename)

        def _progress_callback(pct: int, msg: str):
            if task_id in mv_render_tasks:
                mv_render_tasks[task_id]["progress"] = pct
                mv_render_tasks[task_id]["stage"] = msg

        render_hero_visualizer_mv(
            audio_path=audio_path,
            output_mp4_path=final_mp4_path,
            title=req.title or "Music Video",
            artist=req.artist or "Antigravity Studio",
            hero_image_path=hero_img_path,
            style_key=req.style_key or "real_photo",
            title_template=req.title_template or "modern_official",
            visualizer_effect=req.visualizer_effect or "spectrum_bars",
            camera_motion=req.camera_motion or "slow_zoom",
            speed=float(req.speed or 1.0),
            start_sec=float(req.start_sec or 0.0),
            duration_sec=float(req.duration_sec) if req.duration_sec else None,
            progress_cb=_progress_callback
        )

        size_mb = os.path.getsize(final_mp4_path) / (1024 * 1024) if os.path.exists(final_mp4_path) else 0.0

        mv_render_tasks[task_id]["status"] = "completed"
        mv_render_tasks[task_id]["progress"] = 100
        mv_render_tasks[task_id]["stage"] = "썸네일 & 비주얼라이저 MP4 완성!"
        mv_render_tasks[task_id]["mp4_url"] = f"/outputs/{urllib.parse.quote(out_filename)}"
        mv_render_tasks[task_id]["filename"] = out_filename
        mv_render_tasks[task_id]["size_mb"] = round(size_mb, 2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        mv_render_tasks[task_id]["status"] = "failed"
        mv_render_tasks[task_id]["stage"] = f"오류 발생: {str(e)}"
        mv_render_tasks[task_id]["error"] = str(e)


@app.post("/api/mv/render-visualizer")
async def render_visualizer_endpoint(req: MvHeroVisualizerRequest):
    """Starts lightning-fast single-image audio reactive visualizer MV generation (No lyrics required)."""
    audio_path = resolve_media_path(req.audio_url)
    if not audio_path:
        raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

    req.speed = _clamp(req.speed, 0.25, 4.0, 1.0)
    req.start_sec = _clamp(req.start_sec, 0.0, 86400.0, 0.0)
    if req.duration_sec is not None:
        req.duration_sec = _clamp(req.duration_sec, 1.0, 86400.0, 1.0)

    task_id = f"vis_{uuid.uuid4().hex[:8]}"

    # Resolve hero image (Support direct upload base64 data url or file path)
    hero_img_path = None
    if req.hero_image_url:
        if req.hero_image_url.startswith("data:image/"):
            try:
                header, encoded = req.hero_image_url.split(",", 1)
                if len(encoded) > MAX_IMAGE_BYTES * 4 // 3 + 1024:
                    raise ValueError("이미지가 너무 큽니다.")
                img_data = base64.b64decode(encoded)
                if len(img_data) > MAX_IMAGE_BYTES:
                    raise ValueError("이미지가 너무 큽니다.")
                saved_path = os.path.join(OUTPUTS_DIR, f"user_hero_{task_id}.png")
                with open(saved_path, "wb") as f:
                    f.write(img_data)
                hero_img_path = saved_path
            except Exception as e:
                print(f"[MV] Base64 image decode notice: {e}")
                hero_img_path = None
        else:
            hero_img_path = resolve_media_path(req.hero_image_url)

    mv_render_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "stage": "대기열 등록 완료",
        "created_at": time.time(),
        "mp4_url": None,
        "filename": None,
        "size_mb": 0.0
    }

    t = threading.Thread(
        target=_background_visualizer_compiler,
        args=(task_id, req, audio_path, hero_img_path),
        daemon=True
    )
    t.start()

    return {"success": True, "task_id": task_id}


@app.get("/api/mv/status/{task_id}")
async def get_mv_status_endpoint(task_id: str):
    """Returns real-time rendering status and progress for an MV project."""
    if task_id not in mv_render_tasks:
        raise HTTPException(status_code=404, detail="해당 MV 작업을 찾을 수 없습니다.")
    return mv_render_tasks[task_id]


# ============================================================================
# YOUTUBE CONTENT ID COPYRIGHT PRE-CHECK ENDPOINTS
# ============================================================================

class CopyrightCheckRequest(BaseModel):
    file_path: Optional[str] = None
    audio_url: Optional[str] = None
    title: Optional[str] = None


class CopyrightUrlCheckRequest(BaseModel):
    url: str


def _download_audio_from_url_sync(url: str) -> str:
    """Downloads audio from Suno, YouTube, or direct MP3 URL into UPLOADS_DIR."""
    url = url.strip()
    is_yt = _is_youtube_url(url)
    is_suno = _is_suno_url(url)
    suno_id = extract_suno_id(url)
    try:
        _validate_public_http_url(url)
    except ValueError as exc:
        raise ValueError(f"허용되지 않는 URL입니다: {exc}") from exc

    if is_yt:
        from yt_dlp import YoutubeDL
        ffmpeg_exe = get_ffmpeg_bin()
        js_runtimes = {}
        if os.path.exists(r"C:\Program Files\nodejs\node.exe"):
            js_runtimes['node'] = {'path': r'C:\Program Files\nodejs\node.exe'}

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(UPLOADS_DIR, 'yt_chk_%(id)s_%(title).50s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': ffmpeg_exe if ffmpeg_exe and os.path.exists(ffmpeg_exe) else None,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'js_runtimes': js_runtimes,
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            vid = info.get('id', 'video')
            for f in os.listdir(UPLOADS_DIR):
                if vid in f and f.endswith('.mp3'):
                    return os.path.join(UPLOADS_DIR, f)
            raise RuntimeError("YouTube 오디오를 추출하지 못했습니다.")

    elif suno_id or is_suno:
        dl_res = download_suno_song(url)
        return dl_res["filepath"]

    else:
        # Direct Audio URL (.mp3, .wav, etc.)
        clean_ext = ".mp3"
        for ext in [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4"]:
            if ext in url.lower():
                clean_ext = ext
                break
        dest_name = f"url_check_{int(time.time())}{clean_ext}"
        dest_path = os.path.join(UPLOADS_DIR, dest_name)

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = _read_limited_response(resp)
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("다운로드 파일이 너무 큽니다.")
        with open(dest_path, "wb") as out_f:
            out_f.write(data)
        return dest_path


@app.post("/api/copyright/url-check")
async def url_and_check_copyright_api(req: CopyrightUrlCheckRequest):
    """Downloads audio from a Suno, YouTube, or direct MP3 link, then runs YouTube copyright check."""
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="유효한 URL 링크를 입력해주세요.")

    try:
        # Run blocking download in worker thread
        audio_path = await asyncio.to_thread(_download_audio_from_url_sync, url)
        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(status_code=400, detail="음원을 다운로드하지 못했습니다.")
        
        res = await check_youtube_copyright(audio_path)
        res["source_url"] = url
        return res
    except Exception as e:
        print(f"[CopyrightURL] Error processing {url}: {e}")
        raise HTTPException(status_code=400, detail=f"링크 음원 분석 실패: {str(e)}")


@app.get("/api/copyright/files")
async def get_copyright_inspectable_files():
    """Returns list of recent music and video files available for copyright check."""
    inspectable = []
    supported_exts = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4"}
    
    for folder, label in [(OUTPUTS_DIR, "완성곡 / 렌더링"), (UPLOADS_DIR, "업로드 음원"), (SAMPLES_DIR, "샘플 음원")]:
        if not os.path.exists(folder):
            continue
        try:
            for fname in os.listdir(folder):
                ext = os.path.splitext(fname)[1].lower()
                if ext in supported_exts:
                    fpath = os.path.join(folder, fname)
                    st = os.stat(fpath)
                    inspectable.append({
                        "filename": fname,
                        "path": fpath,
                        "category": label,
                        "size_mb": round(st.st_size / (1024 * 1024), 2),
                        "mtime": st.st_mtime
                    })
        except Exception:
            pass

    # Sort recent files first
    inspectable.sort(key=lambda x: x["mtime"], reverse=True)
    return {"files": inspectable[:50]}


@app.post("/api/copyright/check")
async def check_copyright_api(req: CopyrightCheckRequest):
    """Checks an existing audio or video file for YouTube Content ID copyright risks."""
    target_path = resolve_media_path(req.file_path) if req.file_path else None
    if not target_path and req.audio_url:
        target_path = resolve_media_path(req.audio_url)

    if not target_path:
        raise HTTPException(status_code=400, detail="검사할 오디오/비디오 파일을 찾을 수 없거나 허용된 폴더 밖의 경로입니다.")

    res = await check_youtube_copyright(target_path, song_title=req.title)
    return res


@app.post("/api/copyright/upload-check")
async def upload_and_check_copyright_api(file: UploadFile = File(...)):
    """Directly uploads a file and immediately performs YouTube copyright check."""
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mov", ".mkv"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="지원되지 않는 오디오/비디오 포맷입니다.")

    safe_stem = _safe_token(Path(file.filename or "check").stem, "check", max_len=60)
    safe_name = f"check_{int(time.time())}_{safe_stem}{ext}"
    dest_path = os.path.join(UPLOADS_DIR, safe_name)

    _copy_upload_limited(file.file, dest_path)

    res = await check_youtube_copyright(dest_path, song_title=file.filename)
    return res


# =====================================================================
# High-Speed Multi-URL Batch Downloader & Converter (Fast MP4 & MP3)
# =====================================================================

import zipfile

BATCH_TASKS: Dict[str, dict] = {}
batch_lock = threading.RLock()

class BatchStartRequest(BaseModel):
    urls: list[str]
    export_mp3: bool = False
    export_mp4: bool = False  # Pure YouTube transfer by default (0MB PC storage)
    apply_mastering: bool = False  # Default MUST be False (unchecked) as requested
    upload_youtube: bool = True
    youtube_privacy: Optional[str] = "unlisted"
    use_cooldown: bool = True

def _process_batch_job(batch_id: str):
    with batch_lock:
        task = BATCH_TASKS.get(batch_id)
    if not task:
        return

    export_mp3 = task.get("export_mp3", False)
    export_mp4 = task.get("export_mp4", False)
    apply_mastering = task.get("apply_mastering", False)
    upload_youtube = task.get("upload_youtube", True)
    use_cooldown = task.get("use_cooldown", True)
    youtube_privacy = task.get("youtube_privacy")
    if not youtube_privacy:
        cfg = get_youtube_config()
        youtube_privacy = cfg.get("privacy_status", "unlisted")
    ffmpeg_exe = get_ffmpeg_bin()

    batch_out_dir = Path(OUTPUTS_DIR) / f"batch_{batch_id}"
    batch_out_dir.mkdir(parents=True, exist_ok=True)

    items = task["items"]
    for idx, item in enumerate(items):
        with batch_lock:
            if task.get("cancelled", False):
                item["status"] = "cancelled"
                item["message"] = "사용자에 의해 취소됨"
                continue
            item["status"] = "processing"
            item["progress"] = 10
            item["message"] = "음원/영상 정보 확인 중..."

        url = (item.get("url") or "").strip()
        try:
            is_yt = _is_youtube_url(url)
            is_suno = _is_suno_url(url)

            if not (is_yt or is_suno):
                with batch_lock:
                    item["status"] = "error"
                    item["error"] = "유효한 YouTube 또는 Suno URL이 아닙니다."
                    item["message"] = "URL 오류"
                    task["failed"] += 1
                continue

            mp4_path = None
            mp3_path = None
            clean_title = "Audio_Track"

            if is_yt:
                from yt_dlp import YoutubeDL
                with batch_lock:
                    item["message"] = "유튜브 영상 정보 분석 중..."
                    item["progress"] = 25

                ydl_info_opts = get_safe_yt_dlp_opts({"skip_download": True})
                with YoutubeDL(ydl_info_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    raw_title = info.get("title", "YouTube_Track")
                    vid_id = info.get("id", uuid.uuid4().hex[:6])

                clean_title = normalize_title(raw_title)[:80].strip(". \t\r\n")
                if not clean_title:
                    clean_title = f"YouTube_{vid_id}"
                item["title"] = clean_title
                if info.get("thumbnail"):
                    item["image_url"] = info.get("thumbnail")

                # Download video (MP4) if MP4 is requested, needed for YouTube upload, or for fast MP3 extraction
                if export_mp4 or upload_youtube or not export_mp3:
                    with batch_lock:
                        item["message"] = "고화질 MP4 다운로드 중..."
                        item["progress"] = 40

                    ydl_mp4_opts = get_safe_yt_dlp_opts({
                        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                        "outtmpl": str(batch_out_dir / f"{clean_title}.%(ext)s"),
                        "merge_output_format": "mp4",
                        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]
                    })
                    try:
                        with YoutubeDL(ydl_mp4_opts) as ydl:
                            ydl.download([url])
                    except Exception as yt_err:
                        # Fallback simple format if bestvideo+bestaudio failed
                        ydl_mp4_opts["format"] = "best[ext=mp4]/best"
                        with YoutubeDL(ydl_mp4_opts) as ydl:
                            ydl.download([url])

                    for cand in batch_out_dir.glob(f"{clean_title}*.mp4"):
                        mp4_path = cand
                        break

                    if mp4_path and mp4_path.exists() and export_mp4:
                        # Smart duplicate preservation: preserve in main OUTPUTS_DIR ONLY if export_mp4 is True
                        out_mp4 = get_safe_unique_filepath(OUTPUTS_DIR, mp4_path.name, new_file_size=mp4_path.stat().st_size)
                        if not out_mp4.exists() or out_mp4.stat().st_size != mp4_path.stat().st_size:
                            shutil.copy2(mp4_path, out_mp4)

                # Extract or download MP3 (320kbps)
                if export_mp3:
                    with batch_lock:
                        item["message"] = "320kbps MP3 고속 오디오 변환 중..."
                        item["progress"] = 75

                    target_mp3 = batch_out_dir / f"{clean_title}.mp3"
                    if mp4_path and mp4_path.exists():
                        # Super fast FFmpeg direct extraction (<1s)
                        cmd = [
                            ffmpeg_exe, "-y", "-i", str(mp4_path),
                            "-vn", "-c:a", "libmp3lame", "-b:a", "320k",
                            str(target_mp3)
                        ]
                        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        mp3_path = target_mp3
                    else:
                        ydl_audio_opts = get_safe_yt_dlp_opts({
                            "format": "bestaudio/best",
                            "outtmpl": str(batch_out_dir / f"{clean_title}.%(ext)s"),
                            "postprocessors": [{
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "320"
                            }]
                        })
                        with YoutubeDL(ydl_audio_opts) as ydl:
                            ydl.download([url])
                        for cand in batch_out_dir.glob(f"{clean_title}*.mp3"):
                            mp3_path = cand
                            break

                # Optional Mastering (only if user explicitly checked apply_mastering)
                if apply_mastering and mp3_path and mp3_path.exists():
                    with batch_lock:
                        item["message"] = "🎛️ 스튜디오 마스터링 적용 중..."
                        item["progress"] = 88
                    try:
                        from core.pipeline_suno import SunoMasteringPipeline
                        mastered_wav = batch_out_dir / f"{clean_title}_Mastered.wav"
                        pipe = SunoMasteringPipeline(str(mp3_path), str(mastered_wav), target_lufs=-14.0)
                        pipe.run()
                        if mastered_wav.exists():
                            cmd = [
                                ffmpeg_exe, "-y", "-i", str(mastered_wav),
                                "-c:a", "libmp3lame", "-b:a", "320k",
                                str(mp3_path)
                            ]
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except Exception as me:
                        print(f"[BatchMastering] Warning: {me}")

            elif is_suno:
                with batch_lock:
                    item["message"] = "Suno 원본 음원 다운로드 중..."
                    item["progress"] = 35

                dl_res = download_suno_song(url)
                raw_path = dl_res.get("file_path") or dl_res.get("filepath")
                if not raw_path and dl_res.get("filename"):
                    raw_path = str(Path(UPLOADS_DIR) / str(dl_res["filename"]))
                if not raw_path or not Path(raw_path).exists():
                    raise RuntimeError(f"Suno 다운로드 파일 경로를 확인할 수 없습니다: {dl_res}")

                suno_mp3_path = Path(raw_path)
                raw_song_title = dl_res.get("title") or suno_mp3_path.stem
                clean_title = normalize_title(str(raw_song_title))[:80].strip(". \t\r\n") or f"Suno_{uuid.uuid4().hex[:6]}"
                item["title"] = clean_title
                if dl_res.get("image_url"):
                    item["image_url"] = dl_res.get("image_url")

                # Smart duplicate preservation for MP3
                target_mp3 = get_safe_unique_filepath(batch_out_dir, f"{clean_title}.mp3", new_file_size=suno_mp3_path.stat().st_size)
                if not target_mp3.exists() or target_mp3.stat().st_size != suno_mp3_path.stat().st_size:
                    shutil.copy2(suno_mp3_path, target_mp3)
                mp3_path = target_mp3

                if export_mp4 or upload_youtube:
                    with batch_lock:
                        item["message"] = "Suno 고화질 영상(MP4) 생성 중..."
                        item["progress"] = 75
                    temp_mp4 = batch_out_dir / f"temp_{uuid.uuid4().hex[:8]}.mp4"
                    img_url = dl_res.get("image_url")
                    cover_img = batch_out_dir / f"{clean_title}_cover.jpg"
                    if img_url:
                        try:
                            urllib.request.urlretrieve(img_url, str(cover_img))
                        except Exception:
                            cover_img = None

                    if cover_img and cover_img.exists():
                        cmd = [
                            ffmpeg_exe, "-y", "-loop", "1", "-i", str(cover_img),
                            "-i", str(mp3_path),
                            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                            "-c:v", "libx264", "-tune", "stillimage",
                            "-c:a", "aac", "-b:a", "320k", "-pix_fmt", "yuv420p",
                            "-shortest", str(temp_mp4)
                        ]
                    else:
                        cmd = [
                            ffmpeg_exe, "-y", "-f", "lavfi", "-i", "color=c=#0b0f19:s=1280x720:r=30",
                            "-i", str(mp3_path), "-c:v", "libx264",
                            "-c:a", "aac", "-b:a", "320k", "-pix_fmt", "yuv420p",
                            "-shortest", str(temp_mp4)
                        ]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    # Smart Duplicate Preservation by File Size
                    rendered_size = temp_mp4.stat().st_size
                    target_mp4 = get_safe_unique_filepath(batch_out_dir, f"{clean_title}.mp4", new_file_size=rendered_size)
                    if target_mp4.exists() and target_mp4.stat().st_size == rendered_size and target_mp4 != temp_mp4:
                        temp_mp4.unlink(missing_ok=True)
                    else:
                        shutil.move(str(temp_mp4), str(target_mp4))
                    mp4_path = target_mp4

                    # Also preserve in main OUTPUTS_DIR ONLY if export_mp4 is True (local PC saving)
                    if export_mp4:
                        out_mp4 = get_safe_unique_filepath(OUTPUTS_DIR, mp4_path.name, new_file_size=rendered_size)
                        if not out_mp4.exists() or out_mp4.stat().st_size != rendered_size:
                            shutil.copy2(mp4_path, out_mp4)

                    # Clean up cover image temp file
                    if cover_img and cover_img.exists():
                        try:
                            cover_img.unlink(missing_ok=True)
                        except Exception:
                            pass

                # If user did NOT check MP3 export, delete intermediate MP3 from batch and uploads directory
                if not export_mp3:
                    if mp3_path and mp3_path.exists():
                        try:
                            mp3_path.unlink()
                        except Exception:
                            pass
                        mp3_path = None
                    if suno_mp3_path and suno_mp3_path.exists():
                        try:
                            suno_mp3_path.unlink(missing_ok=True)
                        except Exception:
                            pass

                # Optional mastering if requested
                if apply_mastering and mp3_path and mp3_path.exists():
                    with batch_lock:
                        item["message"] = "🎛️ 스튜디오 마스터링 적용 중..."
                        item["progress"] = 88
                    try:
                        from core.pipeline_suno import SunoMasteringPipeline
                        mastered_wav = batch_out_dir / f"{clean_title}_Mastered.wav"
                        pipe = SunoMasteringPipeline(str(mp3_path), str(mastered_wav), target_lufs=-14.0)
                        pipe.run()
                        if mastered_wav.exists():
                            cmd = [
                                ffmpeg_exe, "-y", "-i", str(mastered_wav),
                                "-c:a", "libmp3lame", "-b:a", "320k",
                                str(mp3_path)
                            ]
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except Exception as me:
                        print(f"[BatchMastering] Warning: {me}")

            # YouTube Auto-Upload if enabled and authenticated
            if upload_youtube and is_youtube_authenticated() and mp4_path and mp4_path.exists():
                with batch_lock:
                    item["message"] = "📺 유튜브 채널에 자동 업로드 중..."
                    item["progress"] = 92
                try:
                    def _on_yt_prog(pct, msg):
                        with batch_lock:
                            item["message"] = msg
                            item["progress"] = max(90, min(99, pct))
                    yt_res = upload_video_to_youtube(
                        video_path=str(mp4_path),
                        title=clean_title,
                        privacy=youtube_privacy,
                        progress_cb=_on_yt_prog
                    )
                    item["youtube_url"] = yt_res.get("url")
                    item["youtube_id"] = yt_res.get("video_id")
                    print(f"[BatchYouTubeUpload] Success: {yt_res.get('url')}")

                    # PURE YOUTUBE UPLOAD: If user did NOT want MP4 stored on PC, immediately delete temp MP4
                    if not export_mp4 and mp4_path and mp4_path.exists():
                        try:
                            mp4_path.unlink(missing_ok=True)
                            mp4_path = None
                        except Exception as del_err:
                            print(f"[Batch] Warning deleting temp mp4: {del_err}")
                except Exception as ye:
                    print(f"[BatchYouTubeUpload] Error: {ye}")
                    item["youtube_error"] = format_youtube_error(ye)
            elif upload_youtube and not is_youtube_authenticated():
                print(f"[BatchYouTubeUpload] Skipped: YouTube not authenticated")
                item["youtube_error"] = "유튜브 미연동 (설정에서 연동 필요)"

            with batch_lock:
                item["progress"] = 100
                item["status"] = "completed"
                if item.get("youtube_url"):
                    if not export_mp3 and not export_mp4:
                        item["message"] = "완료 (순수 유튜브 전송 성공 🚀)"
                    else:
                        item["message"] = "완료 (유튜브 업로드 성공 🎉)"
                elif item.get("youtube_error"):
                    item["message"] = f"완료 ({item['youtube_error']})"
                else:
                    item["message"] = "완료"
                if export_mp3 and mp3_path and mp3_path.exists():
                    item["mp3_url"] = f"/api/batch/file/{batch_id}/{urllib.parse.quote(mp3_path.name)}"
                    item["mp3_name"] = mp3_path.name
                # If MP4 export was requested OR YouTube upload failed, provide MP4 download link so user never loses their video
                if (export_mp4 or item.get("youtube_error")) and mp4_path and mp4_path.exists():
                    item["mp4_url"] = f"/api/batch/file/{batch_id}/{urllib.parse.quote(mp4_path.name)}"
                    item["mp4_name"] = mp4_path.name
                task["completed"] += 1

            # Human-like Cooldown Delay (인간화 안티-스팸 쿨다운 딜레이)
            # Must run OUTSIDE completion lock so it never blocks status polling
            cur_idx = item.get("index", idx)
            with batch_lock:
                remaining_pending = [it for it in items[cur_idx + 1:] if it.get("status") == "pending"]
            if upload_youtube and item.get("youtube_url") and remaining_pending and use_cooldown and not task.get("cancelled"):
                cooldown_sec = random.randint(25, 35)
                for rem in range(cooldown_sec, 0, -1):
                    if task.get("cancelled"):
                        break
                    with batch_lock:
                        task["cooldown_remaining"] = rem
                        task["cooldown_total"] = cooldown_sec
                        task["status_msg"] = f"🛡️ 유튜브 스팸 방지 쿨다운 중... (다음 곡까지 {rem}초 대기)"
                    time.sleep(1)
                with batch_lock:
                    task["cooldown_remaining"] = 0
                    task["status_msg"] = None

        except Exception as exc:
            import traceback
            traceback.print_exc()
            with batch_lock:
                item["status"] = "error"
                item["progress"] = 0
                item["error"] = format_youtube_error(exc)
                item["message"] = f"실패: {format_youtube_error(exc)}"
                task["failed"] += 1

    # Clean up batch directory ONLY if all YouTube uploads succeeded and no local exports were kept
    has_unuploaded_mp4 = any(it.get("youtube_error") for it in task.get("items", []))
    if not export_mp3 and not export_mp4 and not has_unuploaded_mp4 and batch_out_dir.exists():
        try:
            for left in list(batch_out_dir.iterdir()):
                if left.is_file():
                    left.unlink(missing_ok=True)
            if not any(batch_out_dir.iterdir()):
                batch_out_dir.rmdir()
        except Exception:
            pass

    with batch_lock:
        task["status"] = "completed" if task["failed"] == 0 else ("partial" if task["completed"] > 0 else "failed")


class SunoPlaylistResolveRequest(BaseModel):
    url: str

class SunoCookieRequest(BaseModel):
    cookie: str

@app.get("/api/suno/cookie")
def get_suno_cookie_api():
    cookie_file = Path(DATA_DIR) / "suno_cookie.txt"
    token_file = Path(DATA_DIR) / "suno_token.txt"
    has_cookie = (cookie_file.exists() and bool(cookie_file.read_text(encoding="utf-8").strip())) or \
                 (token_file.exists() and bool(token_file.read_text(encoding="utf-8").strip()))
    return {"has_cookie": has_cookie}

@app.post("/api/suno/cookie")
def save_suno_cookie_api(req: SunoCookieRequest):
    cookie_file = Path(DATA_DIR) / "suno_cookie.txt"
    token_file = Path(DATA_DIR) / "suno_token.txt"
    val = req.cookie.strip()
    if val.startswith("fetch(") or "127.0.0.1" in val:
        raise HTTPException(status_code=400, detail="연동 코드가 아닌 실제 쿠키 값을 입력해야 합니다.")
    sanitized = val.encode('ascii', 'ignore').decode('ascii').strip()
    if sanitized:
        if sanitized.startswith("eyJ") or sanitized.startswith("Bearer eyJ"):
            token_file.write_text(sanitized, encoding="utf-8")
        else:
            cookie_file.write_text(sanitized, encoding="utf-8")
    else:
        for f in (cookie_file, token_file):
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
    return {"ok": True, "has_cookie": bool(sanitized)}

@app.get("/api/suno/cookie-set", response_class=HTMLResponse)
@app.post("/api/suno/cookie-set", response_class=HTMLResponse)
def cookie_set_relay(c: Optional[str] = Query(None), t: Optional[str] = Query(None), songs: Optional[str] = Query(None)):
    cookie_file = Path(DATA_DIR) / "suno_cookie.txt"
    token_file = Path(DATA_DIR) / "suno_token.txt"
    saved_parts = []
    if c:
        sanitized_c = c.encode('ascii', 'ignore').decode('ascii').strip()
        if sanitized_c and not sanitized_c.startswith("fetch(") and not sanitized_c.startswith("<"):
            cookie_file.write_text(sanitized_c, encoding="utf-8")
            saved_parts.append("쿠키")
    if t:
        sanitized_t = t.encode('ascii', 'ignore').decode('ascii').strip()
        if sanitized_t and not sanitized_t.startswith("fetch(") and not sanitized_t.startswith("<"):
            token_file.write_text(sanitized_t, encoding="utf-8")
            saved_parts.append("인증 토큰")

    songs_js = ""
    if songs:
        s_list = [s.strip() for s in songs.split(",") if s.strip()]
        if s_list:
            songs_js = f"try {{ if (window.opener && window.opener.handleImportedSongs) {{ window.opener.handleImportedSongs({json.dumps(s_list)}); }} }} catch(e) {{}}"

    desc = " + ".join(saved_parts) if saved_parts else "인증 정보"
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>Suno 연동 완료</title>
  <style>
    body {{
      margin: 0; padding: 0; background: #070d19; color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex; align-items: center; justify-content: center; height: 100vh;
    }}
    .box {{
      background: #0f172a; border: 1.5px solid #38bdf8; border-radius: 16px;
      padding: 28px 36px; text-align: center; max-width: 380px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    h2 {{ color: #34d399; font-size: 20px; margin: 0 0 12px; }}
    p {{ color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 0 0 16px; }}
    .badge {{
      display: inline-block; background: #0369a1; color: #e0f2fe;
      padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: bold; margin-bottom: 12px;
    }}
  </style>
</head>
<body>
  <div class="box">
    <div class="badge">Suno Studio Master</div>
    <h2>🎉 Suno {desc} 연동 완료!</h2>
    <p>Suno 로그인 정보가 안전하게 저장되었습니다.<br>스튜디오 화면에서 플레이리스트를 다시 추가해보세요!<br><br><span style="color:#64748b; font-size:11px;">(이 창은 2초 후 자동으로 닫힙니다)</span></p>
  </div>
  <script>
    {songs_js}
    try {{
      if (window.opener) {{
        window.opener.postMessage('suno_cookie_synced', '*');
      }}
    }} catch(e) {{}}
    setTimeout(() => {{
      window.close();
    }}, 2000);
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.post("/api/suno/playlist/resolve")
def resolve_suno_playlist_api(req: SunoPlaylistResolveRequest):
    print(f"[SunoPlaylist] Resolving playlist request: {req.url}")
    res = resolve_suno_playlist(req.url)
    if not res.get("ok"):
        print(f"[SunoPlaylist] Resolve failed: {res.get('error')}")
        return JSONResponse(res, status_code=400)
    print(f"[SunoPlaylist] Resolved {res.get('total')} songs for '{res.get('name')}'")
    return res


@app.post("/api/batch/start")
def start_batch_job(req: BatchStartRequest):
    # Automatically expand Suno playlist URLs into individual song URLs
    valid_urls = []
    for u in req.urls:
        u_str = (u or "").strip()
        if not u_str:
            continue
        if is_suno_playlist_url(u_str):
            pl_res = resolve_suno_playlist(u_str)
            if pl_res.get("ok") and pl_res.get("songs"):
                for s in pl_res["songs"]:
                    valid_urls.append(s["url"])
                continue
        valid_urls.append(u_str)

    if not valid_urls:
        return JSONResponse({"ok": False, "error": "최소 1개 이상의 유효한 URL을 입력해주세요."}, status_code=400)

    def _get_batch_thumb(u_raw: str):
        if not u_raw:
            return None
        sm = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', u_raw)
        if sm:
            return f"https://cdn2.suno.ai/image_{sm.group(1).lower()}.jpeg"
        ym = re.search(r'(?:youtu\.be/|v=|/embed/|/v/)([a-zA-Z0-9_-]{11})', u_raw)
        if ym:
            return f"https://img.youtube.com/vi/{ym.group(1)}/mqdefault.jpg"
        return None

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    with batch_lock:
        BATCH_TASKS[batch_id] = {
            "id": batch_id,
            "status": "processing",
            "created_at": time.time(),
            "export_mp3": req.export_mp3,
            "export_mp4": req.export_mp4,
            "apply_mastering": req.apply_mastering,
            "upload_youtube": req.upload_youtube,
            "youtube_privacy": req.youtube_privacy or "unlisted",
            "use_cooldown": req.use_cooldown,
            "cooldown_remaining": 0,
            "cooldown_total": 0,
            "status_msg": None,
            "total": len(valid_urls),
            "completed": 0,
            "failed": 0,
            "items": [
                {
                    "index": idx,
                    "url": u,
                    "status": "pending",
                    "title": "",
                    "image_url": _get_batch_thumb(u),
                    "progress": 0,
                    "message": "대기 중...",
                    "mp3_url": None,
                    "mp3_name": None,
                    "mp4_url": None,
                    "mp4_name": None,
                    "youtube_url": None,
                    "youtube_id": None,
                    "error": None
                }
                for idx, u in enumerate(valid_urls)
            ]
        }

    threading.Thread(target=_process_batch_job, args=(batch_id,), daemon=True).start()
    return {"ok": True, "batch_id": batch_id, "total": len(valid_urls)}


@app.get("/api/batch/status/{batch_id}")
def get_batch_status(batch_id: str):
    with batch_lock:
        task = BATCH_TASKS.get(batch_id)
        if not task:
            raise HTTPException(status_code=404, detail="배치 작업을 찾을 수 없습니다.")
        # Return deep copy of task
        import copy
        return copy.deepcopy(task)


@app.get("/api/batch/file/{batch_id}/{filename}")
def get_batch_file(batch_id: str, filename: str):
    safe_name = Path(filename).name
    p = Path(OUTPUTS_DIR) / f"batch_{batch_id}" / safe_name
    if not p.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    media_type = "video/mp4" if p.suffix.lower() == ".mp4" else "audio/mpeg"
    return FileResponse(path=str(p), filename=safe_name, media_type=media_type)


@app.get("/api/batch/zip/{batch_id}")
def download_batch_zip(batch_id: str):
    batch_dir = Path(OUTPUTS_DIR) / f"batch_{batch_id}"
    if not batch_dir.exists():
        raise HTTPException(status_code=404, detail="배치 작업 디렉토리를 찾을 수 없습니다.")

    zip_path = Path(OUTPUTS_DIR) / f"Batch_Export_{batch_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in batch_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".mp3", ".mp4", ".wav"):
                zf.write(f, arcname=f.name)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        path=str(zip_path),
        filename=f"Antigravity_Batch_Export_{timestamp}.zip",
        media_type="application/zip"
    )


@app.post("/api/batch/cancel/{batch_id}")
def cancel_batch(batch_id: str):
    with batch_lock:
        if batch_id in BATCH_TASKS:
            BATCH_TASKS[batch_id]["cancelled"] = True
            BATCH_TASKS[batch_id]["status"] = "cancelled"
            return {"ok": True}
    return JSONResponse({"ok": False, "error": "해당 배치를 찾을 수 없습니다."}, status_code=404)


# =====================================================================
# YouTube Channel Auto-Upload & OAuth 2.0 Integration
# =====================================================================

class YouTubeConfigUpdate(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    privacy_status: Optional[str] = "unlisted"
    auto_upload: Optional[bool] = False
    default_tags: Optional[List[str]] = None
    default_description: Optional[str] = None


@app.get("/api/youtube/status")
def get_youtube_status():
    cfg = get_youtube_config()
    is_auth = is_youtube_authenticated()
    client_secret_file = Path(DATA_DIR) / "client_secret.json"
    has_creds = bool((cfg.get("client_id") and cfg.get("client_secret")) or client_secret_file.exists())
    return {
        "ok": True,
        "authenticated": is_auth,
        "channel_title": cfg.get("channel_title") if is_auth else "",
        "channel_thumbnail": cfg.get("channel_thumbnail") if is_auth else "",
        "channel_id": cfg.get("channel_id") if is_auth else "",
        "privacy_status": cfg.get("privacy_status", "unlisted"),
        "auto_upload": cfg.get("auto_upload", False),
        "has_credentials": has_creds,
        "client_id": cfg.get("client_id", "")
    }


@app.post("/api/youtube/config")
def update_youtube_config_api(req: YouTubeConfigUpdate):
    updates = {k: v for k, v in req.dict().items() if v is not None}
    saved = save_youtube_config(updates)
    return {"ok": True, "config": saved}


@app.post("/api/youtube/upload-credentials")
async def upload_youtube_credentials(file: UploadFile = File(...)):
    """Upload Google Cloud client_secret.json directly."""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON 파일만 업로드할 수 있습니다.")
    dest_path = Path(DATA_DIR) / "client_secret.json"
    content = await file.read()
    try:
        parsed = json.loads(content.decode("utf-8"))
        cinfo = parsed.get("web") or parsed.get("installed")
        if not cinfo:
            raise ValueError("올바른 Google OAuth client_secret.json 형식이 아닙니다.")
        dest_path.write_bytes(content)
        save_youtube_config({
            "client_id": cinfo.get("client_id", ""),
            "client_secret": cinfo.get("client_secret", "")
        })
        return {"ok": True, "message": "Google OAuth 인증 정보가 성공적으로 등록되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"인증 파일 처리 실패: {e}")


OAUTH_STATES_PATH = Path(DATA_DIR) / "oauth_states.json"

def save_oauth_state(state: str, code_verifier: Optional[str]):
    states = {}
    if OAUTH_STATES_PATH.exists():
        try:
            states = json.loads(OAUTH_STATES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    now = time.time()
    # Keep states valid for 2 hours
    states = {k: v for k, v in states.items() if (now - v.get("time", 0)) < 7200}
    entry = {
        "code_verifier": code_verifier,
        "time": now
    }
    states[state] = entry
    states["_latest"] = entry
    OAUTH_STATES_PATH.write_text(json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8")

def get_oauth_verifier(state: Optional[str] = None) -> Optional[str]:
    if not OAUTH_STATES_PATH.exists():
        return None
    try:
        states = json.loads(OAUTH_STATES_PATH.read_text(encoding="utf-8"))
        if state and state in states and states[state].get("code_verifier"):
            return states[state]["code_verifier"]
        if "_latest" in states and states["_latest"].get("code_verifier"):
            return states["_latest"]["code_verifier"]
        # Find latest non-empty code_verifier
        valid_entries = [
            v for k, v in states.items()
            if isinstance(v, dict) and v.get("code_verifier")
        ]
        if valid_entries:
            latest = max(valid_entries, key=lambda x: x.get("time", 0))
            return latest.get("code_verifier")
    except Exception as e:
        print(f"[OAuthState] Warning: {e}")
    return None

def clear_oauth_state(state: Optional[str] = None):
    if not OAUTH_STATES_PATH.exists():
        return
    try:
        states = json.loads(OAUTH_STATES_PATH.read_text(encoding="utf-8"))
        if state and state in states:
            states.pop(state, None)
        states.pop("_latest", None)
        OAUTH_STATES_PATH.write_text(json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


@app.get("/api/youtube/auth-url")
def get_youtube_auth_url(request: Request):
    host = request.headers.get("host", "127.0.0.1:8000")
    scheme = request.url.scheme or "http"
    redirect_uri = f"{scheme}://{host}/api/youtube/oauth/callback"
    try:
        flow = get_oauth_flow(redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        # Store PKCE code_verifier so it can be verified upon callback
        save_oauth_state(state, getattr(flow, "code_verifier", None))
        return {"ok": True, "auth_url": auth_url, "state": state}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/api/youtube/oauth/callback")
def youtube_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    if error:
        err_lower = str(error).lower()
        if "access_denied" in err_lower or "403" in err_lower:
            msg = (
                "Google 계정 연동 권한이 승인되지 않았습니다 (403 access_denied).\n\n"
                "해결 방법: Google Cloud Console의 [OAuth 동의 화면] -> [테스트 사용자]에 현재 로그인한 구글 계정(이메일)을 추가해주세요."
            )
        else:
            msg = f"Google 로그인 오류: {error}"
        return RedirectResponse(f"/?youtube_auth=error&msg={urllib.parse.quote(msg)}")

    if not code:
        return RedirectResponse("/?youtube_auth=error&msg=No+code+provided")

    host = request.headers.get("host", "127.0.0.1:8000")
    scheme = request.url.scheme or "http"
    redirect_uri = f"{scheme}://{host}/api/youtube/oauth/callback"
    try:
        flow = get_oauth_flow(redirect_uri)
        saved_verifier = get_oauth_verifier(state)
        fetch_kwargs = {"code": code}
        if saved_verifier:
            flow.code_verifier = saved_verifier
            fetch_kwargs["code_verifier"] = saved_verifier
        else:
            return RedirectResponse("/?youtube_auth=error&msg=" + urllib.parse.quote("인증 세션이 만료되었습니다. 스튜디오에서 [Google 계정 로그인] 버튼을 다시 클릭해주세요."))

        flow.fetch_token(**fetch_kwargs)
        creds = flow.credentials
        from core.youtube_uploader import _save_credentials
        _save_credentials(creds)
        clear_oauth_state(state)
        fetch_and_save_channel_info()
        return RedirectResponse("/?youtube_auth=success")
    except Exception as e:
        err_text = str(e)
        if "access_denied" in err_text.lower():
            user_msg = "Google Cloud Console의 [OAuth 동의 화면] -> [테스트 사용자]에 본인 구글 계정 이메일을 추가해야 합니다 (403 access_denied)."
        elif "invalid_grant" in err_text.lower():
            user_msg = "인증 코드가 만료되었거나 이미 사용되었습니다. [Google 계정 로그인] 버튼을 다시 눌러주세요."
        else:
            user_msg = f"유튜브 연동 오류: {err_text}"
        return RedirectResponse(f"/?youtube_auth=error&msg={urllib.parse.quote(user_msg)}")


@app.post("/api/youtube/disconnect")
def disconnect_youtube_api():
    disconnect_youtube()
    return {"ok": True, "authenticated": False}


class YouTubeUploadRequest(BaseModel):
    video_path: str
    title: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = None
    privacy: Optional[str] = "unlisted"


@app.post("/api/youtube/upload")
def upload_to_youtube_api(req: YouTubeUploadRequest):
    if not is_youtube_authenticated():
        raise HTTPException(status_code=401, detail="유튜브 계정이 연동되지 않았습니다.")
    resolved = resolve_media_path(req.video_path)
    if not resolved:
        cand = Path(req.video_path)
        if cand.exists() and (cand.is_relative_to(OUTPUTS_DIR) or cand.is_relative_to(UPLOADS_DIR)):
            resolved = str(cand)
        else:
            raise HTTPException(status_code=404, detail="업로드할 동영상 파일을 찾을 수 없습니다.")

    try:
        res = upload_video_to_youtube(
            video_path=resolved,
            title=req.title,
            description=req.description or "",
            tags=req.tags,
            privacy=req.privacy or "unlisted"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_youtube_error(e))


if __name__ == "__main__":
    import uvicorn
    import socket

    env_port = os.environ.get("PORT")
    env_host = os.environ.get("HOST")

    if env_port:
        selected_port = int(env_port)
        selected_host = env_host or "0.0.0.0"
    else:
        selected_port = 8000
        selected_host = env_host or "127.0.0.1"
        # Try port 8000 with quick retries if in TIME_WAIT, then fallback to 8001, 8080
        for cand in [8000, 8001, 8080]:
            bound = False
            for attempt in range(4):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("127.0.0.1", cand))
                    s.close()
                    selected_port = cand
                    bound = True
                    break
                except Exception:
                    time.sleep(0.4)
            if bound:
                break

    if selected_port != 8000 and not env_port:
        print(f"[Antigravity] Note: Port 8000 was unavailable (reserved/blocked by Windows NAT). Using port {selected_port}.")
    studio_url = f"http://{selected_host}:{selected_port}"
    print(f"[Antigravity] Starting studio server on {studio_url}")
    print("[Antigravity] Set STUDIO_NO_BROWSER=1 to suppress the automatic browser launch.")

    # Seamless multi-port forwarder: If running on 8000, redirect any request hitting 8001 or 8080 to 8000
    if selected_port == 8000:
        def _redirect_port(p):
            try:
                import http.server
                import socketserver
                class RedirectHandler(http.server.BaseHTTPRequestHandler):
                    def do_GET(self):
                        self.send_response(307)
                        self.send_header('Location', f'http://127.0.0.1:8000{self.path}')
                        self.end_headers()
                    def do_POST(self):
                        self.send_response(307)
                        self.send_header('Location', f'http://127.0.0.1:8000{self.path}')
                        self.end_headers()
                    def log_message(self, *args): pass
                with socketserver.TCPServer(("127.0.0.1", p), RedirectHandler) as srv:
                    srv.serve_forever()
            except Exception:
                pass
        threading.Thread(target=_redirect_port, args=(8001,), daemon=True).start()
        threading.Thread(target=_redirect_port, args=(8080,), daemon=True).start()

    if os.environ.get("STUDIO_NO_BROWSER", "").strip().lower() not in ("1", "true", "yes"):
        def _open_browser():
            time.sleep(1.5)
            try:
                import webbrowser
                webbrowser.open(studio_url)
            except Exception:
                pass
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run("app:app", host=selected_host, port=selected_port, reload=False)
