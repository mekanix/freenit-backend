from __future__ import annotations

from time import time

import jwt
from passlib.hash import pbkdf2_sha256

ALGORITHM = "HS256"


def encrypt(password: str, secret: str) -> str:
    return pbkdf2_sha256.hash(f"{secret}{password}")


def verify(password: str, encpassword: str, secret: str) -> bool:
    return pbkdf2_sha256.verify(f"{secret}{password}", encpassword)


def encode(user, secret: str, expire: int) -> str:
    payload = {
        "pk": user.pk,
        "type": user.dbtype(),
        "jid": getattr(user, "email", None),
        "exp": int(time()) + expire,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode(token: str, secret: str) -> dict | None:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
