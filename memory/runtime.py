from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

DATABASE_DIR = Path("database")
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DB = DATABASE_DIR / "conversation_checkpoints.db"
MEMORY_DB = DATABASE_DIR / "long_term_memory.db"


class Persistence:
    """
    Owns the lifecycle of both SQLite-backed persistence layers:

      - SqliteSaver -> short-term / thread-scoped checkpointer
      - SqliteStore -> long-term / cross-thread memory store

    Both are context managers under the hood, so we enter them once here
    and exit them explicitly via close() when the app shuts down.
    """

    def __init__(self):
        self.checkpoint_context = SqliteSaver.from_conn_string(str(CHECKPOINT_DB))
        self.checkpointer = self.checkpoint_context.__enter__()

        self.store_context = SqliteStore.from_conn_string(str(MEMORY_DB))
        self.store = self.store_context.__enter__()
        self.store.setup()

    def close(self):
        try:
            self.checkpoint_context.__exit__(None, None, None)
        except Exception:
            pass
        try:
            self.store_context.__exit__(None, None, None)
        except Exception:
            pass