from cryptography.hazmat.primitives import hashes
import hashlib


def hash_message(message: str) -> str:
    digest = hashlib.sha256(message).hexdigest()
    return digest