from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import oxyde
import pydantic

from freenit.models.sql import OxydeBaseModel

NotFoundError = oxyde.NotFoundError
IntegrityError = oxyde.IntegrityError


class MailingList(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    name: str = oxyde.Field(db_unique=True)
    address: pydantic.EmailStr = oxyde.Field(db_unique=True)
    distribution_address: pydantic.EmailStr = oxyde.Field(db_unique=True)
    archive_address: pydantic.EmailStr = oxyde.Field(db_unique=True)
    description: str | None = oxyde.Field(default=None)
    public: bool = oxyde.Field(default=True)
    archive_enabled: bool = oxyde.Field(default=True)
    moderation_enabled: bool = oxyde.Field(default=False)
    principal_id: int | None = oxyde.Field(default=None)
    inbox_principal_id: int | None = oxyde.Field(default=None)
    archive_principal_id: int | None = oxyde.Field(default=None)
    created_at: datetime | None = oxyde.Field(default=None)
    updated_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "mailing_list"


class Subscriber(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    mailing_list: MailingList | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    email: pydantic.EmailStr = oxyde.Field()
    created_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "mailing_list_subscriber"
        unique_together = [("mailing_list_id", "email")]


class PendingSubscriber(OxydeBaseModel):
    """Subscriptions/unsubscriptions awaiting email confirmation."""

    id: int | None = oxyde.Field(default=None, db_pk=True)
    mailing_list: MailingList | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    email: pydantic.EmailStr = oxyde.Field()
    token: str = oxyde.Field(default_factory=lambda: str(uuid4()))
    action: str = oxyde.Field(default="subscribe")
    created_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "pending_subscriber"
        unique_together = [("mailing_list_id", "email", "action")]


class ModerationMessage(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    mailing_list: MailingList | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    message_id: str | None = oxyde.Field(default=None)
    subject: str | None = oxyde.Field(default=None)
    sender: pydantic.EmailStr | None = oxyde.Field(default=None)
    sent_at: datetime | None = oxyde.Field(default=None)
    text_body: str | None = oxyde.Field(default=None)
    html_body: str | None = oxyde.Field(default=None)
    status: str = oxyde.Field(default="pending")
    created_at: datetime | None = oxyde.Field(default=None)
    decided_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "moderation_message"


async def _get_list(id: int) -> MailingList:
    try:
        return await MailingList.objects.get(id=id)
    except NotFoundError:
        raise ValueError("No such mailing list")


async def _get_pending(id: int, token: str, action: str) -> PendingSubscriber:
    try:
        return await PendingSubscriber.objects.filter(
            mailing_list_id=id, token=token, action=action
        ).get()
    except NotFoundError:
        raise ValueError("No such pending request")


async def _get_subscriber(list_id: int, email: str) -> Subscriber:
    try:
        return await Subscriber.objects.filter(
            mailing_list_id=list_id, email=email
        ).get()
    except NotFoundError:
        raise ValueError("No such subscriber")


async def _get_moderation(list_id: int, msg_id: int) -> ModerationMessage:
    try:
        return await ModerationMessage.objects.filter(
            mailing_list_id=list_id, id=msg_id
        ).get()
    except NotFoundError:
        raise ValueError("No such moderation message")


async def _list_subscribers(list_id: int) -> list[Subscriber]:
    return await Subscriber.objects.filter(mailing_list_id=list_id).all()


MailingList.model_rebuild()
Subscriber.model_rebuild()
PendingSubscriber.model_rebuild()
ModerationMessage.model_rebuild()
