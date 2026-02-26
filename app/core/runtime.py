# pc/app/core/runtime.py
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RecorderRuntime:
    """
    Thread-shared recorder runtime state.

    We intentionally keep `rec` as `object` to avoid import cycles.
    """
    lock: threading.Lock = field(default_factory=threading.Lock)
    rec: object = None  # SegmentRecorder instance
    recording_start_ts: Optional[float] = None

    def is_opened(self) -> bool:
        with self.lock:
            return self.rec is not None