import os
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin

from .db import User, get_user_db

SECRET = os.getenv("AUTH_SECRET")
if not SECRET:
    raise ValueError(
        "AUTH_SECRET is not set. Generate one with: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"[auth] User {user.id} ({user.email}) registered.")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        # v1: no email sending configured. Print for manual dev use only —
        # wire up real email delivery before this touches real users beyond
        # the small trusted group mentioned.
        print(f"[auth] Password reset requested for {user.email}. Token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
