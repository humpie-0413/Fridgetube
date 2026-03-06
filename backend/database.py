import ssl as ssl_module
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings


def _prepare_engine_args(url: str) -> tuple[str, dict]:
    """asyncpg 호환 URL + connect_args를 반환."""
    parts = urlsplit(url)
    params = parse_qs(parts.query, keep_blank_values=True)

    use_ssl = False
    if "sslmode" in params:
        mode = params.pop("sslmode")[0]
        if mode in ("require", "verify-ca", "verify-full", "prefer"):
            use_ssl = True

    if "ssl" in params:
        val = params.pop("ssl")[0]
        if val.lower() not in ("disable", "false", "0"):
            use_ssl = True

    params.pop("channel_binding", None)

    new_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunsplit(parts._replace(query=new_query))

    connect_args: dict = {}
    if use_ssl:
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


_clean_url, _connect_args = _prepare_engine_args(settings.database_url)

engine = create_async_engine(
    _clean_url,
    echo=settings.environment == "development",
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
