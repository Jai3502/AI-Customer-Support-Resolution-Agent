import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

from database.pg_client import is_postgres_available, get_engine, get_db_session

logger = logging.getLogger(__name__)
Base = declarative_base()

# ---------------------------------------------------------------------------
# SQLAlchemy ORM Models
# ---------------------------------------------------------------------------

class UserModel(Base):
    __tablename__ = "users"

    username = Column(String(100), primary_key=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(50), nullable=False, default="customer")
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    customer_id = Column(String(50), nullable=True)
    created_at = Column(String(50), default=lambda: datetime.utcnow().isoformat())


class CustomerModel(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(50), nullable=True)
    preferred_language = Column(String(50), default="English")
    membership = Column(String(50), default="Standard")
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    total_orders = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(String(50), default=lambda: datetime.utcnow().isoformat())


class OrderModel(Base):
    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(String(50), nullable=False)
    payment_method = Column(String(100), nullable=False)
    order_status = Column(String(50), nullable=False)
    carrier = Column(String(100), nullable=True)
    tracking_id = Column(String(100), nullable=True)
    order_date = Column(String(50), nullable=False)
    estimated_delivery = Column(String(50), nullable=True)


class TicketModel(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(50), default="Medium")
    status = Column(String(50), default="Open")
    assigned_agent = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(String(50), default=lambda: datetime.utcnow().isoformat())


class PerformanceLogModel(Base):
    __tablename__ = "performance_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(100), nullable=False)
    customer_id = Column(String(50), nullable=True)
    intent = Column(String(50), nullable=True)
    total_latency_ms = Column(Float, nullable=False)
    node_latencies_json = Column(Text, nullable=False)
    tokens_used_json = Column(Text, nullable=False)
    created_at = Column(String(50), default=lambda: datetime.utcnow().isoformat())


class KnowledgeVectorModel(Base):
    __tablename__ = "knowledge_vectors"

    id = Column(String(100), primary_key=True)
    filename = Column(String(150), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=False)
    vector_dim = Column(Integer, default=768)
    created_at = Column(String(50), default=lambda: datetime.utcnow().isoformat())


class LongTermMemoryModel(Base):
    __tablename__ = "long_term_memories"

    id = Column(String(100), primary_key=True)
    user_id = Column(String(100), nullable=False)
    memory_text = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    embedding_json = Column(Text, nullable=True)
    created_at = Column(String(50), default=lambda: datetime.utcnow().isoformat())

# ---------------------------------------------------------------------------
# Database Initialization & Migration Seeding
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")

