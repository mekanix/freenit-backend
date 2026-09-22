from __future__ import annotations

from bonsai import LDAPClient, LDAPSearchScope, errors

from .config import LDAPConfig


class LDAPError(Exception):
    """Raised when the LDAP server is unreachable or misconfigured."""


def _get_client(dn: str, password: str, config: LDAPConfig) -> LDAPClient:
    client = LDAPClient(f"ldap://{config.host}", config.tls)
    client.set_credentials("SIMPLE", user=dn, password=password)
    return client


def _first(values: list[str] | None) -> str | None:
    if not values:
        return None
    return values[0]


def _has_class(values: list[str] | None, targets: frozenset[str]) -> bool:
    if not values or not targets:
        return False
    return any(value in targets for value in values)


def _omemo_bundle(entry, config: LDAPConfig) -> str | None:
    if config.omemo_attr == "description":
        for desc in entry.get("description", []):
            if desc.startswith("__OMEMO__:"):
                return desc[len("__OMEMO__:"):]
        return None
    return _first(entry.get(config.omemo_attr, []))


def _entry_to_dict(entry, config: LDAPConfig) -> dict:
    email = _first(entry.get(config.attr_email, [])) or ""
    fullname = _first(entry.get(config.attr_fullname, [])) or ""
    user_classes = entry.get(config.attr_user_class, [])
    return {
        "email": email,
        "fullname": fullname,
        "active": _has_class(user_classes, config.active_classes),
        "admin": _has_class(user_classes, config.admin_classes),
        "omemo_bundle": _omemo_bundle(entry, config),
    }


async def ldap_login(email: str, password: str, config: LDAPConfig) -> dict | None:
    """Authenticate against LDAP and return user attributes.

    Returns ``None`` when credentials are invalid. Raises ``LDAPError`` when
    the LDAP server cannot be reached.
    """
    if "@" not in email:
        return None

    username, domain = email.split("@", 1)

    try:
        if config.user_dn_template:
            user_dn = config.user_dn_template.format(
                username=username, domain=domain
            )
            client = _get_client(user_dn, password, config)
            async with client.connect(is_async=True) as conn:
                res = await conn.search(
                    user_dn, LDAPSearchScope.BASE, "(objectClass=*)"
                )
                if not res:
                    return None
                return _entry_to_dict(res[0], config)

        # No DN template: search with a service account, then bind as the user.
        service_client = _get_client(config.service_dn, config.service_pw, config)
        async with service_client.connect(is_async=True) as conn:
            search_filter = config.search_filter.format(
                email=email, username=username, domain=domain
            )
            res = await conn.search(
                config.user_base,
                LDAPSearchScope.SUB,
                search_filter,
                [config.attr_email, config.attr_fullname, config.attr_user_class],
            )
            if not res:
                return None
            user_dn = str(res[0].dn)
            ldap_attrs = _entry_to_dict(res[0], config)

        user_client = _get_client(user_dn, password, config)
        async with user_client.connect(is_async=True):
            pass  # bind-only to verify the password

        return ldap_attrs

    except errors.AuthenticationError:
        return None
    except errors.ConnectionError as exc:
        raise LDAPError(f"Cannot connect to LDAP server {config.host}") from exc
    except errors.LDAPError as exc:
        raise LDAPError(f"LDAP error: {exc}") from exc
