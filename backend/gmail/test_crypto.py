import pytest
import os
import base64
from backend.gmail.crypto import encrypt_secret, decrypt_secret

@pytest.fixture
def master_key():
    return base64.b64encode(os.urandom(32)).decode('utf-8')

def test_round_trip(master_key):
    secret = "my_super_secret_refresh_token_123!"
    enc_refresh_token, dek_wrapped = encrypt_secret(secret, master_key)
    
    assert enc_refresh_token != secret
    assert dek_wrapped != secret
    
    decrypted = decrypt_secret(enc_refresh_token, dek_wrapped, master_key)
    assert decrypted == secret

def test_wrong_master_key(master_key):
    secret = "test"
    enc_refresh_token, dek_wrapped = encrypt_secret(secret, master_key)
    
    wrong_key = base64.b64encode(os.urandom(32)).decode('utf-8')
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_secret(enc_refresh_token, dek_wrapped, wrong_key)

def test_tamper_detection(master_key):
    secret = "test"
    enc_refresh_token, dek_wrapped = encrypt_secret(secret, master_key)
    
    # Tamper with the ciphertext
    tampered_b64 = list(enc_refresh_token)
    tampered_b64[15] = 'A' if tampered_b64[15] != 'A' else 'B'
    tampered_refresh_token = "".join(tampered_b64)
    
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_secret(tampered_refresh_token, dek_wrapped, master_key)

def test_invalid_master_key_length():
    bad_key = base64.b64encode(os.urandom(16)).decode('utf-8')
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        encrypt_secret("test", bad_key)
