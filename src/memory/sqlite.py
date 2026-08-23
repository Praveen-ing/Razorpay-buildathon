from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from core.settings import settings


class AsyncMemorySaverWrapper:
    """Wrapper for MemorySaver that provides an async context manager interface."""

    def __init__(self):
        self.saver = MemorySaver()

    async def __aenter__(self):
        return self.saver

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def setup(self):
        pass


def get_sqlite_saver() -> Any:
    """Initialize and return a saver instance."""
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        return AsyncSqliteSaver.from_conn_string(settings.SQLITE_DB_PATH)
    except Exception:
        return AsyncMemorySaverWrapper()


class AsyncInMemoryStore:
    """Wrapper for InMemoryStore that provides an async context manager interface."""

    def __init__(self):
        self.store = InMemoryStore()

    async def __aenter__(self):
        return self.store

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def setup(self):
        pass


@asynccontextmanager
async def get_sqlite_store():
    """Initialize and return a store instance for long-term memory."""
    store_manager = AsyncInMemoryStore()
    yield await store_manager.__aenter__()
