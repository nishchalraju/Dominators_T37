"""Shared request dependencies: who is calling, and are they allowed to?"""

from __future__ import annotations

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import RateLimiter, decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False, description="Log in at POST /api/auth/login, then paste the access_token here.")

# Sketch generation can call paid AI services: cap how fast one account can trigger it.
sketch_limiter = RateLimiter(max_calls=20, window_seconds=60)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, "Authentication required.", "not_authenticated", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError(
            401, "Your session is invalid or has expired. Please log in again.", "invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "This account is not available.", "invalid_token", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(403, "Only an administrator can do this.", "admin_only")
    return user


def limit_sketch_requests(user: User = Depends(get_current_user)) -> User:
    wait = sketch_limiter.check(str(user.id))
    if wait:
        raise AppError(
            429, f"Too many sketch requests. Wait {wait} seconds and try again.", "rate_limited",
            headers={"Retry-After": str(wait)},
        )
    return user
