from datetime import datetime
from uuid import uuid4

from flask import Blueprint, abort, current_app, redirect, request

from freenit import auth
from freenit.db import run_async
from freenit.models.mailinglist import (
    MailingList,
    ModerationMessage,
    PendingSubscriber,
    Subscriber,
    _get_list,
    _get_moderation,
    _get_pending,
    _get_subscriber,
    _list_subscribers,
)
from freenit.views import render_fragment_response, render_page

bp = Blueprint("mailinglist", __name__)


def _parse_address(address: str) -> tuple[str, str]:
    local, _, domain = address.partition("@")
    return local, domain


@bp.get("/mailinglists")
@auth.roles_required("admin")
def mailinglists():
    user = auth.current_user()
    lists = run_async(MailingList.objects.order_by("name").all())
    return render_page("mailinglists.html", "Mailing lists", lists=lists, user=user)


@bp.post("/mailinglists")
@auth.roles_required("admin")
def mailinglists_create():
    user = auth.current_user()
    name = request.form.get("name", "").strip()
    domain = request.form.get("domain", "").strip()
    description = request.form.get("description") or None
    public = request.form.get("public") == "true"
    archive_enabled = request.form.get("archive_enabled") == "true"
    moderation_enabled = request.form.get("moderation_enabled") == "true"

    if "@" in name or "/" in name or not name or not domain:
        lists = run_async(MailingList.objects.order_by("name").all())
        return render_fragment_response(
            "mailinglists.html",
            lists=lists,
            user=user,
            toast="Invalid mailing list name or domain",
            status=400,
        )

    address = f"{name}@{domain}"
    local, _ = _parse_address(address)
    distribution_address = f"{local}-members@{domain}"
    archive_address = f"{local}-archive@{domain}"

    existing = run_async(
        MailingList.objects.filter(
            address__in=[address, distribution_address, archive_address]
        ).all()
    )
    if existing:
        lists = run_async(MailingList.objects.order_by("name").all())
        return render_fragment_response(
            "mailinglists.html",
            lists=lists,
            user=user,
            toast="Mailing list address already in use",
            status=409,
        )

    now = datetime.utcnow()
    run_async(
        MailingList.objects.create(
            name=name,
            address=address,
            distribution_address=distribution_address,
            archive_address=archive_address,
            description=description,
            public=public,
            archive_enabled=archive_enabled,
            moderation_enabled=moderation_enabled,
            created_at=now,
            updated_at=now,
        )
    )
    lists = run_async(MailingList.objects.order_by("name").all())
    return render_fragment_response(
        "mailinglists.html",
        lists=lists,
        user=user,
        toast=f"Mailing list {name} created",
    )


@bp.get("/mailinglists/public")
def mailinglists_public():
    lists = run_async(MailingList.objects.filter(public=True).order_by("name").all())
    return render_page(
        "mailinglists_public.html", "Mailing lists", lists=lists, user=auth.current_user()
    )


@bp.get("/mailinglists/<int:list_id>")
@auth.roles_required("admin")
def mailinglist_detail(list_id: int):
    user = auth.current_user()
    mailing_list = run_async(_get_list(list_id))
    subscribers = run_async(_list_subscribers(list_id))
    pending = run_async(
        PendingSubscriber.objects.filter(mailing_list_id=list_id).all()
    )
    moderation = run_async(
        ModerationMessage.objects.filter(mailing_list_id=list_id, status="pending")
        .order_by("-created_at")
        .all()
    )
    return render_page(
        "mailinglist_detail.html",
        mailing_list.name,
        mailing_list=mailing_list,
        subscribers=subscribers,
        pending=pending,
        moderation=moderation,
        user=user,
    )


@bp.post("/mailinglists/<int:list_id>")
@auth.roles_required("admin")
def mailinglist_update(list_id: int):
    user = auth.current_user()
    mailing_list = run_async(_get_list(list_id))
    description = request.form.get("description")
    public = request.form.get("public") == "true"
    archive_enabled = request.form.get("archive_enabled") == "true"
    moderation_enabled = request.form.get("moderation_enabled") == "true"

    mailing_list.description = description or None
    mailing_list.public = public
    mailing_list.archive_enabled = archive_enabled
    mailing_list.moderation_enabled = moderation_enabled
    mailing_list.updated_at = datetime.utcnow()
    run_async(mailing_list.save())
    return redirect(f"/mailinglists/{list_id}", code=303)


@bp.post("/mailinglists/<int:list_id>/delete")
@auth.roles_required("admin")
def mailinglist_delete(list_id: int):
    user = auth.current_user()
    mailing_list = run_async(_get_list(list_id))
    run_async(mailing_list.delete())
    return redirect("/mailinglists", code=303)


