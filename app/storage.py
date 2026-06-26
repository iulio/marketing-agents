# app/storage.py
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'marketing_agents.db')

def get_db_connection():
    """Get a connection to the SQLite database, ensuring the directory exists."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Optimization history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS optimization_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_description TEXT,
            kpi_before TEXT,
            kpi_after TEXT,
            status TEXT DEFAULT 'completed'
        )
    ''')
    
    # Campaigns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id TEXT PRIMARY KEY,
            client_id TEXT,
            created_by TEXT,
            state TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Clients table
    cursor.execute('''
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
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL CHECK(role IN ('admin', 'client_manager', 'client_viewer')),
            client_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        )
    ''')
    
    # API Keys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            last_used TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# ================================================================
# CAMPAIGN FUNCTIONS
# ================================================================

def save_campaign_state(campaign_id: str, state: Dict, status: str, client_id: str = None, created_by: str = None):
    """Persist the full campaign state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    existing = cursor.execute('SELECT campaign_id FROM campaigns WHERE campaign_id = ?', (campaign_id,)).fetchone()
    if existing:
        cursor.execute('''
            UPDATE campaigns
            SET state = ?, status = ?, updated_at = ?, client_id = ?
            WHERE campaign_id = ?
        ''', (json.dumps(state), status, now, client_id, campaign_id))
    else:
        cursor.execute('''
            INSERT INTO campaigns (campaign_id, client_id, created_by, state, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (campaign_id, client_id, created_by, json.dumps(state), status, now, now))
    conn.commit()
    conn.close()

def load_campaign_state(campaign_id: str) -> Optional[Dict]:
    """Load a campaign state from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT state FROM campaigns WHERE campaign_id = ?', (campaign_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row['state'])
    return None

def get_all_campaigns() -> List[Dict]:
    """Get all campaigns with their state and metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM campaigns ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item['state'] = json.loads(item['state'])
        result.append(item)
    return result

def get_client_campaigns(client_id: str) -> List[Dict]:
    """Get all campaigns for a specific client."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM campaigns WHERE client_id = ? ORDER BY created_at DESC', (client_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item['state'] = json.loads(item['state'])
        result.append(item)
    return result

# ================================================================
# OPTIMIZATION HISTORY FUNCTIONS
# ================================================================

def save_optimization_action(campaign_id: str, action_type: str, action_description: str, 
                             kpi_before: Dict = None, kpi_after: Dict = None, 
                             status: str = 'completed'):
    """Insert an optimization action into the history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO optimization_history 
        (campaign_id, timestamp, action_type, action_description, kpi_before, kpi_after, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        campaign_id,
        datetime.now().isoformat(),
        action_type,
        action_description,
        json.dumps(kpi_before) if kpi_before else None,
        json.dumps(kpi_after) if kpi_after else None,
        status
    ))
    conn.commit()
    conn.close()

def get_optimization_history(campaign_id: str, limit: int = 50) -> List[Dict]:
    """Retrieve optimization history for a campaign."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM optimization_history
        WHERE campaign_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (campaign_id, limit))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        if item['kpi_before']:
            item['kpi_before'] = json.loads(item['kpi_before'])
        if item['kpi_after']:
            item['kpi_after'] = json.loads(item['kpi_after'])
        result.append(item)
    return result

# ================================================================
# CLIENT FUNCTIONS
# ================================================================

def create_client(client_data: Dict) -> str:
    """Create a new client."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    client_id = client_data.get('id', str(uuid.uuid4())[:8])
    cursor.execute('''
        INSERT INTO clients (id, name, industry, website, logo_url, billing_email, billing_info, settings, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        client_id,
        client_data.get('name'),
        client_data.get('industry', ''),
        client_data.get('website', ''),
        client_data.get('logo_url', ''),
        client_data.get('billing_email', ''),
        json.dumps(client_data.get('billing_info', {})),
        json.dumps(client_data.get('settings', {})),
        now,
        now
    ))
    conn.commit()
    conn.close()
    return client_id

def get_all_clients() -> List[Dict]:
    """Get all clients."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item['billing_info'] = json.loads(item['billing_info']) if item['billing_info'] else {}
        item['settings'] = json.loads(item['settings']) if item['settings'] else {}
        result.append(item)
    return result

def get_client(client_id: str) -> Optional[Dict]:
    """Get a single client by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        item = dict(row)
        item['billing_info'] = json.loads(item['billing_info']) if item['billing_info'] else {}
        item['settings'] = json.loads(item['settings']) if item['settings'] else {}
        return item
    return None

# ================================================================
# USER FUNCTIONS
# ================================================================

def create_user(user_data: Dict) -> str:
    """Create a new user."""
    import hashlib
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    user_id = user_data.get('id', str(uuid.uuid4())[:8])
    
    password_hash = hashlib.sha256(user_data['password'].encode()).hexdigest()
    
    cursor.execute('''
        INSERT INTO users (id, email, password_hash, full_name, role, client_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        user_data['email'],
        password_hash,
        user_data.get('full_name', ''),
        user_data['role'],
        user_data.get('client_id'),
        now,
        now
    ))
    conn.commit()
    conn.close()
    return user_id

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_users_by_client(client_id: str) -> List[Dict]:
    """Get all users for a specific client."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE client_id = ? ORDER BY created_at DESC', (client_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_users() -> List[Dict]:
    """Get all users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def verify_user(email: str, password: str) -> Optional[Dict]:
    """Verify user credentials."""
    import hashlib
    user = get_user_by_email(email)
    if not user:
        return None
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user['password_hash'] == password_hash:
        return user
    return None

# Initialize DB
init_db()