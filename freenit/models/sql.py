from __future__ import annotations

import oxyde
import pydantic

from freenit import security
from freenit.config import LDAPConfig
from freenit.ldap_auth import LDAPError, ldap_login


class OxydeBaseModel(oxyde.Model):
    @classmethod
    def dbtype(cls):
        return "sql"

    @property
    def pk(self):
        return self.id

    async def patch(self, fields):
        data = fields.model_dump(exclude_none=True)
        for key, value in data.items():
            setattr(self, key, value)
        await self.save(update_fields=data.keys())
        return self

    async def load_all(self):
        if hasattr(self, "roles"):
            object.__setattr__(self, "roles", await self.fetch_roles())
        if hasattr(self, "users"):
            object.__setattr__(self, "users", await self.fetch_users())
        return self


class RoleRelationManager:
    def __init__(self, user: "User"):
        self.user = user

    async def add(self, role: "BaseRole"):
        try:
            await UserRole.objects.create(
                user=self.user,
                role=role,
                user_id=self.user.id,
                role_id=role.id,
            )
        except oxyde.IntegrityError as exc:
            raise ValueError("User already assigned") from exc
        object.__setattr__(self.user, "roles", await self.user.fetch_roles())

    async def remove(self, role: "BaseRole"):
        link = await UserRole.objects.get(user_id=self.user.id, role_id=role.id)
        await link.delete()
        object.__setattr__(self.user, "roles", await self.user.fetch_roles())


class RoleList(list):
    def __init__(self, user: "User", roles: list["BaseRole"] | None = None):
        super().__init__(roles or [])
        self.user = user

    async def add(self, role: "BaseRole"):
        await RoleRelationManager(self.user).add(role)
        self[:] = await self.user.fetch_roles()

    async def remove(self, role: "BaseRole"):
        await RoleRelationManager(self.user).remove(role)
        self[:] = await self.user.fetch_roles()


class BaseRole(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    name: str = oxyde.Field(db_unique=True, db_index=True)
    users: list["User"] = oxyde.Field(
        default_factory=list, db_m2m=True, db_through="UserRole"
    )

    class Meta:
        is_table = True
        table_name = "role"

    def model_post_init(self, __context):
        object.__setattr__(self, "users", list(getattr(self, "users", []) or []))

    async def fetch_users(self) -> list[str]:
        users = await User.objects.prefetch("roles").all()
        return [
            user.email
            for user in users
            if any(role.id == self.id for role in user.roles)
        ]


Role = BaseRole


class User(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    email: pydantic.EmailStr = oxyde.Field(db_unique=True)
    password: str = oxyde.Field()
    fullname: str | None = oxyde.Field(default=None)
    active: bool = oxyde.Field(default=False)
    admin: bool = oxyde.Field(default=False)
    provider: str = oxyde.Field(default="local")
    omemo_bundle: str | None = oxyde.Field(default=None)
    roles: list[BaseRole] = oxyde.Field(
        default_factory=list, db_m2m=True, db_through="UserRole"
    )

    class Meta:
        is_table = True
        table_name = "user"

    def model_post_init(self, __context):
        object.__setattr__(
            self, "roles", RoleList(self, list(getattr(self, "roles", []) or []))
        )

    def check(self, password: str, secret: str) -> bool:
        if self.password is None:
            return False
        return security.verify(password, self.password, secret)

    @classmethod
    async def _sync_ldap_user(
        cls, attrs: dict, ldap_config: LDAPConfig
    ) -> "User | None":
        email = attrs.get("email")
        if not email:
            return None

        try:
            user = await cls.objects.filter(email=email).get()
        except oxyde.NotFoundError:
            user = cls(
                email=email,
                password="",
                provider="ldap",
            )

        user.fullname = attrs.get("fullname") or user.fullname
        user.active = attrs.get("active", True)
        user.admin = attrs.get("admin", False)
        user.provider = "ldap"
        if attrs.get("omemo_bundle") is not None:
            user.omemo_bundle = attrs["omemo_bundle"]
        await user.save()
        return await cls.objects.prefetch("roles").filter(email=email).get()

    @classmethod
    async def _local_login(
        cls, email: str, password: str, secret: str
    ) -> "User | None":
        try:
            user = await cls.objects.prefetch("roles").filter(
                email=email, active=True
            ).get()
        except oxyde.NotFoundError:
            return None
        if user.check(password, secret):
            return user
        return None

    @classmethod
    async def login(
        cls,
        email: str,
        password: str,
        secret: str,
        ldap_config: LDAPConfig | None = None,
    ) -> "User | None":
        if ldap_config is not None:
            try:
                attrs = await ldap_login(email, password, ldap_config)
            except LDAPError:
                # If the LDAP server is unreachable, do not fall back to local
                # auth unless explicitly allowed.
                if not ldap_config.allow_local_fallback:
                    return None
                attrs = None

            if attrs is not None:
                return await cls._sync_ldap_user(attrs, ldap_config)

            if not ldap_config.allow_local_fallback:
                return None

        return await cls._local_login(email, password, secret)

    async def fetch_roles(self) -> RoleList:
        links = await UserRole.objects.filter(user_id=self.id).all()
        role_ids = [link.role_id for link in links]
        if not role_ids:
            return RoleList(self, [])
        roles = await BaseRole.objects.filter(id__in=role_ids).all()
        return RoleList(self, roles)

    def has_role(self, name: str) -> bool:
        return any(role.name == name for role in self.roles)


class UserRole(OxydeBaseModel):
    id: int | None = oxyde.Field(default=None, db_pk=True)
    user: User | None = oxyde.Field(default=None, db_fk="id", db_on_delete="CASCADE")
    role: BaseRole | None = oxyde.Field(
        default=None, db_fk="id", db_on_delete="CASCADE"
    )

    class Meta:
        is_table = True
        table_name = "user_role"
        unique_together = [("user_id", "role_id")]


User.model_rebuild()
BaseRole.model_rebuild()
UserRole.model_rebuild()
