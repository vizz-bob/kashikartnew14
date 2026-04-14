from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
from fastapi import Request
from app.models.login_history import LoginHistory
import secrets
import random
import string
from app.models.refresh_token import RefreshToken
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    hash_refresh_token,
    get_refresh_token_expiry,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    TokenWithRefresh,
    RefreshTokenRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
    UpdateEmailRequest,
    UpdatePasswordRequest,
    UserUpdateRequest,
)

from app.notifications.email_sender import (
    send_verification_email, send_password_reset_otp
)

from app.utils.file_upload import (
    validate_image,
    save_upload_file,
    delete_old_profile_picture,
    build_profile_url
)

from fastapi import UploadFile, File

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter()

# Email validation - block temporary emails
TEMP_EMAIL_DOMAINS = [
    "tempmail.com", "throwaway.email", "guerrillamail.com", "10minutemail.com",
    "mailinator.com", "sharklasers.com", "maildrop.cc", "yopmail.com",
    "temp-mail.org", "fakeinbox.com", "trashmail.com"
]


def is_valid_email(email: str) -> bool:
    domain = email.split("@")[1].lower()
    return domain not in TEMP_EMAIL_DOMAINS


def generate_verification_token() -> str:

    return secrets.token_urlsafe(32)


def generate_otp() -> str:

    return ''.join(random.choices(string.digits, k=6))


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")

    if email is None:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    if not is_valid_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Temporary or disposable email addresses are not allowed"
        )

    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    verification_token = generate_verification_token()
    token_expires = datetime.utcnow() + timedelta(hours=24)

    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=token_expires,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    background_tasks.add_task(
        send_verification_email,
        to_email=user.email,
        verification_link=verification_link,
        user_name=user.full_name or "User"
    )

    return {"message": "Registration successful. Verify your email."}



@router.post("/verify-email", response_model=TokenWithRefresh)
async def verify_email(
    verify_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.verification_token == verify_data.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    if user.verification_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )

    # Verify user
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Create refresh token
    raw_refresh_token = create_refresh_token()
    hashed_refresh_token = hash_refresh_token(raw_refresh_token)

    refresh_token = RefreshToken(
        token_hash=hashed_refresh_token,
        user_id=user.id,
        expires_at=get_refresh_token_expiry(),
    )

    db.add(refresh_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "last_login": user.last_login,
        },
    }



@router.post("/resend-verification", response_model=dict)
async def resend_verification(
        request: ResendVerificationRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent."}

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Generate new token
    verification_token = generate_verification_token()
    token_expires = datetime.utcnow() + timedelta(hours=24)

    user.verification_token = verification_token
    user.verification_token_expires = token_expires
    await db.commit()

    # Send email
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    background_tasks.add_task(
        send_verification_email,
        to_email=user.email,
        verification_link=verification_link,
        user_name=user.full_name or "User"
    )

    return {"message": "Verification email sent. Please check your inbox."}


@router.post("/login", response_model=TokenWithRefresh)
async def login(
        login_data: UserLogin,
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    ip = request.client.host
    device = request.headers.get("user-agent")

    #  User not found or wrong password
    if not user or not verify_password(login_data.password, user.hashed_password):

        if user:
            db.add(
                LoginHistory(
                    user_id=user.id,
                    ip_address=ip,
                    user_agent=device,
                    status="failed"
                )
            )
            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    #  Blocked by admin
    if user.is_blocked:
        raise HTTPException(
            status_code=403,
            detail="Your account is blocked by admin"
        )

    #  Not verified
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email first"
        )

    #  Inactive
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive"
        )

    #  Success login
    user.last_login = datetime.utcnow()

    db.add(
        LoginHistory(
            user_id=user.id,
            ip_address=ip,
            user_agent=device,
            status="success"
        )
    )

    # Create token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    raw_refresh_token = create_refresh_token()
    hashed_refresh_token = hash_refresh_token(raw_refresh_token)

    refresh_token = RefreshToken(
        token_hash=hashed_refresh_token,
        user_id=user.id,
        expires_at=get_refresh_token_expiry(),
    )

    db.add(refresh_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
        request: ForgotPasswordRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, an OTP has been sent."}

    # Generate OTP
    otp = generate_otp()
    otp_expires = datetime.utcnow() + timedelta(minutes=10)

    user.reset_otp = otp
    user.reset_otp_expires = otp_expires
    user.reset_otp_attempts = 0
    await db.commit()

    # Send OTP via email
    background_tasks.add_task(
        send_password_reset_otp,
        to_email=user.email,
        otp=otp,
        user_name=user.full_name or "User"
    )

    return {
        "message": "OTP sent to your email. Valid for 10 minutes.",
        "email": user.email
    }


@router.post("/reset-password", response_model=dict)
async def reset_password(
        reset_data: ResetPasswordRequest,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == reset_data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP"
        )

    if not user.reset_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP requested. Please request a password reset first."
        )

    # Check OTP attempts
    if user.reset_otp_attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please request a new OTP."
        )

    # Check if OTP expired
    if user.reset_otp_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    # Verify OTP
    if user.reset_otp != reset_data.otp:
        user.reset_otp_attempts += 1
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {5 - user.reset_otp_attempts} attempts remaining."
        )

    # Reset password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_otp = None
    user.reset_otp_expires = None
    user.reset_otp_attempts = 0
    await db.commit()

    return {"message": "Password reset successful. You can now login with your new password."}


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    user_data = UserResponse.model_validate(current_user)


    user_data.profile_picture = build_profile_url(
        current_user.profile_picture
    )

    return user_data



