import json
from database.schema import get_connection

def get_config(key: str, default=None):
    """Lê configuração. Retorna default se não existir."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return default
            
        val = row["value"]
        try:
            return json.loads(val)
        except:
            return val
    except Exception:
        return default
    finally:
        if 'conn' in locals(): conn.close()

def set_config(key: str, value) -> None:
    """Salva configuração. Serializa automaticamente dict/list para JSON."""
    try:
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value)
        else:
            val_str = str(value)
            
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_config (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            ''', (key, val_str))
    except Exception:
        pass
    finally:
        if 'conn' in locals(): conn.close()

def get_all_configs() -> dict:
    """Retorna todas as configurações como dicionário."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_config")
        results = {}
        for row in cursor.fetchall():
            val = row["value"]
            try:
                results[row["key"]] = json.loads(val)
            except:
                results[row["key"]] = val
        return results
    except Exception:
        return {}
    finally:
        if 'conn' in locals(): conn.close()
