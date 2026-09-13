"""
FastAPI-Users Instance & Dependencies
=====================================
Instantiates the central FastAPIUsers helper and provides the `current_active_user`
dependency used across protected API endpoints to resolve the authenticated User.
"""

import uuid
from fastapi_users import FastAPIUsers

from .backend import auth_backend
from .db import User
from .manager import get_user_manager

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# FastAPI dependency to inject the current active user from the JWT Bearer token
current_active_user = fastapi_users.current_user(active=True)

