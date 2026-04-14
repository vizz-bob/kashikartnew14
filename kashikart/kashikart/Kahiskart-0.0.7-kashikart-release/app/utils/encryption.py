from cryptography.fernet import Fernet
from app.core.config import settings


class EncryptionService:
    def __init__(self):
        key = settings.ENCRYPTION_KEY.encode()

        # if len(key) != 32:
        #     raise ValueError("ENCRYPTION_KEY must be exactly 32 bytes")

        # Fernet requires base64-encoded 32-byte key
        # self.cipher = Fernet(Fernet.generate_key())
        self.cipher = Fernet(key) 

    def encrypt(self, text: str) -> str:
        if not text:
            return ""
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, text: str) -> str:
        if not text:
            return ""
        return self.cipher.decrypt(text.encode()).decode()


#  SINGLE INSTANCE
encryption_service = EncryptionService()


#  SIMPLE FUNCTION API (THIS FIXES ALL ERRORS)
def encrypt_password(text: str) -> str:
    return encryption_service.encrypt(text)


def decrypt_password(text: str) -> str:
    return encryption_service.decrypt(text)


__all__ = [
    "encrypt_password",
    "decrypt_password",
    "encryption_service",
    "EncryptionService",
]
