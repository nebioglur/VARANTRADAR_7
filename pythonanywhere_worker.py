"""Run VarantRadar background services as a PythonAnywhere Always-on task.

Keep this process separate from WSGI: PythonAnywhere web workers are request
workers and do not support persistent background threads.
"""
import os
import signal
import threading
import json
import time
from pathlib import Path


PROJECT_HOME = Path(__file__).resolve().parent
os.chdir(PROJECT_HOME)
os.environ.setdefault("ENVIRONMENT", "production")
os.environ["ENABLE_BACKGROUND_SERVICES"] = "true"
os.environ.setdefault("TELEGRAM_PRIMARY_HOST", "pythonanywhere")
os.environ.setdefault("IS_PRIMARY_TELEGRAM", "true")

_stop = threading.Event()
HEARTBEAT = PROJECT_HOME / "data" / "background_worker_heartbeat.json"


def _request_stop(signum, frame):
    _stop.set()


def main():
    import logging
    import server

    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Starting VarantRadar PythonAnywhere background worker")
    server.start_background_services()
    while not _stop.is_set():
        temporary = HEARTBEAT.with_suffix(".tmp")
        temporary.write_text(json.dumps({
            "timestamp": time.time(),
            "pid": os.getpid(),
        }), encoding="utf-8")
        os.replace(temporary, HEARTBEAT)
        _stop.wait(60)
    logging.info("Stopping VarantRadar PythonAnywhere background worker")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    main()
