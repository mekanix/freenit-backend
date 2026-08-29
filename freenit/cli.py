from __future__ import annotations

from .app import create_app


def main() -> None:
    create_app().run()
