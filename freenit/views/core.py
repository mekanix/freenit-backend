from flask import Blueprint, jsonify

from freenit import auth
from freenit.views import render_page

bp = Blueprint("core", __name__)


MODULES = {
    "auth": {"dependencies": ["user", "role"]},
    "user": {"dependencies": ["role"]},
    "role": {"dependencies": ["user"]},
    "blog": {"dependencies": ["user"]},
    "project": {"dependencies": ["user"]},
    "lms": {"dependencies": ["user"]},
    "mailinglist": {"dependencies": ["user"]},
    "git": {"dependencies": ["user"]},
    "dav": {"dependencies": ["user"]},
    "mail": {"dependencies": ["user"]},
    "sieve": {"dependencies": ["user"]},
    "chat": {"dependencies": ["user"]},
    "domain": {"dependencies": ["user"]},
}


@bp.get("/")
def home():
    return render_page("home.html", "Home", user=auth.current_user())


@bp.get("/about")
def about():
    return render_page("about.html", "About", user=auth.current_user())


@bp.get("/protected")
@auth.login_required
def protected():
    return render_page("protected.html", "Protected", user=auth.current_user())


@bp.get("/admin")
@auth.roles_required("admin")
def admin():
    return render_page("admin.html", "Admin", user=auth.current_user())


@bp.get("/discovery")
def discovery():
    return jsonify({
        "modules": sorted(MODULES.keys()),
        "meta": {name: {"dependencies": info["dependencies"]} for name, info in MODULES.items()},
    })
