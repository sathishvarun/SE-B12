"""Email sending (SMTP) and Jinja2 template rendering.

Public API used by other modules:
    send_email(to, subject, html) -> None
    render_template(name, **context) -> str

When ``settings.SMTP_HOST`` is empty (local dev) emails are logged, not sent.
SMTP errors are logged and swallowed so a mail outage never breaks a request.
"""

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html",), default=True),
)


def render_template(name: str, **context: object) -> str:
    """Render an email template from app/templates/email/ (autoescaped).

    ``app_url`` and ``app_name`` are filled in automatically if not given.
    """
    context.setdefault("app_url", settings.FRONTEND_URL)
    context.setdefault("app_name", "Sathish CRM")
    return _env.get_template(name).render(**context)


def send_email(to: str, subject: str, html: str) -> None:
    """Send an HTML email. Logs instead of sending when SMTP_HOST is not configured."""
    if not settings.SMTP_HOST:
        logger.info("Email (SMTP not configured, not sent) to=%s subject=%r", to, subject)
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content("This email requires an HTML-capable email client.")
    message.add_alternative(html, subtype="html")

    host, port = settings.SMTP_HOST, settings.SMTP_PORT
    try:
        if port == 465:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            smtp = smtplib.SMTP(host, port, timeout=10)
        with smtp:
            if port == 587:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("Email sent to=%s subject=%r", to, subject)
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send email to=%s subject=%r", to, subject)
