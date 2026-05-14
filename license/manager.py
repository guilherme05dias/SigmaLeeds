import os
from license.trial import get_trial_status
from license.validator import validate_key
from license.hardware import get_hardware_id

LICENSE_FILE = os.path.join(os.environ.get('APPDATA', ''), 'ZapManagerPro', 'license.dat')

PLAN_LIMITS = {
    "starter": {
        "max_accounts": 1,
        "max_dispatches_day": 300,
        "templates": 5,
        "scheduling": False,
        "multi_attachment": False,
        "export_xlsx": False
    },
    "pro": {
        "max_accounts": 3,
        "max_dispatches_day": 1000,
        "templates": 999999,
        "scheduling": True,
        "multi_attachment": True,
        "export_xlsx": True
    },
    "agency": {
        "max_accounts": 999,
        "max_dispatches_day": 999999,
        "templates": 999999,
        "scheduling": True,
        "multi_attachment": True,
        "export_xlsx": True
    }
}

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
    Retorna 300 (Starter) em caso de falha de leitura da licença.
    """
    try:
        info = check_license()
        plan = info.get("plan", "").lower() if info.get("plan") else "starter"
        limits = {
            "starter": 300,
            "pro": 1000,
            "agency": 999999,
        }
        return limits.get(plan, 300)
    except Exception:
        return 300  # fail safe: restringe se licença ilegível