def init_db_and_seed() -> Dict[str, Any]:
    """
    Creates tables in PostgreSQL and seeds initial data from data/*.json if tables are empty.
    Returns status report dictionary.
    """
    if not is_postgres_available():
        return {"status": "skipped", "reason": "PostgreSQL not reachable"}

    engine = get_engine()
    if engine is None:
        return {"status": "skipped", "reason": "No engine"}

    try:
        # Enable pgvector if extension available
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            except Exception:
                pass

        Base.metadata.create_all(engine)
    except Exception as e:
        logger.error(f"Error creating PostgreSQL schema: {e}")
        return {"status": "error", "error": str(e)}

    session = get_db_session()
    if session is None:
        return {"status": "error", "error": "Could not acquire DB session"}

    seeded_summary = {}

    try:
        # Seed Users
        if session.query(UserModel).count() == 0:
            users_file = DATA_DIR / "users.json"
            if users_file.exists():
                users_data = json.loads(users_file.read_text(encoding="utf-8"))
                for u_data in users_data.values():
                    session.add(UserModel(
                        username=u_data["username"],
                        password_hash=u_data["password_hash"],
                        role=u_data.get("role", "customer"),
                        name=u_data.get("name", "User"),
                        email=u_data.get("email", ""),
                        customer_id=u_data.get("customer_id"),
                        created_at=u_data.get("created_at", datetime.utcnow().isoformat())
                    ))
                seeded_summary["users"] = len(users_data)

        # Seed Customers
        if session.query(CustomerModel).count() == 0:
            cust_file = DATA_DIR / "customers.json"
            if cust_file.exists():
                cust_data = json.loads(cust_file.read_text(encoding="utf-8"))
                for c_data in cust_data.values():
                    session.add(CustomerModel(
                        customer_id=c_data["customer_id"],
                        name=c_data["name"],
                        email=c_data["email"],
                        phone=c_data.get("phone"),
                        preferred_language=c_data.get("preferred_language", "English"),
                        membership=c_data.get("membership", "Standard"),
                        city=c_data.get("city"),
                        state=c_data.get("state"),
                        pincode=c_data.get("pincode"),
                        total_orders=c_data.get("total_orders", 0),
                        notes=c_data.get("notes")
                    ))
                seeded_summary["customers"] = len(cust_data)

        # Seed Orders
        if session.query(OrderModel).count() == 0:
            order_file = DATA_DIR / "orders.json"
            if order_file.exists():
                order_data = json.loads(order_file.read_text(encoding="utf-8"))
                for o_data in order_data.values():
                    session.add(OrderModel(
                        order_id=o_data["order_id"],
                        customer_id=o_data["customer_id"],
                        product=o_data["product"],
                        category=o_data.get("category", "General"),
                        amount=float(o_data["amount"]),
                        payment_status=o_data.get("payment_status", "Paid"),
                        payment_method=o_data.get("payment_method", "Credit Card"),
                        order_status=o_data.get("order_status", "Processing"),
                        carrier=o_data.get("carrier"),
                        tracking_id=o_data.get("tracking_id"),
                        order_date=o_data.get("order_date", ""),
                        estimated_delivery=o_data.get("estimated_delivery")
                    ))
                seeded_summary["orders"] = len(order_data)

        # Seed Tickets
        if session.query(TicketModel).count() == 0:
            ticket_file = DATA_DIR / "tickets.json"
            if ticket_file.exists():
                ticket_data = json.loads(ticket_file.read_text(encoding="utf-8"))
                for t_data in ticket_data:
                    session.add(TicketModel(
                        ticket_id=t_data["ticket_id"],
                        customer_id=t_data["customer_id"],
                        category=t_data.get("category", "General"),
                        description=t_data.get("description", ""),
                        priority=t_data.get("priority", "Medium"),
                        status=t_data.get("status", "Open"),
                        assigned_agent=t_data.get("assigned_agent"),
                        resolution_notes=t_data.get("resolution_notes"),
                        created_at=t_data.get("created_at", datetime.utcnow().isoformat())
                    ))
                seeded_summary["tickets"] = len(ticket_data)

        # Seed Performance Logs
        if session.query(PerformanceLogModel).count() == 0:
            perf_file = DATA_DIR / "performance_logs.json"
            if perf_file.exists():
                perf_data = json.loads(perf_file.read_text(encoding="utf-8"))
                for p_data in perf_data:
                    session.add(PerformanceLogModel(
                        thread_id=p_data.get("thread_id", "default"),
                        customer_id=p_data.get("customer_id"),
                        intent=p_data.get("intent"),
                        total_latency_ms=float(p_data.get("total_latency_ms", 0.0)),
                        node_latencies_json=json.dumps(p_data.get("node_latencies_ms", {})),
                        tokens_used_json=json.dumps(p_data.get("tokens_used", {})),
                        created_at=p_data.get("timestamp", datetime.utcnow().isoformat())
                    ))
                seeded_summary["performance_logs"] = len(perf_data)

        session.commit()
        return {"status": "success", "seeded": seeded_summary}
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding PostgreSQL tables: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        session.close()

def get_table_counts() -> Dict[str, int]:
    """
    Returns record count for all PostgreSQL tables.
    """
    if not is_postgres_available():
        return {}

    session = get_db_session()
    if session is None:
        return {}

    try:
        counts = {
            "users": session.query(UserModel).count(),
            "customers": session.query(CustomerModel).count(),
            "orders": session.query(OrderModel).count(),
            "tickets": session.query(TicketModel).count(),
            "performance_logs": session.query(PerformanceLogModel).count(),
            "knowledge_vectors": session.query(KnowledgeVectorModel).count(),
            "long_term_memories": session.query(LongTermMemoryModel).count(),
        }
        return counts
    except Exception:
        return {}
    finally:
        session.close()
