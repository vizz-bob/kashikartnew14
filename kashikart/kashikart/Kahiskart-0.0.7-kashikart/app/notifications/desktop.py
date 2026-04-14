from plyer import notification
from app.utils.logger import setup_logger

logger = setup_logger("desktop_notification")

class DesktopNotificationService:
    """Service for sending desktop notifications"""

    def __init__(self):
        # Keep app name short to satisfy Windows balloon limits (<=64 chars)
        self.app_name = "Tender Intel"
        self.app_icon = None  # Path to icon file if available
        # Windows Shell_NotifyIconW has a 64‑char limit on title / tooltip; keep headroom
        self.max_title_len = 60
        self.max_message_len = 180

    def send_notification(
            self,
            title: str,
            message: str,
            tender_url: str = None,
            timeout: int = 10
    ):
        """
        Send desktop notification.

        Args:
            title: Notification title
            message: Notification message
            tender_url: Optional URL to open on click
            timeout: Notification display duration in seconds
        """
        # Hard trim to avoid Shell_NotifyIconW length errors on Windows
        safe_title = (title or "").strip()
        if len(safe_title) > self.max_title_len:
            safe_title = safe_title[: self.max_title_len - 1] + "…"

        safe_message = (message or "").strip()
        if len(safe_message) > self.max_message_len:
            safe_message = safe_message[: self.max_message_len - 1] + "…"

        try:
            notification.notify(
                title=safe_title,
                message=safe_message,
                app_name=self.app_name,
                app_icon=self.app_icon,
                timeout=timeout
            )

            logger.info(f"Desktop notification sent: {title}")

        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")

    def send_tender_alert(self, tender_title: str, keywords: str):
        """Send tender match alert"""
        self.send_notification(
            title="🎯 New Tender Match!",
            message=f"{tender_title}\nKeywords: {keywords}",
            timeout=15
        )

    def send_deadline_warning(self, tender_title: str, days_remaining: int):
        """Send deadline warning"""
        self.send_notification(
            title=f"⏰ Deadline Alert - {days_remaining} days",
            message=tender_title,
            timeout=10
        )

    def send_system_alert(self, message: str):
        """Send system-level alert"""
        self.send_notification(
            title="System Alert",
            message=message,
            timeout=10
        )

def send_desktop_notification(
    title: str,
    message: str,
    timeout: int = 10
):
    """
    Wrapper function used across the app
    """
    service = DesktopNotificationService()
    service.send_notification(
        title=title,
        message=message,
        timeout=timeout
    )
