from __future__ import annotations

from functools import wraps

import oxyde
from flask import current_app, g, make_response, redirect, request

from . import security
from .db import run_async
from .models import User

ACCESS_COOKIE = "access"
REFRESH_COOKIE = "refresh"


def _cookie_attrs(config, max_age: int) -> dict:
    return {
        "httponly": True,
        "secure": config.cookie_secure,
        "samesite": "Lax",
        "path": "/",
        "max_age": max_age,
    }


def set_auth_cookies(response, user) -> None:
    config = current_app.config["FREENIT_CONFIG"]
    access = security.encode(user, config.secret_key, config.auth.expire)
    refresh = security.encode(user, config.secret_key, config.auth.refresh_expire)
    response.set_cookie(ACCESS_COOKIE, access, **_cookie_attrs(config, config.auth.expire))
    response.set_cookie(
        REFRESH_COOKIE, refresh, **_cookie_attrs(config, config.auth.refresh_expire)
    )


def clear_auth_cookies(response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", samesite="Lax")


async def _decode_user(token: str) -> User | None:
    config = current_app.config["FREENIT_CONFIG"]
    data = security.decode(token, config.secret_key)
    if data is None:
        return None
    pk = data.get("pk")
    if pk is None:
        return None
    try:
        return await User.objects.prefetch("roles").filter(id=pk, active=True).get()
    except oxyde.NotFoundError:
        return None


async def _current_user() -> User | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    return await _decode_user(token)


def current_user() -> User | None:
    if "user" not in g:
        g.user = run_async(_current_user())
    return g.user


async def authorize(cookie: str = ACCESS_COOKIE, roles: list[str] | None = None, allof: list[str] | None = None) -> User:
    roles = roles or []
    allof = allof or []
    token = request.cookies.get(cookie)
    if not token:
        raise PermissionError("Unauthorized")
    user = await _decode_user(token)
    if user is None:
        raise PermissionError("Unauthorized")
    if user.admin:
        return user
    if not user.roles:
        if roles or allof:
            raise PermissionError("Permission denied")
    else:
        user_roles = {role.name for role in user.roles}
        if roles and not any(role in user_roles for role in roles):
            raise PermissionError("Permission denied")
        if allof and not all(role in user_roles for role in allof):
            raise PermissionError("Permission denied")
    return user


def permissions(roles: list[str] | None = None, allof: list[str] | None = None):
    async def handler() -> User:
        return await authorize(roles=roles, allof=allof)

    return handler


profile_perms = permissions()
user_perms = permissions()
role_perms = permissions()


def htmx_redirect(path: str):
    response = make_response("", 204)
    response.headers["HX-Redirect"] = path
    return response


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            if request.headers.get("HX-Request"):
                return htmx_redirect("/login")
            return redirect("/login", code=303)
        return view(*args, **kwargs)

    return wrapper


def roles_required(*role_names: str):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                if request.headers.get("HX-Request"):
                    return htmx_redirect("/login")
                return redirect("/login", code=303)
            if user.admin or all(user.has_role(name) for name in role_names):
                return view(*args, **kwargs)
            if request.headers.get("HX-Request"):
                response = make_response("", 204)
                response.headers["HX-Push-Url"] = "/"
                response.headers["HX-Reswap"] = "none"
                response.headers["HX-Trigger"] = "forbidden"
                return response
            return redirect("/", code=303)

        return wrapper

    return decorator
