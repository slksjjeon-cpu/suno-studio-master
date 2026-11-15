import requests
import time
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

presets = requests.get('http://127.0.0.1:8000/api/presets').json()['genre_presets']
trot = next(p for p in presets if p['id'] == 'k_trot_classic')

req = {
    'name': '시안 A (정통 K-Trot)',
    'job_type': 'preview',
    'source_audio_path': os.path.join(BASE_DIR, 'samples', 'demo_pop_ballad.wav'),
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
r = requests.post('http://127.0.0.1:8000/api/queue/enqueue', json=req).json()
print('Enqueued K-Trot Job:', r['job_id'])

for _ in range(25):
    time.sleep(1)
    jobs = requests.get('http://127.0.0.1:8000/api/queue/jobs').json()['jobs']
    job = next((j for j in jobs if j['id'] == r['job_id']), None)
    if job:
        print(f"Status: {job['status']} ({job['progress']}%) - {job['progress_msg']}")
        if job['status'] == 'completed':
            print('-> K-Trot Result URL:', job['result_url'])
            print('-> Render Time:', job['metadata']['render_time_sec'], 'seconds')
            print('-> Duration:', job['metadata']['duration'], 'seconds')
            break
        elif job['status'] == 'failed':
            print('-> Failed:', job.get('error_msg'))
            break
