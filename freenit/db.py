from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import oxyde

from .config import Config

T = TypeVar("T")


database: oxyde.AsyncDatabase | None = None


def init_database(
    config: Config,
    settings: oxyde.db.pool.PoolSettings | None = None,
) -> oxyde.AsyncDatabase:
    global database

    # SQLite in-memory databases cannot use WAL mode and do not need disk
    # synchronous settings. Auto-disable them so tests and local runs work.
    if config.dburl == "sqlite::memory:" and settings is None:
        settings = oxyde.db.pool.PoolSettings(
            sqlite_journal_mode=None,
            sqlite_synchronous=None,
        )

    # Avoid recreating a connection pool for the same URL. This is essential
    # for SQLite in-memory databases, where each new pool is an empty DB.
    if database is not None and database.url == config.dburl:
        return database

    database = oxyde.AsyncDatabase(config.dburl, settings=settings, overwrite=True)
    return database


async def connect() -> None:
    if database is not None and not database.connected:
        await database.connect()


async def disconnect() -> None:
    if database is not None and database.connected:
        await database.disconnect()


def run_async(awaitable: Awaitable[T]) -> T:
    return asyncio.run(awaitable)


def sync(coro_factory: Callable[[], Awaitable[T]]) -> T:
    return run_async(coro_factory())
