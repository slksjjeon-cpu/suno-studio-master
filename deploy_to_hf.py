import os
import sys
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "data" / "hf_config.json"

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(username, token):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": username, "token": token}, f, indent=2)

def deploy(username=None, token=None):
    cfg = load_config()
    token = token or cfg.get("token") or os.environ.get("HF_TOKEN")
    username = username or cfg.get("username")

    if not token:
        print("[ERROR] Hugging Face write token이 필요합니다.")
        print("사용법: python deploy_to_hf.py <HF_TOKEN> 또는 python deploy_to_hf.py <HF_USERNAME> <HF_TOKEN>")
        return False

    from huggingface_hub import HfApi, create_repo
    api = HfApi(token=token)

    if not username:
        try:
            user_info = api.whoami()
            username = user_info.get("name")
            print(f"[OK] Hugging Face 계정 자동 확인: @{username}")
        except Exception as e:
            print(f"[ERROR] 토큰 유효성 검사 실패: {e}")
            return False

    save_config(username, token)
    repo_id = f"{username}/suno-studio"

    print(f"[1/3] Hugging Face Space 확인 및 생성 중: {repo_id}...")
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            token=token,
            exist_ok=True,
            private=False
        )
        print(f"[OK] Space 준비 완료: https://huggingface.co/spaces/{repo_id}")
    except Exception as e:
        print(f"[WARN] Space 생성 알림: {e}")

    print(f"[2/3] 최신 코드 및 Docker 환경 업로드 중...")
    workspace_dir = Path(__file__).parent.resolve()

    ignore_patterns = [
        ".git/**",
        "outputs/**",
        "uploads/**",
        ".hum_cache/**",
        "__pycache__/**",
        "scratch/**",
        "*.mp3",
        "*.wav",
        "*.mp4",
        "*.zip",
        "*.pyc",
        "data/*token*",
        "data/*secret*",
        "data/oauth_states.json",
        "data/hf_config.json"
    ]

    try:
        commit_info = api.upload_folder(
            folder_path=str(workspace_dir),
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=ignore_patterns,
            commit_message="🚀 Deploy Suno Studio Master (Latest Version)"
        )
        print(f"[OK] 업로드 완료! (Commit: {commit_info})")
    except Exception as e:
        print(f"[ERROR] 업로드 실패: {e}")
        return False

    public_url = f"https://{username.lower()}-suno-studio.hf.space"
    space_page = f"https://huggingface.co/spaces/{repo_id}"

    print(f"\n==================================================")
    print(f"🎉 24시간 영구 무료 클라우드 배포 성공!")
    print(f"🌐 영구 웹 앱 주소: {public_url}")
    print(f"📁 Space 관리 페이지: {space_page}")
    print(f"==================================================\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) == 2:
        arg = sys.argv[1].strip()
        if arg.startswith("hf_"):
            deploy(token=arg)
        else:
            deploy(username=arg)
    elif len(sys.argv) > 2:
        deploy(username=sys.argv[1].strip(), token=sys.argv[2].strip())
    else:
        deploy()
