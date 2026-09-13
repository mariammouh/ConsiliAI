"""
Authentication & User Pydantic Schemas
======================================
Defines schemas for reading, creating, and updating user profiles via fastapi-users.
Extends base schemas with ConsiliAI-specific fields:
  - llm_provider: Active LLM provider selection ('cloud' | 'local').
  - task_models: User-configured model mappings per task category.
"""

import uuid
from typing import Optional, Dict, Any
from fastapi_users import schemas
from pydantic import field_validator


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for serializing authenticated user data returned to the client."""
    llm_provider: str = "cloud"
    task_models: Optional[Dict[str, Any]] = None


class UserCreate(schemas.BaseUserCreate):
    """Schema for user registration requests."""
    pass



class UserUpdate(schemas.BaseUserUpdate):
    llm_provider: Optional[str] = "cloud"
    task_models: Optional[Dict[str, Any]] = None

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("cloud", "local"):
            raise ValueError("llm_provider must be either 'cloud' or 'local'")
        return v

