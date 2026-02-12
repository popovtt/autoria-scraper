import pathlib

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.settings import config

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "alembic.ini"
MIGRATION_PATH = BASE_DIR / "migrations"

cfg = Config(str(CONFIG_PATH))
cfg.set_main_option("script_location", str(MIGRATION_PATH))

engine = create_async_engine(config.POSTGRESQL_DSN, pool_size=20, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def migrate_db(conn_url: str) -> None:
    async_engine = create_async_engine(conn_url, echo=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(__execute_upgrade)


def __execute_upgrade(connection) -> None:  # noqa: ANN001
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")
