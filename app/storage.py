# app/storage.py
import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .encryption import encrypt, decrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "marketing_agents.db")

SETTINGS_KEY_GLOBAL_AD_CREDENTIALS = "global_ad_credentials"
AUDIT_STATUS_NEW = "new"
AUDIT_STATUS_CONTACTED = "contacted"
AUDIT_STATUS_QUALIFIED = "qualified"
AUDIT_STATUS_WON = "won"
AUDIT_STATUS_LOST = "lost"


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




def _ensure_client_platform_status_column(conn):
    if IS_SQLITE:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(clients)"))]
    else:
        columns = [row[0] for row in conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'clients'
        """))]
    if "platform_status" not in columns:
        conn.execute(text("ALTER TABLE clients ADD COLUMN platform_status TEXT DEFAULT 'inactive'"))


def _get_table_columns(conn, table_name: str) -> List[str]:
    if IS_SQLITE:
        return [row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})"))]
    return [
        row[0]
        for row in conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :table_name
            """),
            {"table_name": table_name},
        )
    ]


def _ensure_user_billing_columns(conn):
    columns = _get_table_columns(conn, "users")
    if "stripe_customer_id" not in columns:
        conn.execute(text("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT"))
    if "subscription_status" not in columns:
        conn.execute(text("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'trial'"))
    if "plan" not in columns:
        conn.execute(text("ALTER TABLE users ADD COLUMN plan TEXT"))


def _ensure_client_credential_columns(conn):
    columns = _get_table_columns(conn, "clients")
    credential_columns = {
        "google_ads_developer_token": "TEXT",
        "google_ads_client_id": "TEXT",
        "google_ads_client_secret": "TEXT",
        "google_ads_refresh_token": "TEXT",
        "google_ads_customer_id": "TEXT",
        "meta_app_id": "TEXT",
        "meta_app_secret": "TEXT",
        "meta_access_token": "TEXT",
        "meta_ad_account_id": "TEXT",
        "google_ads_configured": "BOOLEAN DEFAULT 0" if IS_SQLITE else "BOOLEAN DEFAULT FALSE",
        "meta_ads_configured": "BOOLEAN DEFAULT 0" if IS_SQLITE else "BOOLEAN DEFAULT FALSE",
    }
    for column_name, column_type in credential_columns.items():
        if column_name not in columns:
            conn.execute(text(f"ALTER TABLE clients ADD COLUMN {column_name} {column_type}"))


def _ensure_settings_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            is_encrypted INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """))


def _ensure_leads_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            website TEXT NOT NULL,
            company TEXT,
            source TEXT DEFAULT 'audit',
            status TEXT DEFAULT 'new',
            notes TEXT,
            audit_id TEXT,
            proposal_id TEXT,
            follow_up_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """))


def _ensure_audit_reports_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_reports (
            id TEXT PRIMARY KEY,
            website TEXT NOT NULL,
            title TEXT,
            audit_json TEXT NOT NULL,
            lead_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """))


def _ensure_proposals_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY,
            lead_id TEXT,
            website TEXT,
            proposal_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """))


