"""数据库配置 - 优先 Postgres，连接失败自动降级到 SQLite。"""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings


def _sqlite_url() -> str:
    p = Path(settings.SQLITE_PATH).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{p.as_posix()}"


def _make_engine(url: str):
    return create_async_engine(url, echo=settings.DEBUG, future=True)


# 初始先按配置建引擎，init_db() 里会真实探测；失败则切 SQLite
engine = _make_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def _try_create_all(eng) -> bool:
    try:
        async with eng.begin() as conn:
            from app.models import Base as _Base
            await conn.run_sync(_Base.metadata.create_all)
        return True
    except Exception as e:
        print(f"⚠️  数据库连接失败：{e.__class__.__name__}: {e}")
        return False


async def init_db():
    """尝试 Postgres；失败且允许 SQLite 时切换。"""
    global engine, AsyncSessionLocal

    if await _try_create_all(engine):
        print(f"✅ 数据库就绪：{engine.url.drivername}")
        return

    if not settings.USE_SQLITE_FALLBACK:
        raise RuntimeError("数据库初始化失败且未启用 SQLite 回退")

    sqlite_url = _sqlite_url()
    print(f"↪ 回退到 SQLite：{sqlite_url}")
    await engine.dispose()
    engine = _make_engine(sqlite_url)
    AsyncSessionLocal.configure(bind=engine)

    if not await _try_create_all(engine):
        raise RuntimeError("SQLite 回退也失败")
    print("✅ 数据库表创建成功 (SQLite)")
