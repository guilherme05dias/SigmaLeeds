import json
import re
from database.schema import get_connection

def create_template(name: str, content: str) -> int:
    """Cria template, detecta variáveis {var} automaticamente e salva. Retorna ID."""
    try:
        variables = list(set(re.findall(r'\{([^}]+)\}', content)))
        
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO templates (name, content, variables)
                VALUES (?, ?, ?)
            ''', (name, content, json.dumps(variables)))
            return cursor.lastrowid
    except Exception:
        return -1
    finally:
        if 'conn' in locals():
            conn.close()

def get_all_templates() -> list:
    """Retorna todos os templates."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates")
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        if 'conn' in locals(): conn.close()

def get_template(template_id: int) -> dict:
    """Retorna template por ID."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}
    except Exception:
        return {}
    finally:
        if 'conn' in locals(): conn.close()

def update_template(template_id: int, name: str, content: str) -> bool:
    try:
        variables = list(set(re.findall(r'\{([^}]+)\}', content)))
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE templates SET name = ?, content = ?, variables = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, content, json.dumps(variables), template_id))
            return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        if 'conn' in locals(): conn.close()

def delete_template(template_id: int) -> bool:
    try:
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        if 'conn' in locals(): conn.close()

def render_template(content: str, contact: dict) -> str:
    import json
    result = content
    fields = {
        'nome':    str(contact.get('name') or ''),
        'empresa': str(contact.get('company') or ''),
        'numero':  str(contact.get('phone') or ''),
    }
    try:
        extra = json.loads(contact.get('extra_fields') or '{}')
        fields.update({k.lower(): str(v) for k, v in extra.items()})
    except Exception:
        pass
    for key, value in fields.items():
        result = result.replace('{' + key + '}', value)
    return result