def _ensure_publish_events_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS publish_events (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            attempted INTEGER DEFAULT 0,
            succeeded INTEGER DEFAULT 0,
            response_id TEXT,
            error_message TEXT,
            payload_summary TEXT,
            created_at TEXT NOT NULL
        )
    """))


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
                platform_status TEXT DEFAULT 'inactive',
                google_ads_developer_token TEXT,
                google_ads_client_id TEXT,
                google_ads_client_secret TEXT,
                google_ads_refresh_token TEXT,
                google_ads_customer_id TEXT,
                meta_app_id TEXT,
                meta_app_secret TEXT,
                meta_access_token TEXT,
                meta_ad_account_id TEXT,
                google_ads_configured INTEGER DEFAULT 0,
                meta_ads_configured INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
        _ensure_client_platform_status_column(conn)
        _ensure_client_credential_columns(conn)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL CHECK(role IN ('admin', 'client_manager', 'client_viewer')),
                client_id TEXT,
                stripe_customer_id TEXT,
                subscription_status TEXT DEFAULT 'trial',
                plan TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
        _ensure_user_billing_columns(conn)
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
        _ensure_settings_table(conn)
        _ensure_leads_table(conn)
        _ensure_audit_reports_table(conn)
        _ensure_proposals_table(conn)
        _ensure_publish_events_table(conn)
        _ensure_report_templates_table(conn)
        _ensure_onboarding_progress_table(conn)



def set_setting(key: str, value: Any, encrypt_value: bool = False) -> None:
    serialized = json.dumps(value) if not isinstance(value, str) else value
    stored_value = encrypt(serialized) if encrypt_value else serialized
    now = datetime.utcnow().isoformat()
    with engine.begin() as conn:
        existing = _scalar_or_none(
            conn.execute(text("SELECT key FROM settings WHERE key = :key"), {"key": key})
        )
        if existing:
            conn.execute(
                text("""
                    UPDATE settings
                    SET value = :value, is_encrypted = :is_encrypted, updated_at = :updated_at
                    WHERE key = :key
                """),
                {
                    "key": key,
                    "value": stored_value,
                    "is_encrypted": 1 if encrypt_value else 0,
                    "updated_at": now,
                },
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO settings (key, value, is_encrypted, updated_at)
                    VALUES (:key, :value, :is_encrypted, :updated_at)
                """),
                {
                    "key": key,
                    "value": stored_value,
                    "is_encrypted": 1 if encrypt_value else 0,
                    "updated_at": now,
                },
            )


def get_setting(key: str, default: Any = None) -> Any:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT value, is_encrypted FROM settings WHERE key = :key"),
            {"key": key},
        ).first()
    if not row:
        return default
    raw_value = decrypt(row[0]) if row[1] else row[0]
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return raw_value


def _mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def save_global_ad_credentials(creds: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "google_ads_developer_token": creds.get("google_ads_developer_token") or "",
        "google_ads_client_id": creds.get("google_ads_client_id") or "",
        "google_ads_client_secret": creds.get("google_ads_client_secret") or "",
        "google_ads_refresh_token": creds.get("google_ads_refresh_token") or "",
        "google_ads_customer_id": creds.get("google_ads_customer_id") or "",
        "meta_app_id": creds.get("meta_app_id") or "",
        "meta_app_secret": creds.get("meta_app_secret") or "",
        "meta_access_token": creds.get("meta_access_token") or "",
        "meta_ad_account_id": creds.get("meta_ad_account_id") or "",
        "google_ads_configured": bool(creds.get("google_ads_developer_token") or os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")),
        "meta_ads_configured": bool(creds.get("meta_app_id") or os.getenv("META_APP_ID")),
    }
    set_setting(SETTINGS_KEY_GLOBAL_AD_CREDENTIALS, payload, encrypt_value=True)
    return payload


def load_global_ad_credentials(mask_secrets: bool = False) -> Dict[str, Any]:
    stored = get_setting(SETTINGS_KEY_GLOBAL_AD_CREDENTIALS, default={}) or {}
    fallback = {
        "google_ads_developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        "google_ads_client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", ""),
        "google_ads_client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", ""),
        "google_ads_refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN", ""),
        "google_ads_customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID", ""),
        "meta_app_id": os.getenv("META_APP_ID", ""),
        "meta_app_secret": os.getenv("META_APP_SECRET", ""),
        "meta_access_token": os.getenv("META_ACCESS_TOKEN", ""),
        "meta_ad_account_id": os.getenv("META_AD_ACCOUNT_ID", ""),
    }
    merged = {**fallback, **stored}
    merged["google_ads_configured"] = bool(merged.get("google_ads_developer_token"))
    merged["meta_ads_configured"] = bool(merged.get("meta_app_id"))
    if not mask_secrets:
        return merged
    masked = dict(merged)
    for key in [
        "google_ads_developer_token",
        "google_ads_client_secret",
        "google_ads_refresh_token",
        "meta_app_secret",
        "meta_access_token",
    ]:
        masked[key] = _mask_secret(masked.get(key))
    return masked


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
    return get_all_campaigns()


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
                (id, name, industry, website, logo_url, billing_email, billing_info, settings, platform_status, 
                google_ads_developer_token, google_ads_client_id, google_ads_client_secret, google_ads_refresh_token, 
                google_ads_customer_id, meta_app_id, meta_app_secret, meta_access_token, meta_ad_account_id,
                google_ads_configured, meta_ads_configured, agent_llm_settings, image_generation_preferences, default_budget,
                created_at, updated_at)
                VALUES (:id, :name, :industry, :website, :logo_url, :billing_email, :billing_info, :settings, :platform_status,
                :google_ads_developer_token, :google_ads_client_id, :google_ads_client_secret, :google_ads_refresh_token,
                :google_ads_customer_id, :meta_app_id, :meta_app_secret, :meta_access_token, :meta_ad_account_id,
                :google_ads_configured, :meta_ads_configured, :agent_llm_settings, :image_generation_preferences, :default_budget,
                :created_at, :updated_at)
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
                "platform_status": client_data.get("platform_status", "inactive"),
                # Ad credentials (encrypted)
                "google_ads_developer_token": encrypt(client_data.get("google_ads_developer_token", "")),
                "google_ads_client_id": encrypt(client_data.get("google_ads_client_id", "")),
                "google_ads_client_secret": encrypt(client_data.get("google_ads_client_secret", "")),
                "google_ads_refresh_token": encrypt(client_data.get("google_ads_refresh_token", "")),
                "google_ads_customer_id": encrypt(client_data.get("google_ads_customer_id", "")),
                "meta_app_id": encrypt(client_data.get("meta_app_id", "")),
                "meta_app_secret": encrypt(client_data.get("meta_app_secret", "")),
                "meta_access_token": encrypt(client_data.get("meta_access_token", "")),
                "meta_ad_account_id": encrypt(client_data.get("meta_ad_account_id", "")),
                "google_ads_configured": client_data.get("google_ads_configured", False),
                "meta_ads_configured": client_data.get("meta_ads_configured", False),
                # Per-Agent LLM Settings
                "agent_llm_settings": json.dumps(client_data.get("agent_llm_settings", {})),
                # Additional fields
                "image_generation_preferences": json.dumps(client_data.get("image_generation_preferences", {})),
                "default_budget": client_data.get("default_budget"),
                "created_at": now,
                "updated_at": now,
            },
        )
    return client_id


