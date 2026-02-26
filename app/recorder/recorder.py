# pc/app/recorder/recorder.py
import os
import time
from datetime import datetime

import cv2


class SegmentRecorder:
    """
    Continuously writes video and rotates files by fixed duration.

    Output example:
      recordings/videos/YYYYMMDD/phone1_YYYYMMDD_HHMMSS.mp4
    """
    def __init__(self, out_root: str = "recordings", fps: int = 10, segment_seconds: int = 60,
                 codec: str = "avc1", cam_name: str = "cam1"):
        self.out_root = out_root
        self.fps = fps
        self.segment_seconds = segment_seconds
        self.fourcc = cv2.VideoWriter_fourcc(*codec)
        self.cam_name = cam_name

        self.writer = None
        self.segment_start_ts = None
        self.current_path = None
        os.makedirs(self.out_root, exist_ok=True)

    def _make_path(self) -> str:
        now = datetime.now()
        day_dir = os.path.join(self.out_root, now.strftime("%Y%m%d"))
        os.makedirs(day_dir, exist_ok=True)
        fname = f"{self.cam_name}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
        return os.path.join(day_dir, fname)

    def _open_writer(self, frame_w: int, frame_h: int) -> str:
        self.current_path = self._make_path()
        self.writer = cv2.VideoWriter(self.current_path, self.fourcc, self.fps, (frame_w, frame_h))
        self.segment_start_ts = time.time()
        if not self.writer.isOpened():
            self.writer = None
            raise RuntimeError("VideoWriter open failed. Try codec='XVID' + .avi, or install codecs.")
        return self.current_path

    def _close_writer(self) -> None:
        if self.writer is not None:
            self.writer.release()
        self.writer = None
        self.segment_start_ts = None
        self.current_path = None

    def write(self, frame_bgr) -> None:
        """Write one frame; auto-open and auto-rotate by time."""
        h, w = frame_bgr.shape[:2]
        now = time.time()

        if self.writer is None:
            path = self._open_writer(w, h)
            print(f"[REC] start {path}")

        if self.segment_start_ts is not None and (now - self.segment_start_ts) >= self.segment_seconds:
            old = self.current_path
            self._close_writer()
            path = self._open_writer(w, h)
            print(f"[REC] rotate {old} -> {path}")

        self.writer.write(frame_bgr)

    def stop(self) -> None:
        if self.writer is not None:
            print(f"[REC] stop {self.current_path}")
        self._close_writer()