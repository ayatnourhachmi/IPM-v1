"""SQLAlchemy async engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Some DATABASE_URLs include `?sslmode=require` which the asyncpg driver
# does not accept as a keyword argument. Sanitize and convert to a proper
# `ssl` connect arg so SQLAlchemy/asyncpg connect works both locally and on
# hosted platforms (e.g., Neon via Render).
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

raw_url = settings.database_url
split = urlsplit(raw_url)
query_items = dict(parse_qsl(split.query))
sslmode = query_items.pop("sslmode", None)
new_query = urlencode(query_items)
sanitized_url = urlunsplit((split.scheme, split.netloc, split.path, new_query, split.fragment))

connect_args = {}
if sslmode:
    connect_args["ssl"] = True

engine = create_async_engine(
    sanitized_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args or None,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """Yield a database session for dependency injection."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
