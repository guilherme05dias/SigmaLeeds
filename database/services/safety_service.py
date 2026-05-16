"""
Logica de seguranca anti-banimento WhatsApp.

Dois mecanismos:
  1. Warm-up: limite escalonado por dia desde a 1a conexao do WhatsApp.
  2. Safety daily limit: limite configuravel pelo operador (default 300).

Ambos NAO bloqueiam — pausam a campanha e exigem que o operador clique
"Aceito o risco" para continuar. O aceite e registrado em safety_consents
e vale ate o fim do dia.
"""
import logging
from datetime import datetime, date
from database.schema import get_connection
from database.services.config_service import get_config, set_config

_log = logging.getLogger("zapmanager.safety")

WARMUP_SCHEDULE = [
    (1, 20),
    (2, 40),
    (3, 80),
    (7, 150),
    (14, 250),
]
DEFAULT_FULL_LIMIT = 300  # apos warmup termina aqui (sobrescrito por safety_limit)

CONSENT_WARMUP = "warmup"
CONSENT_DAILY = "daily"


def record_first_connection_if_missing() -> None:
    """Chamado quando o motor Node reporta 'ready' pela primeira vez."""
    existing = get_config("whatsapp_first_connection_at", None)
    if existing:
        return
    set_config("whatsapp_first_connection_at", datetime.now().isoformat(timespec="seconds"))


def get_warmup_state() -> dict:
    """
    Retorna o estado do warm-up:
        {
            "enabled": bool,
            "active": bool,           # True se ainda esta na fase de aquecimento
            "day_number": int,        # 1, 2, 3, ...
            "limit_today": int,       # limite recomendado hoje
            "final_limit": int,       # limite quando termina o warmup
            "days_until_full": int,   # 0 quando ja saiu do warmup
        }
    """
    enabled = str(get_config("warmup_enabled", "1")) == "1"
    final_limit = _get_safety_daily_limit()
    if not enabled:
        return {
            "enabled": False,
            "active": False,
            "day_number": 0,
            "limit_today": final_limit,
            "final_limit": final_limit,
            "days_until_full": 0,
        }

    first_conn = get_config("whatsapp_first_connection_at", None)
    if not first_conn:
        # ainda nao conectou — sem warm-up ate primeira conexao
        return {
            "enabled": True,
            "active": False,
            "day_number": 0,
            "limit_today": final_limit,
            "final_limit": final_limit,
            "days_until_full": 0,
        }

    try:
        first_dt = datetime.fromisoformat(first_conn)
    except Exception:
        return {
            "enabled": True,
            "active": False,
            "day_number": 0,
            "limit_today": final_limit,
            "final_limit": final_limit,
            "days_until_full": 0,
        }

    days_since = (date.today() - first_dt.date()).days + 1   # dia 1 = dia da 1a conexao
    limit_today = _limit_for_day(days_since, final_limit)
    active = limit_today < final_limit
    return {
        "enabled": True,
        "active": active,
        "day_number": days_since,
        "limit_today": limit_today,
        "final_limit": final_limit,
        "days_until_full": max(0, WARMUP_SCHEDULE[-1][0] + 1 - days_since) if active else 0,
    }


def _limit_for_day(day: int, final_limit: int) -> int:
    last_day = WARMUP_SCHEDULE[-1][0]
    if day > last_day:
        return final_limit
    for cap_day, cap_limit in WARMUP_SCHEDULE:
        if day <= cap_day:
            return min(cap_limit, final_limit)
    return final_limit


def _get_safety_daily_limit() -> int:
    try:
        val = get_config("daily_safety_limit", DEFAULT_FULL_LIMIT)
        return int(val) if val else DEFAULT_FULL_LIMIT
    except Exception:
        return DEFAULT_FULL_LIMIT


def has_consent_today(consent_type: str) -> bool:
    today = date.today().isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM safety_consents WHERE consent_date = ? AND consent_type = ? LIMIT 1",
            (today, consent_type),
        ).fetchone()
        return row is not None
    except Exception:
        _log.exception("Falha ao consultar consent")
        return False
    finally:
        conn.close()


def register_consent(consent_type: str, limit_value: int, sent_count: int) -> None:
    today = date.today().isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO safety_consents (consent_date, consent_type, limit_value, sent_count) VALUES (?, ?, ?, ?)",
                (today, consent_type, limit_value, sent_count),
            )
    except Exception:
        _log.exception("Falha ao registrar consent")
    finally:
        conn.close()


def get_consents_history(limit: int = 50) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT consent_date, consent_type, limit_value, sent_count, accepted_at "
            "FROM safety_consents ORDER BY accepted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        _log.exception("Falha ao ler historico de consents")
        return []
    finally:
        conn.close()


def get_effective_limit_today() -> dict:
    """
    Combina warm-up + safety limit em um unico veredito.
    Retorna o limite EFETIVO de hoje (o menor dos dois).
    """
    warmup = get_warmup_state()
    safety = _get_safety_daily_limit()
    if warmup["active"]:
        # Durante warmup, o limite escalonado prevalece sobre o safety_limit
        effective = warmup["limit_today"]
        limit_type = CONSENT_WARMUP
    else:
        effective = safety
        limit_type = CONSENT_DAILY
    return {
        "limit": effective,
        "type": limit_type,
        "warmup": warmup,
        "safety_daily": safety,
    }
