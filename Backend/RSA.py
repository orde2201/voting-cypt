from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding


class RSAEncryptor:

    def __init__(self):
        with open("public_key.pem", "rb") as f:
            self.public_key = serialization.load_pem_public_key(f.read())

        with open("private_key.pem", "rb") as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )

    # -------------------------
    # ENCRYPT
    # -------------------------
    def encrypt(self, message: str) -> bytes:
        ciphertext = self.public_key.encrypt(
            message.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext

    # -------------------------
    # DECRYPT
    # -------------------------
    def decrypt(self, ciphertext: bytes) -> str:
        plaintext = self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return plaintext.decode()