# app/storage.py
import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "marketing_agents.db")


def _sync_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        return f"sqlite:///{os.path.abspath(DB_PATH)}"
    return url.replace("+asyncpg", "")


DATABASE_URL = _sync_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")
engine: Engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=not IS_SQLITE)


def _json_load(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _rows(result) -> List[Dict[str, Any]]:
    return [dict(row._mapping) for row in result]


def _scalar_or_none(result) -> Optional[Any]:
    row = result.first()
    return row[0] if row else None


def init_db():
    """Create all tables if they do not exist."""
    optimization_id = "INTEGER PRIMARY KEY AUTOINCREMENT" if IS_SQLITE else "SERIAL PRIMARY KEY"
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS optimization_history (
                id {optimization_id},
                campaign_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_description TEXT,
                kpi_before TEXT,
                kpi_after TEXT,
                status TEXT DEFAULT 'completed'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaigns (
                campaign_id TEXT PRIMARY KEY,
                client_id TEXT,
                created_by TEXT,
                state TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                industry TEXT,
                website TEXT,
                logo_url TEXT,
                billing_email TEXT,
                billing_info TEXT,
                settings TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL CHECK(role IN ('admin', 'client_manager', 'client_viewer')),
                client_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                name TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                last_used TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        """))


def save_campaign_state(
    campaign_id: str,
    state: Dict,
    status: str,
    client_id: str = None,
    created_by: str = None,
):
    """Persist the full campaign state."""
    now = datetime.utcnow().isoformat()
    state_json = json.dumps(state)
    with engine.begin() as conn:
        existing = _scalar_or_none(
            conn.execute(
                text("SELECT campaign_id FROM campaigns WHERE campaign_id = :campaign_id"),
                {"campaign_id": campaign_id},
            )
        )
        if existing:
            conn.execute(
                text("""
                    UPDATE campaigns
                    SET state = :state, status = :status, updated_at = :updated_at, client_id = :client_id
                    WHERE campaign_id = :campaign_id
                """),
                {
                    "state": state_json,
                    "status": status,
                    "updated_at": now,
                    "client_id": client_id,
                    "campaign_id": campaign_id,
                },
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO campaigns
                    (campaign_id, client_id, created_by, state, status, created_at, updated_at)
                    VALUES (:campaign_id, :client_id, :created_by, :state, :status, :created_at, :updated_at)
                """),
                {
                    "campaign_id": campaign_id,
                    "client_id": client_id,
                    "created_by": created_by,
                    "state": state_json,
                    "status": status,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def load_campaign_state(campaign_id: str) -> Optional[Dict]:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT state FROM campaigns WHERE campaign_id = :campaign_id"),
            {"campaign_id": campaign_id},
        ).first()
    return _json_load(result[0]) if result else None


def get_all_campaigns() -> List[Dict]:
    with engine.begin() as conn:
        rows = _rows(conn.execute(text("SELECT * FROM campaigns ORDER BY created_at DESC")))
    for item in rows:
        item["state"] = _json_load(item["state"], {})
    return rows


def get_client_campaigns(client_id: str) -> List[Dict]:
    with engine.begin() as conn:
        rows = _rows(
            conn.execute(
                text("SELECT * FROM campaigns WHERE client_id = :client_id ORDER BY created_at DESC"),
                {"client_id": client_id},
            )
        )
    for item in rows:
        item["state"] = _json_load(item["state"], {})
    return rows


def delete_campaign(campaign_id: str) -> bool:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM optimization_history WHERE campaign_id = :campaign_id"),
            {"campaign_id": campaign_id},
        )
        result = conn.execute(
            text("DELETE FROM campaigns WHERE campaign_id = :campaign_id"),
            {"campaign_id": campaign_id},
        )
    return result.rowcount > 0


def save_optimization_action(
    campaign_id: str,
    action_type: str,
    action_description: str,
    kpi_before: Dict = None,
    kpi_after: Dict = None,
    status: str = "completed",
):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO optimization_history
                (campaign_id, timestamp, action_type, action_description, kpi_before, kpi_after, status)
                VALUES (:campaign_id, :timestamp, :action_type, :action_description, :kpi_before, :kpi_after, :status)
            """),
            {
                "campaign_id": campaign_id,
                "timestamp": datetime.utcnow().isoformat(),
                "action_type": action_type,
                "action_description": action_description,
                "kpi_before": json.dumps(kpi_before) if kpi_before else None,
                "kpi_after": json.dumps(kpi_after) if kpi_after else None,
                "status": status,
            },
        )


def get_optimization_history(campaign_id: str, limit: int = 50) -> List[Dict]:
    with engine.begin() as conn:
        rows = _rows(
            conn.execute(
                text("""
                    SELECT * FROM optimization_history
                    WHERE campaign_id = :campaign_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"campaign_id": campaign_id, "limit": limit},
            )
        )
    for item in rows:
        item["kpi_before"] = _json_load(item.get("kpi_before")) if item.get("kpi_before") else None
        item["kpi_after"] = _json_load(item.get("kpi_after")) if item.get("kpi_after") else None
    return rows


