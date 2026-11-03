"""Gunicorn runtime: one worker owns the legacy in-process background loops."""
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
threads = 4
timeout = 120
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
preload_app = False


def post_worker_init(worker):
    import server
    server.start_background_services()
