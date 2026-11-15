import time
import sys
from core.pipeline_suno import process_suno_mastering
from core.analyzer_suno import analyze_suno_track

sys.stdout.reconfigure(encoding='utf-8')

sample = 'samples/demo_suno_drift.wav'
print("[Benchmark] Testing Suno Mastering Studio Processing Speed...")

t0 = time.time()
ana = analyze_suno_track(sample)
ana_time = round(time.time() - t0, 3)
print(f"1. Analysis Completed in: {ana_time}s")
print(f"   • Start BPM: {ana['tempo_analysis']['start_bpm']} -> End: {ana['tempo_analysis']['end_bpm']}")
print(f"   • Watermark Confidence: {ana['watermark_analysis']['confidence']}%")

opt = {
    'dewatermark_enabled': True,
    'tempo_stabilize_enabled': True,
    'tempo_info': ana['tempo_analysis'],
    'target_lufs': -14.0,
    'auto_leveling': True,
    'stereo_width': 1.25,
    'tape_warmth': 0.15,
    'limiter_ceiling_db': -0.3
}

t1 = time.time()
res = process_suno_mastering(sample, 'outputs/benchmark_fast.wav', opt, start_sec=0.0, duration_sec=15.0)
render_time = round(time.time() - t1, 3)

print(f"2. 15s Preview Mastering Completed in: {render_time}s! (Ultra-Fast!)")
print(f"   • Input: {res['metrics_before']['lufs']} LUFS -> Mastered: {res['metrics_after']['lufs']} LUFS")
print(f"   • Watermark Removed: {res['watermark_removed']}")
print(f"   • Tempo Stabilized: {res['tempo_stabilized']}")
print(f"   • File: {res['output_filepath']}")