@bp.get("/mailinglists/<int:list_id>/subscribers")
@auth.roles_required("admin")
def mailinglist_subscribers(list_id: int):
    user = auth.current_user()
    mailing_list = run_async(_get_list(list_id))
    subscribers = run_async(_list_subscribers(list_id))
    return render_page(
        "mailinglist_subscribers.html",
        f"{mailing_list.name} subscribers",
        mailing_list=mailing_list,
        subscribers=subscribers,
        user=user,
    )


@bp.post("/mailinglists/<int:list_id>/subscribers")
@auth.roles_required("admin")
def mailinglist_subscriber_add(list_id: int):
    user = auth.current_user()
    mailing_list = run_async(_get_list(list_id))
    email = request.form.get("email", "").strip()
    if email:
        now = datetime.utcnow()
        try:
            run_async(
                Subscriber.objects.create(
                    mailing_list_id=list_id, email=email, created_at=now
                )
            )
        except Exception:
            pass
    return redirect(f"/mailinglists/{list_id}/subscribers", code=303)


@bp.post("/mailinglists/<int:list_id>/subscribers/<int:subscriber_id>/delete")
@auth.roles_required("admin")
def mailinglist_subscriber_remove(list_id: int, subscriber_id: int):
    user = auth.current_user()
    run_async(_get_list(list_id))
    try:
        subscriber = run_async(Subscriber.objects.get(id=subscriber_id))
        run_async(subscriber.delete())
    except Exception:
        pass
    return redirect(f"/mailinglists/{list_id}/subscribers", code=303)


@bp.get("/mailinglists/<int:list_id>/subscribe")
def mailinglist_subscribe_form(list_id: int):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public:
        abort(403)
    return render_page(
        "mailinglist_subscribe.html",
        f"Subscribe to {mailing_list.name}",
        mailing_list=mailing_list,
        user=auth.current_user(),
    )


@bp.post("/mailinglists/<int:list_id>/subscribe")
def mailinglist_subscribe(list_id: int):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public:
        abort(403)
    email = request.form.get("email", "").strip()
    if not email:
        return render_fragment_response(
            "mailinglist_subscribe.html",
            mailing_list=mailing_list,
            user=auth.current_user(),
            toast="Email is required",
            status=400,
        )

    now = datetime.utcnow()
    existing = run_async(
        Subscriber.objects.filter(mailing_list_id=list_id, email=email).all()
    )
    if existing:
        return render_fragment_response(
            "mailinglist_subscribe.html",
            mailing_list=mailing_list,
            user=auth.current_user(),
            toast="You are already subscribed",
        )

    pending = run_async(
        PendingSubscriber.objects.filter(
            mailing_list_id=list_id, email=email, action="subscribe"
        ).all()
    )
    if pending:
        token = pending[0].token
    else:
        token = str(uuid4())
        run_async(
            PendingSubscriber.objects.create(
                mailing_list_id=list_id,
                email=email,
                token=token,
                action="subscribe",
                created_at=now,
            )
        )

    config = current_app.config["FREENIT_CONFIG"]
    confirm_url = f"{config.hostname}/mailinglists/{list_id}/confirm/{token}"
    return render_fragment_response(
        "mailinglist_subscribe.html",
        mailing_list=mailing_list,
        user=auth.current_user(),
        toast=f"Please confirm your subscription by visiting {confirm_url}",
    )


@bp.get("/mailinglists/<int:list_id>/confirm/<token>")
def mailinglist_confirm(list_id: int, token: str):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public:
        abort(403)
    pending = run_async(_get_pending(list_id, token, "subscribe"))
    now = datetime.utcnow()
    try:
        run_async(
            Subscriber.objects.create(
                mailing_list_id=list_id, email=pending.email, created_at=now
            )
        )
    except Exception:
        pass
    run_async(pending.delete())
    return render_page(
        "mailinglist_confirm.html",
        "Subscription confirmed",
        mailing_list=mailing_list,
        user=auth.current_user(),
    )


@bp.get("/mailinglists/<int:list_id>/unsubscribe")
def mailinglist_unsubscribe_form(list_id: int):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public:
        abort(403)
    return render_page(
        "mailinglist_unsubscribe.html",
        f"Unsubscribe from {mailing_list.name}",
        mailing_list=mailing_list,
        user=auth.current_user(),
    )


