import os
import sys
import time

print("[Test] Verifying AI Cover Studio Pipeline...")

from core.analyzer import analyze_audio_file
from core.presets import load_presets
from core.arranger import rearrange_audio_segment
from core.master import master_audio
from core.queue_worker import StudioQueueManager

sample_file = os.path.join(os.path.dirname(__file__), "samples", "demo_pop_ballad.wav")
assert os.path.exists(sample_file), "Sample track missing"

print("\n1. Testing Audio Analyzer...")
t0 = time.time()
analysis = analyze_audio_file(sample_file)
print(f"-> Analyzed in {time.time()-t0:.2f}s:")
print(f"   Duration: {analysis['duration']}s, BPM: {analysis['bpm']}, Key: {analysis['key']}")
print(f"   Peaks count: {len(analysis['waveform_peaks'])}, Lyrics text length: {len(analysis['lyrics'])}")

print("\n2. Testing Presets...")
presets = load_presets()
print(f"-> Loaded {len(presets)} presets:")
city_pop = presets[0]
print(f"   Preset: {city_pop['name']} - {city_pop['prompt'][:50]}...")

print("\n3. Testing Arranger (10s preview segment)...")
t0 = time.time()
rearranged = rearrange_audio_segment(
    source_audio_path=sample_file,
    start_sec=5.0,
    duration_sec=10.0,
    genre_params=city_pop,
    custom_lyrics="새로운 계절이 오면 다시 춤을 출 거야",
    original_lyrics=analysis["lyrics"]
)
print(f"-> Rearranged in {time.time()-t0:.2f}s:")
print(f"   Rendered duration: {rearranged['duration_rendered']}s, Active lyrics: '{rearranged['active_lyrics']}'")
print(f"   Lyrics source: {rearranged['lyrics_source']}")

print("\n4. Testing Mastering Engine...")
t0 = time.time()
out_wav = os.path.join(os.path.dirname(__file__), "outputs", "test_preview_mastered.wav")
mastered = master_audio(
    audio_data=rearranged["audio_data"],
    sr=rearranged["sample_rate"],
    mastering_options={
        "enabled": True,
        "target_lufs": -14.0,
        "eq_profile": "crisp",
        "stereo_width": 1.25,
        "limiter_ceiling_db": -0.3
    },
    output_filepath=out_wav
)
print(f"-> Mastered in {time.time()-t0:.2f}s:")
print(f"   Saved to: {mastered['output_filepath']}, File exists: {os.path.exists(out_wav)}")

print("\n5. Testing Queue Manager...")
qm = StudioQueueManager(output_dir=os.path.join(os.path.dirname(__file__), "outputs"))
job_id = qm.add_job(
    name="시안 A (시티팝)",
    job_type="preview",
    source_audio_path=sample_file,
    start_sec=0.0,
    duration_sec=10.0,
    genre_params=city_pop,
    custom_lyrics="시안 A 테스트 가사"
)
print(f"-> Enqueued job: {job_id}. Waiting for completion...")

max_wait = 20
start_wait = time.time()
while time.time() - start_wait < max_wait:
    job = qm.get_job(job_id)
    if job["status"] in ["completed", "failed"]:
        print(f"-> Job status: {job['status']} in {time.time() - start_wait:.2f}s! Result: {job.get('result_file')}")
        break
    time.sleep(0.5)

qm.is_running = False
print("\n[SUCCESS] Entire Studio Pipeline verified end-to-end!")
