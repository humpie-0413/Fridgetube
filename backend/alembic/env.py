import asyncio
import os
import ssl as ssl_module
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata

_USE_SSL = False


def _sanitize_url_for_asyncpg(url: str) -> str:
    """asyncpg가 이해하지 못하는 sslmode, channel_binding 파라미터를 제거."""
    global _USE_SSL
    parts = urlsplit(url)
    params = parse_qs(parts.query, keep_blank_values=True)

    if "sslmode" in params:
        mode = params.pop("sslmode")[0]
        if mode in ("require", "verify-ca", "verify-full", "prefer"):
            _USE_SSL = True

    params.pop("channel_binding", None)

    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunsplit(parts._replace(query=new_query))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})

    raw_url = section.get("sqlalchemy.url", "")
    section["sqlalchemy.url"] = _sanitize_url_for_asyncpg(raw_url)

    connect_args = {}
    if _USE_SSL:
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
