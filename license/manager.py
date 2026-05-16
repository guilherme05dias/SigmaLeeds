import os
from license.trial import get_trial_status
from license.validator import validate_key
from license.hardware import get_hardware_id

LICENSE_FILE = os.path.join(os.environ.get('APPDATA', ''), 'ZapManagerPro', 'license.dat')

# A partir de v4.2.5 o produto e single-tier (plano unico = "pro").
# Nao ha limite de mensagens enforced pela licenca. O usuario configura
# um daily_safety_limit em system_config para receber AVISO (nao bloqueio)
# quando o volume diario aumenta o risco de banimento pelo WhatsApp.
SINGLE_PLAN = {
    "max_accounts": 999,
    "max_dispatches_day": 999999,   # nao enforced; soft limit fica em system_config.daily_safety_limit
    "templates": 999999,
    "scheduling": True,
    "multi_attachment": True,
    "export_xlsx": True
}
PLAN_LIMITS = {
    # Mantemos chaves antigas apontando para SINGLE_PLAN para compatibilidade
    # com licencas existentes que ainda tem plan="starter"/"agency" no payload.
    "starter": SINGLE_PLAN,
    "pro": SINGLE_PLAN,
    "agency": SINGLE_PLAN,
}

DEFAULT_DAILY_SAFETY_LIMIT = 500   # mensagens por dia antes de avisar risco de banimento

def get_daily_safety_limit() -> int:
    """Le limite diario de seguranca configurado pelo operador (system_config),
    ou retorna o default. Se 0, desativa o aviso."""
    try:
        from database.services.config_service import get_config
        val = get_config("daily_safety_limit", DEFAULT_DAILY_SAFETY_LIMIT)
        return int(val)
    except Exception:
        return DEFAULT_DAILY_SAFETY_LIMIT

def activate_license(key_string: str) -> dict:
    try:
        val = validate_key(key_string)
        if not val["valid"]:
            return val
            
        os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
        with open(LICENSE_FILE, "w") as f:
            f.write(key_string)
            
        return {"valid": True, "message": "Ativação concluída com sucesso"}
    except Exception as e:
        return {"valid": False, "error_message": "Erro ao salvar licença"}

def check_license() -> dict:
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, "r") as f:
                key_string = f.read().strip()
                
            val = validate_key(key_string)
            if val["valid"]:
                return {
                    "status": "active",
                    "plan": val["plan"],
                    "days_remaining": val["days_remaining"],
                    "expires_at": val.get("expires_at"),
                    "limits": PLAN_LIMITS.get(val["plan"], PLAN_LIMITS["starter"]),
                    "message": f"Licença ativa. Plano: {val['plan'].upper()}"
                }
            else:
                return {
                    "status": "invalid",
                    "plan": None,
                    "days_remaining": 0,
                    "limits": PLAN_LIMITS["starter"],
                    "message": val["error_message"]
                }
                
        # Fallback to trial
        trial = get_trial_status()
        if trial["active"]:
            return {
                "status": "trial",
                "plan": "trial",
                "days_remaining": trial["days_remaining"],
                "trial_days": 7, # TRIAL_DAYS from trial.py
                "limits": PLAN_LIMITS["starter"],
                "message": f"Trial ativo ({trial['days_remaining']} dias restantes)"
            }
        else:
            return {
                "status": "expired",
                "plan": None,
                "days_remaining": 0,
                "limits": PLAN_LIMITS["starter"],
                "message": "Trial expirado"
            }
    except Exception:
        return {
            "status": "invalid",
            "plan": None,
            "days_remaining": 0,
            "limits": PLAN_LIMITS["starter"],
            "message": "Erro de verificação"
        }

def get_current_plan_limits() -> dict:
    status = check_license()
    return status.get("limits", PLAN_LIMITS["starter"])

def get_daily_limit() -> int:
    """
    Retorna o máximo de mensagens permitidas por dia para a licença atual.
    Retorna 999999 se nenhum limite se aplica (plano Agency).
    DEPRECATED desde v4.2.5 — single-tier nao tem limite por licenca.
    Mantida para compatibilidade com callers antigos; retorna 999999
    (sem enforcement). O aviso de seguranca usa get_daily_safety_limit().
    """
    return 999999

