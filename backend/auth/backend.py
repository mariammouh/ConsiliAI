"""
Authentication Backend & JWT Strategy
=====================================
Configures Bearer token transport and JWT signing strategy for user sessions.
Uses a 7-day token lifetime for persistent client login sessions.
"""

import os
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

SECRET = os.getenv("AUTH_SECRET")
if not SECRET:
    raise ValueError("AUTH_SECRET is not set (see manager.py for how to generate one).")

# Bearer transport configured to the fastapi-users login route
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Construct a JWTStrategy configured with a 7-day token expiration lifetime."""
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600 * 24 * 7)


# FastAPI-Users authentication backend instance combining Bearer transport and JWT strategy
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

