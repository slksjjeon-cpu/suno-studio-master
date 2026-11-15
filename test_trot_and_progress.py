import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("[Test] Verifying K-Trot Preset & Async Progress Tracking...")

# 1. System status
sys_res = requests.get('http://127.0.0.1:8000/api/system-status').json()
print("1. System Status:", sys_res['gpu']['name'])

# 2. Check K-Trot Preset
presets_res = requests.get('http://127.0.0.1:8000/api/presets').json()
presets = presets_res['genre_presets']
trot = next((p for p in presets if p['id'] == 'k_trot_classic'), None)
print("2. K-Trot Preset Found:", trot is not None)
if trot:
    print("   Name:", trot['name'], "| Icon:", trot['icon'])
    print("   Prompt:", trot['prompt'][:60], "...")
    print("   Vocal:", trot['vocal_mood'])

# 3. Test Async Analysis with Progress
print("\n3. Testing Async Demo Analysis with Progress...")
start_res = requests.post('http://127.0.0.1:8000/api/load-sample-async').json()
task_id = start_res['task_id']
print("   Task ID:", task_id)

file_path = None
for i in range(30):
    time.sleep(0.4)
    st = requests.get(f'http://127.0.0.1:8000/api/analysis-status/{task_id}').json()
    pct = st.get('progress', 0)
    stage = st.get('stage', '')
    eta = st.get('remaining_sec', 0)
    print(f"   [{pct}%] {stage} (ETA: {eta:.1f}s)")
    if st['status'] == 'completed':
        file_path = st['data']['file_path']
        print(f"   -> [COMPLETE] Duration: {st['data']['duration']}s, BPM: {st['data']['bpm']}, Key: {st['data']['key']}")
        break
    elif st['status'] == 'failed':
        print("   -> Failed:", st.get('error'))
        break

# 4. Enqueue K-Trot Preview
if file_path and trot:
    print("\n4. Testing K-Trot Preview Rendering...")
    req = {
        'name': '시안 A (정통 K-Trot)',
        'job_type': 'preview',
        'source_audio_path': file_path,
        'start_sec': 0.0,
        'duration_sec': 12.0,
        'genre_params': trot,
        'custom_lyrics': '내 나이가 어때서 사랑에 나이가 있나요 쿵짝쿵짝',
        'original_lyrics': '바람이 불어오는 길목에서',
        'mastering_options': {
            'enabled': True,
            'target_lufs': -14.0,
            'eq_profile': 'crisp',
            'stereo_width': 1.25,
            'limiter_ceiling_db': -0.3
        }
    }
    enq_res = requests.post('http://127.0.0.1:8000/api/queue/enqueue', json=req).json()
    job_id = enq_res['job_id']
    print("   Enqueued Job ID:", job_id)

    # Wait for completion
    for i in range(25):
        time.sleep(0.5)
        jobs_res = requests.get('http://127.0.0.1:8000/api/queue/jobs').json()
        job = next((j for j in jobs_res['jobs'] if j['id'] == job_id), None)
        if job and job['status'] == 'completed':
            m = job['metadata']
            print("   -> [COMPLETE] K-Trot Preview Rendered!")
            print("      File:", job['result_url'])
            print(f"      Render Time: {m['render_time_sec']}s")
            print(f"      Output Duration: {m['duration']}s")
            print(f"      Genre: {m['genre_name']}, Vocal Mood: {m['vocal_mood']}")
            print(f"      Applied Lyrics: [{m['lyrics_source']}] {m['active_lyrics']}")
            break
        elif job and job['status'] == 'failed':
            print("   -> Render Failed:", job.get('error_msg'))
            break
