import uuid

from fastapi_users import FastAPIUsers

from .backend import auth_backend
from .db import User
from .manager import get_user_manager

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Use this as a dependency on any endpoint that must be tied to a specific
# logged-in user (e.g. /chat) — FastAPI resolves it from the Bearer token
# in the Authorization header, no manual token parsing needed.
current_active_user = fastapi_users.current_user(active=True)
