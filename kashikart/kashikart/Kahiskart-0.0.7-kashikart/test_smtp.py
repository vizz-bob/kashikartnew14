import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
from datetime import datetime
from app.core.config import settings


def resolve_recipient() -> str:
    """
    Determine which email to send to:
      1) CLI arg: python test_smtp.py recipient@example.com
      2) Env var: TEST_RECIPIENT or RECIPIENT_EMAIL
      3) Fallback: settings.SMTP_USER (self-send)
    """
    if len(sys.argv) > 1 and "@" in sys.argv[1]:
        return sys.argv[1]
    for var in ("TEST_RECIPIENT", "RECIPIENT_EMAIL"):
        val = os.getenv(var)
        if val and "@" in val:
            return val
    return settings.SMTP_USER


def test_smtp():
    """Test SMTP connection and send test email to a user-provided address."""
    recipient = resolve_recipient()
    try:
        print(f"Testing SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        print(f"From: {settings.SMTP_FROM_EMAIL}")
        print(f"To:   {recipient}")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "SMTP Test - Tender Intel"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = recipient

        text = f"SMTP test successful! Server connected and authenticated at {datetime.now()}."
        html = f"""
        <h2>✅ SMTP Test Successful!</h2>
        <p>Server: <strong>{settings.SMTP_HOST}</strong>:<strong>{settings.SMTP_PORT}</strong></p>
        <p>Recipient: <strong>{recipient}</strong></p>
        <p>Timestamp: <strong>{datetime.now()}</strong></p>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        print("✅ Email sent successfully!")
        return True

    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_smtp()
