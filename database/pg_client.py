import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

logger = logging.getLogger(__name__)

def get_postgres_url() -> Optional[str]:
    """
    Constructs or retrieves the PostgreSQL connection URL from environment variables.
    """
    url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if url:
        # Standardize postgresql:// protocol
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "ai_support_db")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")

    if host and user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    return None

_engine = None
_SessionLocal = None
_is_available = None

def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    pg_url = get_postgres_url()
    if not pg_url:
        return None

    try:
        _engine = create_engine(
            pg_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 3}
        )
        return _engine
    except Exception as e:
        logger.warning(f"Failed to create SQLAlchemy engine for PostgreSQL: {e}")
        return None

def is_postgres_available() -> bool:
    """
    Tests if PostgreSQL connection is currently reachable and valid.
    """
    global _is_available
    engine = get_engine()
    if engine is None:
        _is_available = False
        return False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _is_available = True
        return True
    except Exception as e:
        logger.debug(f"PostgreSQL connection test failed: {e}")
        _is_available = False
        return False

def get_db_session() -> Optional[Session]:
    """
    Returns a fresh database session if PostgreSQL is available, else None.
    """
    global _SessionLocal
    if not is_postgres_available():
        return None

    engine = get_engine()
    if engine is None:
        return None

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return _SessionLocal()

def check_connection_status() -> Dict[str, Any]:
    """
    Returns detailed diagnostics on PostgreSQL connection status.
    """
    url = get_postgres_url()
    available = is_postgres_available()
    
    masked_url = "Not configured"
    if url:
        try:
            # Mask password in URL for UI presentation
            if "@" in url:
                user_pass, host_db = url.split("@", 1)
                proto_user = user_pass.split(":", 2)[0] if ":" in user_pass else user_pass
                masked_url = f"{proto_user}:****@{host_db}"
            else:
                masked_url = url
        except Exception:
            masked_url = "Configured"

    return {
        "configured": bool(url),
        "available": available,
        "connection_url": masked_url,
        "mode": "PostgreSQL Active" if available else "SQLite/JSON Fallback"
    }
