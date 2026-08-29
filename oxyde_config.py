from __future__ import annotations

import os
from pathlib import Path

from oxyde.migrations.utils import detect_dialect


def database_url() -> str:
    env = os.getenv("FREENIT_ENV", "production").lower()
    aliases = {"dev": "development", "test": "testing", "prod": "production"}
    env = aliases.get(env, env)
    env_upper = env.upper()
    for name in ("FREENIT_DBURL", "DATABASE_URL", f"FREENIT_{env_upper}_DBURL"):
        value = os.getenv(name)
        if value:
            return value
    if env == "production":
        raise RuntimeError(
            "No database URL configured. Set FREENIT_DBURL, DATABASE_URL, "
            "or FREENIT_PRODUCTION_DBURL."
        )
    filename = ".test.sqlite" if env == "testing" else ".dev.sqlite"
    return f"sqlite:///{Path(filename).resolve()}"


def database_dialect() -> str:
    explicit = os.getenv("FREENIT_DIALECT")
    if explicit:
        return explicit
    return detect_dialect(database_url())


MODELS = [
    "freenit.models.sql",
    "freenit.models.blog",
    "freenit.models.project",
    "freenit.models.lms",
    "freenit.models.mailinglist",
    "freenit.models.git",
]
DIALECT = database_dialect()
MIGRATIONS_DIR = "migrations"
DATABASES = {"default": database_url()}
