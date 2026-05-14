from datetime import datetime, time, timedelta
import re


DEFAULT_SEND_WINDOW = {
    "enabled": False,
    "start": "08:00",
    "end": "20:00",
    "days": [0, 1, 2, 3, 4],
}


def normalize_send_window_config(window: dict | None) -> dict:
    """Valida e normaliza a configuração da janela de envio."""
    raw = dict(DEFAULT_SEND_WINDOW)
    if isinstance(window, dict):
        raw.update(window)

    enabled = bool(raw.get("enabled", False))
    start = _validate_hhmm(raw.get("start", DEFAULT_SEND_WINDOW["start"]), "start")
    end = _validate_hhmm(raw.get("end", DEFAULT_SEND_WINDOW["end"]), "end")
    days = raw.get("days", DEFAULT_SEND_WINDOW["days"])

    if not isinstance(days, list):
        raise ValueError("days deve ser uma lista")
    normalized_days = sorted({int(day) for day in days})
    if any(day < 0 or day > 6 for day in normalized_days):
        raise ValueError("days deve conter valores entre 0 e 6")
    if enabled and not normalized_days:
        raise ValueError("days não pode ficar vazio quando a janela está ativa")
    if start == end:
        raise ValueError("start e end não podem ser iguais")

    return {
        "enabled": enabled,
        "start": start,
        "end": end,
        "days": normalized_days,
    }


def is_within_window(now: datetime, window: dict) -> bool:
    """Retorna True se now está dentro da janela configurada ou se enabled=False."""
    config = normalize_send_window_config(window)
    if not config["enabled"]:
        return True

    start = _parse_time(config["start"])
    end = _parse_time(config["end"])
    current = now.time()
    weekday = now.weekday()
    previous_weekday = (weekday - 1) % 7
    days = set(config["days"])

    if start < end:
        return weekday in days and start <= current < end

    if current >= start:
        return weekday in days
    if current < end:
        return previous_weekday in days
    return False


def seconds_until_window_opens(now: datetime, window: dict) -> int:
    """Retorna segundos até a próxima abertura da janela. 0 se já está dentro."""
    config = normalize_send_window_config(window)
    if not config["enabled"] or is_within_window(now, config):
        return 0

    start = _parse_time(config["start"])
    days = set(config["days"])

    for offset in range(8):
        candidate_date = now.date() + timedelta(days=offset)
        if candidate_date.weekday() not in days:
            continue
        candidate = datetime.combine(candidate_date, start)
        if candidate > now:
            return max(0, int((candidate - now).total_seconds()))

    return 0


def _validate_hhmm(value, field: str) -> str:
    text = str(value)
    if not re.fullmatch(r"\d{2}:\d{2}", text):
        raise ValueError(f"{field} deve estar no formato HH:MM")
    parsed = _parse_time(text)
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def _parse_time(value: str) -> time:
    hour, minute = map(int, value.split(":"))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("horário inválido")
    return time(hour=hour, minute=minute)
