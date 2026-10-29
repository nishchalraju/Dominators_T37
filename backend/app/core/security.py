"""Password hashing, signed access tokens and a small login throttle.

* Passwords are hashed with scrypt (Python standard library, memory-hard) using a
  random per-user salt. Plain-text passwords are never stored or logged.
* Access tokens are short-lived signed JWTs (HS256). They are stateless, so a
  "logout" simply makes the browser forget the token (see README: limitations).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

# --- password hashing ---------------------------------------------------------
_SCRYPT_LOG_N = 15  # N = 2**15 (about 32 MiB of memory per hash)
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 128 * 1024 * 1024


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**_SCRYPT_LOG_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        maxmem=_SCRYPT_MAXMEM,
        dklen=32,
    )
    return f"scrypt${_SCRYPT_LOG_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, log_n, r, p, salt_b64, digest_b64 = stored_hash.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2 ** int(log_n),
            r=int(r),
            p=int(p),
            maxmem=_SCRYPT_MAXMEM,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


# A pre-computed hash used to keep response time similar for unknown usernames.
_DUMMY_HASH = hash_password("not-a-real-password")


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


# --- access tokens --------------------------------------------------------------
_ALGORITHM = "HS256"


def create_access_token(*, user_id: int, username: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.resolve_secret_key(), algorithm=_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Return the token claims or raise ``jwt.PyJWTError``."""
    return jwt.decode(
        token,
        get_settings().resolve_secret_key(),
        algorithms=[_ALGORITHM],
        options={"require": ["exp", "sub"]},
    )


# --- login throttle ---------------------------------------------------------------
class LoginThrottle:
    """Blocks repeated failed logins (in memory, single process - a prototype guard)."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 900, lock_seconds: int = 300) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lock_seconds = lock_seconds
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """Seconds the caller must still wait (0 when allowed)."""
        with self._lock:
            until = self._locked_until.get(key, 0.0)
            remaining = until - time.monotonic()
            return int(remaining) + 1 if remaining > 0 else 0

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
            recent.append(now)
            self._failures[key] = recent
            if len(recent) >= self.max_failures:
                self._locked_until[key] = now + self.lock_seconds
                self._failures[key] = []

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()


login_throttle = LoginThrottle()


class RateLimiter:
    """At most ``max_calls`` per ``window_seconds`` for each key (in memory; protects paid AI calls)."""

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int:
        """Record a call. Returns 0 if allowed, else the seconds to wait."""
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._calls.get(key, []) if now - t < self.window_seconds]
            if len(recent) >= self.max_calls:
                self._calls[key] = recent
                return int(self.window_seconds - (now - recent[0])) + 1
            recent.append(now)
            self._calls[key] = recent
            return 0

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()
