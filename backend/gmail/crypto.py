import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def _encrypt_with_key(key: bytes, plaintext: bytes) -> str:
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)
    return base64.b64encode(iv + ciphertext).decode('utf-8')

def _decrypt_with_key(key: bytes, encrypted_b64: str) -> bytes:
    try:
        data = base64.b64decode(encrypted_b64)
        iv = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(iv, ciphertext, None)
    except Exception as e:
        raise ValueError("Decryption failed or data is corrupted") from e

def encrypt_secret(plaintext: str, master_key_b64: str) -> tuple[str, str]:
    """
    Returns (enc_refresh_token, dek_wrapped)
    """
    master_key = base64.b64decode(master_key_b64)
    if len(master_key) != 32:
        raise ValueError("Master key must be exactly 32 bytes")
        
    dek = os.urandom(32)
    
    enc_refresh_token = _encrypt_with_key(dek, plaintext.encode('utf-8'))
    dek_wrapped = _encrypt_with_key(master_key, dek)
    
    return enc_refresh_token, dek_wrapped

def decrypt_secret(enc_refresh_token: str, dek_wrapped: str, master_key_b64: str) -> str:
    master_key = base64.b64decode(master_key_b64)
    if len(master_key) != 32:
        raise ValueError("Master key must be exactly 32 bytes")
        
    dek = _decrypt_with_key(master_key, dek_wrapped)
    plaintext_bytes = _decrypt_with_key(dek, enc_refresh_token)
    
    return plaintext_bytes.decode('utf-8')
