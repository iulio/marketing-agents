# scripts/migrate_add_platform_status.py
from sqlalchemy import text

from app.storage import IS_SQLITE, engine


def migrate():
    with engine.begin() as conn:
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
            print("Added platform_status column")
        else:
            print("platform_status column already exists")


if __name__ == "__main__":
    migrate()