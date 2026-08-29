from flask import Blueprint, current_app, request

from freenit import auth, security
from freenit.db import run_async
from freenit.models import Role, User
from freenit.views import render_fragment_response, render_page

bp = Blueprint("users", __name__)


def _config():
    return current_app.config["FREENIT_CONFIG"]


@bp.get("/profile")
@auth.login_required
def profile():
    return render_page("profile.html", "Profile", user=auth.current_user())


@bp.patch("/profile")
@auth.login_required
def profile_patch():
    user = auth.current_user()
    data = request.get_json(silent=True) or request.form.to_dict()
    if data.get("password"):
        data["password"] = security.encrypt(data["password"], _config().secret_key)

    async def _patch():
        from pydantic import BaseModel, ConfigDict, EmailStr

        class UserOptional(BaseModel):
            model_config = ConfigDict(extra="forbid")
            email: EmailStr | None = None
            password: str | None = None
            fullname: str | None = None

        fields = UserOptional(**data)
        await user.patch(fields)
        await user.load_all()
        return user

    run_async(_patch())
    return render_fragment_response(
        "profile.html",
        user=user,
        toast="Profile updated",
    )


@bp.get("/users")
@auth.login_required
def users_list():
    users = run_async(User.objects.prefetch("roles").all())
    return render_page("users.html", "Users", users=users, user=auth.current_user())


@bp.get("/users/<int:pk>")
@auth.login_required
def user_detail(pk: int):
    user = run_async(User.objects.prefetch("roles").filter(id=pk).get())
    return render_page("user_detail.html", user.email, user=user, current_user=auth.current_user())


@bp.get("/roles")
@auth.login_required
def roles_list():
    roles = run_async(Role.objects.all())
    return render_page("roles.html", "Roles", roles=roles, user=auth.current_user())


@bp.post("/roles")
@auth.login_required
def roles_create():
    name = request.form.get("name", "")
    role = run_async(Role.objects.create(name=name))
    roles = run_async(Role.objects.all())
    return render_fragment_response(
        "roles.html",
        roles=roles,
        user=auth.current_user(),
        toast=f"Role {role.name} created",
    )


@bp.get("/roles/<int:pk>")
@auth.login_required
def role_detail(pk: int):
    role = run_async(Role.objects.filter(id=pk).get())
    run_async(role.load_all())
    return render_page("role_detail.html", role.name, role=role, user=auth.current_user())
