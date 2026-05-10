"""Alembic environment.

Responsibilities:

1. Pull DATABASE_URL from our Settings (.env) instead of from alembic.ini, so
   secrets live in exactly one place.
2. Import every ORM model so ``Base.metadata`` is fully populated before
   autogenerate compares it to the live database.
3. Run migrations in either offline (emit SQL) or online (open a connection)
   mode, with ``compare_type=True`` so column-type changes are detected.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# These imports succeed because alembic.ini sets ``prepend_sys_path = .``,
# putting the backend/ directory on sys.path when alembic is invoked from
# there.
from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401  -- registers all tables on Base.metadata

config = context.config

# Inject the URL from Settings so we never write credentials into alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without opening a database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Open a connection and apply migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