def _hydrate_client(item: Dict[str, Any]) -> Dict[str, Any]:
    item["billing_info"] = _json_load(item.get("billing_info"), {})
    item["settings"] = _json_load(item.get("settings"), {})
    item["platform_status"] = item.get("platform_status") or "inactive"
    item["campaign_count"] = int(item.get("campaign_count") or 0)
    return item


def get_all_clients() -> List[Dict]:
    with engine.begin() as conn:
        rows = _rows(conn.execute(text("""
            SELECT c.*, COALESCE(cc.campaign_count, 0) AS campaign_count
            FROM clients c
            LEFT JOIN (
                SELECT client_id, COUNT(*) AS campaign_count
                FROM campaigns
                GROUP BY client_id
            ) cc ON cc.client_id = c.id
            ORDER BY c.created_at DESC
        """)))
    return [_hydrate_client(item) for item in rows]


def get_client(client_id: str) -> Optional[Dict]:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM clients WHERE id = :client_id"),
            {"client_id": client_id},
        ).first()
    return _hydrate_client(dict(row._mapping)) if row else None




def update_client(client_id: str, updates: Dict) -> bool:
    allowed_fields = {
        "name",
        "industry",
        "website",
        "logo_url",
        "billing_email",
        "billing_info",
        "settings",
        "platform_status",
        "google_ads_developer_token",
        "google_ads_client_id",
        "google_ads_client_secret",
        "google_ads_refresh_token",
        "google_ads_customer_id",
        "meta_app_id",
        "meta_app_secret",
        "meta_access_token",
        "meta_ad_account_id",
        "google_ads_configured",
        "meta_ads_configured",
        "agent_llm_settings",
        "image_generation_preferences",
        "default_budget",
    }
    values: Dict[str, Any] = {"client_id": client_id, "updated_at": datetime.utcnow().isoformat()}
    assignments = []
    for field in allowed_fields:
        if field not in updates:
            continue
        value = updates[field]
        if field in {"billing_info", "settings", "agent_llm_settings", "image_generation_preferences"}:
            value = json.dumps(value or {})
        elif field in {"google_ads_developer_token", "google_ads_client_id", "google_ads_client_secret", 
                      "google_ads_refresh_token", "google_ads_customer_id", "meta_app_id", "meta_app_secret", 
                      "meta_access_token", "meta_ad_account_id"}:
            value = encrypt(value) if value else ""
        values[field] = value
        assignments.append(f"{field} = :{field}")
    if not assignments:
        return False
    assignments.append("updated_at = :updated_at")
    with engine.begin() as conn:
        result = conn.execute(
            text(f"UPDATE clients SET {', '.join(assignments)} WHERE id = :client_id"),
            values,
        )
    return result.rowcount > 0