@router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_current_user_info(
        user_update: UserUpdateRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    """Update user's full name and phone number"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    # Update only the fields that were provided
    if user_update.full_name is not None:
        if len(user_update.full_name.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Full name cannot be empty"
            )
        current_user.full_name = user_update.full_name.strip()

    if user_update.phone_number is not None:
        # Handle empty string as None
        if user_update.phone_number and len(user_update.phone_number.strip()) > 0:
            current_user.phone_number = user_update.phone_number.strip()
        else:
            current_user.phone_number = None

    try:
        await db.commit()
        await db.refresh(current_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user information"
        )

    return UserResponse.model_validate(current_user)

@router.post("/me/profile-picture", response_model=UserResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    # IMPORTANT: await async functions
    await validate_image(file)

    try:
        # Delete old image
        if current_user.profile_picture:
            delete_old_profile_picture(current_user.profile_picture)

        # Save new image
        filename = await save_upload_file(file, current_user.id)

        # Update DB
        current_user.profile_picture = filename

        await db.commit()
        await db.refresh(current_user)

        user_data = UserResponse.model_validate(current_user)

        user_data.profile_picture = build_profile_url(
            current_user.profile_picture
        )

        return user_data


    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload profile picture: {str(e)}"
        )


@router.delete("/me/profile-picture", response_model=UserResponse)
async def delete_profile_picture(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    if not current_user:
        raise HTTPException(401, "Unauthorized")

    if not current_user.profile_picture:
        raise HTTPException(404, "No profile picture")

    try:

        delete_old_profile_picture(current_user.profile_picture)

        current_user.profile_picture = None

        await db.commit()
        await db.refresh(current_user)

        user_data = UserResponse.model_validate(current_user)

        user_data.profile_picture = build_profile_url(
            current_user.profile_picture
        )

        return user_data


    except Exception as e:

        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete profile picture: {str(e)}"
        )


@router.post("/update-email", response_model=dict)
async def update_email(
    data: UpdateEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Check if new email is same as current
    if data.new_email == current_user.email:
        raise HTTPException(status_code=400, detail="New email is the same as current email")

    # Check email uniqueness
    result = await db.execute(
        select(User).where(User.email == data.new_email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already in use")

    # Validate domain
    if not is_valid_email(data.new_email):
        raise HTTPException(status_code=400, detail="Temporary emails not allowed")

    # Generate verification token
    token = generate_verification_token()
    expires = datetime.utcnow() + timedelta(hours=24)

    current_user.email = data.new_email
    current_user.is_verified = False
    current_user.verification_token = token
    current_user.verification_token_expires = expires
    await db.commit()

    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    background_tasks.add_task(
        send_verification_email,
        to_email=data.new_email,
        verification_link=verification_link,
        user_name=current_user.full_name or "User",
    )

    return {
        "message": "Email updated. Please verify your new email address."
    }


@router.post("/update-password", response_model=dict)
async def update_password(
    data: UpdatePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify current password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid current password")

    # Prevent password reuse
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    # Update password
    current_user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"message": "Password updated successfully"}

@router.post("/refresh-token", response_model=TokenWithRefresh)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    hashed = hash_refresh_token(data.refresh_token)

    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash == hashed,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    token_entry = result.scalar_one_or_none()

    if not token_entry:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    #  DO NOT use token_entry.user
    result = await db.execute(
        select(User).where(User.id == token_entry.user_id)
    )
    user = result.scalar_one()

    # Rotate refresh token
    await db.delete(token_entry)

    new_raw_refresh = create_refresh_token()
    new_hashed_refresh = hash_refresh_token(new_raw_refresh)

    db.add(
        RefreshToken(
            token_hash=new_hashed_refresh,
            user_id=user.id,
            expires_at=get_refresh_token_expiry(),
        )
    )

    await db.commit()

    return {
        "access_token": create_access_token({"sub": user.email}),
        "refresh_token": new_raw_refresh,
        "token_type": "bearer",
        "user": user,
    }

@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    # Hash incoming refresh token
    token_hash = hash_refresh_token(data.refresh_token)

    # Find refresh token in DB
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False
        )
    )
    refresh_token = result.scalar_one_or_none()

    if refresh_token:
        refresh_token.revoked = True
        await db.commit()

    # Always return success (do not reveal token state)
    return {"message": "Logged out successfully"}
