# pc/app/core/frame_buffer.py
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class FrameBuffer:
    """Thread-safe latest-frame buffer shared by upload/stream/recorder/AI."""
    lock: threading.Lock = field(default_factory=threading.Lock)
    frame: Optional[np.ndarray] = None
    ts: float = 0.0

    def clear(self) -> None:
        with self.lock:
            self.frame = None
            self.ts = 0.0

    def set(self, frame_bgr: np.ndarray) -> None:
        with self.lock:
            self.frame = frame_bgr
            self.ts = time.time()

    def get_copy(self) -> Optional[np.ndarray]:
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def age_sec(self) -> Optional[float]:
        with self.lock:
            if self.ts <= 0:
                return None
            return round(time.time() - self.ts, 3)