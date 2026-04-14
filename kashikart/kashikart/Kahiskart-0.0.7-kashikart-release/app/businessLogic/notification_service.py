from typing import List
import logging
from datetime import datetime, date, timedelta

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationChannel
from app.models.tender import Tender
from app.models.keyword import Keyword
from app.models.user import User
from app.notifications.email import EmailNotificationService
from app.notifications.desktop import DesktopNotificationService
from app.core.config import settings


logger = logging.getLogger(__name__)


# Central place for module names
MODULES = {
    "DASHBOARD": "dashboard",
    "TENDERS": "tenders",
    "KEYWORDS": "keywords",
    "SYSTEM": "system-logs",
}


class NotificationService:

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

        email_service = EmailNotificationService()
        desktop_service = DesktopNotificationService()

        for user in users:

            deadline = (
                datetime.strptime(tender.deadline_date, "%Y-%m-%d")
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
            if settings.ENABLE_EMAIL_NOTIFICATIONS:
                try:
                    await email_service.send_new_tender_notification(
                        tender=tender,
                        matched_keywords=matched_keywords,
                        recipients=[user.email]
                    )
                    notification.email_sent = True

                except Exception as e:
                    logger.error(f"Email failed: {e}")
                    notification.error_message = str(e)

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

            # FINAL STATUS
            notification.is_sent = (
                notification.email_sent or notification.desktop_sent
            )

            if notification.is_sent:
                notification.sent_at = datetime.utcnow()

        await db.commit()

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

        for user in users:

            notification = Notification(
                user_id=user.id,
                tender_id=tender.id,

                #  MODULE
                module=MODULES["DASHBOARD"],

                type=NotificationType.NEW_TENDER,
                channel=NotificationChannel.EMAIL,

                title=f"New Tender Published: {tender.title[:50]}...",
                message=(
                    f"Agency: {tender.agency_name or 'N/A'}. "
                    f"Published: "
                    f"{tender.published_date.strftime('%Y-%m-%d') if tender.published_date else 'N/A'}"
                )
            )

            db.add(notification)

        await db.commit()

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
                if settings.ENABLE_EMAIL_NOTIFICATIONS:
                    try:
                        await email_service.send_deadline_alert(
                            tender=tender,
                            recipients=[user.email],
                            days_remaining=days_remaining
                        )
                        notification.email_sent = True

                    except Exception as e:
                        logger.error(f"Deadline email failed: {e}")
                        notification.error_message = str(e)

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

                notification.is_sent = (
                    notification.email_sent or notification.desktop_sent
                )

                if notification.is_sent:
                    notification.sent_at = datetime.utcnow()

        await db.commit()

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
