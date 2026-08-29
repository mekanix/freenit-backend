from __future__ import annotations

import base64
import logging
from urllib.parse import urlparse

import httpx
from flask import Blueprint, Response, abort, current_app, redirect, request

from freenit import auth
from freenit.db import run_async
from freenit.views import render_page

bp = Blueprint("mail", __name__)
log = logging.getLogger("mail")

SIEVE_PORT = 4190


def _current_user():
    user = auth.current_user()
    if user is not None:
        return user
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "basic" and token:
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except Exception:
            return None
        email, _, password = decoded.partition(":")
        if email and password:
            from freenit.models import User

            config = current_app.config["FREENIT_CONFIG"]
            return run_async(User.login(email, password, config.secret_key))
    return None


def _jmap_auth(config, user_email: str) -> str:
    credentials = f"{user_email}%{config.stalwart_admin}:{config.stalwart_admin_pass}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def _stalwart_url(config) -> str:
    return config.stalwart_url.rstrip("/")


def _require_stalwart(config) -> None:
    if not config.stalwart_url:
        abort(503)


# ---------- HTMX pages ----------


@bp.get("/mail")
def mail_index():
    user = _current_user()
    if user is None:
        return redirect("/login", code=303)
    return render_page("mail.html", "Mail", user=user)


@bp.get("/mail/compose")
def mail_compose_form():
    user = _current_user()
    if user is None:
        return redirect("/login", code=303)
    return render_page("mail_compose.html", "Compose", user=user)


@bp.post("/mail/compose")
def mail_compose():
    user = _current_user()
    if user is None:
        return redirect("/login", code=303)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)

    to = request.form.get("to", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if not to or not subject:
        return render_page(
            "mail_compose.html",
            "Compose",
            user=user,
            error="To and subject are required",
        )

    jmap_body = {
        "using": ["urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail"],
        "methodCalls": [
            [
                "Email/set",
                {
                    "accountId": user.email,
                    "create": {
                        "email": {
                            "mailboxIds": {"#send": True},
                            "from": [{"email": user.email}],
                            "to": [{"email": to}],
                            "subject": subject,
                            "textBody": [{"partId": "body", "type": "text/plain"}],
                            "bodyValues": {"body": {"value": body, "type": "text/plain"}},
                        }
                    }
                },
                "0",
            ],
            ["EmailSubmission/set", {"accountId": user.email, "onSuccessUpdateEmail": {}}, "1"],
        ],
    }

    resp = httpx.post(
        f"{_stalwart_url(config)}/jmap",
        json=jmap_body,
        headers={
            "Authorization": _jmap_auth(config, user.email),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    if resp.status_code >= 400:
        log.warning("Mail compose error: user=%s status=%s", user.email, resp.status_code)
        return render_page(
            "mail_compose.html",
            "Compose",
            user=user,
            error=f"Failed to send message: {resp.status_code}",
        )

    return render_page("mail.html", "Mail", user=user, toast="Message sent")


# ---------- JMAP proxy ----------


@bp.post("/mail/jmap")
def jmap_proxy():
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)
    resp = httpx.post(
        f"{_stalwart_url(config)}/jmap",
        content=request.get_data(),
        headers={
            "Authorization": _jmap_auth(config, user.email),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    return Response(
        response=resp.content,
        status=resp.status_code,
        content_type="application/json",
    )


@bp.get("/mail/jmap/session")
def jmap_session():
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)
    resp = httpx.get(
        f"{_stalwart_url(config)}/jmap/session",
        headers={
            "Authorization": _jmap_auth(config, user.email),
            "Accept": "application/json",
        },
    )
    return Response(
        response=resp.content,
        status=resp.status_code,
        content_type="application/json",
    )


@bp.post("/mail/jmap/upload/<account_id>")
def jmap_upload(account_id: str):
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)
    content_type = request.headers.get("Content-Type", "application/octet-stream")
    resp = httpx.post(
        f"{_stalwart_url(config)}/jmap/upload/{account_id}",
        content=request.get_data(),
        headers={
            "Authorization": _jmap_auth(config, user.email),
            "Content-Type": content_type,
        },
    )
    return Response(
        response=resp.content,
        status=resp.status_code,
        content_type="application/json",
    )


@bp.get("/mail/jmap/download/<account_id>/<blob_id>/<name>")
def jmap_download(account_id: str, blob_id: str, name: str):
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)
    resp = httpx.get(
        f"{_stalwart_url(config)}/jmap/download/{account_id}/{blob_id}/{name}",
        headers={"Authorization": _jmap_auth(config, user.email)},
    )
    headers = {}
    if "content-disposition" in resp.headers:
        headers["Content-Disposition"] = resp.headers["content-disposition"]
    return Response(
        response=resp.content,
        status=resp.status_code,
        content_type=resp.headers.get("content-type", "application/octet-stream"),
        headers=headers,
    )


# ---------- Sieve management ----------


def _sieve_token(config, user_email: str) -> str:
    raw = f"\x00{user_email}%{config.stalwart_admin}\x00{config.stalwart_admin_pass}"
    return base64.b64encode(raw.encode()).decode()


def _sieve_host(config) -> str:
    return urlparse(config.stalwart_url).hostname


@bp.get("/mail/sieve/scripts")
def sieve_scripts():
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)

    async def _list():
        from freenit.sieve import ManageSieveClient

        async with ManageSieveClient(
            host=_sieve_host(config), port=SIEVE_PORT, token=_sieve_token(config, user.email)
        ) as sieve:
            return await sieve.list_scripts()

    scripts = run_async(_list())
    return render_page("sieve_scripts.html", "Sieve scripts", scripts=scripts, user=user)


@bp.get("/mail/sieve/scripts/<name>")
def sieve_script(name: str):
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)

    async def _get():
        from freenit.sieve import ManageSieveClient

        async with ManageSieveClient(
            host=_sieve_host(config), port=SIEVE_PORT, token=_sieve_token(config, user.email)
        ) as sieve:
            content, active = await sieve.get_script(name)
            return content, active

    content, active = run_async(_get())
    return render_page(
        "sieve_script.html", name, script_name=name, content=content, active=active, user=user
    )


@bp.post("/mail/sieve/scripts/<name>")
def sieve_script_save(name: str):
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)
    content = request.form.get("content", "")

    async def _put():
        from freenit.sieve import ManageSieveClient

        async with ManageSieveClient(
            host=_sieve_host(config), port=SIEVE_PORT, token=_sieve_token(config, user.email)
        ) as sieve:
            await sieve.put_script(name, content)

    run_async(_put())
    return redirect(f"/mail/sieve/scripts/{name}", code=303)


@bp.post("/mail/sieve/scripts/<name>/delete")
def sieve_script_delete(name: str):
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)

    async def _delete():
        from freenit.sieve import ManageSieveClient

        async with ManageSieveClient(
            host=_sieve_host(config), port=SIEVE_PORT, token=_sieve_token(config, user.email)
        ) as sieve:
            await sieve.delete_script(name)

    run_async(_delete())
    return redirect("/mail/sieve/scripts", code=303)


@bp.post("/mail/sieve/scripts/<name>/active")
def sieve_script_activate(name: str):
    user = _current_user()
    if user is None:
        abort(401)
    config = current_app.config["FREENIT_CONFIG"]
    _require_stalwart(config)

    async def _activate():
        from freenit.sieve import ManageSieveClient

        async with ManageSieveClient(
            host=_sieve_host(config), port=SIEVE_PORT, token=_sieve_token(config, user.email)
        ) as sieve:
            await sieve.set_active(name)

    run_async(_activate())
    return redirect("/mail/sieve/scripts", code=303)
