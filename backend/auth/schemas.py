import uuid

from fastapi_users import schemas


from typing import Optional
from pydantic import field_validator


class UserRead(schemas.BaseUser[uuid.UUID]):
    llm_provider: str = "cloud"


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    llm_provider: Optional[str] = "cloud"

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("cloud", "local"):
            raise ValueError("llm_provider must be either 'cloud' or 'local'")
        return v

