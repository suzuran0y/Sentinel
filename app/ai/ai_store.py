# pc/app/ai/ai_store.py
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AiRuntime:
    """Thread-shared AI monitor runtime state."""
    lock: threading.Lock = field(default_factory=threading.Lock)

    # state machine: SLEEP / OBSERVE
    state: str = "SLEEP"

    # last trigger and last ai call timestamps
    last_trigger_ts: float = 0.0
    last_ai_call_ts: float = 0.0

    # current event
    event_id: Optional[str] = None
    event_start_ts: Optional[float] = None

    # person dwell tracking
    person_present_acc_sec: float = 0.0
    last_person_true_ts: Optional[float] = None
    last_person_false_ts: Optional[float] = None
    dwell_confirmed: bool = False

    # debug info
    last_trigger_reason: str = ""
    last_ai_error: str = ""
    last_ai_json: Optional[Dict[str, Any]] = None

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "state": self.state,
                "last_trigger_ts": self.last_trigger_ts,
                "last_ai_call_ts": self.last_ai_call_ts,
                "event_id": self.event_id,
                "event_start_ts": self.event_start_ts,
                "person_present_acc_sec": round(self.person_present_acc_sec, 3),
                "dwell_confirmed": self.dwell_confirmed,
                "last_trigger_reason": self.last_trigger_reason,
                "last_ai_error": self.last_ai_error,
                "last_ai_json": self.last_ai_json,
            }


class EventStore:
    """
    Append-only JSONL event store + tail memory cache.

    Each line is a JSON object, which is convenient for debugging and later migration to SQLite.
    """
    def __init__(self, path: str = "ai_events.jsonl", keep_last: int = 300):
        self.path = path
        self.keep_last = keep_last
        self.lock = threading.Lock()
        self._buf: List[Dict[str, Any]] = []

        # Ensure directory exists
        d = os.path.dirname(os.path.abspath(self.path))
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

        # Load last N records on startup (best-effort).
        self._load_tail()

    def _load_tail(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-self.keep_last:]
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    self._buf.append(json.loads(ln))
                except Exception:
                    continue
        except Exception:
            pass

    def _append_mem(self, obj: Dict[str, Any]) -> None:
        self._buf.append(obj)
        if len(self._buf) > self.keep_last:
            self._buf = self._buf[-self.keep_last:]

    def add_event(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-fill id/ts and append to JSONL."""
        with self.lock:
            event = dict(obj)
            event.setdefault("id", str(uuid.uuid4()))
            event.setdefault("ts", time.time())

            line = json.dumps(event, ensure_ascii=False)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

            self._append_mem(event)
            return event

    def latest(self, n: int = 50) -> List[Dict[str, Any]]:
        n = max(1, min(int(n), 500))
        with self.lock:
            return list(reversed(self._buf[-n:]))