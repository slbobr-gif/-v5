"""Alembic env: миграции пишутся SQL-ом вручную, автогенерация не используется.

Строка подключения — DATABASE_URL (postgresql+psycopg://...). Секреты в репозиторий не кладём:
локально — .env, в облаке — Lockbox.
"""

import os

from alembic import context
from sqlalchemy import create_engine, pool

url = os.environ["DATABASE_URL"]


def run_offline() -> None:
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


run_offline() if context.is_offline_mode() else run_online()
