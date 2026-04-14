from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token
)
from app.core.config import settings
from app.models.user import User
from pydantic import BaseModel, EmailStr

settings = settings()
router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str



class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None



@router.post("/login", response_model=LoginResponse)
async def login(
        login_data: LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT token.

    Args:
        login_data: Username and password
        db: Database session

    Returns:
        Access token and user info
    """
    # Find user
    query = select(User).where(User.email == login_data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Verify user and password
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return LoginResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    )


@router.post("/register")
async def register(
        register_data: RegisterRequest,
        db: AsyncSession = Depends(get_db)
):
    """
    Register new user account.

    Args:
        register_data: User registration data
        db: Database session

    Returns:
        Success message
    """

    # Check if email exists
    query = select(User).where(User.email == register_data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(
        email=register_data.email,
        full_name=register_data.full_name,
        hashed_password=get_password_hash(register_data.password),
        is_active=True,
        is_superuser=False
    )

    db.add(user)
    await db.commit()

    return {
        "message": "User registered successfully",
        "username": user.email
    }


@router.post("/logout")
async def logout():
    """
    Logout user (client should discard token).
    """
    return {"message": "Logged out successfully"}