def delete_client(client_id: str) -> bool:
    with engine.begin() as conn:
        conn.execute(
            text("""
                DELETE FROM optimization_history
                WHERE campaign_id IN (
                    SELECT campaign_id FROM campaigns WHERE client_id = :client_id
                )
            """),
            {"client_id": client_id},
        )
        conn.execute(
            text("DELETE FROM api_keys WHERE client_id = :client_id"),
            {"client_id": client_id},
        )
        conn.execute(
            text("DELETE FROM campaigns WHERE client_id = :client_id"),
            {"client_id": client_id},
        )
        conn.execute(
            text("UPDATE users SET client_id = NULL, updated_at = :updated_at WHERE client_id = :client_id"),
            {"client_id": client_id, "updated_at": datetime.utcnow().isoformat()},
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
                (id, email, password_hash, full_name, role, client_id, stripe_customer_id, subscription_status, plan, created_at, updated_at)
                VALUES (:id, :email, :password_hash, :full_name, :role, :client_id, :stripe_customer_id, :subscription_status, :plan, :created_at, :updated_at)
            """),
            {
                "id": user_id,
                "email": user_data["email"],
                "password_hash": password_hash,
                "full_name": user_data.get("full_name", ""),
                "role": user_data["role"],
                "client_id": user_data.get("client_id"),
                "stripe_customer_id": user_data.get("stripe_customer_id"),
                "subscription_status": user_data.get("subscription_status", "trial"),
                "plan": user_data.get("plan"),
                "created_at": now,
                "updated_at": now,
            },
        )
    return user_id


async def update_user_role(user_id: str, role: str) -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE users
                SET role = :role, updated_at = :updated_at
                WHERE id = :user_id
            """),
            {"user_id": user_id, "role": role, "updated_at": datetime.utcnow().isoformat()},
        )
    return result.rowcount > 0


async def update_user_stripe_id(user_id: str, stripe_customer_id: str, subscription_status: str = "active", plan: str = "pro") -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE users
                SET stripe_customer_id = :stripe_customer_id,
                    subscription_status = :subscription_status,
                    plan = :plan,
                    updated_at = :updated_at
                WHERE id = :user_id
            """),
            {
                "user_id": user_id,
                "stripe_customer_id": stripe_customer_id,
                "subscription_status": subscription_status,
                "plan": plan,
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
    return result.rowcount > 0


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


async def update_client_credentials(client_id: str, creds: dict):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE clients
                SET google_ads_developer_token = :google_ads_developer_token,
                    google_ads_client_id = :google_ads_client_id,
                    google_ads_client_secret = :google_ads_client_secret,
                    google_ads_refresh_token = :google_ads_refresh_token,
                    google_ads_customer_id = :google_ads_customer_id,
                    meta_app_id = :meta_app_id,
                    meta_app_secret = :meta_app_secret,
                    meta_access_token = :meta_access_token,
                    meta_ad_account_id = :meta_ad_account_id,
                    google_ads_configured = :google_ads_configured,
                    meta_ads_configured = :meta_ads_configured,
                    updated_at = :updated_at
                WHERE id = :client_id
            """),
            {
                "client_id": client_id,
                "google_ads_developer_token": encrypt(creds.get("google_ads_developer_token")),
                "google_ads_client_id": encrypt(creds.get("google_ads_client_id")),
                "google_ads_client_secret": encrypt(creds.get("google_ads_client_secret")),
                "google_ads_refresh_token": encrypt(creds.get("google_ads_refresh_token")),
                "google_ads_customer_id": encrypt(creds.get("google_ads_customer_id")),
                "meta_app_id": encrypt(creds.get("meta_app_id")),
                "meta_app_secret": encrypt(creds.get("meta_app_secret")),
                "meta_access_token": encrypt(creds.get("meta_access_token")),
                "meta_ad_account_id": encrypt(creds.get("meta_ad_account_id")),
                "google_ads_configured": bool(creds.get("google_ads_developer_token")),
                "meta_ads_configured": bool(creds.get("meta_app_id")),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )


