"""Заглушка аутентификации.

Граница интеграции: authenticate / login_user / logout_user / current_user.
Позже здесь появляется адаптер к внешней системе (OIDC / SSO / reverse-proxy
header / LDAP), а роуты и шаблоны не меняются.
"""

import hmac
from functools import wraps
from urllib.parse import urlsplit

from flask import flash, redirect, request, session, url_for

# Единственная учётка. Открытый пароль — осознанно, ТОЛЬКО для локальной заглушки.
STUB_USERS = {"admin": "admin"}

_USER_KEY = "auth.username"


def authenticate(username: str, password: str) -> bool:
    expected = STUB_USERS.get(username)
    if expected is None:
        return False
    # compare_digest на str не принимает не-ASCII, поэтому кодируем.
    return hmac.compare_digest(expected.encode("utf-8"), password.encode("utf-8"))


def current_user() -> str | None:
    return session.get(_USER_KEY)


def login_user(username: str) -> None:
    session.clear()  # фиксируем сессию после входа
    session.permanent = True
    session[_USER_KEY] = username


def logout_user() -> None:
    session.clear()


def safe_next_url(target: str | None) -> str | None:
    """Разрешаем только внутренние пути: никакого open redirect."""
    if not target or target.startswith("//") or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/"):
        return None
    return target


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Войдите, чтобы загружать и редактировать картинки.", "info")
            return redirect(url_for("login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped
