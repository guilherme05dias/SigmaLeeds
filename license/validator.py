import base64
import json
import time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

PUBLIC_KEY_PATH = Path(__file__).parent / "public_key.pem"

def get_public_key():
    pem_bytes = PUBLIC_KEY_PATH.read_bytes()
    return serialization.load_pem_public_key(pem_bytes)

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

        # Hardware binding — skip if key has no hardware_id (backward compat)
        payload_hwid = payload.get("hardware_id", "")
        if payload_hwid:
            from license.hardware import get_hardware_id
            current_hwid = get_hardware_id()
            if payload_hwid != current_hwid:
                result["error_message"] = "Licença vinculada a outro dispositivo"
                return result

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
