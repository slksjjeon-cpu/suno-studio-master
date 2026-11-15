import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("[Test] Verifying Descriptive Mastered Filename Generation...")

# 1. Start Demo Analysis
start_res = requests.post('http://127.0.0.1:8000/api/load-sample-async').json()
task_id = start_res['task_id']

file_path = None
for _ in range(25):
    time.sleep(0.4)
    st = requests.get(f'http://127.0.0.1:8000/api/analysis-status/{task_id}').json()
    if st['status'] == 'completed':
        file_path = st['data']['file_path']
        t_info = st['data']['tempo_analysis']
        break

print(f"• Analyzed: {file_path}")

# 2. Enqueue Preview Job
req = {
    "name": "마스터 A",
    "job_type": "preview",
    "source_audio_path": file_path,
    "start_sec": 0.0,
    "duration_sec": 15.0,
    "mastering_options": {
        "dewatermark_enabled": True,
        "tempo_stabilize_enabled": True,
        "tempo_info": t_info,
        "target_lufs": -14.0,
        "auto_leveling": True,
        "stereo_width": 1.25,
        "tape_warmth": 0.15,
        "limiter_ceiling_db": -0.3
    }
}

enq = requests.post('http://127.0.0.1:8000/api/queue/enqueue', json=req).json()
job_id = enq['job_id']
print(f"• Enqueued Job: {job_id}")

for _ in range(15):
    time.sleep(0.5)
    jobs = requests.get('http://127.0.0.1:8000/api/queue/jobs').json()['jobs']
    job = next((j for j in jobs if j['id'] == job_id), None)
    if job and job['status'] == 'completed':
        fn = job.get('filename')
        print(f"\n=== Output Filename Check ===")
        print(f"• Generated Filename: {fn}")
        print(f"• File URL: {job['result_url']}")
        
        # Verify naming format
        assert "demo_suno_drift" in fn, "Source filename missing!"
        assert "DeWatermarked" in fn, "Watermark tag missing!"
        assert "TempoFixed" in fn, "Tempo tag missing!"
        assert "-14LUFS" in fn, "LUFS tag missing!"
        assert "AutoLeveled" in fn, "AutoLevel tag missing!"
        print("[SUCCESS] All mastering details accurately embedded into filename!")
        break
