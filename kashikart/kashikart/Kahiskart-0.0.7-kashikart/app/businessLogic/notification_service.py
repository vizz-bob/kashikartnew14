from typing import List
import logging
from datetime import datetime, date, timedelta

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationChannel
from app.models.tender import Tender
from app.models.keyword import Keyword
from app.models.user import User
from app.models.notification_settings import NotificationSettings as NotificationSettingsModel
from app.notifications.email import EmailNotificationService
from app.notifications.desktop import DesktopNotificationService
from app.core.config import settings
from app.core.realtime import push_notification


logger = logging.getLogger(__name__)


# Central place for module names
MODULES = {
    "DASHBOARD": "dashboard",
    "TENDERS": "tenders",
    "KEYWORDS": "keywords",
    "SYSTEM": "system-logs",
}


class NotificationService:
    def __init__(self, db: AsyncSession = None):
        self.db = db

    async def notify_new_tender(self, tender: Tender):
        await self.send_new_tender_notification(self.db, tender)

    def send_system_notification(self, title: str, message: str):
        """
        Lightweight helper for scheduler/system events.
        Uses desktop notifications only (no DB dependency).
        """
        try:
            DesktopNotificationService().send_notification(title=title, message=message)
        except Exception as e:
            logger.error(f"System notification failed: {e}")

    # --------------------------------------------------
    # ADMIN ERROR PIPE
    # --------------------------------------------------
    @staticmethod
    async def _notify_admins_of_error(
        db: AsyncSession,
        title: str,
        message: str
    ):
        """
        Create SYSTEM_ERROR notifications for all active superusers.
        Keeps failures contained so it never breaks the caller flow.
        """
        try:
            result = await db.execute(
                select(User).where(
                    User.is_active == True,
                    User.is_superuser == True,
                )
            )
            admins = result.scalars().all()

            if not admins:
                return

            for admin in admins:
                admin_notification = Notification(
                    user_id=admin.id,
                    module=MODULES["SYSTEM"],
                    type=NotificationType.SYSTEM_ERROR,
                    channel=NotificationChannel.DESKTOP,
                    title=title[:255],
                    message=message,
                )
                db.add(admin_notification)

            await db.flush()
        except Exception as inner_ex:
            # Last-resort log so we don't mask the original caller
            logger.error(f"Failed to notify admins: {inner_ex}")

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------
    @staticmethod
    async def _get_user_settings_map(
        db: AsyncSession,
        user_ids: List[int]
    ) -> dict:
        """
        Fetch notification settings for a list of users as a dict[user_id] = settings.
        """
        if not user_ids:
            return {}

        result = await db.execute(
            select(NotificationSettingsModel).where(
                NotificationSettingsModel.user_id.in_(user_ids)
            )
        )
        settings_list = result.scalars().all()
        return {s.user_id: s for s in settings_list}

    @staticmethod
    def _build_recipient_list(user: User, settings_obj: NotificationSettingsModel) -> List[str]:
        """
        Combine the primary user email with additional recipients from settings.
        """
        recipients = []

        if settings_obj:
            if settings_obj.enable_email:
                if user.email:
                    recipients.append(user.email)
                if settings_obj.email_recipients:
                    recipients.extend(settings_obj.email_recipients)
        else:
            # fallback to user email if settings are missing
            if user.email:
                recipients.append(user.email)

        # deduplicate while preserving order
        seen = set()
        unique = []
        for r in recipients:
            if not r:
                continue
            key = r.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(r)
        return unique

    # --------------------------------------------------
    # KEYWORD MATCH
    # --------------------------------------------------
    @staticmethod
    async def send_keyword_match_notification(
        db: AsyncSession,
        tender: Tender,
        matched_keywords: List[Keyword]
    ):

        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        settings_map = await NotificationService._get_user_settings_map(
            db, [u.id for u in users]
        )

        email_service = EmailNotificationService()
        desktop_service = DesktopNotificationService()

        for user in users:

            deadline = (
                tender.deadline_date
                if tender.deadline_date else None
            )

            deadline_str = deadline.strftime("%Y-%m-%d") if deadline else "N/A"

            notification = Notification(
                user_id=user.id,
                tender_id=tender.id,

                #  MODULE
                module=MODULES["TENDERS"],

                type=NotificationType.KEYWORD_MATCH,
                channel=NotificationChannel.BOTH,

                title=f"New Tender Match: {tender.title[:50]}...",
                message=(
                    f"Matched keywords: "
                    f"{', '.join([k.keyword for k in matched_keywords[:3]])}. "
                    f"Agency: {tender.agency_name or 'N/A'}. "
                    f"Deadline: {deadline_str}"
                )
            )

            db.add(notification)
            await db.flush()

            # EMAIL
            recipients = NotificationService._build_recipient_list(
                user, settings_map.get(user.id)
            )

            if settings.ENABLE_EMAIL_NOTIFICATIONS and recipients:
                try:
                    await email_service.send_new_tender_notification(
                        tender=tender,
                        matched_keywords=matched_keywords,
                        recipients=recipients
                    )
                    notification.email_sent = True

                except Exception as e:
                    logger.error(f"Email failed: {e}")
                    notification.error_message = str(e)
                    await NotificationService._notify_admins_of_error(
                        db,
                        title="Keyword notification email failed",
                        message=f"Tender {tender.reference_id}: {e}"
                    )

            # DESKTOP
            if settings.ENABLE_DESKTOP_NOTIFICATIONS:
                try:
                    desktop_service.send_notification(
                        title=notification.title,
                        message=notification.message
                    )
                    notification.desktop_sent = True

                except Exception as e:
                    logger.error(f"Desktop failed: {e}")
                    notification.error_message = str(e)
                    await NotificationService._notify_admins_of_error(
                        db,
                        title="Keyword notification desktop failed",
                        message=f"Tender {tender.reference_id}: {e}"
                    )

            # FINAL STATUS
            notification.is_sent = (
                notification.email_sent or notification.desktop_sent
            )

            if notification.is_sent:
                notification.sent_at = datetime.utcnow()
                # Push live to connected clients (websocket)
                await push_notification({
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "module": notification.module,
                    "type": notification.type.value if hasattr(notification.type, "value") else str(notification.type),
                    "tender_id": notification.tender_id,
                    "created_at": notification.created_at.isoformat() + "Z" if notification.created_at else datetime.utcnow().isoformat() + "Z"
                })

        await db.flush()

        logger.info(
            f"Keyword notifications sent for tender {tender.reference_id}"
        )

    # --------------------------------------------------
    # NEW TENDER
    # --------------------------------------------------
    @staticmethod
    async def send_new_tender_notification(
        db: AsyncSession,
        tender: Tender
    ):

        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        settings_map = await NotificationService._get_user_settings_map(
            db,
            [u.id for u in users]
        )

        email_service = EmailNotificationService()
        desktop_service = DesktopNotificationService()

        for user in users:

            user_settings = settings_map.get(user.id)

            notification = Notification(
                user_id=user.id,
                tender_id=tender.id,

                #  MODULE
                module=MODULES["DASHBOARD"],

                type=NotificationType.NEW_TENDER,
                channel=NotificationChannel.BOTH,

                title=f"New Tender Published: {tender.title[:50]}...",
                message=(
                    f"Agency: {tender.agency_name or 'N/A'}. "
                    f"Published: "
                    f"{tender.published_date.strftime('%Y-%m-%d') if tender.published_date else 'N/A'}"
                )
            )

            db.add(notification)

            await db.flush()

            # EMAIL
            recipients = NotificationService._build_recipient_list(user, user_settings)

            if settings.ENABLE_EMAIL_NOTIFICATIONS and recipients:
                try:
                    await email_service.send_new_tender_notification(
                        tender=tender,
                        matched_keywords=[],
                        recipients=recipients
                    )
                    notification.email_sent = True
                except Exception as e:
                    logger.error(f"New tender email failed: {e}")
                    notification.error_message = str(e)
                    await NotificationService._notify_admins_of_error(
                        db,
                        title="New tender email failed",
                        message=f"Tender {tender.reference_id}: {e}"
                    )

            # DESKTOP
            if settings.ENABLE_DESKTOP_NOTIFICATIONS:
                try:
                    desktop_service.send_notification(
                        title=notification.title,
                        message=notification.message
                    )
                    notification.desktop_sent = True
                except Exception as e:
                    logger.error(f"New tender desktop notification failed: {e}")
                    notification.error_message = str(e)
                    await NotificationService._notify_admins_of_error(
                        db,
                        title="New tender desktop failed",
                        message=f"Tender {tender.reference_id}: {e}"
                    )

            notification.is_sent = (
                notification.email_sent or notification.desktop_sent
            )

            if notification.is_sent:
                notification.sent_at = datetime.utcnow()
                await push_notification({
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "module": notification.module,
                    "type": notification.type.value if hasattr(notification.type, "value") else str(notification.type),
                    "tender_id": notification.tender_id,
                    "created_at": notification.created_at.isoformat() + "Z" if notification.created_at else datetime.utcnow().isoformat() + "Z"
                })

        await db.flush()

    # --------------------------------------------------
    # DEADLINE ALERT
    # --------------------------------------------------
    @staticmethod
    async def send_deadline_approaching_notification(
        db: AsyncSession,
        tender: Tender,
        days_remaining: int
    ):

        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        settings_map = await NotificationService._get_user_settings_map(
            db, [u.id for u in users]
        )

        email_service = EmailNotificationService()
        desktop_service = DesktopNotificationService()

        for user in users:

            notification = Notification(
                user_id=user.id,
                tender_id=tender.id,

                #  MODULE
                module=MODULES["TENDERS"],

                type=NotificationType.DEADLINE_APPROACHING,
                channel=NotificationChannel.BOTH,

                title=f"Deadline Approaching: {tender.title[:50]}...",
                message=(
                    f"{days_remaining} days remaining. "
                    f"Deadline: {tender.deadline_date.strftime('%Y-%m-%d')}"
                )
            )

            db.add(notification)
            await db.flush()

            if days_remaining <= 7:

                # EMAIL
                recipients = NotificationService._build_recipient_list(
                    user, settings_map.get(user.id)
                )
                if settings.ENABLE_EMAIL_NOTIFICATIONS and recipients:
                    try:
                        await email_service.send_deadline_alert(
                            tender=tender,
                            recipients=recipients,
                            days_remaining=days_remaining
                        )
                        notification.email_sent = True

                    except Exception as e:
                        logger.error(f"Deadline email failed: {e}")
                        notification.error_message = str(e)
                        await NotificationService._notify_admins_of_error(
                            db,
                            title="Deadline email failed",
                            message=f"Tender {tender.reference_id}: {e}"
                        )

                # DESKTOP
                if settings.ENABLE_DESKTOP_NOTIFICATIONS:
                    try:
                        desktop_service.send_notification(
                            title=notification.title,
                            message=notification.message
                        )
                        notification.desktop_sent = True

                    except Exception as e:
                        logger.error(f"Desktop deadline failed: {e}")
                        notification.error_message = str(e)
                        await NotificationService._notify_admins_of_error(
                            db,
                            title="Deadline desktop failed",
                            message=f"Tender {tender.reference_id}: {e}"
                        )

                notification.is_sent = (
                    notification.email_sent or notification.desktop_sent
                )

            if notification.is_sent:
                notification.sent_at = datetime.utcnow()
                await push_notification({
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "module": notification.module,
                    "type": notification.type.value if hasattr(notification.type, "value") else str(notification.type),
                    "tender_id": notification.tender_id,
                    "created_at": notification.created_at.isoformat() + "Z" if notification.created_at else datetime.utcnow().isoformat() + "Z"
                })

        await db.flush()

    # --------------------------------------------------
    # CRON JOB: DEADLINE CHECK
    # --------------------------------------------------
    @staticmethod
    async def check_approaching_deadlines(db: AsyncSession):

        today = date.today()
        deadline_7days = today + timedelta(days=7)

        result = await db.execute(
            select(Tender).where(
                Tender.deadline_date <= deadline_7days,
                Tender.deadline_date >= today,
                Tender.status != "expired",
                Tender.is_deleted == False
            )
        )

        tenders = result.scalars().all()

        for tender in tenders:

            days_remaining = (tender.deadline_date - today).days

            existing = await db.execute(
                select(Notification).where(
                    Notification.tender_id == tender.id,
                    Notification.type == NotificationType.DEADLINE_APPROACHING
                )
            )

            if not existing.scalars().first():

                await NotificationService.send_deadline_approaching_notification(
                    db,
                    tender,
                    days_remaining
                )

        logger.info(f"Checked {len(tenders)} tenders for deadlines")
