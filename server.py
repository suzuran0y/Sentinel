# pc/server.py
import os
import socket
import threading

from app.core.logger import setup_logger
from app.core.frame_buffer import FrameBuffer
from app.core.upload_stats import UploadStats
from app.core.runtime import RecorderRuntime
from app.config.config_store import ConfigStore, DEFAULT_CONFIG
from app.recorder.recorder_worker import start_record_thread
from app.ai.ai_store import AiRuntime, EventStore
from app.ai.ai_monitor_worker import start_ai_monitor_thread
from app.web.webapp import create_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
APP_CONFIG_DIR = os.path.join(BASE_DIR, "app", "config")
SERVER_LOG_PATH = os.path.join(LOG_DIR, "server.log")
AI_EVENTS_PATH = os.path.join(LOG_DIR, "ai_events.jsonl")
CONFIG_PATH = os.path.join(APP_CONFIG_DIR, "config.json")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(APP_CONFIG_DIR, exist_ok=True)

def get_local_ip() -> str:
    """Best-effort LAN IP detection without sending traffic."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    logger = setup_logger(SERVER_LOG_PATH)
    stop_event = threading.Event()

    cfg_store = ConfigStore(path=CONFIG_PATH, initial=DEFAULT_CONFIG.copy())
    frame_buf = FrameBuffer()
    stats = UploadStats()
    rec_rt = RecorderRuntime()

    # Load config before starting the UI session.
    cfg_store.load_from_disk(logger)

    # Force-reset on startup: open the web UI first, then enable ingest/recording manually from dashboard.
    cfg_store.set_key("ingest_enabled", False)
    cfg_store.set_key("recording", False)
    cfg_store.save_to_disk(logger)

    # Background recorder thread (original code starts it again; recorder_worker has an internal guard).
    record_thread = start_record_thread(cfg_store, frame_buf, rec_rt, logger, stop_event)

    # AI runtime + event store
    ai_rt = AiRuntime()
    event_store = EventStore(path=AI_EVENTS_PATH)

    # Background AI monitor thread (triggered mode)
    ai_thread = start_ai_monitor_thread(cfg_store, frame_buf, ai_rt, event_store, logger, stop_event)

    threads = {"record": record_thread, "ai": ai_thread}

    app = create_app(
        cfg_store=cfg_store,
        frame_buf=frame_buf,
        stats=stats,
        rec_rt=rec_rt,
        ai_rt=ai_rt,
        event_store=event_store,
        logger=logger,
        stop_event=stop_event,
        threads=threads,
        server_log_path=SERVER_LOG_PATH,
    )

    host = "0.0.0.0"
    port = 8000
    local_ip = get_local_ip()

    url_lan = f"http://{local_ip}:{port}/"
    url_local = f"http://127.0.0.1:{port}/"

    print("\n====================================================================")
    print(" PhoneCam Server Started")
    print(f" Local:      {url_local}            for dashboard web")
    print(f" LAN:        {url_lan}       for CamFlow link")
    print(" Default ingest: OFF (enable in dashboard)")
    print("====================================================================\n", flush=True)

    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()