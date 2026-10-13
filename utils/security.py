from __future__ import annotations

import secrets
from urllib.parse import urlparse, urljoin

from flask import request, session


def generate_csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf_token(token: str | None) -> bool:
    expected = session.get("_csrf_token")
    return bool(token and expected and secrets.compare_digest(token, expected))


def is_safe_redirect_url(target: str) -> bool:
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc
