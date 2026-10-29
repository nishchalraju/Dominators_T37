from __future__ import annotations

import re
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel, OutModel

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")


class RegisterRequest(ApiModel):
    username: str = Field(description="3-32 characters: letters, digits, underscore, dot or hyphen.")
    password: str = Field(min_length=10, max_length=128, description="At least 10 characters.")
    display_name: str | None = Field(default=None, max_length=80)
    acknowledge_responsible_use: bool = Field(
        description="Must be true: confirms you have read the responsible-use statement."
    )

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        value = value.strip().lower()
        if not USERNAME_RE.match(value):
            raise ValueError("Username must be 3-32 characters: letters, digits, underscore, dot or hyphen.")
        return value

    @field_validator("acknowledge_responsible_use")
    @classmethod
    def _ack(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must confirm that you accept the responsible-use statement.")
        return value

    @model_validator(mode="after")
    def _password_rules(self):  # noqa: ANN204
        if self.password.lower() == self.username:
            raise ValueError("The password must not be the same as the username.")
        if len(set(self.password)) < 5:
            raise ValueError("The password is too repetitive - use a mix of different characters.")
        return self


class LoginRequest(ApiModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)

    @field_validator("username")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(OutModel):
    id: int
    username: str
    display_name: str | None
    role: str
    created_at: datetime


class TokenResponse(OutModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until the token expires.")
    user: UserOut
