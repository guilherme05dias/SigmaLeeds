from database.schema import get_connection
import logging
import unicodedata

_log = logging.getLogger("zapmanager.blacklist")

def add_to_blacklist(phone: str, reason: str = "MANUAL") -> bool:
    """Adiciona número à blacklist. Retorna False se já existir."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("INSERT INTO blacklist (phone, reason) VALUES (?, ?)", (phone, reason))
        return True
    except Exception:
        _log.exception("Falha ao adicionar à blacklist")
        return False
    finally:
        conn.close()

def is_blacklisted(phone: str) -> bool:
    """Verifica se o número está na blacklist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM blacklist WHERE phone = ?", (phone,))
        return cursor.fetchone() is not None
    except Exception:
        _log.exception("Falha ao verificar blacklist")
        return False
    finally:
        conn.close()

def remove_from_blacklist(phone: str) -> bool:
    """Remove número da blacklist. Retorna False se não existir."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM blacklist WHERE phone = ?", (phone,))
        return cursor.rowcount > 0
    except Exception:
        _log.exception("Falha ao remover da blacklist")
        return False
    finally:
        conn.close()

def get_blacklist() -> list:
    """Retorna todos os números na blacklist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM blacklist")
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        _log.exception("Falha ao buscar blacklist")
        return []
    finally:
        conn.close()

def detect_optout_keywords(message: str) -> bool:
    """Verifica se a mensagem contém palavras-chave de descadastro."""
    keywords = [
        'sair', 'parar', 'remover', 'descadastrar',
        'nao quero', 'cancelar', 'bloquear',
        'stop', 'unsubscribe',
    ]
    msg_clean = unicodedata.normalize('NFKD', message.lower().strip())
    msg_clean = msg_clean.encode('ASCII', 'ignore').decode()
    return any(kw in msg_clean for kw in keywords)
