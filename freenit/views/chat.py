from __future__ import annotations

from flask import Blueprint, current_app

from freenit import auth
from freenit.views import render_page

bp = Blueprint("chat", __name__)


@bp.get("/chat")
def chat_config():
    config = current_app.config["FREENIT_CONFIG"]
    return render_page(
        "chat.html",
        "Chat",
        ws_url=config.xmpp_ws_url,
        user=auth.current_user(),
    )
