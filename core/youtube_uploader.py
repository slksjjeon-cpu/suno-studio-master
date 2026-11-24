import os
# Allow HTTP for local OAuth callback
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    import googleapiclient.discovery
    from googleapiclient.http import MediaFileUpload
    HAS_GOOGLE_API = True
except ImportError:
    Credentials = None
    Request = None
    Flow = None
    googleapiclient = None
    MediaFileUpload = None
    HAS_GOOGLE_API = False

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_PATH = DATA_DIR / "youtube_config.json"
TOKEN_PATH = DATA_DIR / "youtube_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

DEFAULT_CONFIG = {
    "client_id": "",
    "client_secret": "",
    "privacy_status": "unlisted",  # unlisted (일부공개 - 기본값), private (비공개), public (공개)
    "auto_upload": False,
    "default_tags": ["Suno", "AI음악", "AntigravityStudio"],
    "default_description": "Uploaded with Antigravity Suno Studio Master",
    "channel_title": "",
    "channel_thumbnail": "",
    "channel_id": ""
}

def get_youtube_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = dict(DEFAULT_CONFIG)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_youtube_config(updates: dict) -> dict:
    cfg = get_youtube_config()
    cfg.update(updates)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg

def is_youtube_authenticated() -> bool:
    if not TOKEN_PATH.exists():
        return False
    try:
        creds = _load_credentials()
        return creds is not None and (creds.valid or creds.refresh_token is not None)
    except Exception:
        return False

def _load_credentials() -> Optional[Any]:
    if not HAS_GOOGLE_API or not TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
        creds = Credentials.from_authorized_user_info(data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_credentials(creds)
        return creds
    except Exception as e:
        print(f"[YouTubeUploader] Failed to load credentials: {e}")
        return None

def _save_credentials(creds: Credentials):
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES)
    }
    TOKEN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_youtube_service():
    creds = _load_credentials()
    if not creds:
        raise RuntimeError("유튜브 계정이 인증되지 않았습니다. 먼저 계정을 연결해주세요.")
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def get_oauth_flow(redirect_uri: str) -> Flow:
    cfg = get_youtube_config()
    client_id = cfg.get("client_id", "").strip()
    client_secret = cfg.get("client_secret", "").strip()
    
    client_secrets_file = DATA_DIR / "client_secret.json"
    if client_secrets_file.exists():
        flow = Flow.from_client_secrets_file(
            str(client_secrets_file),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    elif client_id and client_secret:
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    else:
        raise ValueError("Google OAuth Client ID 및 Secret이 설정되지 않았습니다.")
    
    return flow

def fetch_and_save_channel_info():
    """Fetch user's YouTube channel info and cache in config."""
    try:
        yt = get_youtube_service()
        resp = yt.channels().list(mine=True, part="snippet").execute()
        items = resp.get("items", [])
        if items:
            snip = items[0].get("snippet", {})
            save_youtube_config({
                "channel_id": items[0].get("id", ""),
                "channel_title": snip.get("title", ""),
                "channel_thumbnail": snip.get("thumbnails", {}).get("default", {}).get("url", "")
            })
    except Exception as e:
        print(f"[YouTubeUploader] Warning fetching channel info: {e}")

def disconnect_youtube():
    if TOKEN_PATH.exists():
        try:
            TOKEN_PATH.unlink()
        except Exception:
            pass
    save_youtube_config({
        "channel_id": "",
        "channel_title": "",
        "channel_thumbnail": ""
    })

def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[List[str]] = None,
    privacy: Optional[str] = None,
    progress_cb = None
) -> dict:
    """
    Uploads a video to the user's YouTube channel via YouTube Data API v3.
    """
    p = Path(video_path)
    if not p.exists() or p.stat().st_size == 0:
        raise FileNotFoundError(f"업로드할 동영상 파일을 찾을 수 없습니다: {video_path}")

    yt = get_youtube_service()
    cfg = get_youtube_config()

    privacy_status = (privacy or cfg.get("privacy_status") or "unlisted").lower()
    if privacy_status not in ("private", "unlisted", "public"):
        privacy_status = "unlisted"

    video_tags = tags if tags is not None else cfg.get("default_tags", ["Suno", "Music"])
    desc = description or cfg.get("default_description", "Uploaded with Suno Studio Master")

    body = {
        "snippet": {
            "title": str(title)[:100],
            "description": desc,
            "tags": video_tags,
            "categoryId": "10"  # Music
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(p),
        mimetype="video/mp4",
        chunksize=1024 * 1024 * 5,  # 5MB chunks
        resumable=True
    )

    request = yt.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    if progress_cb:
        progress_cb(10, f"'{title}' 유튜브 업로드 시작...")

    response = None
    retry_count = 0
    max_chunk_retries = 5
    while response is None:
        try:
            status, response = request.next_chunk(num_retries=3)
            if status and progress_cb:
                pct = int(status.progress() * 85) + 10
                progress_cb(pct, f"유튜브 업로드 중... {pct}%")
            retry_count = 0
        except Exception as chunk_err:
            retry_count += 1
            if retry_count > max_chunk_retries:
                raise chunk_err
            print(f"[YouTubeUploader] Chunk upload retry {retry_count}/{max_chunk_retries}: {chunk_err}")
            time.sleep(2 * retry_count)

    video_id = response.get("id")
    if not video_id:
        raise RuntimeError(f"유튜브 업로드 응답에 video_id가 없습니다: {response}")

    video_url = f"https://youtu.be/{video_id}"
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit"

    if progress_cb:
        progress_cb(100, f"유튜브 업로드 완료! ({video_url})")

    return {
        "ok": True,
        "video_id": video_id,
        "url": video_url,
        "studio_url": studio_url,
        "title": title,
        "privacy": privacy_status
    }


def format_youtube_error(exc: Any) -> str:
    """Format YouTube API exception into friendly, actionable Korean explanation."""
    raw = str(exc or "")
    low = raw.lower()
    if "uploadlimitexceeded" in low or "exceeded the number of videos" in low or "upload limit reached" in low:
        return "유튜브 채널 24시간 일일 업로드 한도 도달 (24시간 롤링 제한: 내일 순차 자동 해제)"
    if "quotaexceeded" in low or "quota exceeded" in low or "videouploadsperday" in low or "ratelimitexceeded" in low or "429" in raw:
        return "구글 API 일일 업로드 한도(Quota) 초과 (프로젝트당 하루 6~10개 영상. 오후 4~5시 자동 리셋)"
    if "invalid_grant" in low or "token has been expired" in low or "revoked" in low:
        return "유튜브 인증 만료 (유튜브 설정에서 계정 재연동 필요)"
    if "badrequest" in low or "400" in raw:
        return f"유튜브 요청 오류: {raw[:60]}"
    return f"업로드 실패 ({raw[:50]})"
