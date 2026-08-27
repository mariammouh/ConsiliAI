import os

from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

SECRET = os.getenv("AUTH_SECRET")
if not SECRET:
    raise ValueError("AUTH_SECRET is not set (see manager.py for how to generate one).")

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    # 7-day token lifetime — reasonable for a small trusted group; tighten
    # later if this grows beyond that.
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
