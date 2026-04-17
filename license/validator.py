import base64
import json
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAi4r0+k3Z5s6R0T7Y2nU8n3Z1l8t/Bv6n6xNl2z2jUg0=
-----END PUBLIC KEY-----"""

def get_public_key():
    return serialization.load_pem_public_key(PUBLIC_KEY_PEM)

def validate_key(key_string: str) -> dict:
    result = {
        "valid": False,
        "plan": None,
        "expires_at": None,
        "days_remaining": 0,
        "error_message": ""
    }
    
    try:
        if not key_string.startswith("ZMPRO-"):
            result["error_message"] = "Licença corrompida"
            return result
            
        key_body = key_string[6:]
        if "." not in key_body:
            result["error_message"] = "Licença corrompida"
            return result
            
        encoded_payload, encoded_signature = key_body.split(".", 1)
        
        # Add padding back
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (4 - len(encoded_payload) % 4))
        signature_bytes = base64.urlsafe_b64decode(encoded_signature + "=" * (4 - len(encoded_signature) % 4))
        
        public_key = get_public_key()
        try:
            public_key.verify(signature_bytes, payload_bytes)
        except InvalidSignature:
            result["error_message"] = "Licença inválida"
            return result
            
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        current_time = int(time.time())
        expires_at = payload.get("expires_at", 0)
        
        if current_time > expires_at:
            result["error_message"] = "Licença expirada"
            return result
            
        result["valid"] = True
        result["plan"] = payload.get("plan")
        result["expires_at"] = expires_at
        result["days_remaining"] = max(0, int((expires_at - current_time) / 86400))
        return result
        
    except Exception:
        result["error_message"] = "Licença corrompida"
        return result
