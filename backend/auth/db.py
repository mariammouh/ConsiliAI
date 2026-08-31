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
import uuid
import datetime
from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, ForeignKey, UUID, text

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
    """User model with fastapi-users base fields plus application preferences."""
    llm_provider = Column(String, nullable=False, default="cloud", server_default="cloud")


class Conversation(Base):
    __tablename__ = "conversation"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    title = Column(String, nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS llm_provider VARCHAR NOT NULL DEFAULT \'cloud\';'))



async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
