# pc/app/ai/motion_trigger.py
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np


@dataclass
class MotionTrigger:
    """
    Lightweight motion detector (sentinel) to wake up AI.

    It does not try to understand semantics. It only detects "significant pixel changes",
    which is cheap and suitable while AI is in SLEEP state.
    """
    ratio_threshold: float = 0.02
    min_trigger_interval_sec: float = 1.0

    blur_ksize: int = 9
    diff_threshold: int = 25

    _prev_gray: Optional[np.ndarray] = None
    _last_trigger_ts: float = 0.0

    def reset(self) -> None:
        self._prev_gray = None
        self._last_trigger_ts = 0.0

    def _preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        if self.blur_ksize and self.blur_ksize >= 3:
            gray = cv2.GaussianBlur(gray, (self.blur_ksize, self.blur_ksize), 0)
        return gray

    def check(self, frame_bgr: np.ndarray) -> Tuple[bool, float]:
        """Return (triggered, motion_ratio)."""
        now = time.time()
        if (now - self._last_trigger_ts) < self.min_trigger_interval_sec:
            return False, 0.0

        gray = self._preprocess(frame_bgr)
        if self._prev_gray is None:
            self._prev_gray = gray
            return False, 0.0

        diff = cv2.absdiff(self._prev_gray, gray)
        _, th = cv2.threshold(diff, self.diff_threshold, 255, cv2.THRESH_BINARY)

        # Small morphology open to reduce noise
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

        motion_pixels = float(np.count_nonzero(th))
        total_pixels = float(th.size)
        ratio = 0.0 if total_pixels <= 0 else motion_pixels / total_pixels

        self._prev_gray = gray

        if ratio >= self.ratio_threshold:
            self._last_trigger_ts = now
            return True, ratio

        return False, ratio