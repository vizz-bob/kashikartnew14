import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from app.core.config import settings
from app.models.tender import Tender
from app.models.keyword import Keyword
from app.utils.logger import setup_logger

logger = setup_logger("email")




class EmailNotificationService:
    """Service for sending email notifications"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        # self.smtp_from = settings.SMTP_FROM
        self.smtp_from = settings.SMTP_FROM_EMAIL
        self.smtp_tls = settings.SMTP_TLS

    async def send_new_tender_notification(
            self,
            tender: Tender,
            matched_keywords: List[Keyword],
            recipients: List[str]
    ) -> bool:
        """
        Send notification for new tender with keyword matches.

        Args:
            tender: Tender object
            matched_keywords: List of matched keywords
            recipients: List of email addresses

        Returns:
            True if sent successfully
        """
        subject = f"🎯 New Tender Match: {tender.title[:50]}..."

        # Build email body
        html_body = self._build_tender_email_html(tender, matched_keywords)
        text_body = self._build_tender_email_text(tender, matched_keywords)

        return await self._send_email(
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    async def send_deadline_alert(
            self,
            tender: Tender,
            recipients: List[str],
            days_remaining: int
    ) -> bool:
        """Send deadline reminder notification"""
        subject = f"⏰ Tender Deadline Alert: {days_remaining} days remaining"

        html_body = self._build_deadline_email_html(tender, days_remaining)
        text_body = self._build_deadline_email_text(tender, days_remaining)

        return await self._send_email(
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    async def send_batch_digest(
            self,
            tenders: List[Tender],
            recipients: List[str],
            period: str = "daily"
    ) -> bool:
        """Send digest email with multiple tenders"""
        subject = f"📊 {period.title()} Tender Digest - {len(tenders)} new matches"

        html_body = self._build_digest_email_html(tenders, period)
        text_body = self._build_digest_email_text(tenders, period)

        return await self._send_email(
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    def _build_tender_email_html(
            self,
            tender: Tender,
            keywords: List[Keyword]
    ) -> str:
        """Build HTML email body for tender notification"""
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #2563eb; color: white; padding: 20px; border-radius: 5px; }
                .content { background: #f3f4f6; padding: 20px; margin: 20px 0; border-radius: 5px; }
                .label { font-weight: bold; color: #374151; }
                .keywords { background: #dbeafe; padding: 10px; border-left: 4px solid #2563eb; margin: 10px 0; }
                .button { background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🎯 New Tender Match Found!</h2>
                </div>

                <div class="content">
                    <h3>{{ tender.title }}</h3>

                    <p><span class="label">Agency:</span> {{ tender.agency_name }}</p>
                    <p><span class="label">Reference:</span> {{ tender.reference_id }}</p>
                    <p><span class="label">Deadline:</span> {{ tender.deadline }}</p>
                    <p><span class="label">Location:</span> {{ tender.location }}</p>

                    {% if tender.description %}
                    <p><span class="label">Description:</span></p>
                    <p>{{ tender.description[:500] }}...</p>
                    {% endif %}

                    <div class="keywords">
                        <span class="label">Matched Keywords:</span>
                        {% for keyword in keywords %}
                        <span style="background: #3b82f6; color: white; padding: 4px 8px; border-radius: 3px; margin: 2px; display: inline-block;">
                            {{ keyword.keyword }}
                        </span>
                        {% endfor %}
                    </div>

                    <a href="{{ tender.source_url }}" class="button">View Tender Details</a>
                </div>

                <p style="color: #6b7280; font-size: 12px; text-align: center;">
                    Sent by Tender Intelligence System
                </p>
            </div>
        </body>
        </html>
        """)

        return template.render(tender=tender, keywords=keywords)

    def _build_tender_email_text(
            self,
            tender: Tender,
            keywords: List[Keyword]
    ) -> str:
        """Build plain text email body"""
        text = f"""
NEW TENDER MATCH FOUND!

Title: {tender.title}
Agency: {tender.agency_name}
Reference: {tender.reference_id}
Deadline: {tender.deadline}
Location: {tender.location}

Matched Keywords: {', '.join([k.keyword for k in keywords])}

View Details: {tender.source_url}

---
Sent by Tender Intelligence System
        """
        return text.strip()

    def _build_deadline_email_html(self, tender: Tender, days: int) -> str:
        """Build HTML for deadline alert"""
        # Simplified version
        return f"""
        <h2>⏰ Tender Deadline Alert</h2>
        <p><strong>{tender.title}</strong></p>
        <p>Deadline in {days} days: {tender.deadline}</p>
        <a href="{tender.source_url}">View Tender</a>
        """

    def _build_deadline_email_text(self, tender: Tender, days: int) -> str:
        """Build text for deadline alert"""
        return f"Tender Deadline Alert\n{tender.title}\nDeadline in {days} days: {tender.deadline}"

    def _build_digest_email_html(self, tenders: List[Tender], period: str) -> str:
        """Build HTML for digest email"""
        # Simplified version
        html = f"<h2>📊 {period.title()} Tender Digest</h2><p>Found {len(tenders)} new matching tenders:</p><ul>"
        for tender in tenders[:20]:  # Limit to 20
            html += f"<li><strong>{tender.title}</strong> - {tender.agency_name}</li>"
        html += "</ul>"
        return html

    def _build_digest_email_text(self, tenders: List[Tender], period: str) -> str:
        """Build text for digest email"""
        text = f"{period.title()} Tender Digest\n\nFound {len(tenders)} new matching tenders:\n\n"
        for tender in tenders[:20]:
            text += f"- {tender.title} ({tender.agency_name})\n"
        return text

    async def _send_email(
            self,
            recipients: List[str],
            subject: str,
            html_body: str,
            text_body: str
    ) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_from
            msg['To'] = ', '.join(recipients)

            # Attach parts
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

async def send_email_notification(
    tender: Tender,
    matched_keywords: List[Keyword],
    recipients: List[str]
) -> bool:
    """
    Wrapper function used across the app
    """
    service = EmailNotificationService()
    return await service.send_new_tender_notification(
        tender=tender,
        matched_keywords=matched_keywords,
        recipients=recipients
    )

