#!/usr/bin/env python3
"""
Migration script to add new fields to the clients table.
This script adds the following columns to the clients table:
- google_ads_configured (Boolean)
- meta_ads_configured (Boolean)
- agent_llm_settings (JSON)
- image_generation_preferences (JSON)
- default_budget (Float)
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import storage module which handles database connections
from app.storage import engine, IS_SQLITE

def run_migration():
    """Run the migration to add new fields to the clients table."""
    with engine.begin() as conn:
        if IS_SQLITE:
            # SQLite requires a different approach for adding columns
            print("Adding columns to clients table (SQLite)...")
            
            # Add google_ads_configured column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN google_ads_configured INTEGER DEFAULT 0")
                print("Added google_ads_configured column")
            except Exception as e:
                print(f"Column google_ads_configured may already exist: {e}")
            
            # Add meta_ads_configured column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN meta_ads_configured INTEGER DEFAULT 0")
                print("Added meta_ads_configured column")
            except Exception as e:
                print(f"Column meta_ads_configured may already exist: {e}")
            
            # Add agent_llm_settings column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN agent_llm_settings TEXT")
                print("Added agent_llm_settings column")
            except Exception as e:
                print(f"Column agent_llm_settings may already exist: {e}")
            
            # Add image_generation_preferences column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN image_generation_preferences TEXT")
                print("Added image_generation_preferences column")
            except Exception as e:
                print(f"Column image_generation_preferences may already exist: {e}")
            
            # Add default_budget column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN default_budget REAL")
                print("Added default_budget column")
            except Exception as e:
                print(f"Column default_budget may already exist: {e}")
                
        else:
            # PostgreSQL/MySQL approach
            print("Adding columns to clients table (PostgreSQL/MySQL)...")
            
            # Add google_ads_configured column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN google_ads_configured BOOLEAN DEFAULT FALSE")
                print("Added google_ads_configured column")
            except Exception as e:
                print(f"Column google_ads_configured may already exist: {e}")
            
            # Add meta_ads_configured column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN meta_ads_configured BOOLEAN DEFAULT FALSE")
                print("Added meta_ads_configured column")
            except Exception as e:
                print(f"Column meta_ads_configured may already exist: {e}")
            
            # Add agent_llm_settings column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN agent_llm_settings JSON")
                print("Added agent_llm_settings column")
            except Exception as e:
                print(f"Column agent_llm_settings may already exist: {e}")
            
            # Add image_generation_preferences column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN image_generation_preferences JSON")
                print("Added image_generation_preferences column")
            except Exception as e:
                print(f"Column image_generation_preferences may already exist: {e}")
            
            # Add default_budget column
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN default_budget DOUBLE PRECISION")
                print("Added default_budget column")
            except Exception as e:
                print(f"Column default_budget may already exist: {e}")
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()