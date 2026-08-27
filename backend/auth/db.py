"""
Database setup for authentication.

Uses async SQLAlchemy against Postgres. This is a SEPARATE connection
string format from the one LangGraph's PostgresSaver needs in
orchestrator.py (asyncpg vs psycopg) — both point at the same physical
Postgres instance/database, just via different drivers, since fastapi-users
requires an async SQLAlchemy engine and langgraph-checkpoint-postgres
requires psycopg. Two connection strings to one database, not two databases.
"""

import os
from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# e.g. postgresql+asyncpg://consiliai:consiliai@localhost:5432/consiliai
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set. Expected format: "
        "postgresql+asyncpg://<user>:<password>@<host>:5432/<dbname>"
    )


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Adds nothing beyond fastapi-users' base fields (email, hashed_password,
    is_active, is_superuser, is_verified) for v1. Extend here later if you
    need e.g. a role (student/teacher) or display name."""
    pass


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
