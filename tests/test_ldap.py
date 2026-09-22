from __future__ import annotations

from unittest.mock import patch

import pytest
from bonsai.errors import AuthenticationError as LDAPAuthenticationError

from freenit.config import AuthConfig, Config, LDAPConfig
from freenit.db import init_database, run_async
from freenit.models import User


TEST_SECRET = "test-secret-with-at-least-32-bytes"


class _MockLDAPEntry:
    def __init__(self, dn: str, attrs: dict):
        self.dn = dn
        self._attrs = attrs

    def get(self, key: str, default=None):
        return self._attrs.get(key, default)


class _MockConnection:
    def __init__(self, entries: list, auth_fail: bool = False):
        self.entries = entries
        self.auth_fail = auth_fail

    async def __aenter__(self):
        if self.auth_fail:
            raise LDAPAuthenticationError("invalid credentials")
        return self

    async def __aexit__(self, *args):
        return False

    async def search(self, *args, **kwargs):
        return self.entries


class _MockLDAPClient:
    def __init__(self, entries: list, auth_fail: bool = False):
        self.entries = entries
        self.auth_fail = auth_fail

    def set_credentials(self, *args, **kwargs):
        pass

    def connect(self, is_async: bool = False):
        return _MockConnection(self.entries, self.auth_fail)


@pytest.fixture
def ldap_config():
    return LDAPConfig(
        host="ldap.example.com",
        tls=True,
        user_dn_template="uid={username},ou=people,dc=example,dc=com",
        attr_email="mail",
        attr_fullname="cn",
        attr_user_class="userClass",
        active_classes={"active"},
        admin_classes={"admin"},
        allow_local_fallback=True,
    )


@pytest.fixture
def ldap_app(ldap_config):
    import os

    os.environ["FREENIT_ENV"] = "testing"
    os.environ["FREENIT_DBURL"] = "sqlite::memory:"

    from freenit.app import create_app
    from freenit.db import connect, disconnect
    from oxyde.migrations import apply_migrations, get_applied_migrations, get_pending_migrations
    from oxyde.migrations.config import load_config as load_oxyde_config

    config = Config(
        environment="testing",
        dburl="sqlite::memory:",
        secret_key=TEST_SECRET,
        debug=True,
        testing=True,
        auth=AuthConfig(secure=False),
        ldap=ldap_config,
    )
    init_database(config)
    run_async(connect())

    oxyde_config = load_oxyde_config()
    applied = run_async(get_applied_migrations("default"))
    pending = get_pending_migrations(oxyde_config.migrations_dir, applied)
    if pending:
        run_async(
            apply_migrations(
                migrations_dir=oxyde_config.migrations_dir,
                db_alias="default",
                target=None,
                fake=False,
            )
        )

    app = create_app(config)
    yield app

    run_async(disconnect())
    os.environ.pop("FREENIT_ENV", None)
    os.environ.pop("FREENIT_DBURL", None)


@pytest.fixture
def ldap_client(ldap_app):
    return ldap_app.test_client()


def _make_entry(
    dn: str,
    email: str,
    fullname: str,
    user_classes: list[str],
    omemo_bundle: str | None = None,
):
    attrs = {
        "mail": [email],
        "cn": [fullname],
        "userClass": user_classes,
    }
    if omemo_bundle is not None:
        attrs["omemoBundle"] = [omemo_bundle]
    return _MockLDAPEntry(dn, attrs)


