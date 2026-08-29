from datetime import datetime

from flask import Blueprint, redirect, request

import oxyde

from freenit import auth
from freenit.db import run_async
from freenit.models import User
from freenit.models.lms import (
    Course,
    CourseGroup,
    CourseMember,
    Lecture,
    LectureState,
)
from freenit.views import render_fragment_response, render_page

bp = Blueprint("lms", __name__)


@bp.get("/courses")
@auth.login_required
def courses_list():
    courses = run_async(Course.objects.all())
    return render_page("courses.html", "Courses", courses=courses, user=auth.current_user())


@bp.post("/courses")
@auth.login_required
def courses_create():
    user = auth.current_user()
    now = datetime.utcnow()
    course = run_async(
        Course.objects.create(
            name=request.form.get("name", ""),
            description=request.form.get("description") or None,
            created_by_id=user.id,
            created_at=now,
            updated_at=now,
        )
    )
    courses = run_async(Course.objects.all())
    return render_fragment_response(
        "courses.html",
        courses=courses,
        user=user,
        toast=f"Course {course.name} created",
    )


@bp.get("/courses/<int:course_id>")
@auth.login_required
def course_detail(course_id: int):
    course = run_async(Course.objects.get(id=course_id))
    lectures = run_async(
        Lecture.objects.filter(
            course_id=course_id,
            state__in=[LectureState.PUBLISHED_PUBLIC, LectureState.PUBLISHED_PRIVATE],
        ).order_by("position").all()
    )
    return render_page(
        "course_detail.html", course.name, course=course, lectures=lectures, user=auth.current_user()
    )


@bp.post("/courses/<int:course_id>/lectures")
@auth.login_required
def course_lecture_create(course_id: int):
    now = datetime.utcnow()
    lecture = run_async(
        Lecture.objects.create(
            course_id=course_id,
            title=request.form.get("title", ""),
            content=request.form.get("content") or None,
            position=0,
            state=LectureState.PUBLISHED_PUBLIC,
            created_at=now,
            updated_at=now,
        )
    )
    course = run_async(Course.objects.get(id=course_id))
    lectures = run_async(Lecture.objects.filter(course_id=course_id).order_by("position").all())
    return render_fragment_response(
        "course_detail.html",
        course=course,
        lectures=lectures,
        user=auth.current_user(),
        toast=f"Lecture {lecture.title} created",
    )


@bp.get("/courses/<int:course_id>/lectures/<int:lecture_id>")
@auth.login_required
def lecture_detail(course_id: int, lecture_id: int):
    course = run_async(Course.objects.get(id=course_id))
    lecture = run_async(Lecture.objects.get(id=lecture_id))
    return render_page(
        "lecture.html", lecture.title, course=course, lecture=lecture, user=auth.current_user()
    )


@bp.get("/courses/<int:course_id>/groups")
@auth.login_required
def course_groups_list(course_id: int):
    course = run_async(Course.objects.get(id=course_id))
    groups = run_async(CourseGroup.objects.filter(course_id=course_id).all())
    return render_page(
        "course_groups.html", f"{course.name} groups", course=course, groups=groups, user=auth.current_user()
    )


@bp.post("/courses/<int:course_id>/groups")
@auth.login_required
def course_group_create(course_id: int):
    now = datetime.utcnow()
    run_async(
        CourseGroup.objects.create(
            course_id=course_id,
            name=request.form.get("name", ""),
            description=request.form.get("description") or None,
            created_at=now,
            updated_at=now,
        )
    )
    return redirect(f"/courses/{course_id}/groups", code=303)


@bp.get("/courses/<int:course_id>/groups/<int:group_id>/members")
@auth.login_required
def course_group_members(course_id: int, group_id: int):
    course = run_async(Course.objects.get(id=course_id))
    group = run_async(CourseGroup.objects.get(id=group_id))
    member_links = run_async(CourseMember.objects.filter(group_id=group_id).all())
    members = []
    for link in member_links:
        user = run_async(User.objects.get(id=link.user_id))
        members.append(user)
    return render_page(
        "course_group_members.html",
        f"{group.name} members",
        course=course,
        group=group,
        members=members,
        user=auth.current_user(),
    )


@bp.post("/courses/<int:course_id>/groups/<int:group_id>/members")
@auth.login_required
def course_group_member_add(course_id: int, group_id: int):
    email = request.form.get("email", "")
    user = run_async(User.objects.get(email=email))
    now = datetime.utcnow()
    try:
        run_async(CourseMember.objects.create(group_id=group_id, user_id=user.id, created_at=now))
    except oxyde.IntegrityError:
        pass
    return redirect(f"/courses/{course_id}/groups/{group_id}/members", code=303)
