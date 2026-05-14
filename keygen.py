import sys
import json
import base64
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def load_private_key(path="private_key.pem"):
    try:
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None
            )
    except FileNotFoundError:
        print(f"Erro: Chave '{path}' não encontrada.")
        print("Certifique-se de que a chave privada (private_key.pem) está no diretório atual.")
        sys.exit(1)

def generate_license_key(private_key, hardware_id, plan, days):
    issued_at = int(time.time())
    expires_at = issued_at + (days * 86400)
    
    payload = {
        "hardware_id": hardware_id,
        "plan": plan,
        "expires_at": expires_at,
        "issued_at": issued_at
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = private_key.sign(payload_str.encode('utf-8'))
    
    encoded_payload = base64.urlsafe_b64encode(payload_str.encode('utf-8')).decode('utf-8').rstrip("=")
    encoded_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip("=")
    
    return f"ZMPRO-{encoded_payload}.{encoded_signature}"

def main():
    print("=== ZapManager Pro v4.0 - Key Generator ===")
    
    try:
        hw_id = input("Hardware ID: ").strip()
        if not hw_id:
            print("Erro: Hardware ID é obrigatório.")
            sys.exit(1)
            
        days_input = input("Days valid [365]: ").strip()
        days = int(days_input) if days_input else 365
        
        plan_input = input("Plan [pro]: ").strip()
        plan = plan_input if plan_input else "pro"
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(0)
    except EOFError:
        print("Erro: EOF atingido.")
        sys.exit(1)
        
    priv_key = load_private_key()
    
    key = generate_license_key(priv_key, hw_id, plan, days)
    
    print(f"\n✅ License Key:\n{key}")

if __name__ == "__main__":
    main()
