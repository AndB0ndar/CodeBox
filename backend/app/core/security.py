from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The hashed password (e.g., from database).

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a secure hash of a plain text password.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password string (bcrypt hash).
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with expiration.

    The token will include the provided data and an 'exp' claim set to the
    expiration time. If no `expires_delta` is provided, the expiration is
    taken from `settings.ACCESS_TOKEN_EXPIRE_MINUTES`.

    Args:
        data: A dictionary of claims to encode into the token.
        expires_delta: Optional timedelta for token expiration.
                       If not provided, uses the default from settings.

    Returns:
        The encoded JWT string.

    Example:
        token = create_access_token({"sub": "user_id"}, expires_delta=timedelta(minutes=30))
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

