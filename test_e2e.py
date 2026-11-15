import requests
import time

print("[E2E Test] Starting End-to-End Workflow Verification...")

# 1. Load sample
r_sample = requests.post('http://127.0.0.1:8000/api/load-sample').json()
print("1. Sample loaded successfully:", r_sample.get("success"))
file_path = r_sample["data"]["file_path"]

# 2. Enqueue Draft A (City Pop with custom lyrics)
payload_a = {
    "name": "시안 A (시티팝)",
    "job_type": "preview",
    "source_audio_path": file_path,
    "start_sec": 0.0,
    "duration_sec": 12.0,
    "genre_params": {
        "id": "city_pop_80s",
        "name": "시티팝 (80s City Pop)",
        "icon": "🌴",
        "prompt": "80s retro Japanese City Pop, funky slap bass, sparkling DX7 keys",
        "bpm": 90.0,
        "tempo_scale": 1.05,
        "pitch_shift": 0,
        "vocal_mood": "청아하고 세련된 80s 팝 보컬 (Airy & Bright)"
    },
    "custom_lyrics": "달빛이 비치는 밤거리 위로 우리 둘의 춤이 시작돼",
    "original_lyrics": "바람이 불어오는 길목에서",
    "mastering_options": {
        "enabled": True,
        "target_lufs": -14.0,
        "eq_profile": "crisp",
        "stereo_width": 1.25,
        "limiter_ceiling_db": -0.3
    }
}
r_a = requests.post("http://127.0.0.1:8000/api/queue/enqueue", json=payload_a).json()
print("2. Draft A enqueued:", r_a.get("job_id"))

# 3. Enqueue Draft B (Lo-fi Jazz with original lyrics fallback)
payload_b = {
    "name": "시안 B (로파이 재즈)",
    "job_type": "preview",
    "source_audio_path": file_path,
    "start_sec": 0.0,
    "duration_sec": 12.0,
    "genre_params": {
        "id": "lofi_chill_jazz",
        "name": "로파이 칠 재즈 (Lo-Fi Chill Jazz)",
        "icon": "☕",
        "prompt": "Warm Rhodes keys, smoky upright bass, vinyl crackle",
        "bpm": 90.0,
        "tempo_scale": 0.85,
        "pitch_shift": -1,
        "vocal_mood": "나른하고 감미로운 허스키 재즈 톤 (Husky & Intimate)"
    },
    "custom_lyrics": "", # Empty -> fallback to original
    "original_lyrics": "바람이 불어오는 길목에서 너의 목소리가 들려오는 것 같아",
    "mastering_options": {
        "enabled": True,
        "target_lufs": -16.0,
        "eq_profile": "warm_low",
        "stereo_width": 1.10,
        "limiter_ceiling_db": -0.5
    }
}
r_b = requests.post("http://127.0.0.1:8000/api/queue/enqueue", json=payload_b).json()
print("3. Draft B enqueued:", r_b.get("job_id"))

print("\n4. Polling sequential queue...")
for i in range(25):
    time.sleep(1.0)
    jobs_res = requests.get("http://127.0.0.1:8000/api/queue/jobs").json()
    jobs = jobs_res["jobs"]
    completed = [j for j in jobs if j["status"] == "completed"]
    failed = [j for j in jobs if j["status"] == "failed"]
    processing = [j for j in jobs if j["status"] == "processing"]
    
    print(f"[{i+1}s] Queue: {jobs_res['queue_length']} waiting | Processing: {len(processing)} | Completed: {len(completed)} | Failed: {len(failed)}")
    
    if len(failed) > 0:
        for f in failed:
            print(f"[FAIL] {f['name']}: {f.get('error_msg')}")
        break

    if len(completed) >= 2:
        print("\nAll draft previews rendered successfully!")
        for c in completed:
            m = c["metadata"]
            print(f"- {c['name']}")
            print(f"  URL: {c['result_url']}")
            print(f"  Genre: {m['genre_name']}, Vocal: {m['vocal_mood']}")
            print(f"  Lyrics: [{m['lyrics_source']}] '{m['active_lyrics']}'")
            print(f"  Mastering: {m['target_lufs']} LUFS, EQ: {m['eq_profile']}, Render Time: {m['render_time_sec']}s")
        break