async def get_client_credentials(client_id: str) -> Optional[Dict]:
    """Return decrypted client credentials."""
    client = get_client(client_id)
    if not client:
        return None
    
    return {
        "google_ads_developer_token": decrypt(client.get("google_ads_developer_token", "")),
        "google_ads_client_id": decrypt(client.get("google_ads_client_id", "")),
        "google_ads_client_secret": decrypt(client.get("google_ads_client_secret", "")),
        "google_ads_refresh_token": decrypt(client.get("google_ads_refresh_token", "")),
        "google_ads_customer_id": decrypt(client.get("google_ads_customer_id", "")),
        "meta_app_id": decrypt(client.get("meta_app_id", "")),
        "meta_app_secret": decrypt(client.get("meta_app_secret", "")),
        "meta_access_token": decrypt(client.get("meta_access_token", "")),
        "meta_ad_account_id": decrypt(client.get("meta_ad_account_id", "")),
        "google_ads_configured": client.get("google_ads_configured", False),
        "meta_ads_configured": client.get("meta_ads_configured", False),
    }


async def get_credential_status(client_id: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT google_ads_configured, meta_ads_configured FROM clients WHERE id = :client_id"),
            {"client_id": client_id},
        ).first()
    if not row:
        return {"google_ads": False, "meta_ads": False}
    return {
        "google_ads": bool(row[0]),
        "meta_ads": bool(row[1]),
    }


def get_total_clients_sync() -> int:
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM clients"))
        return int(_scalar_or_none(result) or 0)


def get_active_campaigns_sync() -> int:
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM campaigns WHERE status = 'active'"))
        return int(_scalar_or_none(result) or 0)


def get_new_signups_sync(days: int = 30) -> int:
    if IS_SQLITE:
        query = text("SELECT COUNT(*) FROM users WHERE datetime(created_at) >= datetime('now', :modifier)")
        params = {"modifier": f"-{days} days"}
    else:
        query = text("SELECT COUNT(*) FROM users WHERE CAST(created_at AS timestamp) >= NOW() - (:days * INTERVAL '1 day')")
        params = {"days": days}
    with engine.begin() as conn:
        result = conn.execute(query, params)
        return int(_scalar_or_none(result) or 0)


def create_lead(lead_data: Dict[str, Any]) -> str:
    now = datetime.utcnow().isoformat()
    lead_id = lead_data.get("id", str(uuid.uuid4())[:8])
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO leads
                (id, name, email, website, company, source, status, notes, audit_id, proposal_id, follow_up_at, created_at, updated_at)
                VALUES (:id, :name, :email, :website, :company, :source, :status, :notes, :audit_id, :proposal_id, :follow_up_at, :created_at, :updated_at)
            """),
            {
                "id": lead_id,
                "name": lead_data.get("name", ""),
                "email": lead_data.get("email", ""),
                "website": lead_data.get("website", ""),
                "company": lead_data.get("company", ""),
                "source": lead_data.get("source", "audit"),
                "status": lead_data.get("status", AUDIT_STATUS_NEW),
                "notes": lead_data.get("notes", ""),
                "audit_id": lead_data.get("audit_id"),
                "proposal_id": lead_data.get("proposal_id"),
                "follow_up_at": lead_data.get("follow_up_at"),
                "created_at": now,
                "updated_at": now,
            },
        )
    return lead_id


def get_all_leads() -> List[Dict[str, Any]]:
    with engine.begin() as conn:
        return _rows(conn.execute(text("SELECT * FROM leads ORDER BY created_at DESC")))


def update_lead(lead_id: str, updates: Dict[str, Any]) -> bool:
    allowed = {"name", "email", "website", "company", "source", "status", "notes", "audit_id", "proposal_id", "follow_up_at"}
    assignments = []
    params: Dict[str, Any] = {"lead_id": lead_id, "updated_at": datetime.utcnow().isoformat()}
    for field in allowed:
        if field in updates:
            assignments.append(f"{field} = :{field}")
            params[field] = updates[field]
    if not assignments:
        return False
    assignments.append("updated_at = :updated_at")
    with engine.begin() as conn:
        result = conn.execute(text(f"UPDATE leads SET {', '.join(assignments)} WHERE id = :lead_id"), params)
    return result.rowcount > 0


def save_audit_report(audit_data: Dict[str, Any], lead_id: Optional[str] = None) -> str:
    now = datetime.utcnow().isoformat()
    audit_id = str(uuid.uuid4())[:8]
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO audit_reports (id, website, title, audit_json, lead_id, created_at, updated_at)
                VALUES (:id, :website, :title, :audit_json, :lead_id, :created_at, :updated_at)
            """),
            {
                "id": audit_id,
                "website": audit_data.get("url", ""),
                "title": audit_data.get("data", {}).get("title", ""),
                "audit_json": json.dumps(audit_data),
                "lead_id": lead_id,
                "created_at": now,
                "updated_at": now,
            },
        )
    return audit_id


