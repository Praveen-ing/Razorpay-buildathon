from typing import Any

from core.settings import DatabaseType, settings
from memory.sqlite import get_sqlite_saver, get_sqlite_store


def initialize_database() -> Any:
    """Initialize the appropriate database checkpointer based on configuration."""
    if settings.DATABASE_TYPE == DatabaseType.POSTGRES:
        try:
            from memory.postgres import get_postgres_saver
            return get_postgres_saver()
        except ImportError:
            return get_sqlite_saver()
    elif settings.DATABASE_TYPE == DatabaseType.MONGO:
        try:
            from memory.mongodb import get_mongo_saver
            return get_mongo_saver()
        except ImportError:
            return get_sqlite_saver()
    else:
        return get_sqlite_saver()


def initialize_store() -> Any:
    """Initialize the appropriate store based on configuration."""
    if settings.DATABASE_TYPE == DatabaseType.POSTGRES:
        try:
            from memory.postgres import get_postgres_store
            return get_postgres_store()
        except ImportError:
            return get_sqlite_store()
    else:
        return get_sqlite_store()


__all__ = ["initialize_database", "initialize_store"]
