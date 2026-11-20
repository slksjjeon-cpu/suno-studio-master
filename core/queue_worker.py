import os
import sys
import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from core.pipeline_suno import process_suno_mastering

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import builtins
_orig_print = builtins.print
def _safe_global_print(*args, **kwargs):
    try:
        _orig_print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            enc = sys.stdout.encoding or "utf-8"
            safe_args = [str(a).encode(enc, errors="replace").decode(enc, errors="replace") for a in args]
            _orig_print(*safe_args, **kwargs)
        except Exception:
            pass
builtins.print = _safe_global_print

def safe_print(*args, **kwargs):
    """Crash-proof print for any Unicode characters (Japanese, Chinese, emojis, etc.) on Windows."""
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            enc = sys.stdout.encoding or "utf-8"
            safe_args = [
                str(a).encode(enc, errors="replace").decode(enc, errors="replace")
                for a in args
            ]
            print(*safe_args, **kwargs)
        except Exception:
            pass

class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class StudioQueueManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.queue: List[str] = []
        self.lock = threading.Lock()
        self.is_running = True
        self.current_job_id: Optional[str] = None
        
        # Start background worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def add_job(
        self,
        name: str,
        job_type: str, # "preview" or "full"
        source_audio_path: str,
        start_sec: float,
        duration_sec: float,
        mastering_options: Dict[str, Any]
    ) -> str:
        """Enqueue a mastering / de-watermarking job."""
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        job = {
            "id": job_id,
            "name": name,
            "type": job_type,
            "status": JobStatus.QUEUED,
            "progress": 0,
            "progress_msg": "대기열에서 순서 대기 중...",
            "created_at": time.time(),
            "started_at": None,
            "completed_at": None,
            "source_audio_path": source_audio_path,
            "start_sec": start_sec,
            "duration_sec": duration_sec,
            "mastering_options": mastering_options,
            "result_file": None,
            "result_url": None,
            "error_msg": None,
            "metadata": {}
        }

        with self.lock:
            self.jobs[job_id] = job
            self.queue.append(job_id)

        safe_print(f"[QueueManager] Added mastering job '{name}' ({job_id}) to queue. Position: {len(self.queue)}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self.lock:
            return sorted(list(self.jobs.values()), key=lambda x: x["created_at"], reverse=True)

    def _worker_loop(self):
        while self.is_running:
            job_id_to_run = None
            with self.lock:
                if self.queue:
                    job_id_to_run = self.queue.pop(0)
                    self.current_job_id = job_id_to_run

            if not job_id_to_run:
                time.sleep(0.4)
                continue

            self._execute_job(job_id_to_run)
            
            with self.lock:
                self.current_job_id = None

    def _execute_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            safe_print(f"[QueueWorker] Starting execution of job: {job['name']} ({job_id})")
            job["status"] = JobStatus.PROCESSING
            job["started_at"] = time.time()
            job["progress"] = 10
            job["progress_msg"] = "오디오 슬라이싱 및 준비 중..."

            source_path = job["source_audio_path"]
            start_sec = job["start_sec"]
            duration_sec = job["duration_sec"]
            mastering_options = job["mastering_options"]

            # Generate descriptive mastered filename based on Suno/source track name & applied settings
            base_name = None
            if mastering_options.get("track_title"):
                base_name = mastering_options["track_title"]
            elif job.get("track_title"):
                base_name = job["track_title"]

            if not base_name:
                raw_name = os.path.splitext(os.path.basename(source_path))[0]
                # Strip timestamp upload prefix if exists
                parts = raw_name.split("_", 1)
                if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) >= 10:
                    base_name = parts[1]
                else:
                    base_name = raw_name

            import re
            base_name = re.sub(r'[\\/*?:"<>|]', "", str(base_name)).strip(". ") or "SunoTrack"

            tags = []
            if job["type"] == "full":
                tags.append("Master")
            else:
                tags.append(f"Preview_{int(round(duration_sec))}s")

            if mastering_options.get("dewatermark_enabled", True):
                tags.append("DeWatermarked")

            if mastering_options.get("tempo_stabilize_enabled", True):
                t_info = mastering_options.get("tempo_info", {})
                start_bpm = t_info.get("start_bpm")
                tags.append(f"TempoFixed_{start_bpm}BPM" if start_bpm else "TempoFixed")

            def _safe_float(val, default):
                try:
                    if val is None:
                        return default
                    f = float(val)
                    import math
                    return default if math.isnan(f) else f
                except (ValueError, TypeError):
                    return default

            target_lufs = _safe_float(mastering_options.get("target_lufs"), -14.0)
            mastering_options["target_lufs"] = target_lufs
            mastering_options["bass_boost_db"] = _safe_float(mastering_options.get("bass_boost_db"), 1.0)
            mastering_options["mid_presence_db"] = _safe_float(mastering_options.get("mid_presence_db"), 0.5)
            mastering_options["air_band_boost_db"] = _safe_float(mastering_options.get("air_band_boost_db"), 1.5)
            mastering_options["stereo_width"] = _safe_float(mastering_options.get("stereo_width"), 1.15)
            mastering_options["tape_warmth"] = _safe_float(mastering_options.get("tape_warmth"), 0.08)
            mastering_options["limiter_ceiling_db"] = _safe_float(mastering_options.get("limiter_ceiling_db"), -1.0)

            speed_ratio = _safe_float(mastering_options.get("speed_ratio"), 1.0)
            mastering_options["speed_ratio"] = speed_ratio
            keep_pitch = bool(mastering_options.get("keep_pitch", True))
            mastering_options["keep_pitch"] = keep_pitch

            pitch_shift = _safe_float(mastering_options.get("pitch_shift"), 0.0)
            mastering_options["pitch_shift"] = pitch_shift

            if abs(speed_ratio - 1.0) > 0.005:
                pitch_lbl = "Kp" if keep_pitch else "Vinyl"
                tags.append(f"Speed_{speed_ratio:g}x_{pitch_lbl}")

            if abs(pitch_shift) > 0.005:
                tags.append(f"Key_{pitch_shift:+g}st")

            tags.append(f"{target_lufs:g}LUFS")

            if mastering_options.get("auto_leveling", True):
                tags.append("AutoLeveled")

            short_id = job_id.replace("job_", "")[:4]
            candidate_filename = f"{base_name}_{'_'.join(tags)}.wav"
            if os.path.exists(os.path.join(self.output_dir, candidate_filename)):
                filename = f"{base_name}_{'_'.join(tags)}_{short_id}.wav"
            else:
                filename = candidate_filename
            output_filepath = os.path.join(self.output_dir, filename)

            job["progress"] = 30
            job["progress_msg"] = "초고역대 비가청 워터마크 & 위상 지문 제거 중..."
            time.sleep(0.15)

            if mastering_options.get("tempo_stabilize_enabled", True):
                job["progress"] = 50
                job["progress_msg"] = "동적 템포 가속(Drift) 보정 및 피치 유지 시간축 평탄화 중..."
                time.sleep(0.15)

            if abs(speed_ratio - 1.0) > 0.005:
                job["progress"] = 65
                job["progress_msg"] = f"Suno 곡 빠르기 {speed_ratio:.2f}x 리타이밍 연산 중..."
                time.sleep(0.15)

            job["progress"] = 80
            job["progress_msg"] = "스튜디오 마스터링 (오토레벨링, 4-Band EQ, Mid/Side, LUFS 노멀라이징) 적용 중..."

            # Execute pipeline
            result = process_suno_mastering(
                source_audio_path=source_path,
                output_filepath=output_filepath,
                options=mastering_options,
                start_sec=start_sec,
                duration_sec=duration_sec
            )

            if not os.path.exists(output_filepath) or os.path.getsize(output_filepath) < 1000:
                raise RuntimeError("마스터링 결과 파일 생성이 실패하였거나 손상되었습니다. (디스크 용량을 확인해주세요)")

            job["progress"] = 100
            job["status"] = JobStatus.COMPLETED
            job["progress_msg"] = "마스터링 완료!"
            job["completed_at"] = time.time()
            job["result_file"] = output_filepath
            job["result_url"] = f"/outputs/{filename}"
            job["filename"] = filename
            
            job["metadata"] = {
                "filename": filename,
                "duration": result["duration_sec"],
                "start_sec": start_sec,
                "input_lufs": result["metrics_before"]["lufs"],
                "output_lufs": result["metrics_after"]["lufs"],
                "target_lufs": mastering_options.get("target_lufs", -14.0),
                "peak_db": result["metrics_after"]["peak_db"],
                "watermark_removed": result["watermark_removed"],
                "tempo_stabilized": result["tempo_stabilized"],
                "tempo_report": result.get("tempo_report", {}),
                "metrics_before": result["metrics_before"],
                "metrics_after": result["metrics_after"],
                "render_time_sec": result["process_time_sec"]
            }
            safe_print(f"[QueueWorker] Finished {job['name']} in {result['process_time_sec']}s")

        except Exception as e:
            safe_print(f"[QueueWorker] Error executing {job_id}: {e}")
            import traceback
            safe_print(traceback.format_exc())
            job["status"] = JobStatus.FAILED
            job["progress_msg"] = f"에러 발생: {str(e)}"
            job["error_msg"] = str(e)
            job["completed_at"] = time.time()
