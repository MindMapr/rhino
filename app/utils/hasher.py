
# Hasher class to hash and verify passwords using bcrypt
# from fastapitutorial.com
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Hasher():
    # Verify that input password matches users password
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    # Hash password with bcrypt before storing in database
    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)