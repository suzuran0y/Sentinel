# pc/app/ai/ai_monitor_worker.py
import time
from datetime import datetime
from typing import Optional

from .ai_store import AiRuntime, EventStore
from .motion_trigger import MotionTrigger
from .ai_ark import ArkVisionClient, resolve_api_key


def _now_text() -> str:
    # Use local time string (your system is configured for Asia/Singapore timezone).
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_bool(x) -> bool:
    return bool(x) if isinstance(x, bool) else (str(x).lower() in ("1", "true", "yes", "on"))


def _clamp_int(x, lo, hi, default):
    try:
        v = int(x)
        return max(lo, min(hi, v))
    except Exception:
        return default


def _clamp_float(x, lo, hi, default):
    try:
        v = float(x)
        return max(lo, min(hi, v))
    except Exception:
        return default


def _should_call(now: float, last_ts: float, interval: float) -> bool:
    return (now - last_ts) >= interval


def ai_monitor_loop(cfg_store, frame_buf, ai_rt: AiRuntime, event_store: EventStore, logger, stop_event):
    """
    Triggered mode monitor:
      - SLEEP: run MotionTrigger only
      - OBSERVE: call ArkVisionClient every observe_interval seconds
      - Use has_person to confirm dwell >= threshold and to decide event end.
    """
    motion = MotionTrigger()
    client: Optional[ArkVisionClient] = None

    # Cache to avoid recreating client on every loop.
    last_model = None
    last_key = None

    while not stop_event.is_set():
        cfg = cfg_store.get_copy()

        ai_enabled = _safe_bool(cfg.get("ai_enabled", False))
        ai_mode = str(cfg.get("ai_mode", "triggered"))

        # Only implement triggered branch for now
        if not ai_enabled or ai_mode != "triggered":
            time.sleep(0.1)
            continue

        observe_interval = _clamp_float(cfg.get("ai_interval_observe", 5), 1, 60, 5)
        dwell_threshold = _clamp_float(cfg.get("ai_dwell_threshold_sec", 5), 1, 600, 5)
        end_grace = _clamp_float(cfg.get("ai_end_grace_sec", 3), 0, 60, 3)

        # Motion trigger parameters
        motion.ratio_threshold = _clamp_float(cfg.get("motion_ratio_threshold", 0.02), 0.001, 0.5, 0.02)
        motion.min_trigger_interval_sec = _clamp_float(cfg.get("motion_min_interval", 1.0), 0.1, 10.0, 1.0)

        ark_model = str(cfg.get("ark_model", "")).strip()
        api_key = resolve_api_key(cfg).strip()

        if not ark_model or not api_key:
            time.sleep(0.2)
            continue

        # Initialize / rebuild client if config changed
        if client is None or ark_model != last_model or api_key != last_key:
            try:
                client = ArkVisionClient(api_key=api_key, model=ark_model)
                last_model = ark_model
                last_key = api_key
                logger.info("ArkVisionClient ready")
            except Exception as e:
                with ai_rt.lock:
                    ai_rt.last_ai_error = f"Ark init failed: {e}"
                logger.error(f"Ark init failed: {e}")
                client = None
                time.sleep(1.0)
                continue

        frame = frame_buf.get_copy()
        if frame is None:
            time.sleep(0.05)
            continue

        now = time.time()

        with ai_rt.lock:
            state = ai_rt.state

        # ================= SLEEP: only motion trigger =================
        if state == "SLEEP":
            triggered, ratio = motion.check(frame)
            if triggered:
                with ai_rt.lock:
                    ai_rt.state = "OBSERVE"
                    ai_rt.last_trigger_ts = now
                    ai_rt.last_trigger_reason = f"motion_ratio={ratio:.4f}"
                    ai_rt.event_id = f"evt_{int(now)}"
                    ai_rt.event_start_ts = now
                    ai_rt.person_present_acc_sec = 0.0
                    ai_rt.last_person_true_ts = None
                    ai_rt.last_person_false_ts = None
                    ai_rt.dwell_confirmed = False
                    ai_rt.last_ai_error = ""
                    ai_rt.last_ai_json = None

                event_store.add_event({
                    "event_id": ai_rt.event_id,
                    "kind": "event_start",
                    "trigger": "motion",
                    "motion_ratio": ratio,
                    "time_text": _now_text(),
                })
                logger.info(f"AI event_start (motion ratio={ratio:.4f})")

            time.sleep(0.05)
            continue

        # ================= OBSERVE: periodic model calls =================
        if state == "OBSERVE":
            with ai_rt.lock:
                last_call = ai_rt.last_ai_call_ts
                event_id = ai_rt.event_id
                event_start_ts = ai_rt.event_start_ts or now
                person_acc = ai_rt.person_present_acc_sec
                last_true = ai_rt.last_person_true_ts
                last_false = ai_rt.last_person_false_ts
                dwell_ok = ai_rt.dwell_confirmed

            if not _should_call(now, last_call, observe_interval):
                time.sleep(0.02)
                continue

            prompt_template = str(cfg.get("ai_prompt_template", "") or "")
            scene_profile = str(cfg.get("ai_scene_profile", "") or "")
            session_focus = str(cfg.get("ai_session_focus", "") or "")
            extra_prompt = str(cfg.get("ai_prompt_extra", "") or "")
            jpeg_quality = _clamp_int(cfg.get("ai_jpeg_quality", 85), 50, 95, 85)

            try:
                parsed = client.analyze_frame(
                    frame,
                    time_text=_now_text(),
                    prompt_template=prompt_template,
                    scene_profile=scene_profile,
                    session_focus=session_focus,
                    extra_prompt=extra_prompt,
                    jpeg_quality=jpeg_quality,
                )
                has_person = bool(parsed.get("has_person", False))
                confidence = float(parsed.get("confidence", 0.0) or 0.0)

                with ai_rt.lock:
                    ai_rt.last_ai_call_ts = now
                    ai_rt.last_ai_json = parsed
                    ai_rt.last_ai_error = ""

                event_store.add_event({
                    "event_id": event_id,
                    "kind": "ai_frame",
                    "time_text": _now_text(),
                    "has_person": has_person,
                    "confidence": confidence,
                    "ai": parsed,
                })

            except Exception as e:
                with ai_rt.lock:
                    ai_rt.last_ai_call_ts = now
                    ai_rt.last_ai_error = str(e)

                event_store.add_event({
                    "event_id": event_id,
                    "kind": "ai_error",
                    "time_text": _now_text(),
                    "error": str(e),
                })
                logger.error(f"AI analyze error: {e}")
                time.sleep(0.05)
                continue

            # Dwell integration (approximate by observe_interval)
            if has_person:
                person_acc += observe_interval
                last_true = now
                last_false = None
            else:
                last_false = now if last_false is None else last_false

            # Dwell confirmed
            if (not dwell_ok) and person_acc >= dwell_threshold:
                dwell_ok = True
                event_store.add_event({
                    "event_id": event_id,
                    "kind": "dwell_confirmed",
                    "time_text": _now_text(),
                    "dwell_sec": round(person_acc, 2),
                    "threshold_sec": dwell_threshold,
                })
                logger.info(f"dwell_confirmed: {person_acc:.2f}s >= {dwell_threshold}s")

            # End condition: no person for end_grace seconds
            ended = False
            if last_false is not None and (now - last_false) >= end_grace:
                ended = True

            with ai_rt.lock:
                ai_rt.person_present_acc_sec = person_acc
                ai_rt.last_person_true_ts = last_true
                ai_rt.last_person_false_ts = last_false
                ai_rt.dwell_confirmed = dwell_ok

            if ended:
                event_store.add_event({
                    "event_id": event_id,
                    "kind": "event_end",
                    "time_text": _now_text(),
                    "total_event_sec": round(now - event_start_ts, 2),
                    "person_present_acc_sec": round(person_acc, 2),
                    "dwell_confirmed": dwell_ok,
                })
                logger.info(f"AI event_end: event_id={event_id}")

                with ai_rt.lock:
                    ai_rt.state = "SLEEP"
                    ai_rt.event_id = None
                    ai_rt.event_start_ts = None
                    ai_rt.person_present_acc_sec = 0.0
                    ai_rt.last_person_true_ts = None
                    ai_rt.last_person_false_ts = None
                    ai_rt.dwell_confirmed = False

            time.sleep(0.02)
            continue

        # Unknown state -> reset
        with ai_rt.lock:
            ai_rt.state = "SLEEP"
        time.sleep(0.1)


def start_ai_monitor_thread(cfg_store, frame_buf, ai_rt: AiRuntime, event_store: EventStore, logger, stop_event):
    import threading
    t = threading.Thread(
        target=ai_monitor_loop,
        args=(cfg_store, frame_buf, ai_rt, event_store, logger, stop_event),
        daemon=True,
    )
    t.start()
    return t