@bp.post("/mailinglists/<int:list_id>/unsubscribe")
def mailinglist_unsubscribe_request(list_id: int):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public:
        abort(403)
    email = request.form.get("email", "").strip()
    if not email:
        return render_fragment_response(
            "mailinglist_unsubscribe.html",
            mailing_list=mailing_list,
            user=auth.current_user(),
            toast="Email is required",
            status=400,
        )

    try:
        run_async(_get_subscriber(list_id, email))
    except ValueError:
        return render_fragment_response(
            "mailinglist_unsubscribe.html",
            mailing_list=mailing_list,
            user=auth.current_user(),
            toast="You are not subscribed",
            status=404,
        )

    now = datetime.utcnow()
    pending = run_async(
        PendingSubscriber.objects.filter(
            mailing_list_id=list_id, email=email, action="unsubscribe"
        ).all()
    )
    if pending:
        token = pending[0].token
    else:
        token = str(uuid4())
        run_async(
            PendingSubscriber.objects.create(
                mailing_list_id=list_id,
                email=email,
                token=token,
                action="unsubscribe",
                created_at=now,
            )
        )

    config = current_app.config["FREENIT_CONFIG"]
    confirm_url = f"{config.hostname}/mailinglists/{list_id}/unsubscribe/{token}"
    return render_fragment_response(
        "mailinglist_unsubscribe.html",
        mailing_list=mailing_list,
        user=auth.current_user(),
        toast=f"Please confirm your unsubscription by visiting {confirm_url}",
    )


@bp.get("/mailinglists/<int:list_id>/unsubscribe/<token>")
def mailinglist_unsubscribe_confirm(list_id: int, token: str):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public:
        abort(403)
    pending = run_async(_get_pending(list_id, token, "unsubscribe"))
    try:
        subscriber = run_async(_get_subscriber(list_id, pending.email))
        run_async(subscriber.delete())
    except ValueError:
        pass
    run_async(pending.delete())
    return render_page(
        "mailinglist_unsubscribe.html",
        "Unsubscription confirmed",
        mailing_list=mailing_list,
        user=auth.current_user(),
        confirmed=True,
    )


@bp.get("/mailinglists/<int:list_id>/archive")
def mailinglist_archive(list_id: int):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public or not mailing_list.archive_enabled:
        abort(403)
    messages = run_async(
        ModerationMessage.objects.filter(mailing_list_id=list_id, status="approved")
        .order_by("-sent_at")
        .all()
    )
    return render_page(
        "mailinglist_archive.html",
        f"{mailing_list.name} archive",
        mailing_list=mailing_list,
        messages=messages,
        user=auth.current_user(),
    )


@bp.get("/mailinglists/<int:list_id>/archive/<int:message_id>")
def mailinglist_archive_message(list_id: int, message_id: int):
    mailing_list = run_async(_get_list(list_id))
    if not mailing_list.public or not mailing_list.archive_enabled:
        abort(403)
    message = run_async(_get_moderation(list_id, message_id))
    if message.status != "approved":
        abort(404)
    return render_page(
        "mailinglist_archive_message.html",
        message.subject or "Archive message",
        mailing_list=mailing_list,
        message=message,
        user=auth.current_user(),
    )


@bp.get("/mailinglists/<int:list_id>/moderation")
@auth.roles_required("admin")
def mailinglist_moderation(list_id: int):
    user = auth.current_user()
    mailing_list = run_async(_get_list(list_id))
    messages = run_async(
        ModerationMessage.objects.filter(mailing_list_id=list_id, status="pending")
        .order_by("-created_at")
        .all()
    )
    return render_page(
        "mailinglist_moderation.html",
        f"{mailing_list.name} moderation",
        mailing_list=mailing_list,
        messages=messages,
        user=user,
    )


@bp.post("/mailinglists/<int:list_id>/moderation/<int:message_id>/approve")
@auth.roles_required("admin")
def mailinglist_moderation_approve(list_id: int, message_id: int):
    user = auth.current_user()
    message = run_async(_get_moderation(list_id, message_id))
    message.status = "approved"
    message.decided_at = datetime.utcnow()
    run_async(message.save())
    return redirect(f"/mailinglists/{list_id}/moderation", code=303)


@bp.post("/mailinglists/<int:list_id>/moderation/<int:message_id>/reject")
@auth.roles_required("admin")
def mailinglist_moderation_reject(list_id: int, message_id: int):
    user = auth.current_user()
    message = run_async(_get_moderation(list_id, message_id))
    message.status = "rejected"
    message.decided_at = datetime.utcnow()
    run_async(message.save())
    return redirect(f"/mailinglists/{list_id}/moderation", code=303)
