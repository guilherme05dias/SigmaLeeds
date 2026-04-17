from database.schema import get_connection

def add_to_blacklist(phone: str, reason: str = "MANUAL") -> bool:
    """Adiciona número à blacklist. Retorna False se já existir."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blacklist (phone, reason) VALUES (?, ?)", (phone, reason))
            return True
    except Exception:
        return False
    finally:
        conn.close()

def is_blacklisted(phone: str) -> bool:
    """Verifica se número está na blacklist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM blacklist WHERE phone = ?", (phone,))
        return cursor.fetchone() is not None
    except Exception:
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
        return []
    finally:
        conn.close()

def remove_from_blacklist(phone: str) -> bool:
    """Remove número da blacklist. Retorna False se não existir."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blacklist WHERE phone = ?", (phone,))
            return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        conn.close()

def detect_optout_keywords(message: str) -> bool:
    """Detecta palavras de opt-out em mensagem recebida."""
    keywords = ["sair", "parar", "stop", "cancelar", "remover", 
                "nao quero", "não quero", "descadastrar", 
                "descadastre", "pare", "chega"]
    
    try:
        import unicodedata
        msg_normalized = ''.join(c for c in unicodedata.normalize('NFD', message) if unicodedata.category(c) != 'Mn')
        msg_lower = msg_normalized.lower()
        
        for word in keywords:
            word_norm = ''.join(c for c in unicodedata.normalize('NFD', word) if unicodedata.category(c) != 'Mn').lower()
            if word_norm in msg_lower:
                return True
    except Exception:
        pass
    return False
