"""Gunicorn configuration for the Freenit Flask service.

This config is designed to work with the FreeBSD rc.d script at
/usr/local/etc/rc.d/gunicorn. Put it in the location referenced by
``gunicorn_config`` in ``/etc/rc.conf`` (the default is
``/usr/local/etc/gunicorn/gunicorn.conf.py``).

The rc.d script calls::

    /usr/local/bin/gunicorn -c <gunicorn_config>

so the WSGI application and Python path must be configured here.

Example ``/etc/rc.conf`` entries::

    gunicorn_enable="YES"
    gunicorn_config="/usr/local/etc/gunicorn/gunicorn.conf.py"
    gunicorn_user="freenit"
    gunicorn_group="freenit"

Environment variables for the application can be placed in
``/usr/local/etc/gunicorn/freenit.env`` (one ``KEY=value`` per line) or
exported before starting the service.
"""

import multiprocessing
import os
from pathlib import Path

# Application to run. The FreeBSD rc.d script only passes ``-c <config>``,
# so the WSGI callable must be defined here.
wsgi_app = "freenit.app:create_app()"

# Add the project directory to Python path so gunicorn can import ``freenit``.
# Adjust this if the project is checked out somewhere else.
PROJECT_DIR = Path("/home/meka/repos/freenit/services/f")
pythonpath = [str(PROJECT_DIR)]


def _load_env_file(path: Path) -> None:
    """Load KEY=value pairs from an env file into os.environ."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


# Load optional env file. This is the easiest way to pass secrets to the
# FreeBSD rc.d gunicorn script, which does not have built-in env support.
_load_env_file(Path("/usr/local/etc/gunicorn/freenit.env"))

# Server socket
bind = os.getenv("GUNICORN_BIND", "127.0.0.1:5000")

# Worker processes
# A safe default is (2 * CPU cores) + 1. Override with GUNICORN_WORKERS.
workers = int(os.getenv("GUNICORN_WORKERS", (multiprocessing.cpu_count() * 2) + 1))

# Threads per worker (sync workers ignore this, but it helps threaded/gthread workers)
threads = int(os.getenv("GUNICORN_THREADS", 1))

# Worker class. "sync" is the default and works fine with the current sync Flask
# views. If you switch to async endpoints, consider "gevent" or
# "uvicorn.workers.UvicornWorker".
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# Timeout for worker processes (seconds)
timeout = int(os.getenv("GUNICORN_TIMEOUT", 30))

# Graceful shutdown timeout (seconds)
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 30))

# Keep-alive timeout (seconds)
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 2))

# Maximum number of pending connections
backlog = int(os.getenv("GUNICORN_BACKLOG", 2048))

# Limit request line length to mitigate slowloris-style attacks
limit_request_line = int(os.getenv("GUNICORN_LIMIT_REQUEST_LINE", 4094))
limit_request_fields = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELDS", 100))
limit_request_field_size = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELD_SIZE", 8190))

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" logs to stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")    # "-" logs to stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = os.getenv(
    "GUNICORN_ACCESS_LOG_FORMAT",
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
)

# Process naming
proc_name = os.getenv("GUNICORN_PROC_NAME", "freenit")

# The FreeBSD rc.d script backgrounds gunicorn with daemon(8), so gunicorn
# itself must stay in the foreground.
daemon = False

# PID file management is handled by daemon(8) via the rc.d script. Leave this
# empty so gunicorn does not try to write its own pid file.
pidfile = None

# Preload the app so imports happen once before workers fork.
preload_app = os.getenv("GUNICORN_PRELOAD", "true").lower() in ("true", "1", "yes")


def on_starting(server):
    """Validate required production environment variables early."""
    env = os.getenv("FREENIT_ENV", "production").lower()
    if env == "production":
        if not os.getenv("FREENIT_SECRET_KEY"):
            raise RuntimeError("FREENIT_SECRET_KEY must be set in production.")
        if not (
            os.getenv("FREENIT_DBURL")
            or os.getenv("DATABASE_URL")
            or os.getenv("FREENIT_PRODUCTION_DBURL")
        ):
            raise RuntimeError(
                "A database URL must be set in production. "
                "Use FREENIT_DBURL, DATABASE_URL, or FREENIT_PRODUCTION_DBURL."
            )
