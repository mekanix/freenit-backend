from __future__ import annotations

import socket
from pathlib import Path

from .config import AuthConfig, Config, LDAPConfig


dev = Config(
    environment="development",
    dburl=f"sqlite:///{Path('.dev.sqlite').resolve()}",
    secret_key="dev-secret-change-me",
    debug=True,
    testing=False,
    auth=AuthConfig(secure=False),
)


test = Config(
    environment="testing",
    dburl="sqlite::memory:",
    secret_key="test-secret-change-me",
    debug=True,
    testing=True,
    auth=AuthConfig(secure=False),
)


prod = Config(
    environment="production",
    dburl="postgresql://user:pass@host/dbname",
    secret_key="change-me-in-local-config",
    debug=False,
    testing=False,
    auth=AuthConfig(secure=True),
    hostname=socket.gethostname(),
)


configs = {
    "development": dev,
    "testing": test,
    "production": prod,
}
