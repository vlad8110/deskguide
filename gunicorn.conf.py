"""Run retention maintenance in the worker that mounts DeskGuide's SQLite disk."""

from threading import Event, Thread

from app.feedback import run_inquiry_cleanup


def post_worker_init(worker):
    # Render uses one Gunicorn worker with several request threads.
    worker.inquiry_cleanup_stop = Event()
    Thread(
        target=run_inquiry_cleanup,
        args=(worker.wsgi, worker.inquiry_cleanup_stop, worker.log),
        name="inquiry-cleanup",
        daemon=True,
    ).start()


def worker_exit(server, worker):
    stop = getattr(worker, "inquiry_cleanup_stop", None)
    if stop is not None:
        stop.set()
