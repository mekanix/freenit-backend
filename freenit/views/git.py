from __future__ import annotations

import base64
import logging
import subprocess  # nosec: B404
from datetime import datetime
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    request,
)

import oxyde

from freenit import auth
from freenit.db import run_async
from freenit.models.git import (
    GitPermission,
    GitPushLog,
    GitRepo,
    _check_access,
    _get_permission,
    _get_repo,
    _list_permissions,
    _list_push_logs,
)
from freenit.models.project import Project
from freenit.views import render_fragment_response, render_page

bp = Blueprint("git", __name__)
log = logging.getLogger("git")


def _packet_line(line: str) -> bytes:
    data = line.encode("utf-8")
    length = len(data) + 4
    return f"{length:04x}".encode("ascii") + data


def _service_command(service: str) -> str:
    if service == "git-upload-pack":
        return "upload-pack"
    if service == "git-receive-pack":
        return "receive-pack"
    abort(400)


def _required_access(service: str) -> str:
    if service == "git-upload-pack":
        return "read"
    if service == "git-receive-pack":
        return "write"
    abort(400)


async def _authenticate() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "basic" or not token:
        return None
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except Exception:
        return None
    email, _, password = decoded.partition(":")
    if not email or not password:
        return None
    from freenit.models import User

    user = await User.login(email, password, current_app.config["FREENIT_CONFIG"].secret_key)
    return user.email if user else None


def _basic_auth_challenge() -> Response:
    return Response(
        "Authentication required",
        status=401,
        headers={"WWW-Authenticate": 'Basic realm="git"'},
    )


# ---------- HTMX management routes ----------


@bp.get("/git/repos")
@auth.roles_required("admin")
def git_repos():
    user = auth.current_user()
    repos = run_async(GitRepo.objects.order_by("name").all())
    return render_page("git_repos.html", "Git repositories", repos=repos, user=user)


@bp.post("/git/repos")
@auth.roles_required("admin")
def git_repos_create():
    user = auth.current_user()
    name = request.form.get("name", "").strip()
    path = request.form.get("path", "").strip()
    project_id = request.form.get("project_id", "").strip()
    description = request.form.get("description") or None
    public = request.form.get("public") == "true"
    default_branch = request.form.get("default_branch", "main") or "main"
    tests_enabled = request.form.get("tests_enabled") == "true"
    test_command = request.form.get("test_command") or None

    if "/" in name or name.startswith(".") or not name or not path:
        repos = run_async(GitRepo.objects.order_by("name").all())
        return render_fragment_response(
            "git_repos.html",
            repos=repos,
            user=user,
            toast="Invalid repository name or path",
            status=400,
        )

    existing = run_async(
        GitRepo.objects.filter(name=name).all()
    ) or run_async(GitRepo.objects.filter(path=path).all())
    if existing:
        repos = run_async(GitRepo.objects.order_by("name").all())
        return render_fragment_response(
            "git_repos.html",
            repos=repos,
            user=user,
            toast="Repository name or path already in use",
            status=409,
        )

    now = datetime.utcnow()
    run_async(
        GitRepo.objects.create(
            name=name,
            path=path,
            project_id=int(project_id) if project_id else None,
            description=description,
            public=public,
            default_branch=default_branch,
            tests_enabled=tests_enabled,
            test_command=test_command,
            created_at=now,
            updated_at=now,
        )
    )
    repos = run_async(GitRepo.objects.order_by("name").all())
    return render_fragment_response(
        "git_repos.html",
        repos=repos,
        user=user,
        toast=f"Repository {name} created",
    )


@bp.get("/git/repos/public")
def git_repos_public():
    repos = run_async(GitRepo.objects.filter(public=True).order_by("name").all())
    return render_page(
        "git_repos_public.html", "Public Git repositories", repos=repos, user=auth.current_user()
    )


@bp.get("/git/repos/<int:repo_id>")
@auth.roles_required("admin")
def git_repo_detail(repo_id: int):
    user = auth.current_user()
    repo = run_async(_get_repo(repo_id))
    permissions = run_async(_list_permissions(repo_id))
    push_logs = run_async(_list_push_logs(repo_id))
    projects = run_async(Project.objects.all())
    return render_page(
        "git_repo_detail.html",
        repo.name,
        repo=repo,
        permissions=permissions,
        push_logs=push_logs,
        projects=projects,
        user=user,
    )


@bp.post("/git/repos/<int:repo_id>")
@auth.roles_required("admin")
def git_repo_update(repo_id: int):
    user = auth.current_user()
    repo = run_async(_get_repo(repo_id))
    repo.description = request.form.get("description") or None
    repo.public = request.form.get("public") == "true"
    repo.default_branch = request.form.get("default_branch", "main") or "main"
    repo.tests_enabled = request.form.get("tests_enabled") == "true"
    repo.test_command = request.form.get("test_command") or None
    repo.webhook_url = request.form.get("webhook_url") or None
    repo.updated_at = datetime.utcnow()
    run_async(repo.save())
    return redirect(f"/git/repos/{repo_id}", code=303)


