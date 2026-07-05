from cryptography.fernet import Fernet
import os

KEY = os.getenv("FERNET_KEY", "").encode()
cipher = Fernet(KEY) if KEY else None


def encrypt(text: str) -> str:
    if not cipher or not text:
        return text
    return cipher.encrypt(text.encode()).decode()


def decrypt(encrypted: str) -> str:
    if not cipher or not encrypted:
        return encrypted
    return cipher.decrypt(encrypted.encode()).decode()
