import os
import time

def setup_test_env():
    os.environ['APPDATA'] = os.path.join(os.path.dirname(__file__), '__test_appdata__')
    
setup_test_env()

import license.keygen
import license.validator
import license.manager
import license.trial
from cryptography.hazmat.primitives.asymmetric import ed25519

def test_keygen_and_validator():
    print("Testando geração de par de chaves...")
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()
    
    # Mock para não precisar editar o arquivo pra testar
    license.validator.get_public_key = lambda: pub_key
    
    print("Gerando chave do plano PRO por 10 dias...")
    key_str = license.keygen.generate_key(priv_key, "pro", 10, 1)
    print(f"Key gerada: {key_str[:30]}...")
    
    print("Validando key...")
    result = license.validator.validate_key(key_str)
    
    assert result["valid"] == True, f"Falha na validação: {result}"
    assert result["plan"] == "pro", "Plano incorreto"
    assert result["days_remaining"] == 10, "Dias restantes incorretos"
    
    print("-> OK: Validador confirmou a licença")

    print("Testando ativação e limits no manager...")
    act_res = license.manager.activate_license(key_str)
    assert act_res["valid"] == True, "Manager falhou ao ativar"
    
    limits = license.manager.get_current_plan_limits()
    assert limits["max_accounts"] == 3, "Limites errados para PRO"
    assert limits["export_xlsx"] == True, "Limites errados para PRO"
    print("-> OK: Manager retornou limites do PRO")

    if os.path.exists(license.manager.LICENSE_FILE):
        os.remove(license.manager.LICENSE_FILE)
        
def test_hardware():
    from license.hardware import get_hardware_id
    hwid = get_hardware_id()
    assert type(hwid) == str and len(hwid) == 64, "Formato do Hardware ID incorreto"
    print(f"-> OK: Hardware ID é válido e coletado!\n\t{hwid}")

def test_trial():
    # Remove temp files if exist
    if os.path.exists(license.trial.HIDDEN_FILE_PATH):
        try: os.system(f'attrib -h "{license.trial.HIDDEN_FILE_PATH}"')
        except: pass
        os.remove(license.trial.HIDDEN_FILE_PATH)
        
    res = license.trial.get_trial_status()
    print(f"-> OK: Trial executou sem quebrar. Status: {res['active']} (Restante: {res['days_remaining']})")

if __name__ == "__main__":
    print("=== TESTES DE LICENCIAMENTO ===")
    test_hardware()
    test_keygen_and_validator()
    test_trial()
    print("\nTODOS OS TESTES PASSARAM COM SUCESSO!")
