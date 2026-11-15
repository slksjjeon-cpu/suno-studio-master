import requests
import time
import urllib.parse
import os

base_url = "http://127.0.0.1:8000"
audio_filename = "A2O LITE 'NEON' Official Video_Preview_15s_DeWatermarked_-14LUFS_AutoLeveled.wav"
audio_url = f"/outputs/{urllib.parse.quote(audio_filename)}"

print("[1] Testing /api/mv/plan...")
plan_res = requests.post(f"{base_url}/api/mv/plan", json={
    "audio_url": audio_url,
    "title": "A2O NEON (K-Trot Cover)",
    "artist": "Antigravity Studio",
    "style_key": "kpop_cyberpunk",
    "custom_concept": "네온 불빛 반짝이는 사이버펑크 서울 밤거리",
    "user_lyrics": "달빛 아래 춤추는 불빛들\n네온 사인 속에 사라진 기억\n오늘 밤 너를 향해 달려가",
    "still_count": 3,
    "target_cuts": 4
})
print("Plan status:", plan_res.status_code)
assert plan_res.status_code == 200
sb = plan_res.json()["storyboard"]
print(f"Storyboard created! Stills: {len(sb['key_stills'])}, Cuts: {len(sb['scenes'])}, Duration: {sb['duration']}s")

project_id = f"test_{int(time.time())}"

print("[2] Testing /api/mv/generate-still for Hero (#0)...")
still_res = requests.post(f"{base_url}/api/mv/generate-still", json={
    "project_id": project_id,
    "still_index": 0,
    "prompt": sb["key_stills"][0]["prompt"],
    "style_key": "kpop_cyberpunk",
    "fallback_title": sb["key_stills"][0]["name"],
    "fallback_subtitle": sb["key_stills"][0]["desc"]
})
print("Still 0 status:", still_res.status_code, still_res.json())
assert still_res.status_code == 200

print("[3] Testing /api/mv/render...")
render_res = requests.post(f"{base_url}/api/mv/render", json={
    "project_id": project_id,
    "storyboard": sb,
    "audio_url": audio_url,
    "dissolve_sec": 0.8,
    "enable_subtitles": True,
    "enable_intro": True,
    "enable_outro": True,
    "speed": 1.0
})
print("Render start status:", render_res.status_code, render_res.json())
assert render_res.status_code == 200
task_id = render_res.json()["task_id"]

print("[4] Polling render status...")
for i in range(60):
    time.sleep(2)
    st_res = requests.get(f"{base_url}/api/mv/status/{task_id}")
    st = st_res.json()
    print(f"[{i+1}] Progress: {st.get('progress', 0)}% - {st.get('stage', '')} [Status: {st.get('status')}]")
    if st.get("status") in ["completed", "failed"]:
        break

assert st.get("status") == "completed", f"Render failed: {st}"
print("SUCCESS! Final MP4 URL:", st.get("mp4_url"), "Size:", st.get("size_mb"), "MB")
