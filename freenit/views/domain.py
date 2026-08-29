from __future__ import annotations

from flask import Blueprint, abort, current_app

from freenit import auth
from freenit.db import run_async
from freenit.views import render_page

bp = Blueprint("domain", __name__)


async def _list_stalwart_domains(config) -> list[str]:
    import base64
    import httpx

    credentials = f"{config.stalwart_admin}:{config.stalwart_admin_pass}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.stalwart_url}/api/principal",
            params={"types": "domain", "limit": 1000},
            headers={
                "Authorization": auth_header,
                "Accept": "application/json",
            },
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Stalwart error: {resp.status_code}")
    items = resp.json().get("data", {}).get("items", [])
    return sorted(item["name"] for item in items if item.get("name"))


@bp.get("/domains")
@auth.roles_required("admin")
def domains():
    user = auth.current_user()
    config = current_app.config["FREENIT_CONFIG"]
    if not config.stalwart_url:
        abort(503)
    try:
        domains = run_async(_list_stalwart_domains(config))
    except Exception as exc:
        return render_page(
            "domains.html",
            "Domains",
            domains=[],
            user=user,
            error=str(exc),
        )
    return render_page("domains.html", "Domains", domains=domains, user=user)
