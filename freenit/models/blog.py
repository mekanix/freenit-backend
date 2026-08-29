from __future__ import annotations

from datetime import datetime

import oxyde
import pydantic

from freenit.models.sql import OxydeBaseModel, User

NotFoundError = oxyde.NotFoundError
IntegrityError = oxyde.IntegrityError


class Tag(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    name: str = oxyde.Field(db_unique=True, db_index=True)

    class Meta:
        is_table = True
        table_name = "blog_tag"


class BlogPost(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    title: str = oxyde.Field()
    slug: str = oxyde.Field(db_unique=True, db_index=True)
    content: str = oxyde.Field()
    date: datetime | None = oxyde.Field(default=None)
    author: User | None = oxyde.Field(default=None, db_fk="id", db_on_delete="SET NULL")
    published: bool = oxyde.Field(default=False)
    tags: list[Tag] = oxyde.Field(
        default_factory=list, db_m2m=True, db_through="BlogPostTag"
    )
    created_at: datetime | None = oxyde.Field(default=None)
    updated_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "blog_post"


class BlogPostTag(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    post: BlogPost | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    tag: Tag | None = oxyde.Field(default=None, db_fk="id", db_on_delete="CASCADE")

    class Meta:
        is_table = True
        table_name = "blog_post_tag"
        unique_together = [("post_id", "tag_id")]


class BlogPostOptional(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    title: str | None = None
    slug: str | None = None
    content: str | None = None
    date: datetime | None = None
    published: bool | None = None
    tags: list[str] | None = None


async def _get_post(id: int) -> BlogPost:
    try:
        return await BlogPost.objects.get(id=id)
    except NotFoundError:
        raise ValueError("No such blog post")


async def _get_post_by_slug(slug: str) -> BlogPost:
    try:
        return await BlogPost.objects.filter(slug=slug).get()
    except NotFoundError:
        raise ValueError("No such blog post")


async def _get_tag(name: str) -> Tag:
    try:
        return await Tag.objects.filter(name=name).get()
    except NotFoundError:
        raise ValueError("No such tag")


async def _check_slug_unique(slug: str, exclude_id: int | None = None) -> None:
    existing = await BlogPost.objects.filter(slug=slug).all()
    if any(item.id != exclude_id for item in existing):
        raise ValueError("Blog post slug already exists")


async def _set_post_tags(post: BlogPost, tag_names: list[str]) -> None:
    existing = await BlogPostTag.objects.filter(post_id=post.id).all()
    for link in existing:
        await link.delete()

    tag_objects = []
    for name in set(tag_names):
        name = name.strip().lower()
        if not name:
            continue
        try:
            tag = await Tag.objects.filter(name=name).get()
        except NotFoundError:
            tag = await Tag.objects.create(name=name)
        tag_objects.append(tag)

    for tag in tag_objects:
        try:
            await BlogPostTag.objects.create(post_id=post.id, tag_id=tag.id)
        except IntegrityError:
            pass


async def _get_post_tags(post_id: int) -> list[str]:
    links = await BlogPostTag.objects.filter(post_id=post_id).all()
    if not links:
        return []
    tag_ids = [link.tag_id for link in links]
    tag_objects = await Tag.objects.filter(id__in=tag_ids).all()
    return sorted(tag.name for tag in tag_objects)


async def _enforce_author_or_admin(post: BlogPost, user: User) -> None:
    if not user.admin and post.author_id != user.id:
        raise PermissionError("Only the author or admin can modify this post")


BlogPost.model_rebuild()
Tag.model_rebuild()
BlogPostTag.model_rebuild()
