import sys
import os

sys.path.insert(0, os.path.dirname(__file__).replace("migrations", "."))

from sqlmodel import SQLModel

from alembic import context

config = context.config
# Keep alembic pointed at the same DB the app uses (app/db.py default).
config.set_main_option(
    "sqlalchemy.url",
    os.environ.get("KG_DATABASE_URL", "sqlite:///database/knowledge.db"),
)
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = context.config.attributes.get("connection", None)
    if connectable:
        with connectable.begin() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            context.run_migrations()
    else:
        from sqlalchemy import engine_from_config
        engine = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
        )
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
