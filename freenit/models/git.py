from __future__ import annotations

from datetime import datetime

import oxyde

from freenit.models.project import Project
from freenit.models.sql import OxydeBaseModel

NotFoundError = oxyde.NotFoundError
IntegrityError = oxyde.IntegrityError


class GitRepo(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    project: Project | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    name: str = oxyde.Field(db_unique=True)
    path: str = oxyde.Field(db_unique=True)
    description: str | None = oxyde.Field(default=None)
    public: bool = oxyde.Field(default=False)
    default_branch: str = oxyde.Field(default="main")
    tests_enabled: bool = oxyde.Field(default=False)
    test_command: str | None = oxyde.Field(default=None)
    webhook_url: str | None = oxyde.Field(default=None)
    created_at: datetime | None = oxyde.Field(default=None)
    updated_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "git_repo"


class GitPermission(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    repo: GitRepo | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    user_email: str = oxyde.Field()
    access: str = oxyde.Field(default="read")
    created_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "git_permission"
        unique_together = [("repo_id", "user_email")]


class GitPushLog(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    repo: GitRepo | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    ref: str = oxyde.Field()
    old_rev: str | None = oxyde.Field(default=None)
    new_rev: str | None = oxyde.Field(default=None)
    pusher_email: str = oxyde.Field()
    status: str = oxyde.Field(default="pending")
    output: str | None = oxyde.Field(default=None)
    created_at: datetime | None = oxyde.Field(default=None)
    updated_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "git_push_log"


class GitCommitTaskRef(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    repo: GitRepo | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )
    task_id: int = oxyde.Field()
    commit_sha: str = oxyde.Field()
    relation: str = oxyde.Field(default="refer")
    created_at: datetime | None = oxyde.Field(default=None)

    class Meta:
        is_table = True
        table_name = "git_commit_task_ref"
        unique_together = [("repo_id", "task_id", "commit_sha", "relation")]


async def _get_repo(id: int) -> GitRepo:
    try:
        return await GitRepo.objects.get(id=id)
    except NotFoundError:
        raise ValueError("No such repository")


async def _get_permission(id: int) -> GitPermission:
    try:
        return await GitPermission.objects.get(id=id)
    except NotFoundError:
        raise ValueError("No such permission")


async def _check_access(repo: GitRepo, user_email: str, required: str) -> bool:
    if required == "read" and repo.public:
        return True
    try:
        perm = await GitPermission.objects.filter(
            repo_id=repo.id, user_email=user_email
        ).get()
    except NotFoundError:
        return False
    if perm.access == "write":
        return True
    return required == "read"


async def _list_permissions(repo_id: int) -> list[GitPermission]:
    return await GitPermission.objects.filter(repo_id=repo_id).all()


async def _list_push_logs(repo_id: int) -> list[GitPushLog]:
    return await GitPushLog.objects.filter(repo_id=repo_id).order_by("-created_at").all()


GitRepo.model_rebuild()
GitPermission.model_rebuild()
GitPushLog.model_rebuild()
GitCommitTaskRef.model_rebuild()
