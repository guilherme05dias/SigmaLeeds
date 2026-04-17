import base64
import json
import argparse
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def generate_key_pair(private_key_path="private_key.pem"):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(private_key_path, "wb") as f:
        f.write(private_bytes)
        
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    print(f"Chave privada salva em: {private_key_path}")
    print("CHAVE PÚBLICA (coloque em validator.py):")
    print(public_bytes.decode('utf-8'))
    return private_key

def load_private_key(path="private_key.pem"):
    try:
        with open(path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
            return private_key
    except FileNotFoundError:
        print(f"Erro: Chave {path} não encontrada. Gere uma nova chave primeiro com --generate-keys.")
        return None

def generate_key(private_key, plan, days, max_machines):
    issued_at = int(time.time())
    expires_at = issued_at + (days * 86400)
    
    payload = {
        "plan": plan,
        "expires_at": expires_at,
        "max_machines": max_machines,
        "issued_at": issued_at
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = private_key.sign(payload_str.encode('utf-8'))
    
    encoded_payload = base64.urlsafe_b64encode(payload_str.encode('utf-8')).decode('utf-8').rstrip("=")
    encoded_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip("=")
    
    license_key = f"ZMPRO-{encoded_payload}.{encoded_signature}"
    return license_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZapManager Pro Keygen")
    parser.add_argument("--generate-keys", action="store_true", help="Gera um novo par de chaves Ed25519")
    parser.add_argument("--plan", choices=["starter", "pro", "agency"], help="Plano da licença")
    parser.add_argument("--days", type=int, default=365, help="Dias de validade")
    parser.add_argument("--machines", type=int, default=1, help="Máquinas permitidas")
    
    args = parser.parse_args()
    
    if args.generate_keys:
        generate_key_pair()
    elif args.plan:
        priv_key = load_private_key()
        if priv_key:
            key = generate_key(priv_key, args.plan, args.days, args.machines)
            print(f"\nLicense Key gerada com sucesso!\n{'-'*40}\n{key}\n{'-'*40}")
    else:
        parser.print_help()
