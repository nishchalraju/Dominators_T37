from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db, utcnow
from app.core.errors import AppError
from app.core.security import LoginThrottle, burn_password_check, create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.schemas.common import ErrorBody
from app.services.activity import log_activity

router = APIRouter(prefix="/auth", tags=["Authentication"])
login_throttle = LoginThrottle()


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user_id=user.id, username=user.username, role=user.role)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post(
    "/register", response_model=TokenResponse, status_code=201,
    responses={409: {"model": ErrorBody, "description": "Username already taken"}, 403: {"model": ErrorBody}},
    summary="Create an account",
    description="Creates an investigator account and signs you in. The **first** account created on a fresh "
    "installation becomes the administrator (needed for dataset inspection and evaluation runs).",
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if not get_settings().allow_registration:
        raise AppError(403, "Registration is switched off on this server.", "registration_disabled")
    if db.scalar(select(User.id).where(User.username == body.username)) is not None:
        raise AppError(409, "That username is already taken.", "username_taken")
    is_first = (db.scalar(select(func.count(User.id))) or 0) == 0
    user = User(
        username=body.username, display_name=body.display_name or body.username, password_hash=hash_password(body.password),
        role="admin" if is_first else "investigator", responsible_use_ack_at=utcnow(),
    )  # fmt: skip
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # two people picked the same name at the same moment
        db.rollback()
        raise AppError(409, "That username is already taken.", "username_taken") from exc
    log_activity(db, user=user, action="user_registered", summary=f"Account '{user.username}' created ({user.role})")
    db.commit()
    return _token_response(user)


@router.post(
    "/login", response_model=TokenResponse,
    responses={401: {"model": ErrorBody}, 429: {"model": ErrorBody, "description": "Too many failed attempts"}},
    summary="Sign in",
)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    key = f"{request.client.host if request.client else 'unknown'}:{body.username}"
    wait = login_throttle.retry_after(key)
    if wait:
        raise AppError(
            429, f"Too many failed sign-in attempts. Try again in {wait} seconds.", "too_many_attempts",
            headers={"Retry-After": str(wait)},
        )
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None:
        burn_password_check(body.password)  # keep the timing similar for unknown names
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        login_throttle.record_failure(key)
        raise AppError(401, "Incorrect username or password.", "invalid_credentials")
    login_throttle.record_success(key)
    user.last_login_at = utcnow()
    log_activity(db, user=user, action="user_login", summary=f"'{user.username}' signed in")
    db.commit()
    return _token_response(user)


@router.get("/me", response_model=UserOut, summary="The signed-in user")
def me(user: User = Depends(get_current_user)) -> User:
    return user
