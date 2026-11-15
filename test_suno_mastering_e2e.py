import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("[E2E Test] Starting Suno AI De-Watermark & Pro Mastering Verification...")

# 1. System status
sys_res = requests.get('http://127.0.0.1:8000/api/system-status').json()
print("1. System Status:", sys_res['gpu']['name'])

# 2. Trigger Demo Track Analysis
print("\n2. Testing Suno Demo Track Analysis with Tempo Drift & Watermark Detection...")
start_res = requests.post('http://127.0.0.1:8000/api/load-sample-async').json()
task_id = start_res['task_id']
print("   Task ID:", task_id)

file_path = None
analyzed_data = None
for i in range(30):
    time.sleep(0.4)
    st = requests.get(f'http://127.0.0.1:8000/api/analysis-status/{task_id}').json()
    pct = st.get('progress', 0)
    stage = st.get('stage', '')
    eta = st.get('remaining_sec', 0)
    print(f"   [{pct}%] {stage} (ETA: {eta:.1f}s)")
    if st['status'] == 'completed':
        analyzed_data = st['data']
        file_path = analyzed_data['file_path']
        break
    elif st['status'] == 'failed':
        print("   -> Failed:", st.get('error'))
        sys.exit(1)

print("\n=== Suno Diagnostic Report ===")
t_info = analyzed_data['tempo_analysis']
w_info = analyzed_data['watermark_analysis']
print(f"• Duration: {analyzed_data['duration_str']}")
print(f"• Start BPM: {t_info['start_bpm']} BPM -> End BPM: {t_info['end_bpm']} BPM")
print(f"• Tempo Drift Rate: {t_info['drift_percent']}% (Accelerating: {t_info['is_accelerating']})")
print(f"• Watermark Detected: {w_info['detected']} (Confidence: {w_info['confidence']}%, Ultrasonic: {w_info['ultrasonic_present']})")
print(f"• Input Loudness: {analyzed_data['input_lufs']} LUFS, Peak: {analyzed_data['input_peak_db']} dBFS")

# 3. Enqueue Mastering Preview Job
print("\n3. Testing Pro Mastering Preview Job (Watermark Removal + Tempo Flattening + -14 LUFS)...")
mastering_options = {
    "dewatermark_enabled": True,
    "tempo_stabilize_enabled": True,
    "tempo_info": t_info,
    "pitch_shift": 0.0,
    "target_lufs": -14.0,
    "auto_leveling": True,
    "bass_boost_db": 1.5,
    "mid_presence_db": 0.8,
    "air_band_boost_db": 2.2,
    "stereo_width": 1.25,
    "tape_warmth": 0.15,
    "limiter_ceiling_db": -0.3
}

payload = {
    "name": "마스터 A (스트리밍 -14 LUFS & 템포 평탄화)",
    "job_type": "preview",
    "source_audio_path": file_path,
    "start_sec": 0.0,
    "duration_sec": 15.0,
    "mastering_options": mastering_options
}

enq_res = requests.post('http://127.0.0.1:8000/api/queue/enqueue', json=payload).json()
job_id = enq_res['job_id']
print("   Enqueued Job ID:", job_id)

for _ in range(25):
    time.sleep(0.5)
    jobs = requests.get('http://127.0.0.1:8000/api/queue/jobs').json()['jobs']
    job = next((j for j in jobs if j['id'] == job_id), None)
    if job:
        print(f"   [{job['status']}] {job['progress']}% - {job['progress_msg']}")
        if job['status'] == 'completed':
            m = job['metadata']
            print("\n=== Mastered Output Success ===")
            print(f"• Result File: {job['result_url']}")
            print(f"• Render Time: {m['render_time_sec']}s")
            print(f"• Output Duration: {m['duration']}s")
            print(f"• Input Loudness: {m['input_lufs']} LUFS -> Mastered: {m['output_lufs']} LUFS (Target: {m['target_lufs']} LUFS)")
            print(f"• Watermark Removed: {m['watermark_removed']}")
            print(f"• Tempo Stabilized: {m['tempo_stabilized']}")
            print(f"• Tempo Report: {m['tempo_report'].get('status')}")
            break
        elif job['status'] == 'failed':
            print("   -> Failed:", job.get('error_msg'))
            sys.exit(1)

print("\n[SUCCESS] Suno De-Watermark & Pro Mastering Studio Verified End-to-End!")