def test_ldap_login_creates_user(ldap_client, ldap_config):
    entry = _make_entry(
        "uid=jdoe,ou=people,dc=example,dc=com",
        "jdoe@example.com",
        "Jane Doe",
        ["active", "admin"],
    )
    mock_client = _MockLDAPClient([entry])

    with patch("freenit.ldap_auth.LDAPClient", return_value=mock_client):
        response = ldap_client.post(
            "/login",
            data={"email": "jdoe@example.com", "password": "ldap-pass"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == "/"

    user = run_async(User.objects.get(email="jdoe@example.com"))
    assert user.provider == "ldap"
    assert user.fullname == "Jane Doe"
    assert user.active is True
    assert user.admin is True


def test_ldap_login_existing_user_is_synced(ldap_client, ldap_config):
    from freenit import security

    run_async(
        User.objects.create(
            email="jdoe@example.com",
            password=security.encrypt("local-pass", TEST_SECRET),
            active=True,
            admin=False,
            provider="local",
        )
    )

    entry = _make_entry(
        "uid=jdoe,ou=people,dc=example,dc=com",
        "jdoe@example.com",
        "Jane Doe",
        ["active", "admin"],
    )
    mock_client = _MockLDAPClient([entry])

    with patch("freenit.ldap_auth.LDAPClient", return_value=mock_client):
        response = ldap_client.post(
            "/login",
            data={"email": "jdoe@example.com", "password": "ldap-pass"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    user = run_async(User.objects.get(email="jdoe@example.com"))
    assert user.provider == "ldap"
    assert user.admin is True


def test_ldap_login_syncs_omemo_bundle(ldap_client, ldap_config):
    entry = _make_entry(
        "uid=jdoe,ou=people,dc=example,dc=com",
        "jdoe@example.com",
        "Jane Doe",
        ["active"],
        omemo_bundle="base64-omemo-bundle-data",
    )
    mock_client = _MockLDAPClient([entry])

    with patch("freenit.ldap_auth.LDAPClient", return_value=mock_client):
        response = ldap_client.post(
            "/login",
            data={"email": "jdoe@example.com", "password": "ldap-pass"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    user = run_async(User.objects.get(email="jdoe@example.com"))
    assert user.omemo_bundle == "base64-omemo-bundle-data"


def test_ldap_login_syncs_omemo_bundle_from_description(ldap_client, ldap_app):
    from dataclasses import replace

    config = ldap_app.config["FREENIT_CONFIG"]
    ldap_app.config["FREENIT_CONFIG"] = replace(
        config, ldap=replace(config.ldap, omemo_attr="description")
    )

    entry = _MockLDAPEntry(
        "uid=jdoe,ou=people,dc=example,dc=com",
        {
            "mail": ["jdoe@example.com"],
            "cn": ["Jane Doe"],
            "userClass": ["active"],
            "description": ["some description", "__OMEMO__:desc-omemo-data"],
        },
    )
    mock_client = _MockLDAPClient([entry])

    with patch("freenit.ldap_auth.LDAPClient", return_value=mock_client):
        response = ldap_client.post(
            "/login",
            data={"email": "jdoe@example.com", "password": "ldap-pass"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    user = run_async(User.objects.get(email="jdoe@example.com"))
    assert user.omemo_bundle == "desc-omemo-data"


def test_ldap_failure_falls_back_to_local(ldap_client, ldap_config):
    from freenit import security

    run_async(
        User.objects.create(
            email="local@example.com",
            password=security.encrypt("local-pass", TEST_SECRET),
            active=True,
            admin=False,
            provider="local",
        )
    )

    mock_client = _MockLDAPClient([], auth_fail=True)

    with patch("freenit.ldap_auth.LDAPClient", return_value=mock_client):
        response = ldap_client.post(
            "/login",
            data={"email": "local@example.com", "password": "local-pass"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == "/"


def test_ldap_failure_no_fallback(ldap_client, ldap_app):
    from dataclasses import replace

    from freenit import security

    no_fallback_config = replace(
        ldap_app.config["FREENIT_CONFIG"].ldap,
        allow_local_fallback=False,
    )
    ldap_app.config["FREENIT_CONFIG"] = replace(
        ldap_app.config["FREENIT_CONFIG"], ldap=no_fallback_config
    )

    run_async(
        User.objects.create(
            email="local@example.com",
            password=security.encrypt("local-pass", TEST_SECRET),
            active=True,
            admin=False,
            provider="local",
        )
    )

    mock_client = _MockLDAPClient([], auth_fail=True)

    with patch("freenit.ldap_auth.LDAPClient", return_value=mock_client):
        response = ldap_client.post(
            "/login",
            data={"email": "local@example.com", "password": "local-pass"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data