def get_audit_report(audit_id: str) -> Optional[Dict[str, Any]]:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM audit_reports WHERE id = :audit_id"), {"audit_id": audit_id}).first()
    if not row:
        return None
    item = dict(row._mapping)
    item["audit_json"] = _json_load(item.get("audit_json"), {})
    return item


def save_proposal_record(proposal_data: Dict[str, Any], lead_id: Optional[str] = None, website: str = "") -> str:
    now = datetime.utcnow().isoformat()
    proposal_id = str(uuid.uuid4())[:8]
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO proposals (id, lead_id, website, proposal_json, created_at, updated_at)
                VALUES (:id, :lead_id, :website, :proposal_json, :created_at, :updated_at)
            """),
            {
                "id": proposal_id,
                "lead_id": lead_id,
                "website": website,
                "proposal_json": json.dumps(proposal_data),
                "created_at": now,
                "updated_at": now,
            },
        )
    return proposal_id


def get_proposal_record(proposal_id: str) -> Optional[Dict[str, Any]]:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM proposals WHERE id = :proposal_id"), {"proposal_id": proposal_id}).first()
    if not row:
        return None
    item = dict(row._mapping)
    item["proposal_json"] = _json_load(item.get("proposal_json"), {})
    return item


def log_publish_event(campaign_id: str, platform: str, attempted: bool, succeeded: bool, response_id: Optional[str] = None, error_message: Optional[str] = None, payload_summary: Optional[Dict[str, Any]] = None) -> str:
    event_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO publish_events (id, campaign_id, platform, attempted, succeeded, response_id, error_message, payload_summary, created_at)
                VALUES (:id, :campaign_id, :platform, :attempted, :succeeded, :response_id, :error_message, :payload_summary, :created_at)
            """),
            {
                "id": event_id,
                "campaign_id": campaign_id,
                "platform": platform,
                "attempted": 1 if attempted else 0,
                "succeeded": 1 if succeeded else 0,
                "response_id": response_id,
                "error_message": error_message,
                "payload_summary": json.dumps(payload_summary or {}),
                "created_at": now,
            },
        )
    return event_id


def get_publish_events(campaign_id: str) -> List[Dict[str, Any]]:
    with engine.begin() as conn:
        rows = _rows(
            conn.execute(
                text("SELECT * FROM publish_events WHERE campaign_id = :campaign_id ORDER BY created_at DESC"),
                {"campaign_id": campaign_id},
            )
        )
    for item in rows:
        item["payload_summary"] = _json_load(item.get("payload_summary"), {})
        item["attempted"] = bool(item.get("attempted"))
        item["succeeded"] = bool(item.get("succeeded"))
    return rows


def _ensure_report_templates_table(conn) -> None:
    template_id = "INTEGER PRIMARY KEY AUTOINCREMENT" if IS_SQLITE else "SERIAL PRIMARY KEY"
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS report_templates (
            id {template_id},
            name TEXT NOT NULL,
            description TEXT,
            sections TEXT NOT NULL DEFAULT '["kpi","recommendations"]',
            branding TEXT,
            custom_message TEXT,
            client_id TEXT,
            created_at TEXT NOT NULL
        )
    """))


def create_report_template(data: Dict[str, Any]) -> int:
    """Insert a new report template and return its auto-generated id."""
    now = datetime.utcnow().isoformat()
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO report_templates
                (name, description, sections, branding, custom_message, client_id, created_at)
                VALUES (:name, :description, :sections, :branding, :custom_message, :client_id, :created_at)
            """),
            {
                "name": data.get("name", "Unnamed Template"),
                "description": data.get("description", ""),
                "sections": json.dumps(data.get("sections", ["kpi", "recommendations"])),
                "branding": json.dumps(data.get("branding", {})),
                "custom_message": data.get("custom_message", ""),
                "client_id": data.get("client_id"),
                "created_at": now,
            },
        )
    return result.lastrowid


