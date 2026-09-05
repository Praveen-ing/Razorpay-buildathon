from typing import Any

from memory.sqlite import get_sqlite_saver, get_sqlite_store


def initialize_database() -> Any:
    """Initialize the database checkpointer."""
    return get_sqlite_saver()


def initialize_store() -> Any:
    """Initialize the store for long-term memory."""
    return get_sqlite_store()


__all__ = ["initialize_database", "initialize_store"]

