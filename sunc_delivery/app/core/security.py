from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

MAX_BCRYPT_BYTES = 72


def hash_password(password: str):
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > MAX_BCRYPT_BYTES:
        raise ValueError("Password too long (max 72 bytes for bcrypt)")

    return pwd_context.hash(password)


def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)