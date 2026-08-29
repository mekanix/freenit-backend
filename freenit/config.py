from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AuthConfig:
    secure: bool = True
    expire: int = 3600
    refresh_expire: int = 31536000


@dataclass(frozen=True)
class Config:
    environment: str
    dburl: str
    secret_key: str
    debug: bool = False
    testing: bool = False
    api_root: str = "/api/v1"
    hostname: str = "localhost"
    port: int = 5000
    auth: AuthConfig = field(default_factory=AuthConfig)
    modules: tuple[str, ...] = ("auth", "user", "role")
    stalwart_url: str = ""
    stalwart_admin: str = "%admin"
    stalwart_admin_pass: str = ""
    mail_server: str = "mail.example.com"
    mail_port: int = 587
    mail_user: str = ""
    mail_password: str = ""
    mail_tls: bool = True
    mail_from: str = "no-reply@example.com"
    xmpp_ws_url: str = ""

    @property
    def cookie_secure(self) -> bool:
        return self.auth.secure


def _database_url(environment: str) -> str:
    env_upper = environment.upper()
    for name in ("FREENIT_DBURL", "DATABASE_URL", f"FREENIT_{env_upper}_DBURL"):
        value = os.getenv(name)
        if value:
            return value

    if environment == "production":
        raise RuntimeError(
            "No database URL configured for production. Set FREENIT_DBURL, "
            "DATABASE_URL, or FREENIT_PRODUCTION_DBURL."
        )

    filename = ".test.sqlite" if environment == "testing" else ".dev.sqlite"
    return f"sqlite:///{Path(filename).resolve()}"


def _secret_key(environment: str) -> str:
    value = os.getenv("FREENIT_SECRET_KEY")
    if value:
        return value
    if environment == "production":
        raise RuntimeError("Set FREENIT_SECRET_KEY in production.")
    return "dev-secret-change-me"


def load_config(environment: str | None = None) -> Config:
    environment = (environment or os.getenv("FREENIT_ENV", "development")).lower()
    aliases = {"dev": "development", "test": "testing", "prod": "production"}
    environment = aliases.get(environment, environment)
    if environment not in {"development", "testing", "production"}:
        raise RuntimeError(f"Unsupported FREENIT_ENV: {environment}")

    auth = AuthConfig(secure=environment == "production")
    return Config(
        environment=environment,
        dburl=_database_url(environment),
        secret_key=_secret_key(environment),
        debug=environment == "development",
        testing=environment == "testing",
        auth=auth,
    )
