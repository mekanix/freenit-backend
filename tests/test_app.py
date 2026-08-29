from __future__ import annotations

from http.cookies import SimpleCookie

from freenit import security
from freenit.db import run_async
from freenit.models import Role, User, UserRole

TEST_SECRET = "test-secret-with-at-least-32-bytes"
TEST_EXPIRE = 3600


def create_user(email: str, password: str = "Sekrit", *, admin: bool = False):
    return run_async(
        User.objects.create(
            email=email,
            password=security.encrypt(password, TEST_SECRET),
            active=True,
            admin=admin,
        )
    )


def create_role(name: str):
    return run_async(Role.objects.create(name=name))


def assign_role(user, role):
    run_async(UserRole.objects.create(user_id=user.id, role_id=role.id))


def login_cookie(user_id: int, secret: str = TEST_SECRET) -> str:
    user = run_async(User.objects.get(id=user_id))
    access_token = security.encode(user, secret, TEST_EXPIRE)
    return f"access={access_token}"


def set_login_cookie(client, user_id: int, secret: str = TEST_SECRET) -> None:
    user = run_async(User.objects.get(id=user_id))
    access_token = security.encode(user, secret, TEST_EXPIRE)
    client.set_cookie("access", access_token)


def test_full_page_contains_htmx_shell(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'hx-boost="true"' in response.data
    assert b'id="main"' in response.data
    assert b'id="toast"' in response.data


def test_htmx_page_request_returns_fragment(client):
    response = client.get("/about", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert b"<!doctype html>" not in response.data.lower()
    assert b"<h2>About</h2>" in response.data


def test_login_sets_http_only_insecure_cookie_in_testing(client):
    create_user("login@example.com")
    response = client.post(
        "/login",
        data={"email": "login@example.com", "password": "Sekrit"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == "/"
    cookies = response.headers.getlist("Set-Cookie")
    assert any(cookie.startswith("access=") for cookie in cookies)
    assert all("HttpOnly" in cookie for cookie in cookies)
    assert all("Secure" not in cookie for cookie in cookies)


def test_production_auth_cookie_is_secure(app):
    from dataclasses import replace

    from freenit.config import AuthConfig

    app.config["FREENIT_CONFIG"] = replace(
        app.config["FREENIT_CONFIG"],
        environment="production",
        auth=AuthConfig(secure=True),
    )
    with app.test_request_context("/"):
        from freenit.auth import set_auth_cookies

        user = User(id=1, email="test@example.com", password="x")
        response = app.make_response("")
        set_auth_cookies(response, user)

    cookie = SimpleCookie()
    cookie.load(response.headers.getlist("Set-Cookie")[0])
    morsel = cookie["access"]
    assert morsel["httponly"]
    assert morsel["secure"]


def test_login_failure_returns_oob_toast_and_keeps_email(client):
    create_user("login-fail@example.com")
    response = client.post(
        "/login",
        data={"email": "login-fail@example.com", "password": "wrong"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert b'hx-swap-oob="true"' in response.data
    assert b"Invalid email or password" in response.data
    assert b'value="login-fail@example.com"' in response.data


def test_protected_requires_login(client):
    response = client.get("/protected")

    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_protected_accepts_jwt_cookie(client):
    user = create_user("protected@example.com")
    set_login_cookie(client, user.id)
    response = client.get("/protected")

    assert response.status_code == 200
    assert b"protected@example.com" in response.data


def test_admin_requires_admin_role(client):
    user = create_user("user@example.com")
    set_login_cookie(client, user.id)
    response = client.get("/admin")

    assert response.status_code == 303
    assert response.headers["Location"] == "/"


def test_admin_role_allows_access(client):
    user = create_user("admin-role@example.com")
    role = create_role("admin")
    assign_role(user, role)

    set_login_cookie(client, user.id)
    response = client.get("/admin")

    assert response.status_code == 200
    assert b"admin-role@example.com" in response.data


def test_admin_flag_allows_access(client):
    user = create_user("admin-flag@example.com", admin=True)
    set_login_cookie(client, user.id)
    response = client.get("/admin")

    assert response.status_code == 200
    assert b"admin-flag@example.com" in response.data
