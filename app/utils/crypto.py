import hashlib

def hash_token(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
