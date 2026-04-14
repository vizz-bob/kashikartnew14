from plyer import notification
from app.utils.logger import setup_logger

logger = setup_logger("desktop_notification")

class DesktopNotificationService:
    """Service for sending desktop notifications"""

    def __init__(self):
        self.app_name = "Tender Intelligence System"
        self.app_icon = None  # Path to icon file if available

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
        try:
            notification.notify(
                title=title,
                message=message,
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