# app/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://marketing:marketing123@localhost:5432/marketing_agents")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def init_db_sync():
    """Synchronous database initialization (for setup scripts)"""
    from .models import User, Client, Campaign, OptimizationHistory, ApiKey
    sync_engine = create_engine(DATABASE_URL.replace("+asyncpg", ""))
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()