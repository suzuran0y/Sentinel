# pc/app/config/config_store.py
import json
import os
import threading
from typing import Any, Dict, Tuple

# Optional placeholders (kept to preserve your original structure)
API_KEY = ""
DATABASE_URL = ""
DEBUG = True

DEFAULT_CONFIG: Dict[str, Any] = {
    # communication / ingest
    "ingest_enabled": False,  # default: do not accept phone uploads
    "autosave": False,

    # preview / stream
    "stream_fps": 10,
    "jpeg_quality": 80,

    # recording
    "recording": False,
    "record_fps": 10,
    "segment_seconds": 60,
    "out_root": "recordings",
    "cam_name": "phone1",
    "codec": "avc1",

    # =========================
    # AI monitoring (triggered branch v1)
    # =========================
    "ai_enabled": False,
    "ai_mode": "triggered",

    # Ark / Volcengine
    "ark_model": "doubao-seed-2-0-mini-260215",
    "ark_api_key": API_KEY,  # can also be supplied via env var ARK_API_KEY

    # intervals & thresholds
    "ai_interval_observe": 5,
    "ai_dwell_threshold_sec": 5,
    "ai_end_grace_sec": 3,

    # prompt contexts
    "ai_prompt_template": (
        "You are a video surveillance assistant. You will receive a single CCTV frame and some context. "
        "Output ONLY one JSON object that decides whether there is a person, the person count, the activity, "
        "the risk level, and a short summary."
    ),
    "ai_scene_profile": "none",
    "ai_session_focus": "none",
    "ai_prompt_extra": "none",
    "ai_jpeg_quality": 85,

    # trigger (motion sentinel)
    "motion_ratio_threshold": 0.02,
    "motion_min_interval": 1.0,
}


def merge_known_keys(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = base.copy()
    for k, v in patch.items():
        if k in merged:
            merged[k] = v
    return merged


def validate_and_normalize(patch: dict) -> Tuple[bool, dict, str]:
    cleaned: Dict[str, Any] = {}

    def _int(name: str, lo: int, hi: int) -> None:
        if name not in patch:
            return
        try:
            v = int(patch[name])
        except Exception:
            raise ValueError(f"{name} must be int")
        if v < lo or v > hi:
            raise ValueError(f"{name} must be in [{lo}, {hi}]")
        cleaned[name] = v

    def _float(name: str, lo: float, hi: float) -> None:
        if name not in patch:
            return
        try:
            v = float(patch[name])
        except Exception:
            raise ValueError(f"{name} must be float")
        if v < lo or v > hi:
            raise ValueError(f"{name} must be in [{lo}, {hi}]")
        cleaned[name] = v

    def _bool(name: str) -> None:
        if name not in patch:
            return
        v = patch[name]
        if isinstance(v, bool):
            cleaned[name] = v
            return
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes", "on"):
                cleaned[name] = True
                return
            if v.lower() in ("false", "0", "no", "off"):
                cleaned[name] = False
                return
        raise ValueError(f"{name} must be bool")

    def _str(name: str, maxlen: int = 200) -> None:
        if name not in patch:
            return
        v = str(patch[name])
        if len(v) > maxlen:
            raise ValueError(f"{name} too long")
        cleaned[name] = v

    try:
        _bool("autosave")
        _bool("ingest_enabled")

        _int("stream_fps", 1, 30)
        _int("jpeg_quality", 30, 95)

        _int("record_fps", 1, 30)
        _int("segment_seconds", 10, 3600)

        _str("out_root", 300)
        _str("cam_name", 80)
        _str("codec", 20)

        # AI switches
        _bool("ai_enabled")
        _str("ai_mode", 30)

        # Ark config
        _str("ark_model", 200)
        _str("ark_api_key", 300)

        # AI intervals & thresholds
        _float("ai_interval_observe", 1, 60)
        _float("ai_dwell_threshold_sec", 1, 600)
        _float("ai_end_grace_sec", 0, 60)

        # Prompt contexts
        _str("ai_prompt_template", 2000)
        _str("ai_scene_profile", 2000)
        _str("ai_session_focus", 2000)
        _str("ai_prompt_extra", 4000)

        # JPEG quality
        _int("ai_jpeg_quality", 50, 95)

        # Motion trigger params
        _float("motion_ratio_threshold", 0.001, 0.5)
        _float("motion_min_interval", 0.1, 10.0)

    except Exception as e:
        return False, {}, str(e)

    return True, cleaned, ""


class ConfigStore:
    """Thread-safe config store with load/save and partial updates."""
    def __init__(self, path: str = "config.json", initial: Dict[str, Any] | None = None):
        self.path = path
        self.lock = threading.Lock()
        self.config = initial or DEFAULT_CONFIG.copy()

    def get_copy(self) -> dict:
        with self.lock:
            return self.config.copy()

    def set_many(self, patch: dict) -> dict:
        with self.lock:
            self.config = merge_known_keys(self.config, patch)
            return self.config.copy()

    def set_key(self, key: str, val: Any) -> None:
        with self.lock:
            if key in self.config:
                self.config[key] = val

    def load_from_disk(self, logger=None) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self.lock:
                self.config = merge_known_keys(DEFAULT_CONFIG, data)
            if logger:
                logger.info("config loaded from disk")
        except Exception as e:
            if logger:
                logger.error(f"load config failed: {e}")

    def save_to_disk(self, logger=None) -> None:
        try:
            with self.lock:
                data = self.config.copy()
            with open(self.path, "w", encoding="utf-8") as f:
                # Keep ensure_ascii=False (safe) so config remains human-readable.
                json.dump(data, f, indent=2, ensure_ascii=False)
            if logger:
                logger.info("config saved to disk")
        except Exception as e:
            if logger:
                logger.error(f"save config failed: {e}")