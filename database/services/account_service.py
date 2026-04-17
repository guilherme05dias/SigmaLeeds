from database.schema import get_connection

def create_account(label: str, profile_path: str) -> int:
    """Cria conta. Retorna ID."""
    try:
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO whatsapp_accounts (label, profile_path) VALUES (?, ?)", (label, profile_path))
            return cursor.lastrowid
    except Exception:
        return -1
    finally:
        if 'conn' in locals(): conn.close()

def get_all_accounts() -> list:
    """Retorna todas as contas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM whatsapp_accounts")
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        if 'conn' in locals(): conn.close()

def update_account_status(account_id: int, status: str) -> None:
    """Status: connected | disconnected | connecting"""
    try:
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            if status == 'connected':
                cursor.execute("UPDATE whatsapp_accounts SET status = ?, last_connected = CURRENT_TIMESTAMP WHERE id = ?", (status, account_id))
            else:
                cursor.execute("UPDATE whatsapp_accounts SET status = ? WHERE id = ?", (status, account_id))
    except Exception:
        pass
    finally:
        if 'conn' in locals(): conn.close()

def get_active_account() -> dict:
    """Retorna a conta conectada atual, ou None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM whatsapp_accounts WHERE status = 'connected' LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        if 'conn' in locals(): conn.close()
