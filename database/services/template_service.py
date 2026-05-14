import json
import re
import random
import logging
from database.schema import get_connection

_log = logging.getLogger("zapmanager.template")

def apply_spintax(text: str) -> str:
    pattern = re.compile(r'\{([^{}]+\|[^{}]*)\}')
    while pattern.search(text):
        text = pattern.sub(lambda m: random.choice(m.group(1).split('|')), text)
    return text

def create_template(name: str, content: str, variables: list = None) -> int:
    try:
        conn = get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO templates (name, content, variables)
                VALUES (?, ?, ?)
            ''', (name, content, json.dumps(variables or [])))
            return cursor.lastrowid
    except Exception:
        _log.exception("Falha ao criar template")
        return -1
    finally:
        if 'conn' in locals(): conn.close()

def get_all_templates() -> list:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates")
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        _log.exception("Falha ao buscar templates")
        return []
    finally:
        if 'conn' in locals(): conn.close()

def update_template(template_id: int, name: str, content: str, variables: list = None) -> bool:
    try:
        conn = get_connection()
        with conn:
            conn.execute('''
                UPDATE templates SET name = ?, content = ?, variables = ?
                WHERE id = ?
            ''', (name, content, json.dumps(variables or []), template_id))
        return True
    except Exception:
        _log.exception("Falha ao atualizar template")
        return False
    finally:
        if 'conn' in locals(): conn.close()

def delete_template(template_id: int) -> bool:
    try:
        conn = get_connection()
        with conn:
            conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        return True
    except Exception:
        _log.exception("Falha ao deletar template")
        return False
    finally:
        if 'conn' in locals(): conn.close()

def render_template(template_content: str, contact_data: dict) -> str:
    text = apply_spintax(template_content)
    text = text.replace('{nome}', str(contact_data.get('name') or 'Cliente'))
    text = text.replace('{empresa}', str(contact_data.get('company') or ''))
    if 'extra_fields' in contact_data:
        try:
            extra = json.loads(contact_data['extra_fields'])
            for k, v in extra.items():
                text = text.replace('{' + k + '}', str(v))
        except Exception:
            _log.exception("Failed to render template")
    return text
