from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthConfig:
    secure: bool = True
    expire: int = 3600
    refresh_expire: int = 31536000


@dataclass(frozen=True)
class LDAPConfig:
    host: str = ""
    tls: bool = True
    service_dn: str = ""
    service_pw: str = ""
    user_base: str = "ou=people,dc=example,dc=com"
    user_dn_template: str = "uid={username},ou=people,dc=example,dc=com"
    search_filter: str = "(mail={email})"
    attr_email: str = "mail"
    attr_fullname: str = "cn"
    attr_user_class: str = "userClass"
    omemo_attr: str = "omemoBundle"
    active_classes: frozenset[str] = frozenset({"active"})
    admin_classes: frozenset[str] = frozenset({"admin"})
    allow_local_fallback: bool = True


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
    ldap: LDAPConfig | None = None
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


def load_config(environment: str | None = None) -> Config:
    environment = (environment or os.getenv("FREENIT_ENV", "development")).lower()
    aliases = {"dev": "development", "test": "testing", "prod": "production"}
    environment = aliases.get(environment, environment)
    if environment not in {"development", "testing", "production"}:
        raise RuntimeError(f"Unsupported FREENIT_ENV: {environment}")

    try:
        from . import local_config

        configs = local_config.configs
    except (ImportError, AttributeError):
        from . import base_config

        configs = base_config.configs

    if environment not in configs:
        raise RuntimeError(f"No config defined for environment: {environment}")

    return configs[environment]
