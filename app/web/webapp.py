# pc/app/web/webapp.py
import os
import time
import threading
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, request, Response, jsonify, render_template

from app.config.config_store import validate_and_normalize
from app.recorder.recorder_worker import stop_recorder

def create_app(cfg_store, frame_buf, stats, rec_rt, ai_rt, event_store, logger, stop_event, threads, server_log_path: str) -> Flask:
    """
    Flask app factory.

    IMPORTANT:
    - We keep all routes/JSON fields identical to your original version.
    - We explicitly bind template/static folders so moving files will not break the UI.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    # Disable Werkzeug access logs (keep your original behavior)
    import logging as _logging
    _logging.getLogger("werkzeug").disabled = True

    @app.get("/ping")
    def ping():
        return "OK"

    @app.post("/upload")
    def upload():
        cfg = cfg_store.get_copy()
        if not bool(cfg.get("ingest_enabled", False)):
            stats.mark_rejected()
            return "ingest disabled", 503

        f = request.files.get("image")
        if f is None:
            stats.mark_missing()
            logger.warning("400 missing image field")
            return "missing image", 400

        data = f.read()
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            stats.mark_decode_failed()
            logger.warning(f"400 decode failed bytes={len(data)}")
            return "decode failed", 400

        frame_buf.set(img)
        stats.mark_ok()
        return "OK"

    def mjpeg_generator():
        while True:
            cfg = cfg_store.get_copy()
            stream_fps = int(cfg.get("stream_fps", 10))
            jpeg_quality = int(cfg.get("jpeg_quality", 80))
            ingest_enabled = bool(cfg.get("ingest_enabled", False))

            interval = 1.0 / max(1, stream_fps)
            time.sleep(interval)

            frame = frame_buf.get_copy()
            if frame is None:
                h, w = 360, 640
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                msg = "Ingest OFF - enable in dashboard" if not ingest_enabled else "Waiting for frames..."
                cv2.putText(frame, msg, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
            if not ok:
                continue
            jpg = buf.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" +
                jpg + b"\r\n"
            )

    @app.get("/stream")
    def stream():
        return Response(mjpeg_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/api/config")
    def api_get_config():
        cfg = cfg_store.get_copy()
        # Do not send the real key back to the frontend
        if cfg.get("ark_api_key"):
            cfg["ark_api_key"] = "******"
        else:
            cfg["ark_api_key"] = ""
        return jsonify(cfg)

    @app.put("/api/config")
    def api_put_config():
        patch = request.get_json(silent=True) or {}

        # If frontend returns placeholder/empty value, treat it as "do not modify ark_api_key"
        if "ark_api_key" in patch:
            v = patch.get("ark_api_key")
            if v is None or str(v).strip() in ("", "******"):
                patch.pop("ark_api_key", None)

        ok, cleaned, err = validate_and_normalize(patch)
        if not ok:
            return jsonify({"ok": False, "error": err}), 400

        new_cfg = cfg_store.set_many(cleaned)
        autosave = bool(new_cfg.get("autosave", True))
        if autosave:
            cfg_store.save_to_disk(logger)

        # If recording is ON and key recording params changed, remind user to restart recording.
        changed_record_params = any(
            k in cleaned for k in ("record_fps", "segment_seconds", "out_root", "cam_name", "codec")
        )
        note = ""
        if bool(new_cfg.get("recording")) and changed_record_params:
            note = "Recording is ON. Some record params will fully apply after Stop+Start recording."

        logger.info(f"config updated: {cleaned}")
        return jsonify({"ok": True, "note": note})

    @app.post("/api/config/save")
    def api_save_config():
        cfg_store.save_to_disk(logger)
        return jsonify({"ok": True})

    @app.post("/api/config/load")
    def api_load_config():
        cfg_store.load_from_disk(logger)
        return jsonify({"ok": True})

    @app.post("/api/ingest/enable")
    def api_ingest_enable():
        cfg_store.set_key("ingest_enabled", True)
        cfg = cfg_store.get_copy()
        if bool(cfg.get("autosave", True)):
            cfg_store.save_to_disk(logger)
        logger.info("ingest enabled")
        return jsonify({"ok": True, "ingest_enabled": True})

    @app.post("/api/ingest/disable")
    def api_ingest_disable():
        cfg_store.set_key("ingest_enabled", False)

        # Key behavior: clear the last frame so /stream goes back to placeholder screen.
        frame_buf.clear()

        cfg = cfg_store.get_copy()
        if bool(cfg.get("autosave", True)):
            cfg_store.save_to_disk(logger)
        logger.info("ingest disabled")
        return jsonify({"ok": True, "ingest_enabled": False})

    @app.post("/api/record/start")
    def api_record_start():
        cfg_store.set_key("recording", True)
        cfg = cfg_store.get_copy()
        if bool(cfg.get("autosave", True)):
            cfg_store.save_to_disk(logger)

        with rec_rt.lock:
            rec_rt.recording_start_ts = time.time()

        logger.info("recording started")
        return jsonify({"ok": True, "recording": True, "note": ""})

    @app.post("/api/record/stop")
    def api_record_stop():
        cfg_store.set_key("recording", False)
        cfg = cfg_store.get_copy()
        if bool(cfg.get("autosave", True)):
            cfg_store.save_to_disk(logger)

        stop_recorder(rec_rt, logger)
        with rec_rt.lock:
            rec_rt.recording_start_ts = None

        logger.info("recording stopped")
        return jsonify({"ok": True, "recording": False})

    def _snapshot_path(base_root: str = "recordings"):
        now = datetime.now()
        snap_root = os.path.join(base_root, "snapshots")
        day_dir = os.path.join(snap_root, now.strftime("%Y%m%d"))
        os.makedirs(day_dir, exist_ok=True)
        fname = f"snapshot_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        return os.path.join(day_dir, fname)

    @app.post("/api/system/shutdown")
    def api_system_shutdown():
        logger.warning("Shutdown requested from web UI")

        # Graceful shutdown order
        try:
            cfg_store.set_key("recording", False)
            stop_recorder(rec_rt, logger)
            with rec_rt.lock:
                rec_rt.recording_start_ts = None
        except Exception as e:
            logger.warning(f"shutdown: stop recorder failed: {e}")

        try:
            cfg_store.set_key("ingest_enabled", False)
        except Exception as e:
            logger.warning(f"shutdown: disable ingest failed: {e}")

        # Save config if autosave
        try:
            cfg = cfg_store.get_copy()
            if bool(cfg.get("autosave", True)):
                cfg_store.save_to_disk(logger)
        except Exception as e:
            logger.warning(f"shutdown: save config failed: {e}")

        # Signal workers to exit
        try:
            stop_event.set()
        except Exception as e:
            logger.warning(f"shutdown: set stop_event failed: {e}")

        # Best-effort join so writers flush more cleanly
        try:
            for _, t in (threads or {}).items():
                if t and t.is_alive():
                    t.join(timeout=2.0)
        except Exception as e:
            logger.warning(f"shutdown: join threads failed: {e}")

        # Hard-exit fallback (avoid hanging)
        def _killer():
            time.sleep(0.2)
            os._exit(0)

        threading.Thread(target=_killer, daemon=True).start()
        return jsonify({"ok": True, "message": "shutting down"})

    @app.post("/api/snapshot")
    def api_snapshot():
        frame = frame_buf.get_copy()
        if frame is None:
            return jsonify({"ok": False, "error": "no frame"}), 409

        cfg = cfg_store.get_copy()
        base_root = str(cfg.get("out_root", "recordings"))
        path = _snapshot_path(base_root)

        ok = cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            return jsonify({"ok": False, "error": "write failed"}), 500

        logger.info(f"snapshot saved: {path}")
        return jsonify({"ok": True, "path": path})

    @app.get("/api/status")
    def api_status():
        cfg = cfg_store.get_copy()

        age = frame_buf.age_sec()
        counts = stats.snapshot_counts()
        upload_fps = round(stats.upload_fps(), 2)

        # recorder info
        with rec_rt.lock:
            opened = (rec_rt.rec is not None)
            recording_start_ts = rec_rt.recording_start_ts
            r = rec_rt.rec

        rec_file = None
        seg_remaining = None
        total_elapsed = None

        if r is not None and getattr(r, "current_path", None) and getattr(r, "segment_start_ts", None):
            rec_file = r.current_path
            seg_elapsed = time.time() - r.segment_start_ts
            seg_remaining = max(0.0, float(cfg.get("segment_seconds", 60)) - seg_elapsed)

        if bool(cfg.get("recording")) and recording_start_ts is not None:
            total_elapsed = time.time() - recording_start_ts

        return jsonify({
            "ingest_enabled": bool(cfg.get("ingest_enabled")),
            "recording": bool(cfg.get("recording")),
            "stream_fps": int(cfg.get("stream_fps")),
            "jpeg_quality": int(cfg.get("jpeg_quality")),
            "record_fps": int(cfg.get("record_fps")),
            "segment_seconds": int(cfg.get("segment_seconds")),
            "out_root": cfg.get("out_root"),
            "cam_name": cfg.get("cam_name"),
            "codec": cfg.get("codec"),
            "last_frame_age_sec": age,
            "upload_fps": upload_fps,

            "recorder_opened": opened,
            "recording_file": rec_file,
            "recording_elapsed_sec": None if total_elapsed is None else round(total_elapsed, 1),
            "segment_remaining_sec": None if seg_remaining is None else round(seg_remaining, 1),

            "upload_counts": counts
        })

    @app.get("/api/ai/status")
    def api_ai_status():
        # Return AI thread runtime state (SLEEP/OBSERVE, event id, dwell seconds, last model output, etc.)
        try:
            snap = ai_rt.snapshot()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "data": snap})

    @app.get("/api/ai/events")
    def api_ai_events():
        # ?n=50 returns latest N events (JSONL tail cache)
        n = request.args.get("n", "50")
        try:
            events = event_store.latest(int(n))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        return jsonify({"ok": True, "data": events})

    @app.get("/api/log/tail")
    def api_log_tail():
        n = request.args.get("n", "200")
        try:
            n = max(50, min(int(n), 2000))
        except Exception:
            n = 200

        log_path = server_log_path
        if not os.path.exists(log_path):
            return jsonify({"ok": True, "data": []})

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-n:]
            return jsonify({"ok": True, "data": [ln.rstrip("\n") for ln in lines]})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return app