# pc/app/core/upload_stats.py
import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class UploadStats:
    """Counters + short-window FPS estimate for /upload."""
    lock: threading.Lock = field(default_factory=threading.Lock)
    ok_count: int = 0
    bad_missing_count: int = 0
    bad_decode_count: int = 0
    rejected_ingest_count: int = 0

    upload_ts_lock: threading.Lock = field(default_factory=threading.Lock)
    upload_ts: deque = field(default_factory=lambda: deque(maxlen=400))

    def mark_ok(self) -> None:
        with self.lock:
            self.ok_count += 1
        with self.upload_ts_lock:
            self.upload_ts.append(time.time())

    def mark_missing(self) -> None:
        with self.lock:
            self.bad_missing_count += 1

    def mark_decode_failed(self) -> None:
        with self.lock:
            self.bad_decode_count += 1

    def mark_rejected(self) -> None:
        with self.lock:
            self.rejected_ingest_count += 1

    def snapshot_counts(self) -> dict:
        with self.lock:
            return {
                "200_ok": self.ok_count,
                "400_missing_image": self.bad_missing_count,
                "400_decode_failed": self.bad_decode_count,
                "503_ingest_disabled": self.rejected_ingest_count,
            }

    def upload_fps(self, window: float = 2.0) -> float:
        now = time.time()
        with self.upload_ts_lock:
            while self.upload_ts and (now - self.upload_ts[0]) > window:
                self.upload_ts.popleft()

            if len(self.upload_ts) >= 2:
                return (len(self.upload_ts) - 1) / max(1e-6, (self.upload_ts[-1] - self.upload_ts[0]))
            if len(self.upload_ts) == 1:
                return 0.5
            return 0.0