from __future__ import annotations

import base64
import ipaddress
import logging
import urllib.parse

import httpx
from flask import Blueprint, Response, abort, request

from freenit import auth

bp = Blueprint("dav", __name__)
log = logging.getLogger("dav")

DAV_METHODS = [
    "GET",
    "HEAD",
    "OPTIONS",
    "PUT",
    "DELETE",
    "PROPFIND",
    "PROPPATCH",
    "MKCOL",
    "MKCALENDAR",
    "REPORT",
    "COPY",
    "MOVE",
]

FILE_DAV_METHODS = [
    "GET",
    "HEAD",
    "OPTIONS",
    "PUT",
    "DELETE",
    "PROPFIND",
    "PROPPATCH",
    "MKCOL",
    "COPY",
    "MOVE",
]

FORWARD_REQUEST_HEADERS = [
    "Content-Type",
    "Depth",
    "Prefer",
    "If-Match",
    "If-None-Match",
    "Overwrite",
]

FORWARD_RESPONSE_HEADERS = [
    "Content-Type",
    "ETag",
    "DAV",
    "Allow",
    "Location",
    "Content-Disposition",
]

ICAL_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _dav_auth(config, user_email: str) -> str:
    credentials = f"{user_email}%{config.stalwart_admin}:{config.stalwart_admin_pass}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def _dav_account(email: str) -> str:
    return urllib.parse.quote(email, safe="")


def _check_ssrf(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        abort(400)
    host = parsed.hostname
    if not host:
        abort(400)
    blocked = {"localhost", "localhost.localdomain"}
    if host in blocked or host.endswith(".local"):
        abort(400)
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            abort(400)
    except ValueError:
        pass


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
            from freenit.db import run_async

            config = current_app.config["FREENIT_CONFIG"]
            user = run_async(User.login(email, password, config.secret_key))
            return user
    return None


def _proxy(user, upstream_url: str) -> Response:
    from flask import current_app

    config = current_app.config["FREENIT_CONFIG"]
    if not config.stalwart_url:
        abort(503)

    headers = {"Authorization": _dav_auth(config, user.email)}
    for name in FORWARD_REQUEST_HEADERS:
        val = request.headers.get(name)
        if val:
            headers[name] = val

    destination = request.headers.get("Destination")
    if destination:
        headers["Destination"] = destination

    url = f"{config.stalwart_url}{upstream_url}"

    if request.method == "PUT":
        content_length = request.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length
        resp = httpx.request(
            method="PUT",
            url=url,
            content=request.get_data(),
            headers=headers,
        )
    else:
        has_body = request.method in {
            "POST",
            "PROPFIND",
            "PROPPATCH",
            "REPORT",
            "MKCALENDAR",
            "MKCOL",
        }
        body = request.get_data() if has_body else None
        resp = httpx.request(
            method=request.method,
            url=url,
            content=body,
            headers=headers,
        )

    if resp.status_code >= 400:
        log.warning(
            "DAV proxy error: user=%s method=%s url=%s status=%s",
            user.email, request.method, url, resp.status_code,
        )

    response_headers = {}
    for name in FORWARD_RESPONSE_HEADERS:
        val = resp.headers.get(name)
        if val:
            response_headers[name] = val

    return Response(
        response=resp.content,
        status=resp.status_code,
        headers=response_headers,
    )


# CalDAV


@bp.route("/cal", methods=DAV_METHODS)
@bp.route("/cal/<path:path>", methods=DAV_METHODS)
def cal_proxy(path: str = ""):
    user = _current_user()
    if user is None:
        abort(401)
    upstream = f"/dav/cal/{_dav_account(user.email)}/"
    if path:
        upstream += path
    return _proxy(user, upstream)


# CardDAV


@bp.route("/card", methods=DAV_METHODS)
@bp.route("/card/<path:path>", methods=DAV_METHODS)
def card_proxy(path: str = ""):
    user = _current_user()
    if user is None:
        abort(401)
    upstream = f"/dav/card/{_dav_account(user.email)}/"
    if path:
        upstream += path
    return _proxy(user, upstream)


# WebDAV file storage


@bp.route("/file", methods=FILE_DAV_METHODS)
@bp.route("/file/<path:path>", methods=FILE_DAV_METHODS)
def file_proxy(path: str = ""):
    user = _current_user()
    if user is None:
        abort(401)
    upstream = f"/dav/file/{_dav_account(user.email)}/"
    if path:
        upstream += path
    return _proxy(user, upstream)


@bp.post("/cal/fetch-ical")
def ical_fetch():
    user = _current_user()
    if user is None:
        abort(401)
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    _check_ssrf(url)
    log.debug("iCal fetch: user=%s url=%s", user.email, url)
    try:
        resp = httpx.get(
            url,
            headers={"Accept": "text/calendar"},
            timeout=15,
            follow_redirects=True,
        )
    except httpx.RequestError as e:
        log.warning("iCal fetch error: user=%s url=%s error=%s", user.email, url, e)
        abort(502)

    if resp.status_code >= 400:
        abort(resp.status_code)

    if len(resp.content) > ICAL_MAX_BYTES:
        abort(413)

    return Response(
        response=resp.content,
        status=200,
        content_type="text/calendar",
    )
