import sqlite3
import os
import logging
from pathlib import Path

# DB_PATH resolves to user data directory (AppData on Windows)
_APP_NAME = "ZapManagerPro"
_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    _APP_NAME
)
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, "zapmanager.db")

_log = logging.getLogger("zapmanager.schema")

# Lista de migrations sequenciais.
MIGRATIONS = [
    # v0 — Tabela de campanhas
    """
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        message_template TEXT DEFAULT '',
        attachment_path TEXT DEFAULT NULL,
        account_id INTEGER,
        total_contacts INTEGER DEFAULT 0,
        sent INTEGER DEFAULT 0,
        failed INTEGER DEFAULT 0,
        invalid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'idle',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        started_at TEXT DEFAULT NULL,
        finished_at TEXT DEFAULT NULL
    )
    """,
    # v1 — Tabela de contatos com ON DELETE CASCADE
    """
    CREATE TABLE IF NOT EXISTS campaign_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL
            REFERENCES campaigns(id) ON DELETE CASCADE,
        name TEXT DEFAULT '',
        phone TEXT NOT NULL,
        company TEXT DEFAULT '',
        extra_fields TEXT DEFAULT '{}',
        status TEXT DEFAULT 'PENDENTE',
        error_message TEXT DEFAULT NULL,
        observation TEXT DEFAULT NULL,
        attachment_path TEXT DEFAULT NULL,
        sent_at TEXT DEFAULT NULL,
        processed_at TEXT DEFAULT NULL
    )
    """,
    # v2 — Índice único para evitar duplicados (M4)
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_unique
    ON campaign_contacts(campaign_id, phone)
    """,
    # v3 — Tabela de templates
    """
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
    """,
    # v4 — Tabela de blacklist
    """
    CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL UNIQUE,
        reason TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
    """,
    # v5 — Índices de performance
    """
    CREATE INDEX IF NOT EXISTS idx_contacts_campaign_status
    ON campaign_contacts(campaign_id, status)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_contacts_phone
    ON campaign_contacts(phone)
    """,
    # v6
    """CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )""",
    # v7
    """CREATE TABLE IF NOT EXISTS whatsapp_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        profile_path TEXT NOT NULL,
        status TEXT DEFAULT 'disconnected',
        last_connected TEXT
    )""",
    # v8
    """ALTER TABLE templates ADD COLUMN variables TEXT DEFAULT '[]'"""
]

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    conn = get_connection()
    try:
        # Tabela de controle de versão
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now','localtime')),
                description TEXT DEFAULT ''
            )
        """)
        conn.commit()

        # Versão atual do banco
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        current_version = row[0] if row[0] is not None else -1

        # Aplicar apenas as migrations novas
        applied = 0
        for i, sql in enumerate(MIGRATIONS):
            if i <= current_version:
                continue  # já aplicada
            try:
                try:
                    conn.execute(sql.strip())
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise

                conn.execute(
                    "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                    (i, sql.strip()[:80])
                )
                conn.commit()
                applied += 1
                _log.info(f"Migration {i} aplicada com sucesso")
            except Exception as e:
                conn.rollback()
                _log.exception(f"Falha na migration {i}")
                raise RuntimeError(f"Migration {i} falhou: {e}") from e

        if applied > 0:
            _log.info(f"Banco atualizado: {applied} migration(s) aplicada(s)")
        else:
            _log.debug("Banco já está na versão mais recente")

    except Exception:
        _log.exception("Falha crítica em init_db")
        raise
    finally:
        conn.close()