@bp.post("/git/repos/<int:repo_id>/delete")
@auth.roles_required("admin")
def git_repo_delete(repo_id: int):
    user = auth.current_user()
    repo = run_async(_get_repo(repo_id))
    run_async(repo.delete())
    return redirect("/git/repos", code=303)


@bp.post("/git/repos/<int:repo_id>/permissions")
@auth.roles_required("admin")
def git_repo_permission_add(repo_id: int):
    user = auth.current_user()
    run_async(_get_repo(repo_id))
    email = request.form.get("email", "").strip()
    access = request.form.get("access", "read")
    if email:
        now = datetime.utcnow()
        try:
            run_async(
                GitPermission.objects.create(
                    repo_id=repo_id, user_email=email, access=access, created_at=now
                )
            )
        except Exception:
            pass
    return redirect(f"/git/repos/{repo_id}", code=303)


@bp.post("/git/repos/<int:repo_id>/permissions/<int:perm_id>/delete")
@auth.roles_required("admin")
def git_repo_permission_delete(repo_id: int, perm_id: int):
    user = auth.current_user()
    run_async(_get_repo(repo_id))
    try:
        perm = run_async(_get_permission(perm_id))
        if perm.repo_id == repo_id:
            run_async(perm.delete())
    except Exception:
        pass
    return redirect(f"/git/repos/{repo_id}", code=303)


@bp.get("/git/repos/<int:repo_id>/hooks")
@auth.roles_required("admin")
def git_repo_hooks(repo_id: int):
    user = auth.current_user()
    repo = run_async(_get_repo(repo_id))
    hooks = {
        "pre-receive": (
            "#!/bin/sh\n"
            f"python -m freenit.git.hooks '{repo.name}' pre-receive\n"
        ),
        "update": (
            "#!/bin/sh\n"
            "ref=$1\n"
            "oldrev=$2\n"
            "newrev=$3\n"
            f"python -m freenit.git.hooks '{repo.name}' update \"$ref\" \"$oldrev\" \"$newrev\"\n"
        ),
        "post-receive": (
            "#!/bin/sh\n"
            f"python -m freenit.git.hooks '{repo.name}' post-receive\n"
        ),
    }
    return render_page(
        "git_repo_hooks.html", f"{repo.name} hooks", repo=repo, hooks=hooks, user=user
    )


# ---------- Smart HTTP passthrough ----------


@bp.get("/git/<repo_name>/info/refs")
def git_info_refs(repo_name: str):
    service = request.args.get("service", "")
    if not service:
        abort(400)
    try:
        repo = run_async(_get_repo_by_name(repo_name))
    except ValueError:
        abort(404)
    user_email = run_async(_authenticate())
    if not run_async(_check_access(repo, user_email, _required_access(service))):
        return _basic_auth_challenge()

    command = _service_command(service)
    proc = subprocess.run(
        ["git", "-C", repo.path, command, "--advertise-refs", "."],
        capture_output=True,
        check=False,
    )  # nosec
    if proc.returncode != 0:
        log.error("git advertise-refs failed: %s", proc.stderr.decode("utf-8", errors="replace"))
        abort(502)

    body = _packet_line(f"# service={service}\n") + b"0000" + proc.stdout
    return Response(
        body,
        status=200,
        content_type=f"application/x-{service}-advertisement",
    )


@bp.post("/git/<repo_name>/git-upload-pack")
def git_upload_pack(repo_name: str):
    try:
        repo = run_async(_get_repo_by_name(repo_name))
    except ValueError:
        abort(404)
    user_email = run_async(_authenticate())
    if not run_async(_check_access(repo, user_email, "read")):
        return _basic_auth_challenge()

    proc = subprocess.run(
        ["git", "-C", repo.path, "upload-pack", "--stateless-rpc", "."],
        input=request.get_data(),
        capture_output=True,
        check=False,
    )  # nosec
    return Response(
        proc.stdout,
        status=200,
        content_type="application/x-git-upload-pack-result",
    )


@bp.post("/git/<repo_name>/git-receive-pack")
def git_receive_pack(repo_name: str):
    try:
        repo = run_async(_get_repo_by_name(repo_name))
    except ValueError:
        abort(404)
    user_email = run_async(_authenticate())
    if not run_async(_check_access(repo, user_email, "write")):
        return _basic_auth_challenge()

    proc = subprocess.run(
        ["git", "-C", repo.path, "receive-pack", "--stateless-rpc", "."],
        input=request.get_data(),
        capture_output=True,
        check=False,
    )  # nosec
    return Response(
        proc.stdout,
        status=200,
        content_type="application/x-git-receive-pack-result",
    )


async def _get_repo_by_name(name: str) -> GitRepo:
    try:
        return await GitRepo.objects.filter(name=name).get()
    except oxyde.NotFoundError:
        raise ValueError("No such repository")
