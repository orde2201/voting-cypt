# hashing.py
import hashlib

def hash_message(message: str) -> str:
    """
    Hash a message using SHA-256.
    Args:
        message: String message to hash
    Returns:
        Hexadecimal hash string
    """
    # Pastikan message adalah string
    if not isinstance(message, str):
        message = str(message)
    
    # Encode ke bytes dan hash
    return hashlib.sha256(message.encode('utf-8')).hexdigest()