def get_report_template(template_id: int) -> Optional[Dict[str, Any]]:
    """Return a single report template by id, or None if not found."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM report_templates WHERE id = :id"),
            {"id": template_id},
        ).first()
    if not row:
        return None
    item = dict(row._mapping)
    item["sections"] = _json_load(item.get("sections"), ["kpi", "recommendations"])
    item["branding"] = _json_load(item.get("branding"), {})
    return item


def get_report_templates(client_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all report templates; filter by client_id when provided."""
    with engine.begin() as conn:
        if client_id:
            rows = _rows(
                conn.execute(
                    text("""
                        SELECT * FROM report_templates
                        WHERE client_id = :client_id OR client_id IS NULL
                        ORDER BY created_at DESC
                    """),
                    {"client_id": client_id},
                )
            )
        else:
            rows = _rows(
                conn.execute(text("SELECT * FROM report_templates ORDER BY created_at DESC"))
            )
    for item in rows:
        item["sections"] = _json_load(item.get("sections"), ["kpi", "recommendations"])
        item["branding"] = _json_load(item.get("branding"), {})
    return rows


def _ensure_onboarding_progress_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS onboarding_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            step INTEGER DEFAULT 1,
            data TEXT NOT NULL,
            status TEXT DEFAULT 'in_progress',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """))


def create_onboarding_session(user_id: str) -> str:
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO onboarding_progress (id, user_id, step, data, status, created_at, updated_at)
                VALUES (:id, :user_id, 1, '{}', 'in_progress', :created_at, :updated_at)
            """),
            {
                "id": session_id,
                "user_id": user_id,
                "created_at": now,
                "updated_at": now,
            }
        )
    return session_id


CREDENTIAL_KEYS = [
    "google_ads_developer_token", "google_ads_client_id", "google_ads_client_secret",
    "google_ads_refresh_token", "google_ads_customer_id", "meta_app_id",
    "meta_app_secret", "meta_access_token", "meta_ad_account_id"
]


def save_onboarding_session(session_id: str, step: int, data: dict) -> bool:
    now = datetime.utcnow().isoformat()
    # Encrypt credentials in data before saving
    data_to_save = data.copy()
    for key in CREDENTIAL_KEYS:
        if key in data_to_save and data_to_save[key]:
            data_to_save[key] = encrypt(data_to_save[key])

    with engine.begin() as conn:
        res = conn.execute(
            text("SELECT data FROM onboarding_progress WHERE id = :id"),
            {"id": session_id}
        ).first()
        if not res:
            return False
        existing_data = _json_load(res[0], {})
        existing_data.update(data_to_save)
        
        conn.execute(
            text("""
                UPDATE onboarding_progress
                SET step = :step, data = :data, updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": session_id,
                "step": step,
                "data": json.dumps(existing_data),
                "updated_at": now,
            }
        )
    return True


def get_latest_onboarding_session(user_id: str) -> Optional[dict]:
    with engine.begin() as conn:
        res = conn.execute(
            text("""
                SELECT id, user_id, step, data, status, created_at, updated_at
                FROM onboarding_progress
                WHERE user_id = :user_id AND status = 'in_progress'
                ORDER BY updated_at DESC LIMIT 1
            """),
            {"user_id": user_id}
        ).first()
        if not res:
            return None
        row = dict(res._mapping)
        saved_data = _json_load(row.get("data"), {})
        # Decrypt credentials on retrieval
        for key in CREDENTIAL_KEYS:
            if key in saved_data and saved_data[key]:
                saved_data[key] = decrypt(saved_data[key])
        row["data"] = saved_data
        return row


def update_onboarding_status(session_id: str, status: str) -> bool:
    now = datetime.utcnow().isoformat()
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE onboarding_progress
                SET status = :status, updated_at = :updated_at
                WHERE id = :id
            """),
            {"id": session_id, "status": status, "updated_at": now}
        )
        return result.rowcount > 0


def delete_onboarding_session(session_id: str) -> bool:
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM onboarding_progress WHERE id = :id"),
            {"id": session_id}
        )
        return result.rowcount > 0


init_db()

