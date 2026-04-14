import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("email_sender")


def _send_email(to_email: str, subject: str, html: str, text: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


# ---------------- AUTH EMAILS ----------------

async def send_verification_email(
    to_email: str,
    verification_link: str,
    user_name: Optional[str] = "User"
):
    subject = "Verify your account"

    html = f"""
    <h2>Hello {user_name},</h2>
    <p>Please verify your account:</p>
    <a href="{verification_link}">Verify Email</a>
    """

    text = f"Verify your account: {verification_link}"

    _send_email(to_email, subject, html, text)


async def send_password_reset_otp(
    to_email: str,
    otp: str,
    user_name: Optional[str] = "User"
):
    subject = "Password Reset OTP"

    html = f"""
    <h2>Hello {user_name},</h2>
    <p>Your OTP is:</p>
    <h1>{otp}</h1>
    <p>Valid for 10 minutes.</p>
    """

    text = f"Your OTP is {otp} (valid for 10 minutes)"

    _send_email(to_email, subject, html, text)
