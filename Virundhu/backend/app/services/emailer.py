"""Send email over SMTP. With no SMTP_HOST set, emails are written to the log instead."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to: list[str],
    subject: str,
    text: str,
    html: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    """Send one email to several recipients. Returns True when sent (or logged in development)."""
    recipients = sorted({r.strip().lower() for r in to if r and "@" in r})
    if not recipients:
        return False
    if not settings.SMTP_HOST:
        files = ", ".join(f[0] for f in attachments or [])
        logger.info("EMAIL (not sent, SMTP_HOST is empty) to=%s subject=%s %s\n%s", recipients, subject, files, text)
        return True
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    for filename, data, mime in attachments or []:
        main, _, sub = mime.partition("/")
        msg.add_attachment(data, maintype=main, subtype=sub, filename=filename)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Email to %s failed", recipients)
        return False
