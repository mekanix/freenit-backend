from datetime import datetime

from flask import Blueprint, request

from freenit import auth
from freenit.db import run_async
from freenit.models.blog import BlogPost, BlogPostTag, _get_post_by_slug, _get_post_tags, _get_tag, _set_post_tags
from freenit.views import render_fragment_response, render_page

bp = Blueprint("blog", __name__)


@bp.get("/blog")
def blog():
    posts = run_async(BlogPost.objects.filter(published=True).order_by("-date").all())
    for post in posts:
        post.tags = run_async(_get_post_tags(post.id))
    return render_page("blog.html", "Blog", posts=posts, user=auth.current_user())


@bp.get("/blog/<slug>")
def blog_detail(slug: str):
    post = run_async(_get_post_by_slug(slug))
    post.tags = run_async(_get_post_tags(post.id))
    return render_page("blog_post.html", post.title, post=post, user=auth.current_user())


@bp.get("/blog/tags/<name>")
def blog_tag(name: str):
    tag = run_async(_get_tag(name.lower()))
    links = run_async(BlogPostTag.objects.filter(tag_id=tag.id).all())
    post_ids = [link.post_id for link in links]
    posts = []
    if post_ids:
        posts = run_async(BlogPost.objects.filter(id__in=post_ids, published=True).order_by("-date").all())
        for post in posts:
            post.tags = run_async(_get_post_tags(post.id))
    return render_page("blog_tag.html", f"Tag: {name}", posts=posts, tag_name=name, user=auth.current_user())


@bp.get("/blog/admin")
@auth.login_required
def blog_admin():
    posts = run_async(BlogPost.objects.order_by("-date").all())
    return render_page("blog_admin.html", "Blog admin", posts=posts, user=auth.current_user())


@bp.post("/blog/admin")
@auth.login_required
def blog_admin_create():
    user = auth.current_user()
    now = datetime.utcnow()
    title = request.form.get("title", "")
    slug = request.form.get("slug", "")
    content = request.form.get("content", "")
    published = request.form.get("published") == "true"
    tag_string = request.form.get("tags", "")
    tags = [t.strip().lower() for t in tag_string.split(",") if t.strip()]

    async def _create():
        post = await BlogPost.objects.create(
            title=title,
            slug=slug,
            content=content,
            date=now,
            published=published,
            author_id=user.id,
            created_at=now,
            updated_at=now,
        )
        await _set_post_tags(post, tags)
        return post

    run_async(_create())
    posts = run_async(BlogPost.objects.order_by("-date").all())
    return render_fragment_response(
        "blog_admin.html",
        posts=posts,
        user=user,
        toast="Post created",
    )
