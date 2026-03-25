import jwt
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError

from app.main import limiter
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import UserCreate, Token, UserInDB
from app.api.dependencies import get_user_service
from app.services.user_service import UserService


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=dict,
    summary="Register a new user",
    description="Create a new user account. The username must be unique and the password will be hashed.",
    response_description="Success message",
    responses={
        400: {"description": "Username already exists or validation error"},
        422: {"description": "Validation error (e.g., invalid email format)"},
    },
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    """
    Register a new user.
    """
    created_user = await user_service.create_user(user)
    logger.info(f"User registered: {created_user.username}")
    return {"message": "User created successfully"}


@router.post(
    "/token",
    response_model=Token,
    summary="Login and obtain access token",
    description="Authenticate with username and password to receive a JWT access token. Use this token in the Authorization header as 'Bearer {token}'.",
    response_description="Access token and token type",
    responses={
        401: {
            "description": "Incorrect username or password",
            "headers": {
                "WWW-Authenticate": {
                    "description": "Bearer authentication scheme",
                    "schema": {"type": "string"}
                }
            }
        }
    },
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    """
    Authenticate and return an access token.
    """
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = user_service.create_access_token(user)
    return {"access_token": access_token, "token_type": "bearer"}

