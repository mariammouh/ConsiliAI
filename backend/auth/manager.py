"""
User Manager Module
===================
Defines the UserManager lifecycle class handling user registration, password resets,
and token verification hooks for fastapi-users.
"""

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
    """Manages user lifecycle hooks, password hashing, and authentication token verification."""
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Hook called immediately after successful user registration."""
        # Debug print commented out for production operation:
        # print(f"[auth] User {user.id} ({user.email}) registered.")
        pass

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        """Hook called when a user initiates a password reset flow."""
        # Debug print commented out for normal operation:
        # print(f"[auth] Password reset requested for {user.email}. Token: {token}")
        pass


async def get_user_manager(user_db=Depends(get_user_db)):
    """FastAPI dependency providing a scoped UserManager instance."""
    yield UserManager(user_db)

