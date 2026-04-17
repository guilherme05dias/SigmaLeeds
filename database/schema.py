import sqlite3
import os

DB_DIR = os.path.join(os.getcwd(), 'data')
DB_PATH = os.path.join(DB_DIR, 'app.db')

def get_connection():
    if os.environ.get('ZAP_DB_MEMORY') == '1':
        db_path = os.path.join(DB_DIR, 'test_app.db')
        conn = sqlite3.connect(db_path)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = get_connection()
    try:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS campaigns (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  message_template TEXT NOT NULL,
                  attachment_path TEXT,
                  account_id INTEGER,
                  status TEXT DEFAULT 'draft',
                  total_contacts INTEGER DEFAULT 0,
                  sent INTEGER DEFAULT 0,
                  failed INTEGER DEFAULT 0,
                  invalid INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  started_at TIMESTAMP,
                  finished_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS campaign_contacts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
                  name TEXT,
                  phone TEXT NOT NULL,
                  company TEXT,
                  extra_fields TEXT,
                  status TEXT DEFAULT 'PENDENTE',
                  sent_at TIMESTAMP,
                  error_message TEXT,
                  observation TEXT
                );

                CREATE TABLE IF NOT EXISTS whatsapp_accounts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  label TEXT NOT NULL,
                  phone TEXT,
                  profile_path TEXT NOT NULL,
                  status TEXT DEFAULT 'disconnected',
                  last_connected TIMESTAMP,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS templates (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  content TEXT NOT NULL,
                  variables TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS blacklist (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone TEXT NOT NULL UNIQUE,
                  reason TEXT,
                  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS system_config (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
    except Exception as e:
        pass
    finally:
        conn.close()
