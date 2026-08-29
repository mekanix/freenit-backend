from __future__ import annotations

from freenit.db import run_async
from freenit.models.git import GitRepo
from freenit.models.mailinglist import MailingList
from freenit.models.project import Project
from tests.test_app import create_user, login_cookie, set_login_cookie


def test_discovery_returns_modules(client):
    response = client.get("/discovery")
    assert response.status_code == 200
    data = response.get_json()
    assert "modules" in data
    assert "blog" in data["modules"]


def test_mailinglists_public_empty(client):
    response = client.get("/mailinglists/public")
    assert response.status_code == 200
    assert b"No public mailing lists" in response.data


def test_mailinglists_admin_requires_login(client):
    response = client.get("/mailinglists")
    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_mailinglists_admin_requires_admin(client):
    user = create_user("ml-user@example.com")
    set_login_cookie(client, user.id)
    response = client.get("/mailinglists")
    assert response.status_code == 303


def test_mailinglists_admin_allows_admin(client):
    user = create_user("ml-admin@example.com", admin=True)
    set_login_cookie(client, user.id)
    response = client.get("/mailinglists")
    assert response.status_code == 200
    assert b"Mailing lists" in response.data


def test_mailinglist_subscribe_flow(client):
    ml = run_async(
        MailingList.objects.create(
            name="test-list",
            address="test-list@example.com",
            distribution_address="test-list-members@example.com",
            archive_address="test-list-archive@example.com",
            public=True,
            archive_enabled=True,
        )
    )
    response = client.get(f"/mailinglists/{ml.id}/subscribe")
    assert response.status_code == 200
    assert b"Subscribe" in response.data

    response = client.post(
        f"/mailinglists/{ml.id}/subscribe",
        data={"email": "subscriber@example.com"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200


def test_git_repos_public_empty(client):
    response = client.get("/git/repos/public")
    assert response.status_code == 200
    assert b"No public repositories" in response.data


def test_git_repos_admin_requires_admin(client):
    user = create_user("git-user@example.com")
    set_login_cookie(client, user.id)
    response = client.get("/git/repos")
    assert response.status_code == 303


def test_git_smart_http_missing_repo_returns_404(client):
    response = client.get("/git/nonexistent/info/refs?service=git-upload-pack")
    assert response.status_code == 404


def test_dav_requires_auth(client):
    response = client.get("/cal")
    assert response.status_code == 401


def test_mail_requires_login(client):
    response = client.get("/mail")
    assert response.status_code == 303
    assert response.headers["Location"] == "/login"


def test_chat_public(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert b"Chat" in response.data


def test_domains_requires_admin(client):
    user = create_user("domain-user@example.com")
    set_login_cookie(client, user.id)
    response = client.get("/domains")
    assert response.status_code == 303


def test_navigation_contains_new_modules(client):
    user = create_user("nav-admin@example.com", admin=True)
    set_login_cookie(client, user.id)
    response = client.get("/")
    assert response.status_code == 200
    data = response.data
    assert b"/mailinglists" in data
    assert b"/git/repos" in data
    assert b"/mail" in data
    assert b"/chat" in data
    assert b"/domains" in data
