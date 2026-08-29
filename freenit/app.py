from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from flask import Flask

from .config import Config, load_config
from .db import connect, disconnect, init_database, run_async
from .views import core, auth, users, blog, projects, lms, mailinglist, git, dav, mail, chat, domain


def create_app(config: Config | None = None) -> Flask:
    config = config or load_config()
    init_database(config)

    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.update(
        DEBUG=config.debug,
        TESTING=config.testing,
        SECRET_KEY=config.secret_key,
        FREENIT_CONFIG=config,
    )

    app.register_blueprint(core.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(blog.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(lms.bp)
    app.register_blueprint(mailinglist.bp)
    app.register_blueprint(git.bp)
    app.register_blueprint(dav.bp)
    app.register_blueprint(mail.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(domain.bp)

    if not config.testing:
        _run_migrations()
        run_async(connect())

    return app


def _run_migrations() -> None:
    oxyde = Path(sys.executable).with_name("oxyde")
    subprocess.run([str(oxyde), "migrate"], check=True)  # nosec: B603
