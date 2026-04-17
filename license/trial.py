import os
import winreg
import sqlite3
import time

TRIAL_DAYS = 7
APP_DATA_DIR = os.path.join(os.environ.get('APPDATA', ''), 'ZapManagerPro')
HIDDEN_FILE_PATH = os.path.join(APP_DATA_DIR, '.sys')
DB_PATH = os.path.join(APP_DATA_DIR, 'data', 'app.db')

def _get_reg_date() -> int:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\ZapManagerPro", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "InstallDate")
        winreg.CloseKey(key)
        return int(value)
    except Exception:
        return 0

def _set_reg_date(timestamp: int):
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\ZapManagerPro")
        winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, str(timestamp))
        winreg.CloseKey(key)
    except Exception:
        pass

def _get_hidden_file_date() -> int:
    try:
        if os.path.exists(HIDDEN_FILE_PATH):
            with open(HIDDEN_FILE_PATH, 'r') as f:
                return int(f.read().strip())
    except Exception:
        pass
    return 0

def _set_hidden_file_date(timestamp: int):
    try:
        os.makedirs(os.path.dirname(HIDDEN_FILE_PATH), exist_ok=True)
        if os.path.exists(HIDDEN_FILE_PATH):
            os.system(f'attrib -h "{HIDDEN_FILE_PATH}"')
        with open(HIDDEN_FILE_PATH, 'w') as f:
            f.write(str(timestamp))
        os.system(f'attrib +h "{HIDDEN_FILE_PATH}"')
    except Exception:
        pass

def _get_db_date() -> int:
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT value FROM system_config WHERE key='trial_start'")
            res = c.fetchone()
            conn.close()
            if res:
                return int(res[0])
    except Exception:
        pass
    return 0

def _set_db_date(timestamp: int):
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('trial_start', ?)", (str(timestamp),))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_trial_status() -> dict:
    try:
        dates = [
            _get_reg_date(),
            _get_hidden_file_date(),
            _get_db_date()
        ]
        
        valid_dates = [d for d in dates if d > 0]
        
        if not valid_dates:
            # Nunca instalado, criar registros de primeiro uso
            now = int(time.time())
            _set_reg_date(now)
            _set_hidden_file_date(now)
            _set_db_date(now)
            install_date = now
        else:
            # Usa o registro mais antigo, anti-burla
            install_date = min(valid_dates)
            
            # Restaura nos locais possíveis de exclusão
            if _get_reg_date() == 0: _set_reg_date(install_date)
            if _get_hidden_file_date() == 0: _set_hidden_file_date(install_date)
            if _get_db_date() == 0: _set_db_date(install_date)
            
        current_time = int(time.time())
        days_used = int((current_time - install_date) / 86400)
        
        if days_used >= TRIAL_DAYS:
            return {"active": False, "days_used": days_used, "days_remaining": 0, "expired": True}
        else:
            return {"active": True, "days_used": days_used, "days_remaining": TRIAL_DAYS - days_used, "expired": False}
    except Exception:
        return {"active": False, "days_used": TRIAL_DAYS, "days_remaining": 0, "expired": True}
