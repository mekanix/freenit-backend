from __future__ import annotations

from freenit import auth
from flask import make_response, render_template, request


def wants_fragment() -> bool:
    return request.headers.get("HX-Request") == "true"


def render_page(template: str, title: str, **context):
    content = render_template(template, **context)
    if wants_fragment():
        return content
    return render_template("base.html", title=title, content=content, user=auth.current_user())


def render_fragment_response(
    template: str,
    *,
    push_url: str | None = None,
    status: int = 200,
    toast: str | None = None,
    **context,
):
    html = render_template(template, **context)
    if toast:
        html += render_template("toast.html", message=toast)
    response = make_response(html, status)
    if push_url:
        response.headers["HX-Push-Url"] = push_url
    return response
