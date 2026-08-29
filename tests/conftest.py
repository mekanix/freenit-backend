from __future__ import annotations

import os
from pathlib import Path

import pytest

from oxyde.db.pool import AsyncDatabase, PoolSettings

from freenit.config import AuthConfig, Config
from freenit.db import connect, disconnect, database, init_database, run_async


TEST_SECRET = "test-secret-with-at-least-32-bytes"
TEST_DBURL = "sqlite::memory:"


async def _apply_migrations() -> None:
    """Apply all pending migrations to the in-memory database."""
    from oxyde.migrations import (
        apply_migrations,
        get_applied_migrations,
        get_pending_migrations,
    )
    from oxyde.migrations.config import load_config as load_oxyde_config

    oxyde_config = load_oxyde_config()
    applied = await get_applied_migrations("default")
    pending = get_pending_migrations(oxyde_config.migrations_dir, applied)
    if pending:
        await apply_migrations(
            migrations_dir=oxyde_config.migrations_dir,
            db_alias="default",
            target=None,
            fake=False,
        )


@pytest.fixture
def app():
    os.environ["FREENIT_ENV"] = "testing"
    os.environ["FREENIT_DBURL"] = TEST_DBURL

    from freenit.app import create_app

    config = Config(
        environment="testing",
        dburl=TEST_DBURL,
        secret_key=TEST_SECRET,
        debug=True,
        testing=True,
        auth=AuthConfig(secure=False),
    )
    # In-memory SQLite cannot use WAL mode, so override the default settings.
    init_database(
        config,
        settings=PoolSettings(sqlite_journal_mode=None, sqlite_synchronous=None),
    )
    run_async(connect())
    run_async(_apply_migrations())
    flask_app = create_app(config)

    yield flask_app

    run_async(disconnect())
    os.environ.pop("FREENIT_ENV", None)
    os.environ.pop("FREENIT_DBURL", None)


@pytest.fixture
def client(app):
    return app.test_client()
