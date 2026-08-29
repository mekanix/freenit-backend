from datetime import datetime

from flask import Blueprint, redirect, request

import oxyde

from freenit import auth
from freenit.db import run_async
from freenit.models import User
from freenit.models.project import Board, Column, Project, ProjectGroup, ProjectMember, Task
from freenit.views import render_fragment_response, render_page

bp = Blueprint("projects", __name__)


@bp.get("/projects")
@auth.login_required
def projects_list():
    projects = run_async(Project.objects.all())
    return render_page("projects.html", "Projects", projects=projects, user=auth.current_user())


@bp.post("/projects")
@auth.login_required
def projects_create():
    user = auth.current_user()
    now = datetime.utcnow()
    project = run_async(
        Project.objects.create(
            name=request.form.get("name", ""),
            description=request.form.get("description") or None,
            created_by_id=user.id,
            created_at=now,
            updated_at=now,
        )
    )
    projects = run_async(Project.objects.all())
    return render_fragment_response(
        "projects.html",
        projects=projects,
        user=user,
        toast=f"Project {project.name} created",
    )


@bp.get("/projects/<int:project_id>")
@auth.login_required
def project_detail(project_id: int):
    project = run_async(Project.objects.get(id=project_id))
    boards = run_async(Board.objects.filter(project_id=project_id).all())
    return render_page(
        "project_detail.html", project.name, project=project, boards=boards, user=auth.current_user()
    )


@bp.post("/projects/<int:project_id>/boards")
@auth.login_required
def project_board_create(project_id: int):
    now = datetime.utcnow()
    board = run_async(
        Board.objects.create(
            project_id=project_id,
            name=request.form.get("name", ""),
            description=request.form.get("description") or None,
            created_at=now,
            updated_at=now,
        )
    )
    project = run_async(Project.objects.get(id=project_id))
    boards = run_async(Board.objects.filter(project_id=project_id).all())
    return render_fragment_response(
        "project_detail.html",
        project=project,
        boards=boards,
        user=auth.current_user(),
        toast=f"Board {board.name} created",
    )


@bp.get("/projects/<int:project_id>/boards/<int:board_id>")
@auth.login_required
def board_detail(project_id: int, board_id: int):
    project = run_async(Project.objects.get(id=project_id))
    board = run_async(Board.objects.get(id=board_id))
    columns = run_async(Column.objects.filter(board_id=board_id).order_by("position").all())
    for column in columns:
        column.tasks = run_async(Task.objects.filter(column_id=column.id).order_by("position").all())
    return render_page(
        "board.html", board.name, project=project, board=board, columns=columns, user=auth.current_user()
    )


@bp.post("/projects/<int:project_id>/boards/<int:board_id>/columns")
@auth.login_required
def board_column_create(project_id: int, board_id: int):
    now = datetime.utcnow()
    run_async(
        Column.objects.create(
            board_id=board_id,
            name=request.form.get("name", ""),
            position=0,
            created_at=now,
            updated_at=now,
        )
    )
    return redirect(f"/projects/{project_id}/boards/{board_id}", code=303)


@bp.post("/projects/<int:project_id>/boards/<int:board_id>/columns/<int:column_id>/tasks")
@auth.login_required
def column_task_create(project_id: int, board_id: int, column_id: int):
    now = datetime.utcnow()
    run_async(
        Task.objects.create(
            column_id=column_id,
            title=request.form.get("title", ""),
            position=0,
            created_at=now,
            updated_at=now,
        )
    )
    return redirect(f"/projects/{project_id}/boards/{board_id}", code=303)


@bp.get("/projects/<int:project_id>/boards/<int:board_id>/tasks/<int:task_id>")
@auth.login_required
def task_detail(project_id: int, board_id: int, task_id: int):
    project = run_async(Project.objects.get(id=project_id))
    board = run_async(Board.objects.get(id=board_id))
    task = run_async(Task.objects.get(id=task_id))
    column = run_async(Column.objects.get(id=task.column_id))
    assignee = None
    if task.assignee_id:
        assignee = run_async(User.objects.get(id=task.assignee_id))
    children = run_async(Task.objects.filter(parent_id=task_id).all())
    return render_page(
        "task_detail.html",
        task.title,
        project=project,
        board=board,
        task=task,
        column=column,
        assignee=assignee,
        children=children,
        user=auth.current_user(),
    )


@bp.get("/projects/<int:project_id>/groups")
@auth.login_required
def project_groups_list(project_id: int):
    project = run_async(Project.objects.get(id=project_id))
    groups = run_async(ProjectGroup.objects.filter(project_id=project_id).all())
    return render_page(
        "project_groups.html", f"{project.name} groups", project=project, groups=groups, user=auth.current_user()
    )


@bp.post("/projects/<int:project_id>/groups")
@auth.login_required
def project_group_create(project_id: int):
    now = datetime.utcnow()
    run_async(
        ProjectGroup.objects.create(
            project_id=project_id,
            name=request.form.get("name", ""),
            description=request.form.get("description") or None,
            created_at=now,
            updated_at=now,
        )
    )
    return redirect(f"/projects/{project_id}/groups", code=303)


@bp.get("/projects/<int:project_id>/groups/<int:group_id>/members")
@auth.login_required
def project_group_members(project_id: int, group_id: int):
    project = run_async(Project.objects.get(id=project_id))
    group = run_async(ProjectGroup.objects.get(id=group_id))
    member_links = run_async(ProjectMember.objects.filter(group_id=group_id).all())
    members = []
    for link in member_links:
        user = run_async(User.objects.get(id=link.user_id))
        members.append(user)
    return render_page(
        "project_group_members.html",
        f"{group.name} members",
        project=project,
        group=group,
        members=members,
        user=auth.current_user(),
    )


@bp.post("/projects/<int:project_id>/groups/<int:group_id>/members")
@auth.login_required
def project_group_member_add(project_id: int, group_id: int):
    email = request.form.get("email", "")
    user = run_async(User.objects.get(email=email))
    now = datetime.utcnow()
    try:
        run_async(ProjectMember.objects.create(group_id=group_id, user_id=user.id, created_at=now))
    except oxyde.IntegrityError:
        pass
    return redirect(f"/projects/{project_id}/groups/{group_id}/members", code=303)