def create_client(client_data: Dict) -> str:
    now = datetime.utcnow().isoformat()
    client_id = client_data.get("id", str(uuid.uuid4())[:8])
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO clients
                (id, name, industry, website, logo_url, billing_email, billing_info, settings, created_at, updated_at)
                VALUES (:id, :name, :industry, :website, :logo_url, :billing_email, :billing_info, :settings, :created_at, :updated_at)
            """),
            {
                "id": client_id,
                "name": client_data.get("name"),
                "industry": client_data.get("industry", ""),
                "website": client_data.get("website", ""),
                "logo_url": client_data.get("logo_url", ""),
                "billing_email": client_data.get("billing_email", ""),
                "billing_info": json.dumps(client_data.get("billing_info", {})),
                "settings": json.dumps(client_data.get("settings", {})),
                "created_at": now,
                "updated_at": now,
            },
        )
    return client_id


def _hydrate_client(item: Dict[str, Any]) -> Dict[str, Any]:
    item["billing_info"] = _json_load(item.get("billing_info"), {})
    item["settings"] = _json_load(item.get("settings"), {})
    return item


def get_all_clients() -> List[Dict]:
    with engine.begin() as conn:
        rows = _rows(conn.execute(text("SELECT * FROM clients ORDER BY created_at DESC")))
    return [_hydrate_client(item) for item in rows]


def get_client(client_id: str) -> Optional[Dict]:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM clients WHERE id = :client_id"),
            {"client_id": client_id},
        ).first()
    return _hydrate_client(dict(row._mapping)) if row else None


def delete_client(client_id: str) -> bool:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM campaigns WHERE client_id = :client_id"),
            {"client_id": client_id},
        )
        result = conn.execute(
            text("DELETE FROM clients WHERE id = :client_id"),
            {"client_id": client_id},
        )
    return result.rowcount > 0


def create_user(user_data: Dict) -> str:
    now = datetime.utcnow().isoformat()
    user_id = user_data.get("id", str(uuid.uuid4())[:8])
    password_hash = hashlib.sha256(user_data["password"].encode()).hexdigest()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO users
                (id, email, password_hash, full_name, role, client_id, created_at, updated_at)
                VALUES (:id, :email, :password_hash, :full_name, :role, :client_id, :created_at, :updated_at)
            """),
            {
                "id": user_id,
                "email": user_data["email"],
                "password_hash": password_hash,
                "full_name": user_data.get("full_name", ""),
                "role": user_data["role"],
                "client_id": user_data.get("client_id"),
                "created_at": now,
                "updated_at": now,
            },
        )
    return user_id


def get_user_by_email(email: str) -> Optional[Dict]:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": email},
        ).first()
    return dict(row._mapping) if row else None


def get_users_by_client(client_id: str) -> List[Dict]:
    with engine.begin() as conn:
        return _rows(
            conn.execute(
                text("SELECT * FROM users WHERE client_id = :client_id ORDER BY created_at DESC"),
                {"client_id": client_id},
            )
        )


def get_all_users() -> List[Dict]:
    with engine.begin() as conn:
        return _rows(conn.execute(text("SELECT * FROM users ORDER BY created_at DESC")))


def verify_user(email: str, password: str) -> Optional[Dict]:
    user = get_user_by_email(email)
    if not user:
        return None
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return user if user["password_hash"] == password_hash else None


def update_user_password(email: str, password: str) -> bool:
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE users
                SET password_hash = :password_hash, updated_at = :updated_at
                WHERE email = :email
            """),
            {
                "email": email,
                "password_hash": password_hash,
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
    return result.rowcount > 0


init_db()
