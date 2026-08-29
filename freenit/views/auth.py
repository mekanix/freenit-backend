from flask import Blueprint, current_app, request

import oxyde

from freenit import auth, security
from freenit.db import run_async
from freenit.models import User
from freenit.views import render_fragment_response, render_page

bp = Blueprint("auth", __name__)


def _config():
    return current_app.config["FREENIT_CONFIG"]


@bp.get("/login")
def login():
    return render_page("login.html", "Log in", email="", user=auth.current_user())


@bp.post("/login")
def login_submit():
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    user = run_async(User.login(email, password, _config().secret_key))
    if user is None:
        return render_fragment_response(
            "login.html",
            email=email,
            user=None,
            toast="Invalid email or password",
        )

    response = render_fragment_response(
        "home.html",
        push_url="/",
        user=user,
        toast="Signed in",
    )
    auth.set_auth_cookies(response, user)
    return response


@bp.post("/logout")
def logout():
    response = render_fragment_response(
        "home.html",
        push_url="/",
        user=None,
        toast="Signed out",
    )
    auth.clear_auth_cookies(response)
    return response


@bp.get("/register")
def register():
    return render_page("register.html", "Register", email="", user=auth.current_user())


@bp.post("/register")
def register_submit():
    email = request.form.get("email", "")
    password = request.form.get("password", "")

    async def _create():
        try:
            await User.objects.get(email=email)
            return None
        except oxyde.NotFoundError:
            user = User(
                email=email,
                password=security.encrypt(password, _config().secret_key),
                active=False,
            )
            await user.save()
            return user

    user = run_async(_create())
    if user is None:
        return render_fragment_response(
            "register.html",
            email=email,
            user=None,
            toast="User already registered",
        )
    return render_fragment_response(
        "login.html",
        push_url="/login",
        email=email,
        user=None,
        toast="Check your email to verify your account",
    )


@bp.get("/verify/<token>")
def verify_token(token: str):
    claims = security.decode(token, _config().secret_key)
    verified = False
    if claims and claims.get("pk"):
        pk = claims["pk"]

        async def _activate():
            user = await User.objects.get(id=pk)
            user.active = True
            await user.save(update_fields={"active"})
            return user

        try:
            run_async(_activate())
            verified = True
        except Exception:
            verified = False
    return render_page("verify.html", "Verify", verified=verified, user=auth.current_user())
